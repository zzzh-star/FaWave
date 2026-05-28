import sys
import logging
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer
from FaWave_Python.src.ui.main_window import MainWindow

logger = logging.getLogger("test")
config = {
    "connection": {
        "device_ip": "127.0.0.1",
        "device_port": 16006,
        "mode": "Mock",
        "interval_ms": 20
    },
    "data_buffer": {
        "max_points": 2000
    },
    "protocol": {
        "scale_to_v": 1.0,
        "endian": "<",
        "mock_noise": 0.05
    },
    "save": {
        "default_format": "csv"
    }
}

app = QApplication(sys.argv)
window = MainWindow(config, logger)
window.show()
QTimer.singleShot(1000, app.quit)
app.exec()
