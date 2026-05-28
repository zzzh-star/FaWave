from __future__ import annotations

import random
import sys
from pathlib import Path

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.ui.widgets.model_viewer import ModelViewer  # noqa: E402


class DemoWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Model Viewer Demo")
        self.resize(1100, 700)

        self.viewer = ModelViewer(model_root="assets/models")
        self.status = QLabel()

        root = QVBoxLayout(self)
        root.addWidget(self.viewer, 1)
        root.addWidget(self.status)

        bar = QHBoxLayout()
        root.addLayout(bar)

        btn_dark = QPushButton("Dark Theme")
        btn_light = QPushButton("Light Theme")
        btn_reload = QPushButton("Reload Model")
        btn_force = QPushButton("Simulate Fx/Fy/Fz")

        bar.addWidget(btn_dark)
        bar.addWidget(btn_light)
        bar.addWidget(btn_reload)
        bar.addWidget(btn_force)

        btn_dark.clicked.connect(lambda: self._set_theme("dark"))
        btn_light.clicked.connect(lambda: self._set_theme("light"))
        btn_reload.clicked.connect(self._reload)
        btn_force.clicked.connect(self._simulate_force)

        self._refresh_status()

    def _set_theme(self, theme: str):
        self.viewer.set_theme(theme)
        self._refresh_status()

    def _reload(self):
        self.viewer.reload_model()
        self._refresh_status()

    def _simulate_force(self):
        fx = random.uniform(-120, 120)
        fy = random.uniform(-120, 120)
        fz = random.uniform(-120, 120)
        self.viewer.update_force_vectors(fx, fy, fz)
        self._refresh_status(extra=f" | Fx={fx:.1f}, Fy={fy:.1f}, Fz={fz:.1f}")

    def _refresh_status(self, extra: str = ""):
        s = self.viewer.get_status()
        self.status.setText(
            f"loaded={s['loaded']} type={s['model_type']} parts={s['part_count']} path={s['model_path']} msg={s['message']}{extra}"
        )


if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = DemoWindow()
    win.show()
    QTimer.singleShot(200, win._refresh_status)
    sys.exit(app.exec())
