/**
 * @file    outCode.h
 * @brief   三维力传感器解耦算法 - 通用移植接口
 */

#ifndef OUT_CODE_H
#define OUT_CODE_H

#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

/* =====================================================================
 *  数据类型
 * ===================================================================== */

/** 三维力输出结果 */
typedef struct {
    float Fz;       /**< Z 轴力 (N), 垂直方向 */
    float Fx;       /**< X 轴力 (N) */
    float Fy;       /**< Y 轴力 (N) */
    float d[4];     /**< 各通道差分电压 (V) = filtered - baseline */
} ForceResult_t;

extern uint32_t g_tick_ms;
/* =====================================================================
 *  核心接口
 * ===================================================================== */

/**
 * @brief  初始化力传感器算法
 *
 * @param  init_v  启动零点电压 [V1, V2, V3, V4], 单位 V
 *                 建议上电稳定后多次采样取平均
 * @retval 0 成功, -1 参数错误
 */
int ForceSensor_Init(const float init_v[4]);

/**
 * @brief  周期调用: 输入电压 → 输出三维力
 *
 * @param  v_in          4路 ADC 电压 [V1~V4], 单位 V
 * @param  timestamp_ms  当前系统时间 (ms), 用于稳定检测计时
 * @param  result        输出结果
 *
 * @retval 0 成功, -1 参数错误, -2 未初始化
 *
 * @note   建议调用周期: 20ms (50Hz)
 *         v_in 建议预先做多次 ADC 采样取平均
 */
int ForceSensor_Update(const float v_in[4],
                       uint32_t timestamp_ms,
                       ForceResult_t *result);

/**
 * @brief  手动设置/重置基线
 * @param  baseline_v  新零点电压, NULL=以当前滤波值为基线
 * @retval 0 成功
 */
int ForceSensor_SetBaseline(const float baseline_v[4]);

/**
 * @brief  获取当前基线电压
 */
int ForceSensor_GetBaseline(float baseline_v[4]);

/**
 * @brief  在线修改解耦标定矩阵
 * @param  matrix  3×4 矩阵, 行: Fz/Fx/Fy, 列: d1~d4
 */
int ForceSensor_SetMatrix(const float matrix[3][4]);

#ifdef __cplusplus
}
#endif

#endif /* OUT_CODE_H */
