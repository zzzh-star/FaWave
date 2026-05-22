from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QComboBox, QCheckBox, QDialogButtonBox,
                             QFormLayout, QGroupBox, QMessageBox)
from PySide6.QtCore import Qt
import os
import ctypes
from ..utils.resource import resource_path

class AdvancedSettingsDialog(QDialog):
    def __init__(self, config, parent=None):
        super().__init__(parent)
        self.config = config
        self.setObjectName("advancedSettingsDialog")
        self.setWindowTitle("高级设置")
        self.setMinimumWidth(450)

        # Apply dark titlebar explicitly on Windows
        if os.name == 'nt' and parent and parent.current_theme == 'dark':
            try:
                hwnd = self.winId().__int__()
                DWMWA_USE_IMMERSIVE_DARK_MODE = 20
                set_window_attribute = ctypes.windll.dwmapi.DwmSetWindowAttribute
                value = ctypes.c_int(1)
                set_window_attribute(hwnd, DWMWA_USE_IMMERSIVE_DARK_MODE, ctypes.byref(value), ctypes.sizeof(value))
            except Exception:
                pass

        self.setup_ui()
        self.load_config()

    def setup_ui(self):
        layout = QVBoxLayout(self)

        # Force Decoder Group
        decoder_group = QGroupBox("三维力解耦设置")
        decoder_group.setObjectName("advancedSettingsCard")
        decoder_layout = QFormLayout()

        self.backend_combo = QComboBox()
        self.backend_combo.addItems(["C语言后端", "Python移植"])
        decoder_layout.addRow("解耦后端:", self.backend_combo)

        self.c_backend_status = QLabel("未知")
        self.c_backend_status.setStyleSheet("color: #64748B; font-weight: bold;")

        self.btn_check_c = QPushButton("检测 C 后端")
        self.btn_check_c.setObjectName("btnCheckC")
        self.btn_check_c.clicked.connect(self.check_c_backend)

        status_layout = QHBoxLayout()
        status_layout.addWidget(self.c_backend_status)
        status_layout.addStretch()
        status_layout.addWidget(self.btn_check_c)
        decoder_layout.addRow("C 后端状态:", status_layout)

        self.c_dll_path_label = QLabel()
        self.c_dll_path_label.setWordWrap(True)
        self.c_dll_path_label.setStyleSheet("color: #64748B; font-size: 12px;")
        decoder_layout.addRow("路径:", self.c_dll_path_label)

        self.allow_fallback_cb = QCheckBox("C 后端失败时自动切换 Python移植")
        decoder_layout.addRow("", self.allow_fallback_cb)

        self.input_unit_combo = QComboBox()
        self.input_unit_combo.addItems(["V", "mV"])
        self.input_unit_combo.currentTextChanged.connect(self.on_unit_changed)
        decoder_layout.addRow("输入单位:", self.input_unit_combo)

        self.scale_label = QLabel()
        decoder_layout.addRow("换算比例:", self.scale_label)

        self.auto_baseline_cb = QCheckBox("开启")
        decoder_layout.addRow("自动基线更新:", self.auto_baseline_cb)

        decoder_group.setLayout(decoder_layout)
        layout.addWidget(decoder_group)

        # Buttons
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def load_config(self):
        fd_cfg = self.config.get("force_decoder", {})

        backend = fd_cfg.get("backend", "c_dll")
        if backend == "c_dll":
            self.backend_combo.setCurrentText("C语言后端")
        else:
            self.backend_combo.setCurrentText("Python移植")

        self.allow_fallback_cb.setChecked(fd_cfg.get("allow_python_fallback", True))

        unit = fd_cfg.get("input_unit", "V")
        self.input_unit_combo.setCurrentText(unit)
        self.on_unit_changed(unit)

        baseline_cfg = fd_cfg.get("baseline", {})
        self.auto_baseline_cb.setChecked(baseline_cfg.get("auto_update_enabled", True))

    def load_config(self):
        fd_cfg = self.config.get("force_decoder", {})

        backend = fd_cfg.get("backend", "c_dll")
        if backend == "c_dll":
            self.backend_combo.setCurrentText("C语言后端")
        else:
            self.backend_combo.setCurrentText("Python移植")

        self.allow_fallback_cb.setChecked(fd_cfg.get("allow_python_fallback", True))

        unit = fd_cfg.get("input_unit", "V")
        self.input_unit_combo.setCurrentText(unit)
        self.on_unit_changed(unit)

        baseline_cfg = fd_cfg.get("baseline", {})
        self.auto_baseline_cb.setChecked(baseline_cfg.get("auto_update_enabled", True))

        self.check_c_backend()

    def check_c_backend(self):
        c_dll_path_config = self.config.get("force_decoder", {}).get("c_dll_path", "src/force/c_backend/force_decoder.dll")
        dll_path = resource_path(c_dll_path_config)
        self.c_dll_path_label.setText(dll_path)

        if not os.path.exists(dll_path) and not os.path.exists(dll_path.replace('.dll', '.so')):
            self.c_backend_status.setText("DLL 未找到")
            self.c_backend_status.setStyleSheet("color: #EF4444; font-weight: bold;")
            return

        try:
            lib = ctypes.CDLL(dll_path) if os.path.exists(dll_path) else ctypes.CDLL(dll_path.replace('.dll', '.so'))
            if hasattr(lib, 'init_sensor') and hasattr(lib, 'update_sensor') and hasattr(lib, 'set_baseline'):
                self.c_backend_status.setText("已加载")
                self.c_backend_status.setStyleSheet("color: #22C55E; font-weight: bold;")
            else:
                self.c_backend_status.setText("接口错误 (缺少函数)")
                self.c_backend_status.setStyleSheet("color: #F59E0B; font-weight: bold;")
        except Exception as e:
            self.c_backend_status.setText(f"加载失败")
            self.c_backend_status.setStyleSheet("color: #EF4444; font-weight: bold;")
            self.c_dll_path_label.setText(f"错误: {str(e)}")

    def on_unit_changed(self, text):
        # We need to detect if user transitions FROM V TO mV, and issue a warning.
        # But we also don't want to alert them on initial load.
        current_cfg = self.config.get("force_decoder", {}).get("input_unit", "V")
        if text == "mV" and current_cfg == "V":
            reply = QMessageBox.warning(
                self,
                "单位切换警告",
                "当前 FaWave 真实设备已确认返回单位为 V。\n\n只有接入其他 mV 输出设备时才建议切换为 mV。是否继续？",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            if reply == QMessageBox.No:
                self.input_unit_combo.setCurrentText("V")
                return

        if text == "V":
            self.scale_label.setText("V -> 1.0")
        else:
            self.scale_label.setText("mV -> 0.001")

    def accept(self):
        # Prevent switching while acquiring (handled in MainWindow, but double check)
        fd_cfg = self.config.get("force_decoder", {})
        baseline_cfg = fd_cfg.get("baseline", {})

        fd_cfg["backend"] = "c_dll" if self.backend_combo.currentText() == "C语言后端" else "python"
        fd_cfg["allow_python_fallback"] = self.allow_fallback_cb.isChecked()
        fd_cfg["input_unit"] = self.input_unit_combo.currentText()
        fd_cfg["input_scale_to_v"] = 1.0 if fd_cfg["input_unit"] == "V" else 0.001

        baseline_cfg["auto_update_enabled"] = self.auto_baseline_cb.isChecked()
        fd_cfg["baseline"] = baseline_cfg
        self.config["force_decoder"] = fd_cfg

        super().accept()
