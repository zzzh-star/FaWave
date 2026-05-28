import pyqtgraph as pg
import numpy as np

try:
    import pyqtgraph.opengl as gl
    HAS_GL = True
except ImportError:
    HAS_GL = False

from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PySide6.QtCore import Qt

class GLViewport(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)

        self.gl_widget = None

        if HAS_GL:
            try:
                self.gl_widget = gl.GLViewWidget()
                self.layout.addWidget(self.gl_widget)
                self.setup_scene()
            except Exception as e:
                self.fallback_ui(str(e))
        else:
            self.fallback_ui("缺少 pyqtgraph.opengl 依赖或 OpenGL 驱动不兼容")

    def fallback_ui(self, msg):
        if self.gl_widget:
            self.layout.removeWidget(self.gl_widget)
            self.gl_widget.deleteLater()
            self.gl_widget = None

        lbl = QLabel(f"[3D 装置占位图]\n无法加载 OpenGL\n{msg}")
        lbl.setAlignment(Qt.AlignCenter)
        lbl.setStyleSheet("color: #94A3B8; background: transparent; border: 1px dashed #475569; border-radius: 4px;")
        self.layout.addWidget(lbl)

    def setup_scene(self):
        # Set camera slightly elevated, looking down
        self.gl_widget.setCameraPosition(distance=150, elevation=25, azimuth=45)

        # Grid
        self.grid = gl.GLGridItem(size=pg.Vector(200, 200, 1))
        self.grid.setSpacing(10, 10, 1)
        self.gl_widget.addItem(self.grid)

        # Base Cylinder/Box
        self.base_item = gl.GLBoxItem(size=pg.Vector(40, 40, 10), color=(51, 65, 85, 200))
        self.base_item.translate(-20, -20, 0)
        self.gl_widget.addItem(self.base_item)

        # Rod / Tool
        self.rod_item = gl.GLBoxItem(size=pg.Vector(6, 6, 80), color=(148, 163, 184, 255))
        self.rod_item.translate(-3, -3, 10)
        self.gl_widget.addItem(self.rod_item)

        # Force Arrows (Lines representing Vectors)
        self.arrow_fx = gl.GLLinePlotItem(pos=np.array([[0,0,90], [0,0,90]]), color=pg.glColor('#0EA5E9'), width=3, antialias=True)
        self.arrow_fy = gl.GLLinePlotItem(pos=np.array([[0,0,90], [0,0,90]]), color=pg.glColor('#F59E0B'), width=3, antialias=True)
        self.arrow_fz = gl.GLLinePlotItem(pos=np.array([[0,0,90], [0,0,90]]), color=pg.glColor('#EF4444'), width=3, antialias=True)

        self.gl_widget.addItem(self.arrow_fx)
        self.gl_widget.addItem(self.arrow_fy)
        self.gl_widget.addItem(self.arrow_fz)

        self.apply_theme('light')

    def apply_theme(self, theme):
        if not self.gl_widget: return
        if theme == 'dark':
            self.gl_widget.setBackgroundColor('#1E293B')
            self.grid.setColor(pg.glColor(255, 255, 255, 50))
            self.base_item.setColor(pg.glColor(51, 65, 85, 200))
            self.rod_item.setColor(pg.glColor(148, 163, 184, 255))
        else:
            self.gl_widget.setBackgroundColor('#FFFFFF')
            self.grid.setColor(pg.glColor(0, 0, 0, 50))
            self.base_item.setColor(pg.glColor(203, 213, 225, 200))
            self.rod_item.setColor(pg.glColor(100, 116, 139, 255))

    def update_force_vectors(self, fx, fy, fz):
        if not self.gl_widget: return

        # Scale forces for visual impact
        scale = 5.0

        fx_v = fx * scale
        fy_v = fy * scale
        fz_v = fz * scale

        # Base vector points starting at the tip of the rod (0, 0, 90)
        origin = [0, 0, 90]

        pos_fx = np.array([origin, [origin[0] + fx_v, origin[1], origin[2]]])
        pos_fy = np.array([origin, [origin[0], origin[1] + fy_v, origin[2]]])
        pos_fz = np.array([origin, [origin[0], origin[1], origin[2] + fz_v]])

        self.arrow_fx.setData(pos=pos_fx)
        self.arrow_fy.setData(pos=pos_fy)
        self.arrow_fz.setData(pos=pos_fz)
