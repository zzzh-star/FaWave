import os
import numpy as np
import pyqtgraph as pg

try:
    import pyqtgraph.opengl as gl
    HAS_GL = True
except ImportError:
    HAS_GL = False

try:
    import stl
    HAS_STL = True
except ImportError:
    HAS_STL = False

from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PySide6.QtCore import Qt
from ...utils.resource import resource_path

class ModelViewer(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)

        self.gl_widget = None
        self.mesh_item = None

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

        lbl = QLabel(f"当前环境不支持 OpenGL，已切换为简化视图\n{msg}")
        lbl.setAlignment(Qt.AlignCenter)
        lbl.setStyleSheet("color: #94A3B8; background: transparent; border: 1px dashed #475569; border-radius: 4px;")
        self.layout.addWidget(lbl)

    def setup_scene(self):
        # Set camera slightly elevated, looking down
        self.gl_widget.setCameraPosition(distance=10, elevation=25, azimuth=45)

        # Grid
        self.grid = gl.GLGridItem(size=pg.Vector(20, 20, 1))
        self.grid.setSpacing(1, 1, 1)
        self.gl_widget.addItem(self.grid)

        # Force Arrows (Lines representing Vectors)
        self.arrow_fx = gl.GLLinePlotItem(pos=np.array([[0,0,0], [0,0,0]]), color=pg.glColor('#0EA5E9'), width=3, antialias=True)
        self.arrow_fy = gl.GLLinePlotItem(pos=np.array([[0,0,0], [0,0,0]]), color=pg.glColor('#F59E0B'), width=3, antialias=True)
        self.arrow_fz = gl.GLLinePlotItem(pos=np.array([[0,0,0], [0,0,0]]), color=pg.glColor('#EF4444'), width=3, antialias=True)

        self.gl_widget.addItem(self.arrow_fx)
        self.gl_widget.addItem(self.arrow_fy)
        self.gl_widget.addItem(self.arrow_fz)

        self.load_stl_model()
        self.apply_theme('light')

    def load_stl_model(self):
        model_path = resource_path("assets/models/device_model.stl")

        import logging
        logger = logging.getLogger("ModelViewer")

        if not HAS_STL:
            logger.warning("缺少 numpy-stl 依赖，无法读取 STL 文件")
            self._load_fallback_geometry("缺少 numpy-stl 依赖，无法读取 STL 文件，请执行：python -m pip install numpy-stl")
            return

        if not os.path.exists(model_path):
            logger.warning(f"未找到 3D 模型文件: {model_path}")
            self._load_fallback_geometry("未找到 3D 模型文件：\nassets/models/device_model.stl\n已切换为简化模型")
            return

        logger.info(f"正在加载 3D 模型：{model_path}")

        try:
            stl_mesh = stl.mesh.Mesh.from_file(model_path)

            # Extract vertices and faces
            # numpy-stl stores vertices in flat arrays of 9 elements (3 triangles x 3 coords)
            vertices = stl_mesh.vectors.reshape(-1, 3)

            # Auto-center
            min_bound = vertices.min(axis=0)
            max_bound = vertices.max(axis=0)
            center = (min_bound + max_bound) / 2.0
            vertices = vertices - center

            # Normalize scale to target size 4.0
            max_dim = (max_bound - min_bound).max()
            if max_dim > 0:
                scale = 4.0 / max_dim
                vertices = vertices * scale

            # Create faces array (0,1,2), (3,4,5)...
            faces = np.arange(len(vertices)).reshape(-1, 3)

            meshdata = gl.MeshData(vertexes=vertices, faces=faces)
            self.mesh_item = gl.GLMeshItem(meshdata=meshdata, smooth=True, drawEdges=False, shader='shaded', computeNormals=True)
            self.gl_widget.addItem(self.mesh_item)
            logger.info("3D 模型加载成功")

        except Exception as e:
            logger.error(f"3D 模型解析失败: {e}")
            self._load_fallback_geometry("3D 模型解析失败，请检查 STL 文件格式")

    def _load_fallback_geometry(self, msg="已切换为简化视图"):
        if hasattr(self, 'layout'):
            lbl = QLabel(msg)
            lbl.setAlignment(Qt.AlignCenter)
            lbl.setStyleSheet("color: #94A3B8; background: transparent; border: 1px dashed #475569; border-radius: 4px; padding: 10px;")
            self.layout.addWidget(lbl)

        # Base Cylinder/Box
        self.base_item = gl.GLBoxItem(size=pg.Vector(4, 4, 1), color=(51, 65, 85, 200))
        self.base_item.translate(-2, -2, -0.5)
        self.gl_widget.addItem(self.base_item)

        # Rod / Tool
        self.rod_item = gl.GLBoxItem(size=pg.Vector(0.6, 0.6, 8), color=(148, 163, 184, 255))
        self.rod_item.translate(-0.3, -0.3, 0.5)
        self.gl_widget.addItem(self.rod_item)
        self.mesh_item = None

    def apply_theme(self, theme):
        if not self.gl_widget: return
        if theme == 'dark':
            self.gl_widget.setBackgroundColor('#1E293B')
            self.grid.setColor(pg.glColor(255, 255, 255, 50))
            if hasattr(self, 'base_item'):
                self.base_item.setColor(pg.glColor(51, 65, 85, 200))
                self.rod_item.setColor(pg.glColor(148, 163, 184, 255))
            if self.mesh_item:
                self.mesh_item.setColor((148/255, 163/255, 184/255, 1.0))
        else:
            self.gl_widget.setBackgroundColor('#FFFFFF')
            self.grid.setColor(pg.glColor(0, 0, 0, 50))
            if hasattr(self, 'base_item'):
                self.base_item.setColor(pg.glColor(203, 213, 225, 200))
                self.rod_item.setColor(pg.glColor(100, 116, 139, 255))
            if self.mesh_item:
                self.mesh_item.setColor((100/255, 116/255, 139/255, 1.0))

    def update_force_vectors(self, fx, fy, fz):
        if not self.gl_widget: return

        # Scale forces for visual impact
        scale = 0.5

        fx_v = fx * scale
        fy_v = fy * scale
        fz_v = fz * scale

        # Base vector points starting at origin (center of model)
        # or top of rod if fallback
        origin = [0, 0, 4.5] if not self.mesh_item else [0, 0, 2.0]

        pos_fx = np.array([origin, [origin[0] + fx_v, origin[1], origin[2]]])
        pos_fy = np.array([origin, [origin[0], origin[1] + fy_v, origin[2]]])
        pos_fz = np.array([origin, [origin[0], origin[1], origin[2] + fz_v]])

        self.arrow_fx.setData(pos=pos_fx)
        self.arrow_fy.setData(pos=pos_fy)
        self.arrow_fz.setData(pos=pos_fz)
