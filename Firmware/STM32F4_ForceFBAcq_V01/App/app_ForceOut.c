/**
 * @file    outCode.c
 * @brief   三维力传感器解耦算法 - 抗基准噪声增强版（含开机5秒自动建基线）
 *
 * 说明：
 * 1. 本版本可直接替换原 outCode.c 使用；                           // 整文件替换版
 * 2. 增加输入端3点中值滤波；                                         // 去掉偶发尖峰毛刺
 * 3. 增加解耦后 Fz/Fx/Fy 二次 EMA 滤波；                             // 降低力输出抖动
 * 4. 增加开机自动更新基线功能：开机预热5秒后，若电压稳定则自动建基线； // 上电自动定零
 * 5. 在开机初始基线建立完成前，输出三维力强制为0；                    // 避免开机乱跳
 * 6. 保留正常运行中的自动基线更新逻辑；                              // 长时间静稳时慢速修正零漂
 */

#include "app_ForceOut.h"   // 你的头文件，里面应包含 ForceResult_t 等定义
#include <math.h>           // fabsf 等数学函数
#include <string.h>         // memset、memcpy
#include <stdint.h>         // uint8_t、uint32_t 类型

/* =====================================================================
 *  可调参数区
 * ===================================================================== */

/* ---------- 输入端滤波参数 ---------- */
#define INPUT_EMA_ALPHA          0.03f     // 输入电压的一阶 EMA 系数；越小越稳，越大越灵敏
#define USE_MEDIAN3_FILTER       1         // 是否启用3点中值滤波：1启用，0关闭
#define MEDIAN_BUF_LEN           3         // 3点中值滤波窗口长度，固定为3

/* ---------- 输出端（三维力）滤波参数 ---------- */
#define FORCE_EMA_ALPHA_FZ       0.10f     // Fz 输出EMA系数
#define FORCE_EMA_ALPHA_FX       0.15f     // Fx 输出EMA系数
#define FORCE_EMA_ALPHA_FY       0.15f     // Fy 输出EMA系数

/* ---------- 基线（零点）更新参数 ---------- */
#define BASELINE_SMOOTH_ALPHA    0.03f     // 基线逼近目标值的速度；越小越慢
#define BASELINE_CONVERGE_TH     0.003f    // 判断“基线已经收敛”的阈值，单位V

/* ---------- 自动基线更新判据 ---------- */
#define BASELINE_WIN             30        // 稳定窗口长度；若20ms调用一次，则约0.6s数据
#define BASELINE_RANGE_TH        0.03f     // 正常运行时判定静稳的电压极差阈值，单位V
#define BASELINE_HOLD_MS         1000U     // 正常运行时持续静稳保持时间，单位ms

/* ---------- 开机自动建基线参数 ---------- */
#define STARTUP_WARMUP_MS        5000U     // 开机预热时间，单位ms，这里设为5秒
#define STARTUP_RANGE_TH         0.03f     // 开机建基线时允许的电压稳定极差阈值，单位V

/* ---------- 小力判定阈值（用于允许自动更新基线） ---------- */
#define SMALL_FORCE_TH_FZ        4.0f      // Fz 小力阈值
#define SMALL_FORCE_TH_FX        3.5f      // Fx 小力阈值
#define SMALL_FORCE_TH_FY        3.5f      // Fy 小力阈值

/* ---------- 输出死区阈值 ---------- */
#define FORCE_DEADZONE_FZ        1.0f      // Fz 死区
#define FORCE_DEADZONE_FX        0.5f      // Fx 死区
#define FORCE_DEADZONE_FY        0.5f      // Fy 死区

/* =====================================================================
 *  力解耦标定矩阵 (3×4)
 *  行: Fz, Fx, Fy
 *  列: d1, d2, d3, d4
 * ===================================================================== */
static float g_decouple_matrix[3][4] = {
    {  39.2375f,  29.8622f,  24.3702f,  32.1236f },   // 第1行：Fz 解耦系数
    {  17.6342f,  -0.1770f, -20.2660f,   0.3688f },   // 第2行：Fx 解耦系数
    {  -7.9958f,  19.9397f,  -6.9973f, -17.1562f }    // 第3行：Fy 解耦系数
};

uint32_t g_tick_ms = 0;   // 如外部不用，可保留

