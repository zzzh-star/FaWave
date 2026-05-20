import sys
import json
import os
from PySide6.QtWidgets import QApplication
from .ui.main_window import MainWindow
from .utils.logger import setup_logger

def load_config():
    # If running as executable, the config might be in a different path
    # But PyInstaller --add-data puts it in the same relative location
    base_dir = getattr(sys, '_MEIPASS', os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    config_path = os.path.join(base_dir, 'config', 'default_config.json')

    if not os.path.exists(config_path):
        # Fallback to current working directory
        config_path = os.path.join(os.getcwd(), 'config', 'default_config.json')

    try:
        with open(config_path, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"Failed to load config from {config_path}: {e}")
        # Return a minimal default config if not found
        return {
            "device_ip": "192.168.1.82",
            "device_port": 16006,
            "communication_mode": "Mock"
        }

def run_app():
    logger = setup_logger()
    logger.info("Starting FaWave Python Application")

    config = load_config()

    app = QApplication(sys.argv)
    app.setStyle("Fusion") # Base style to build upon

    window = MainWindow(config)
    window.show()

    sys.exit(app.exec())
