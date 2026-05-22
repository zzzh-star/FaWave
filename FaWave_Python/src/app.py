import sys
import json
import os
from PySide6.QtWidgets import QApplication
from .ui.main_window import MainWindow
from .utils.logger import setup_logger

from .utils.resource import config_path as get_config_path

def load_config():
    target_config = get_config_path()
    try:
        with open(target_config, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Failed to load config from {target_config}: {e}")
        # Return a minimal default config if not found
        return {
            "device_ip": "192.168.1.82",
            "device_port": 16008,
            "communication_mode": "Mock",
            "force_decoder": {"input_unit": "V", "input_scale_to_v": 1.0}
        }

def run_app():
    logger = setup_logger()
    logger.info("程序启动 - FaWave 四通道力传感采集系统")

    config = load_config()

    app = QApplication(sys.argv)
    app.setStyle("Fusion") # Base style to build upon

    window = MainWindow(config, logger)
    window.show()

    sys.exit(app.exec())