/* =====================================================================
 *  内部状态结构体
 * ===================================================================== */
typedef struct
{
    /* ---------- 基线相关 ---------- */
    float baseline_v[4];               // 当前零点基线电压 [V1 V2 V3 V4]
    float baseline_target_v[4];        // 自动更新时希望逼近的新基线目标

    /* ---------- 输入滤波相关 ---------- */
    float filt_v[4];                   // 输入电压经过中值+EMA后的结果
    float raw_hist[4][MEDIAN_BUF_LEN]; // 每路最近3个原始点，用于3点中值滤波
    uint8_t raw_idx;                   // 当前写入原始历史缓冲区的位置

    /* ---------- 输出滤波相关 ---------- */
    float force_filt[3];               // 解耦后 Fz/Fx/Fy 的EMA结果

    /* ---------- 稳定性检测相关 ---------- */
    float stable_buf[4][BASELINE_WIN]; // 用滤波后电压做稳定窗口
    int   stable_buf_idx;              // 稳定窗口当前写指针
    int   stable_sample_count;         // 当前窗口内已写入的样本数
    int   stable_buf_full;             // 窗口是否已填满：1是，0否

    /* ---------- 稳定计时 ---------- */
    uint32_t stable_start_ms;          // 开始“持续静稳”的时间戳
    int      stable_timing;            // 是否正在计时：1是，0否

    /* ---------- 基线更新状态 ---------- */
    int      baseline_updating;        // 是否正在缓慢更新基线：1是，0否

    /* ---------- 初始化标志 ---------- */
    int      initialized;              // 是否完成初始化：1是，0否

    /* ---------- 开机自动建基线相关 ---------- */
    uint32_t startup_begin_ms;         // 开机预热开始时间戳
    int      startup_warmup_started;   // 是否已经开始开机预热计时：1是，0否
    int      startup_baseline_done;    // 开机初始基线是否已经建立完成：1完成，0未完成

} ForceSensorState_t;

static ForceSensorState_t g_sensor;    // 全局内部状态，仅本文件可见

/* =====================================================================
 *  内部辅助函数
 * ===================================================================== */

/* 限幅函数：把数值限制在区间 [lo, hi] 内 */
static float clampf(float v, float lo, float hi)
{
    if (v < lo) return lo;             // 小于下限时返回下限
    if (v > hi) return hi;             // 大于上限时返回上限
    return v;                          // 正常范围内直接返回
}

/* 通用 EMA 函数：alpha 越小越平滑，越大响应越快 */
static float ema_alpha(float new_val, float old_val, float alpha)
{
    alpha = clampf(alpha, 0.0f, 1.0f);                    // 防止参数越界
    return alpha * new_val + (1.0f - alpha) * old_val;   // 标准 EMA 公式
}

/* 3点中值滤波：专门去偶发尖峰毛刺 */
static float median3(float a, float b, float c)
{
    float t;                                              // 交换变量

    if (a > b) { t = a; a = b; b = t; }                  // 保证 a <= b
    if (b > c) { t = b; b = c; c = t; }                  // 保证 b <= c
    if (a > b) { t = a; a = b; b = t; }                  // 再次保证 a <= b

    return b;                                             // 中间那个值就是中值
}

/* 窗口均值：用于生成新的基线目标 */
static float window_mean(const float *buf, int len)
{
    float s = 0.0f;                                       // 求和变量
    int i;
    for (i = 0; i < len; i++)
    {
        s += buf[i];                                      // 累加每个样本
    }
    return s / (float)len;                                // 返回均值
}

/* 窗口极差：max - min，用于判断一段时间内电压是否稳定 */
static float window_range(const float *buf, int len)
{
    float mn = buf[0];                                    // 初始化最小值
    float mx = buf[0];                                    // 初始化最大值
    int i;

    for (i = 1; i < len; i++)
    {
        if (buf[i] < mn) mn = buf[i];                     // 更新最小值
        if (buf[i] > mx) mx = buf[i];                     // 更新最大值
    }

    return mx - mn;                                       // 返回极差
}

/* 死区处理：力值很小时直接置零，减少零点附近乱跳 */
static float apply_deadzone(float val, float threshold)
{
    return (fabsf(val) < threshold) ? 0.0f : val;         // 小于阈值则输出0
}

