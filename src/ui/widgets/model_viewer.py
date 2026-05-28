from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
from PySide6.QtCore import Qt
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


class ModelViewer(QWidget):
    def __init__(self, model_root: str | None = None, parent=None):
        super().__init__(parent)
        self.loader = ModelLoader(model_root=model_root)
        self._status = {"loaded": False, "model_type": "fallback", "model_path": "", "part_count": 0, "fallback": True, "message": "初始化"}
        self._mesh_items = []
        self._force_items = {}
        self._theme = "dark"

        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)

        if gl is None:
            self._view = None
            self._hint = QLabel("当前环境不支持 OpenGL，已切换为简化视图")
            self._hint.setAlignment(Qt.AlignCenter)
            self.layout.addWidget(self._hint)
            self._status["message"] = self._hint.text()
        else:
            self._view = gl.GLViewWidget()
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
        if result.success:
            normalized = self._normalize_parts(result.parts)
            self._add_parts(normalized)
            self._status = {
                "loaded": True,
                "model_type": result.model_type,
                "model_path": result.model_path,
                "part_count": len(normalized),
                "fallback": False,
                "message": "彩色装配体模型加载成功" if result.model_type in {"glb", "gltf", "obj"} else "STL 几何模型加载成功",
            }
            self._hint.setText("")
        else:
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
        for item in self._mesh_items:
            self._view.removeItem(item)
        self._mesh_items.clear()

    def _add_parts(self, parts: list[MeshPart]):
        for part in parts:
            md = gl.MeshData(vertexes=part.vertices, faces=part.faces)
            item = gl.GLMeshItem(meshdata=md, smooth=False, shader="shaded", drawEdges=False, color=part.color)
            self._mesh_items.append(item)
            self._view.addItem(item)

    def _normalize_parts(self, parts: list[MeshPart]) -> list[MeshPart]:
        all_vertices = np.vstack([p.vertices for p in parts])
        min_v, max_v = all_vertices.min(axis=0), all_vertices.max(axis=0)
        center = (min_v + max_v) / 2.0
        extent = np.max(max_v - min_v)
        scale = 1.0 if extent < 1e-6 else 1.6 / extent
        normalized = []
        for p in parts:
            v = (p.vertices - center) * scale
            normalized.append(MeshPart(vertices=v, faces=p.faces, color=p.color, name=p.name))
        if self._view is not None:
            self._view.opts["distance"] = 4.0
            self._view.opts["elevation"] = 20
            self._view.opts["azimuth"] = 35
        return normalized

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
