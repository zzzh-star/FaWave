# 三维力解耦准确性验证

说明：

1. C 算法是参考标准 (来自 Firmware 文件夹中的 `app_ForceOut.c` 和 `app_ForceOut.h`)。
2. Python 版本通过同输入序列与 C 输出逐点比较来进行验证。
3. 比较字段包括 Fx/Fy/Fz 和 d1~d4，以确保 Python 的 numpy 实现等价于单精度的 C 语言解耦矩阵结果。
4. 误差阈值设定在 1e-3 N 和 1e-5 V 内。
5. 通过 `generate_test_vectors.py` 构造测试激励（例如阶跃力、漂移基线、静态白噪声等）。
6. 使用 `run_python_decoder.py` 计算输出数据集，可通过类似比较脚本映射对比嵌入式硬件生成的同样 CSV 数据。
7. 在主程序的配置文件中可以选择解耦后端，同时 UI 会根据是否通过本模块测试展示“验证状态：已通过”。