/* 开机预热期间，强制把输出清零 */
static void clear_force_result(ForceResult_t *result)
{
    if (!result) return;                                  // 空指针保护

    result->Fz = 0.0f;                                    // 开机预热期间 Fz 输出置零
    result->Fx = 0.0f;                                    // 开机预热期间 Fx 输出置零
    result->Fy = 0.0f;                                    // 开机预热期间 Fy 输出置零

    result->d[0] = 0.0f;                                  // 差分电压清零
    result->d[1] = 0.0f;                                  // 差分电压清零
    result->d[2] = 0.0f;                                  // 差分电压清零
    result->d[3] = 0.0f;                                  // 差分电压清零
}

/* =====================================================================
 *  对外接口实现
 * ===================================================================== */

/**
 * @brief  初始化力传感器算法
 * @param  init_v  启动时4路初始电压 [V1, V2, V3, V4]
 * @retval 0 成功, -1 参数错误
 */
int ForceSensor_Init(const float init_v[4])
{
    int ch, k, i;

    if (!init_v) return -1;                               // 空指针保护

    memset(&g_sensor, 0, sizeof(g_sensor));               // 清空内部状态

    for (ch = 0; ch < 4; ch++)
    {
        g_sensor.baseline_v[ch]        = init_v[ch];      // 先用当前输入做临时基线，占位用
        g_sensor.baseline_target_v[ch] = init_v[ch];      // 初始目标基线先与临时基线一致
        g_sensor.filt_v[ch]            = init_v[ch];      // 输入滤波初值先设成当前值，避免启动瞬间突变

        for (k = 0; k < MEDIAN_BUF_LEN; k++)
        {
            g_sensor.raw_hist[ch][k] = init_v[ch];        // 原始历史缓冲先填当前值
        }

        for (i = 0; i < BASELINE_WIN; i++)
        {
            g_sensor.stable_buf[ch][i] = init_v[ch];      // 稳定窗口先填当前值
        }
    }

    g_sensor.raw_idx               = 0;                   // 原始历史写指针归零
    g_sensor.stable_buf_idx        = 0;                   // 稳定窗口写指针归零
    g_sensor.stable_sample_count   = 0;                   // 当前还未重新积累真实稳定样本
    g_sensor.stable_buf_full       = 0;                   // 一开始稳定窗口还不算真正填满
    g_sensor.stable_timing         = 0;                   // 自动基线更新计时关闭
    g_sensor.baseline_updating     = 0;                   // 初始化时不进行慢速基线更新

    g_sensor.force_filt[0] = 0.0f;                        // Fz 输出滤波状态清零
    g_sensor.force_filt[1] = 0.0f;                        // Fx 输出滤波状态清零
    g_sensor.force_filt[2] = 0.0f;                        // Fy 输出滤波状态清零

    g_sensor.startup_begin_ms       = 0U;                 // 开机预热起始时间先清零
    g_sensor.startup_warmup_started = 0;                  // 标记：开机预热还没开始
    g_sensor.startup_baseline_done  = 0;                  // 标记：开机初始基线还没建立

    g_sensor.initialized = 1;                             // 初始化完成

    return 0;
}

/**
 * @brief  周期性调用，输入4路电压，输出解耦后的三维力
 * @param  v_in         当前周期4路电压 [V1, V2, V3, V4]
 * @param  timestamp_ms 当前系统时间，单位 ms
 * @param  result       输出结果
 * @retval 0 成功, -1 参数错误, -2 未初始化
 */
