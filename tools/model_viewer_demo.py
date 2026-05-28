from __future__ import annotations

import random
import sys
from pathlib import Path

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication, QGridLayout, QLabel, QPushButton, QVBoxLayout, QWidget

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.ui.widgets.model_viewer import ModelViewer  # noqa: E402


class DemoWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("三维模型显示模块测试")
        self.resize(1200, 760)

        model_root = REPO_ROOT / "assets" / "models"
        self.viewer = ModelViewer(model_root=str(model_root))
        self.status = QLabel()

        root = QVBoxLayout(self)
        root.addWidget(self.viewer, 1)
        root.addWidget(self.status)

        grid = QGridLayout()
        root.addLayout(grid)

        buttons = [
            ("深色主题", lambda: self._set_theme("dark")),
            ("浅色主题", lambda: self._set_theme("light")),
            ("重新加载模型", self._reload),
            ("模拟三维力", self._simulate_force),
            ("重置视角", self._reset_view),
            ("前视图", self._front),
            ("后视图", self._back),
            ("左视图", self._left),
            ("右视图", self._right),
            ("顶视图", self._top),
            ("底视图", self._bottom),
            ("模型侧躺", self._side_lay),
            ("恢复正放", self._upright),
        ]

        for idx, (text, slot) in enumerate(buttons):
            btn = QPushButton(text)
            btn.clicked.connect(slot)
            grid.addWidget(btn, idx // 5, idx % 5)

        self._refresh_status()

    def _refresh_status(self, extra: str = ""):
        s = self.viewer.get_status()
        self.status.setText(
            f"加载状态={s['loaded']} | 模型类型={s['model_type']} | 零件数量={s['part_count']} | 回退模式={s['fallback']} | 模型路径={s['model_path']} | 提示={s['message']}{extra}"
        )

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

    def _reset_view(self):
        self.viewer.reset_view()
        self._refresh_status()

    def _front(self):
        self.viewer.set_view_front(); self._refresh_status()

    def _back(self):
        self.viewer.set_view_back(); self._refresh_status()

    def _left(self):
        self.viewer.set_view_left(); self._refresh_status()

    def _right(self):
        self.viewer.set_view_right(); self._refresh_status()

    def _top(self):
        self.viewer.set_view_top(); self._refresh_status()

    def _bottom(self):
        self.viewer.set_view_bottom(); self._refresh_status()

    def _side_lay(self):
        self.viewer.set_model_side_lay(); self._refresh_status()

    def _upright(self):
        self.viewer.restore_model_upright(); self._refresh_status()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = DemoWindow()
    win.show()
    QTimer.singleShot(200, win._refresh_status)
    sys.exit(app.exec())
