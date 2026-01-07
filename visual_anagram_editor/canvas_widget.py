from typing import Callable, Optional

import numpy as np
from PyQt6.QtCore import QPoint, QPointF, QSize, Qt
from PyQt6.QtGui import QColor, QImage, QPainter, QPen
from PyQt6.QtWidgets import QWidget


class CanvasWidget(QWidget):
    def __init__(
        self,
        get_image: Callable[[], Optional[np.ndarray]],
        on_stroke_begin: Callable[[int, int], None],
        on_stroke_move: Callable[[int, int], None],
        on_stroke_end: Callable[[], None],
        get_brush_radius: Optional[Callable[[], int]] = None,
        get_tool: Optional[Callable[[], object]] = None,
        on_hover: Optional[Callable[[int, int], None]] = None,
        parent=None,
    ):
        """
        get_image: function returning the current np.ndarray (H, W, 4)
        on_brush: callback to apply brush at (y, x) in image coordinates
        get_brush_radius: optional callable returning current brush radius
        get_tool: optional callable returning current tool enum
        on_hover: optional callable receiving hover image coords (y, x)
        """
        super().__init__(parent)
        self._get_image = get_image
        self._on_stroke_begin = on_stroke_begin
        self._on_stroke_move = on_stroke_move
        self._on_stroke_end = on_stroke_end
        self._get_brush_radius = get_brush_radius
        self._get_tool = get_tool
        self._on_hover = on_hover
        self._zoom = 1.0
        self._last_pos: Optional[QPoint] = None
        self._hover_pos: Optional[QPoint] = None
        self.setMouseTracking(True)

    def paintEvent(self, event):
        del event
        img = self._get_image()
        if img is None:
            return
        H, W, _ = img.shape
        qimg = QImage(img.data, W, H, 4 * W, QImage.Format.Format_RGBA8888)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, False)
        painter.scale(self._zoom, self._zoom)
        painter.drawImage(0, 0, qimg)

        if self._hover_pos is not None and self._get_brush_radius is not None:
            tool = self._get_tool() if self._get_tool is not None else None
            radius = self._get_brush_radius() if self._get_brush_radius is not None else 0
            if tool is None or getattr(tool, "name", "") in ("BRUSH", "ERASER", "EYEDROPPER"):
                pen = QPen(QColor(0, 255, 0, 180))
                pen.setStyle(Qt.PenStyle.DashLine)
                painter.setPen(pen)
                y, x = self._hover_pos.y(), self._hover_pos.x()
                painter.drawEllipse(QPointF(x + 0.5, y + 0.5), radius, radius)
        painter.end()

    def sizeHint(self):
        img = self._get_image()
        if img is None:
            return super().sizeHint()
        H, W, _ = img.shape
        return QSize(int(W * self._zoom), int(H * self._zoom))

    def _widget_to_image_coords(self, pos: QPoint) -> tuple[int, int]:
        x = int(pos.x() / self._zoom)
        y = int(pos.y() / self._zoom)
        return y, x

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._last_pos = event.position().toPoint()
            y, x = self._widget_to_image_coords(self._last_pos)
            if self._on_stroke_begin is not None:
                self._on_stroke_begin(y, x)
            self._handle_hover(self._last_pos)
        elif event.button() == Qt.MouseButton.RightButton:
            pos = event.position().toPoint()
            self._handle_hover(pos)

    def mouseMoveEvent(self, event):
        if self._last_pos is not None and (event.buttons() & Qt.MouseButton.LeftButton):
            pos = event.position().toPoint()
            y, x = self._widget_to_image_coords(pos)
            if self._on_stroke_move is not None:
                self._on_stroke_move(y, x)
            self._last_pos = pos
            self._handle_hover(pos)
        else:
            pos = event.position().toPoint()
            self._handle_hover(pos)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._last_pos = None
            if self._on_stroke_end is not None:
                self._on_stroke_end()
        self._handle_hover(event.position().toPoint())

    def leaveEvent(self, event):
        del event
        self._hover_pos = None
        self.update()

    def wheelEvent(self, event):
        delta = event.angleDelta().y()
        if delta > 0:
            self._zoom *= 1.1
        elif delta < 0:
            self._zoom /= 1.1
        self._zoom = max(0.1, min(10.0, self._zoom))
        self.updateGeometry()
        self.update()

    def _handle_hover(self, pos: QPoint):
        y, x = self._widget_to_image_coords(pos)
        self._hover_pos = QPoint(x, y)
        if self._on_hover is not None:
            self._on_hover(y, x)
        self.update()