int ForceSensor_Update(const float v_in[4], uint32_t timestamp_ms, ForceResult_t *result)
{
    ForceSensorState_t *s;
    int ch;
    float d[4];
    float Fz_raw, Fx_raw, Fy_raw;
    float Fz, Fx, Fy;

    if (!v_in || !result) return -1;                      // 参数检查
    if (!g_sensor.initialized) return -2;                // 未初始化保护

    s = &g_sensor;                                        // 取内部状态指针

    /* -----------------------------------------------------------------
     * 0. 开机预热计时起点
     *    目的：第一次进入 Update 时，记录开机预热的起始时刻
     * ----------------------------------------------------------------- */
    if (!s->startup_warmup_started)
    {
        s->startup_begin_ms = timestamp_ms;              // 用第一次调用时的时间作为开机预热起点
        s->startup_warmup_started = 1;                   // 标记：已经开始开机预热
    }

    /* -----------------------------------------------------------------
     * 1. 输入端：3点中值滤波 + EMA
     *    目的：先去掉偶发毛刺，再做低通平滑
     * ----------------------------------------------------------------- */
    for (ch = 0; ch < 4; ch++)
    {
        float v_med;

        s->raw_hist[ch][s->raw_idx] = v_in[ch];          // 先把新原始电压写入历史缓冲

#if USE_MEDIAN3_FILTER
        v_med = median3(
            s->raw_hist[ch][0],
            s->raw_hist[ch][1],
            s->raw_hist[ch][2]
        );                                               // 对当前3个原始点做中值滤波
#else
        v_med = v_in[ch];                                // 如果关闭中值滤波，则直接使用原始输入
#endif

        s->filt_v[ch] = ema_alpha(
            v_med,
            s->filt_v[ch],
            INPUT_EMA_ALPHA
        );                                               // 对输入电压进行一阶EMA平滑
    }
    s->raw_idx = (uint8_t)((s->raw_idx + 1) % MEDIAN_BUF_LEN); // 原始历史缓冲写指针循环前进

    /* -----------------------------------------------------------------
     * 2. 稳定窗口更新
     *    目的：无论是否完成开机建基线，都持续维护最近一段时间的稳定窗口
     * ----------------------------------------------------------------- */
    for (ch = 0; ch < 4; ch++)
    {
        s->stable_buf[ch][s->stable_buf_idx] = s->filt_v[ch];   // 把当前滤波后电压写入稳定窗口
    }

    s->stable_buf_idx = (s->stable_buf_idx + 1) % BASELINE_WIN; // 稳定窗口写指针循环前进

    if (s->stable_sample_count < BASELINE_WIN)
    {
        s->stable_sample_count++;                        // 记录当前已积累的窗口样本数
        if (s->stable_sample_count >= BASELINE_WIN)
        {
            s->stable_buf_full = 1;                      // 样本够一整窗后，标记窗口已填满
        }
    }

    /* -----------------------------------------------------------------
     * 3. 开机自动建基线
     *    目的：开机先预热5秒，之后把稳定电压均值设为初始基线
     * ----------------------------------------------------------------- */
    if (!s->startup_baseline_done)
    {
        uint32_t warmup_elapsed_ms = timestamp_ms - s->startup_begin_ms; // 计算已经预热了多久

        if ((warmup_elapsed_ms >= STARTUP_WARMUP_MS) && s->stable_buf_full)
        {
            int stable_voltage = 1;                      // 先假设4路电压都已经稳定

            for (ch = 0; ch < 4; ch++)
            {
                if (window_range(s->stable_buf[ch], BASELINE_WIN) >= STARTUP_RANGE_TH)
                {
                    stable_voltage = 0;                  // 只要有一路窗口极差过大，就认为还没稳定
                    break;
                }
            }

            if (stable_voltage)
            {
                for (ch = 0; ch < 4; ch++)
                {
                    float v_mean = window_mean(s->stable_buf[ch], BASELINE_WIN); // 取最近稳定窗口均值
                    s->baseline_v[ch]        = v_mean;   // 将稳定均值直接设为当前基线
                    s->baseline_target_v[ch] = v_mean;   // 同时设为目标基线，避免后面再慢慢追
                }

                s->baseline_updating = 0;                // 开机建基线完成后，不需要再做本轮慢速更新
                s->stable_timing     = 0;                // 清掉普通自动基线更新计时状态
                s->startup_baseline_done = 1;            // 标记：开机初始基线已建立完成

                s->force_filt[0] = 0.0f;                 // 清零输出滤波状态，避免旧残留影响正式输出
                s->force_filt[1] = 0.0f;                 // 清零 Fx 滤波状态
                s->force_filt[2] = 0.0f;                 // 清零 Fy 滤波状态
            }
        }

        clear_force_result(result);                      // 开机预热和建基线期间，输出强制为0
        return 0;                                        // 直接返回，暂不进入正式解耦流程
    }

    /* -----------------------------------------------------------------
     * 4. 基线平滑更新
     *    目的：正常运行后，当系统确认静稳时，让零点缓慢逼近目标
     * ----------------------------------------------------------------- */
    if (s->baseline_updating)
    {
        int converged = 1;                               // 先假设本次能收敛

        for (ch = 0; ch < 4; ch++)
        {
            s->baseline_v[ch] += BASELINE_SMOOTH_ALPHA *
                                 (s->baseline_target_v[ch] - s->baseline_v[ch]); // 基线慢慢逼近目标

            if (fabsf(s->baseline_v[ch] - s->baseline_target_v[ch]) > BASELINE_CONVERGE_TH)
            {
                converged = 0;                           // 只要有一路没收敛，就继续更新
            }
        }

        if (converged)
        {
            s->baseline_updating = 0;                    // 4路全部收敛后，结束本轮慢速基线更新
        }
    }

    /* -----------------------------------------------------------------
     * 5. 计算差分电压 d = filtered - baseline
     *    目的：得到相对于当前基线的真实变化量
     * ----------------------------------------------------------------- */
    for (ch = 0; ch < 4; ch++)
    {
        d[ch] = s->filt_v[ch] - s->baseline_v[ch];      // 差分电压 = 当前滤波值 - 当前基线
    }

    /* -----------------------------------------------------------------
     * 6. 矩阵解耦，得到原始三维力
     * ----------------------------------------------------------------- */
    Fz_raw = g_decouple_matrix[0][0] * d[0]
           + g_decouple_matrix[0][1] * d[1]
           + g_decouple_matrix[0][2] * d[2]
           + g_decouple_matrix[0][3] * d[3];            // 原始Fz

    Fx_raw = g_decouple_matrix[1][0] * d[0]
           + g_decouple_matrix[1][1] * d[1]
           + g_decouple_matrix[1][2] * d[2]
           + g_decouple_matrix[1][3] * d[3];            // 原始Fx

    Fy_raw = g_decouple_matrix[2][0] * d[0]
           + g_decouple_matrix[2][1] * d[1]
           + g_decouple_matrix[2][2] * d[2]
           + g_decouple_matrix[2][3] * d[3];            // 原始Fy

    /* -----------------------------------------------------------------
     * 7. 输出端再做一次EMA
     * ----------------------------------------------------------------- */
    s->force_filt[0] = ema_alpha(Fz_raw, s->force_filt[0], FORCE_EMA_ALPHA_FZ); // Fz 再滤波
    s->force_filt[1] = ema_alpha(Fx_raw, s->force_filt[1], FORCE_EMA_ALPHA_FX); // Fx 再滤波
    s->force_filt[2] = ema_alpha(Fy_raw, s->force_filt[2], FORCE_EMA_ALPHA_FY); // Fy 再滤波

    Fz = s->force_filt[0];                               // 当前滤波后的 Fz
    Fx = s->force_filt[1];                               // 当前滤波后的 Fx
    Fy = s->force_filt[2];                               // 当前滤波后的 Fy

    /* -----------------------------------------------------------------
     * 8. 正常运行时的稳定检测与自动基线更新
     * ----------------------------------------------------------------- */
    if (s->stable_buf_full)
    {
        int small_force = (fabsf(Fz) < SMALL_FORCE_TH_FZ &&
                           fabsf(Fx) < SMALL_FORCE_TH_FX &&
                           fabsf(Fy) < SMALL_FORCE_TH_FY); // 三轴力都很小，说明可能接近空载

        int stable_voltage = 1;                          // 先假设4路电压都很稳定

        for (ch = 0; ch < 4; ch++)
        {
            if (window_range(s->stable_buf[ch], BASELINE_WIN) >= BASELINE_RANGE_TH)
            {
                stable_voltage = 0;                      // 只要有一路不稳，就不允许自动更新基线
                break;
            }
        }

        if (small_force && stable_voltage)
        {
            if (!s->stable_timing)
            {
                s->stable_timing = 1;                    // 第一次进入静稳状态，开始计时
                s->stable_start_ms = timestamp_ms;       // 记录静稳起点
            }
            else if ((timestamp_ms - s->stable_start_ms) >= BASELINE_HOLD_MS)
            {
                for (ch = 0; ch < 4; ch++)
                {
                    s->baseline_target_v[ch] = window_mean(s->stable_buf[ch], BASELINE_WIN); // 用稳定均值作为新目标基线
                }

                s->baseline_updating = 1;                // 启动慢速基线更新
                s->stable_timing = 0;                    // 本轮完成后清除计时状态
            }
        }
        else
        {
            s->stable_timing = 0;                        // 不满足条件则清掉计时，必须重新累计
        }
    }

    /* -----------------------------------------------------------------
     * 9. 死区处理
     * ----------------------------------------------------------------- */
    Fz = apply_deadzone(Fz, FORCE_DEADZONE_FZ);         // Fz 死区
    Fx = apply_deadzone(Fx, FORCE_DEADZONE_FX);         // Fx 死区
    Fy = apply_deadzone(Fy, FORCE_DEADZONE_FY);         // Fy 死区

    /* -----------------------------------------------------------------
     * 10. 输出结果
     * ----------------------------------------------------------------- */
    result->Fz = Fz;                                    // 输出最终 Fz
    result->Fx = Fx;                                    // 输出最终 Fx
    result->Fy = Fy;                                    // 输出最终 Fy

    result->d[0] = d[0];                                // 返回第1路差分电压，便于调试
    result->d[1] = d[1];                                // 返回第2路差分电压，便于调试
    result->d[2] = d[2];                                // 返回第3路差分电压，便于调试
    result->d[3] = d[3];                                // 返回第4路差分电压，便于调试

    return 0;                                           // 正常返回
}

