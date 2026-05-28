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
        self.help_label = QLabel(
            """鼠标操作：
滚轮：按鼠标所在位置缩放，并将该位置逐渐移动到中心；
按住滚轮拖动：旋转模型；
Shift/Ctrl + 按住滚轮拖动：侧滚/侧躺；
右键拖动：平移模型；
左键双击：重置视角；
适合细长夹钳模型局部观察（如放大夹钳顶端）。"""
        )
        self.help_label.setWordWrap(True)

        root = QVBoxLayout(self)
        root.addWidget(self.viewer, 1)
        root.addWidget(self.help_label)
        root.addWidget(self.status)

        grid = QGridLayout()
        root.addLayout(grid)

        buttons = [
            ("深色主题", lambda: self._set_theme("dark")),
            ("浅色主题", lambda: self._set_theme("light")),
            ("重新加载模型", self._reload),
            ("模拟三维力", self._simulate_force),
        ]
        for idx, (text, slot) in enumerate(buttons):
            btn = QPushButton(text)
            btn.clicked.connect(slot)
            grid.addWidget(btn, 0, idx)

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


if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = DemoWindow()
    win.show()
    QTimer.singleShot(200, win._refresh_status)
    sys.exit(app.exec())
