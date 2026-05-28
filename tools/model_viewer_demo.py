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
        self.setWindowTitle("三维模型显示模块测试")
        self.resize(1100, 700)

        self.viewer = ModelViewer(model_root=str(REPO_ROOT / "assets" / "models"))
        self.status = QLabel()

        root = QVBoxLayout(self)
        root.addWidget(self.viewer, 1)
        root.addWidget(self.status)

        bar = QHBoxLayout()
        root.addLayout(bar)

        btn_dark = QPushButton("深色主题")
        btn_light = QPushButton("浅色主题")
        btn_reload = QPushButton("重新加载模型")
        btn_force = QPushButton("模拟三维力")

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
            f"加载状态={s['loaded']} | 模型类型={s['model_type']} | 零件数量={s['part_count']} | 回退模式={s['fallback']} | 模型路径={s['model_path']} | 提示={s['message']}{extra}"
        )


if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = DemoWindow()
    win.show()
    QTimer.singleShot(200, win._refresh_status)
    sys.exit(app.exec())