/**
 * @brief  手动设置/重置基线电压
 * @param  baseline_v  新的基线；若传 NULL，则以当前滤波电压作为新基线
 * @retval 0 成功, -2 未初始化
 */
int ForceSensor_SetBaseline(const float baseline_v[4])
{
    int ch, i;

    if (!g_sensor.initialized) return -2;               // 未初始化保护

    if (baseline_v)
    {
        for (ch = 0; ch < 4; ch++)
        {
            g_sensor.baseline_v[ch]        = baseline_v[ch];      // 手动指定新基线
            g_sensor.baseline_target_v[ch] = baseline_v[ch];      // 目标基线同步设置
        }
    }
    else
    {
        for (ch = 0; ch < 4; ch++)
        {
            g_sensor.baseline_v[ch]        = g_sensor.filt_v[ch]; // 用当前滤波值直接重置基线
            g_sensor.baseline_target_v[ch] = g_sensor.filt_v[ch]; // 目标基线同步设置
        }
    }

    for (ch = 0; ch < 4; ch++)
    {
        for (i = 0; i < BASELINE_WIN; i++)
        {
            g_sensor.stable_buf[ch][i] = g_sensor.baseline_v[ch]; // 重建稳定窗口，避免立即误判
        }
    }

    g_sensor.stable_buf_idx       = 0;                   // 稳定窗口写指针清零
    g_sensor.stable_sample_count  = 0;                   // 重新累计窗口样本
    g_sensor.stable_buf_full      = 0;                   // 稳定窗口重新填充
    g_sensor.stable_timing        = 0;                   // 清除普通自动基线计时
    g_sensor.baseline_updating    = 0;                   // 清除慢速基线更新状态

    g_sensor.force_filt[0] = 0.0f;                       // 清零输出滤波状态
    g_sensor.force_filt[1] = 0.0f;                       // 清零输出滤波状态
    g_sensor.force_filt[2] = 0.0f;                       // 清零输出滤波状态

    g_sensor.startup_baseline_done  = 1;                 // 手动设基线后，认为开机初始基线已完成
    g_sensor.startup_warmup_started = 1;                 // 避免再次进入开机预热流程

    return 0;
}

/**
 * @brief  修改解耦矩阵
 * @param  matrix  新的 3×4 解耦矩阵
 * @retval 0 成功, -1 参数错误
 */
int ForceSensor_SetMatrix(const float matrix[3][4])
{
    if (!matrix) return -1;                              // 空指针保护
    memcpy(g_decouple_matrix, matrix, sizeof(g_decouple_matrix)); // 直接替换矩阵
    return 0;
}

/**
 * @brief  获取当前基线电压
 * @param  baseline_v  输出当前基线
 * @retval 0 成功, -1 参数错误, -2 未初始化
 */
int ForceSensor_GetBaseline(float baseline_v[4])
{
    if (!baseline_v) return -1;                          // 空指针保护
    if (!g_sensor.initialized) return -2;               // 未初始化保护

    memcpy(baseline_v, g_sensor.baseline_v, 4 * sizeof(float));   // 拷贝4路当前基线
    return 0;
}