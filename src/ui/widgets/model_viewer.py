from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QMouseEvent, QVector3D, QWheelEvent
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

from .model_loader import MeshPart, ModelLoader

try:
    import pyqtgraph.opengl as gl
except Exception:  # noqa: BLE001
    gl = None


@dataclass
class Theme:
    bg: tuple[float, float, float, float]
    grid: tuple[float, float, float, float]


THEMES = {
    "dark": Theme((0.08, 0.11, 0.16, 1.0), (0.8, 0.8, 0.8, 0.16)),
    "light": Theme((0.96, 0.96, 0.97, 1.0), (0.6, 0.6, 0.6, 0.25)),
}


class InteractiveGLViewWidget(gl.GLViewWidget):
    def __init__(self):
        super().__init__()
        self.min_distance = 0.55
        self.max_distance = 40.0
        self.zoom_sensitivity = 0.88
        self.zoom_to_cursor_strength = 0.25
        self.zoom_center_lerp = 0.25
        self.pan_sensitivity = 1.0
        self.rotate_sensitivity = 0.35
        self.roll_sensitivity = 0.45
        self.scene_radius = 1.0
        self._last_pos = QPointF()

    def wheelEvent(self, ev: QWheelEvent):
        delta = ev.angleDelta().y()
        if delta == 0:
            return
        steps = delta / 120.0
        old_distance = float(self.opts.get("distance", 4.0))
        new_distance = float(np.clip(old_distance * (self.zoom_sensitivity**steps), self.min_distance, self.max_distance))

        pos = ev.position()
        w = max(1.0, float(self.width()))
        h = max(1.0, float(self.height()))
        nx = (pos.x() / w - 0.5) * 2.0
        ny = (0.5 - pos.y() / h) * 2.0

        distance_ratio = (old_distance - new_distance) / max(old_distance, 1e-6)
        camera_offset = self.cameraPosition() - self.opts["center"]
        side_len = np.linalg.norm([camera_offset.x(), camera_offset.y(), 0.0])
        right = np.array([-camera_offset.y(), camera_offset.x(), 0.0], dtype=float)
        if side_len > 1e-6:
            right /= side_len
        else:
            right = np.array([1.0, 0.0, 0.0])
        up_vec = np.array([0.0, 0.0, 1.0])

        zoom_direction = 1.0 if new_distance < old_distance else 0.6
        base_shift = old_distance * self.zoom_to_cursor_strength * distance_ratio * zoom_direction
        edge_boost = 1.0 + 0.7 * max(abs(nx), abs(ny))
        pan_scale = base_shift * edge_boost

        center = self.opts["center"]
        target = np.array([
            center.x() + float((-nx) * pan_scale * right[0] + ny * pan_scale * up_vec[0]),
            center.y() + float((-nx) * pan_scale * right[1] + ny * pan_scale * up_vec[1]),
            center.z() + float((-nx) * pan_scale * right[2] + ny * pan_scale * up_vec[2]),
        ])
        current = np.array([center.x(), center.y(), center.z()])
        lerp = self.zoom_center_lerp * (1.1 if new_distance < old_distance else 0.8)
        blended = current + (target - current) * float(np.clip(lerp, 0.05, 0.6))
        center.setX(float(blended[0]))
        center.setY(float(blended[1]))
        center.setZ(float(blended[2]))

        self.opts["distance"] = new_distance
        self.update()
        ev.accept()

    def mousePressEvent(self, ev: QMouseEvent):
        self._last_pos = ev.position()
        super().mousePressEvent(ev)

    def mouseMoveEvent(self, ev: QMouseEvent):
        diff = ev.position() - self._last_pos
        self._last_pos = ev.position()
        mid = bool(ev.buttons() & Qt.MiddleButton)
        right = bool(ev.buttons() & Qt.RightButton)
        shift = bool(ev.modifiers() & Qt.ShiftModifier)
        ctrl = bool(ev.modifiers() & Qt.ControlModifier)

        if mid:
            viewer = self.parent()
            if viewer is not None and hasattr(viewer, "rotate_model"):
                if shift or ctrl:
                    viewer.roll_view(diff.x() * self.roll_sensitivity)
                else:
                    viewer.rotate_model("y", -diff.x() * self.rotate_sensitivity)
                    viewer.rotate_model("x", -diff.y() * self.rotate_sensitivity)
                ev.accept()
                return

        if right:
            self.pan(diff.x() * self.pan_sensitivity, diff.y() * self.pan_sensitivity, 0, relative="view")
            self.update()
            ev.accept()
            return

        super().mouseMoveEvent(ev)

    def mouseDoubleClickEvent(self, ev: QMouseEvent):
        if ev.button() == Qt.LeftButton:
            parent = self.parent()
            if parent is not None and hasattr(parent, "reset_view"):
                parent.reset_view()
                ev.accept()
                return
        super().mouseDoubleClickEvent(ev)


