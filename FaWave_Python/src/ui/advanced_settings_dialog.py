from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QComboBox, QCheckBox, QDialogButtonBox,
                             QFormLayout, QGroupBox, QMessageBox)
from PySide6.QtCore import Qt

class AdvancedSettingsDialog(QDialog):
    def __init__(self, config, parent=None):
        super().__init__(parent)
        self.config = config
        self.setWindowTitle("高级设置")
        self.setMinimumWidth(400)
        self.setup_ui()
        self.load_config()

    def setup_ui(self):
        layout = QVBoxLayout(self)

        # Force Decoder Group
        decoder_group = QGroupBox("三维力解耦设置")
        decoder_layout = QFormLayout()

        self.backend_combo = QComboBox()
        self.backend_combo.addItems(["C语言后端", "Python移植"])
        decoder_layout.addRow("解耦后端:", self.backend_combo)

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

    def on_unit_changed(self, text):
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
