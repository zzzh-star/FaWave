import ctypes
import os

class ForceResult(ctypes.Structure):
    _fields_ = [
        ("Fz", ctypes.c_float),
        ("Fx", ctypes.c_float),
        ("Fy", ctypes.c_float),
        ("d", ctypes.c_float * 4)
    ]

class CForceDecoder:
    def __init__(self, config=None):
        self.config = config.get("force_decoder", {}) if config else {}
        self.enabled = self.config.get("enabled", False)

        self.dll = None

        dll_path = os.path.join(os.path.dirname(__file__), 'c_ref', 'force_decoder.dll')
        so_path = os.path.join(os.path.dirname(__file__), 'c_ref', 'force_decoder.so')

        if os.path.exists(dll_path):
            self.dll = ctypes.CDLL(dll_path)
        elif os.path.exists(so_path):
            self.dll = ctypes.CDLL(so_path)

        if self.dll:
            self.dll.init_sensor.argtypes = [ctypes.POINTER(ctypes.c_float)]
            self.dll.update_sensor.argtypes = [ctypes.POINTER(ctypes.c_float), ctypes.c_uint32, ctypes.POINTER(ForceResult)]
            self.dll.set_baseline.argtypes = [ctypes.POINTER(ctypes.c_float)]

        self.initialized = False
        self.startup_baseline_done = False
        self.result = ForceResult()

    def initialize(self, init_v):
        if not self.dll: return -1
        v_arr = (ctypes.c_float * 4)(*init_v)
        res = self.dll.init_sensor(v_arr)
        if res == 0:
            self.initialized = True
        return res

    def update(self, v_in, timestamp_ms):
        if not self.enabled:
            return {"fx": 0.0, "fy": 0.0, "fz": 0.0, "status": "算法未启用", "valid": False}
        if not self.dll:
            return {"fx": 0.0, "fy": 0.0, "fz": 0.0, "status": "错误: 缺少DLL", "valid": False}
        if not self.initialized:
            return {"fx": 0.0, "fy": 0.0, "fz": 0.0, "status": "未初始化", "valid": False}

        v_arr = (ctypes.c_float * 4)(*v_in)
        self.dll.update_sensor(v_arr, timestamp_ms, ctypes.byref(self.result))

        # Determine status. In C it returns 0 during warmup but Fz/Fx/Fy are 0.
        # We can loosely infer baseline done if timestamp > startup_warmup
        if timestamp_ms < self.config.get("startup_warmup_ms", 5000):
            status = "基线建立中"
        else:
            self.startup_baseline_done = True
            status = "解耦已启用"

        return {
            "fx": self.result.Fx,
            "fy": self.result.Fy,
            "fz": self.result.Fz,
            "d": [self.result.d[0], self.result.d[1], self.result.d[2], self.result.d[3]],
            "valid": True,
            "status": status
        }

    def set_baseline(self, baseline_v=None):
        if not self.dll: return -1
        if baseline_v:
            b_arr = (ctypes.c_float * 4)(*baseline_v)
            return self.dll.set_baseline(b_arr)
        else:
            return self.dll.set_baseline(None)
