# C Backend

此目录用于存放和编译从下位机 `Keil C` 移植的原始解耦算法。因为 Python 和 C 之间可能有浮点精度差异，官方推荐使用此 C DLL 作为主要的计算后端，以保证采集平台计算出的三维力值与底层嵌入式算法**绝对一致**。

## 文件说明

- `app_ForceOut.c` / `app_ForceOut.h`：下位机原始三维力算法源码文件。
- `force_wrapper.c`：C 接口包装层，暴露出用于 Python `ctypes` 调用的初始化 (`init_sensor`)、运行更新 (`update_sensor`) 和归零 (`set_baseline`) 接口。
- `build_force_dll.bat`：Windows 编译脚本。

## 编译方法

如果您修改了 `app_ForceOut.c`，您需要重新编译 DLL 文件：

### Windows (使用 MinGW GCC)

确保您已经安装了 MinGW 并配置了环境变量，然后在命令行运行：

```bash
cd src/force/c_backend
build_force_dll.bat
```

这将会调用：`gcc -shared -o force_decoder.dll force_wrapper.c app_ForceOut.c`。

### Windows (使用 MSVC)

如果您使用 Visual Studio：

```cmd
cd src/force/c_backend
cl /LD force_wrapper.c app_ForceOut.c /Feforce_decoder.dll
```

### Linux (使用 GCC 生成 .so 文件)

```bash
cd src/force/c_backend
gcc -shared -fPIC -o force_decoder.so force_wrapper.c app_ForceOut.c
```

生成的 `.dll` 或 `.so` 会被上位机在启动或重连时自动加载。