class ModelViewer(QWidget):
    def __init__(self, model_root: str | None = None, parent=None):
        super().__init__(parent)
        self.loader = ModelLoader(model_root=model_root)
        self._status = {"loaded": False, "model_type": "fallback", "model_path": "", "part_count": 0, "fallback": True, "message": "初始化"}
        self._mesh_items = []
        self._base_parts: list[MeshPart] = []
        self._force_items = {}
        self._theme = "dark"
        self._model_rotation = np.eye(3)
        self._scene_extent = 1.6

        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)

        if gl is None:
            self._view = None
            self._hint = QLabel("当前环境不支持 OpenGL，已切换为简化视图")
            self._hint.setAlignment(Qt.AlignCenter)
            self.layout.addWidget(self._hint)
            self._status["message"] = self._hint.text()
        else:
            self._view = InteractiveGLViewWidget()
            self.layout.addWidget(self._view)
            self._hint = QLabel("")
            self._hint.setAlignment(Qt.AlignCenter)
            self.layout.addWidget(self._hint)
            self._grid = gl.GLGridItem()
            self._grid.setSize(x=2, y=2)
            self._grid.setSpacing(x=0.2, y=0.2)
            self._view.addItem(self._grid)
            self._setup_force_items()
            self.set_theme("dark")
            self.load_best_available_model()

    def load_best_available_model(self):
        if self._view is None:
            return
        result = self.loader.load_best_available_model()
        for line in result.logs:
            print(f"[ModelViewer] {line}")

        self._clear_meshes()
        self._model_rotation = np.eye(3)
        if result.success:
            self._base_parts = self._normalize_parts(result.parts)
            self._view.scene_radius = max(0.8, float(self._scene_extent) * 0.5)
            self._redraw_model_parts()
            self._status = {
                "loaded": True,
                "model_type": result.model_type,
                "model_path": result.model_path,
                "part_count": len(self._base_parts),
                "fallback": False,
                "message": "彩色装配体模型加载成功" if result.model_type in {"glb", "gltf", "obj"} else "STL 几何模型加载成功",
            }
            self._hint.setText("")
        else:
            self._base_parts = []
            self._add_fallback_cube()
            self._status = {
                "loaded": False,
                "model_type": "fallback",
                "model_path": "",
                "part_count": 0,
                "fallback": True,
                "message": result.message,
            }
            self._hint.setText(result.message)
        self.reset_view()

    def reload_model(self):
        self.load_best_available_model()

    def set_theme(self, theme: str):
        self._theme = theme if theme in THEMES else "dark"
        t = THEMES[self._theme]
        if self._view is not None:
            self._view.setBackgroundColor(tuple(int(c * 255) for c in t.bg[:3]))
            self._grid.setColor(t.grid)

    def update_force_vectors(self, fx: float, fy: float, fz: float):
        if self._view is None:
            return
        self._set_force("fx", np.array([fx, 0, 0], dtype=float), (0.2, 0.47, 0.95, 1.0))
        self._set_force("fy", np.array([0, fy, 0], dtype=float), (0.95, 0.55, 0.18, 1.0))
        self._set_force("fz", np.array([0, 0, fz], dtype=float), (0.92, 0.26, 0.23, 1.0))

    def get_status(self) -> dict:
        return dict(self._status)

    def reset_view(self):
        if self._view is None:
            return
        self._model_rotation = np.eye(3)
        self._redraw_model_parts()
        self._view.opts["center"] = QVector3D(0.0, 0.0, 0.0)
        self._view.opts["distance"] = max(3.0, self._view.scene_radius * 3.2)
        self._view.opts["elevation"] = 22.0
        self._view.opts["azimuth"] = 35.0
        self._view.update()

    def roll_view(self, angle_deg: float):
        self.rotate_model("z", angle_deg)

    def rotate_model(self, axis: str, angle_deg: float):
        if not self._base_parts:
            return
        rad = np.deg2rad(angle_deg)
        c, s = np.cos(rad), np.sin(rad)
        if axis == "x":
            r = np.array([[1, 0, 0], [0, c, -s], [0, s, c]], dtype=float)
        elif axis == "y":
            r = np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]], dtype=float)
        else:
            r = np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]], dtype=float)
        self._model_rotation = r @ self._model_rotation
        self._redraw_model_parts()

    def _setup_force_items(self):
        for key in ("fx", "fy", "fz"):
            item = gl.GLLinePlotItem(pos=np.zeros((2, 3)), width=2, antialias=True)
            self._force_items[key] = item
            self._view.addItem(item)

    def _set_force(self, key: str, vec: np.ndarray, color):
        length = float(np.linalg.norm(vec))
        if length < 1e-3:
            self._force_items[key].setData(pos=np.zeros((2, 3)), color=(0, 0, 0, 0))
            return
        max_len = 0.7
        scale = min(1.0, length / 100.0)
        end = vec / length * (0.1 + max_len * scale)
        self._force_items[key].setData(pos=np.vstack([[0, 0, 0], end]), color=color)

    def _clear_meshes(self):
        if self._view is None:
            return
        for item in self._mesh_items:
            self._view.removeItem(item)
        self._mesh_items.clear()

    def _redraw_model_parts(self):
        self._clear_meshes()
        rotated = []
        for p in self._base_parts:
            v = p.vertices @ self._model_rotation.T
            rotated.append(MeshPart(vertices=v, faces=p.faces, color=p.color, name=p.name))
        self._add_parts(rotated)

    def _add_parts(self, parts: list[MeshPart]):
        if self._view is None:
            return
        for part in parts:
            md = gl.MeshData(vertexes=part.vertices, faces=part.faces)
            item = gl.GLMeshItem(meshdata=md, smooth=False, shader="shaded", drawEdges=False, color=part.color)
            self._mesh_items.append(item)
            self._view.addItem(item)

    def _normalize_parts(self, parts: list[MeshPart]) -> list[MeshPart]:
        all_vertices = np.vstack([p.vertices for p in parts])
        min_v, max_v = all_vertices.min(axis=0), all_vertices.max(axis=0)
        center = (min_v + max_v) / 2.0
        extent_vec = max_v - min_v
        extent = float(np.max(extent_vec))
        self._scene_extent = max(1e-6, extent)
        scale = 1.0 if extent < 1e-6 else 1.6 / extent
        return [MeshPart(vertices=(p.vertices - center) * scale, faces=p.faces, color=p.color, name=p.name) for p in parts]

    def _add_fallback_cube(self):
        vertices = np.array([
            [-0.4, -0.4, -0.4], [0.4, -0.4, -0.4], [0.4, 0.4, -0.4], [-0.4, 0.4, -0.4],
            [-0.4, -0.4, 0.4], [0.4, -0.4, 0.4], [0.4, 0.4, 0.4], [-0.4, 0.4, 0.4],
        ], dtype=float)
        faces = np.array([
            [0, 1, 2], [0, 2, 3], [4, 5, 6], [4, 6, 7], [0, 1, 5], [0, 5, 4],
            [2, 3, 7], [2, 7, 6], [1, 2, 6], [1, 6, 5], [0, 3, 7], [0, 7, 4],
        ], dtype=np.int32)
        self._add_parts([MeshPart(vertices=vertices, faces=faces, color=(0.72, 0.78, 0.86, 1.0), name="fallback")])
