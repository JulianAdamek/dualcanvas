import sys
import numpy as np
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction, QActionGroup, QColor
from PyQt6.QtWidgets import (
    QApplication,
    QColorDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QSlider,
    QSpinBox,
    QToolBar,
    QWidget,
)

from .canvas_widget import CanvasWidget
from .controller import Tool, VisualAnagramController


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.controller = VisualAnagramController()
        self._show_piece_outlines = False
        self._init_ui()

    def _init_ui(self):
        self.setWindowTitle("Visual Anagram Editor (Prototype)")

        central = QWidget()
        layout = QHBoxLayout(central)

        self.canvasA = CanvasWidget(
            get_image=lambda: self.controller.imgA,
            on_stroke_begin=self._stroke_begin_A,
            on_stroke_move=self._stroke_move_A,
            on_stroke_end=self._stroke_end_A,
            get_brush_radius=lambda: self.controller.brush_radius,
            get_tool=lambda: self.controller.current_tool,
            on_hover=self._hover_A,
            get_overlay_mask=lambda: self.controller.flagged_mask_A,
            show_overlay=lambda: self._show_piece_outlines,
        )
        self.canvasB = CanvasWidget(
            get_image=lambda: self.controller.imgB,
            on_stroke_begin=self._stroke_begin_B,
            on_stroke_move=self._stroke_move_B,
            on_stroke_end=self._stroke_end_B,
            get_brush_radius=lambda: self.controller.brush_radius,
            get_tool=lambda: self.controller.current_tool,
            on_hover=self._hover_B,
            get_overlay_mask=lambda: self.controller.flagged_mask_B,
            show_overlay=lambda: self._show_piece_outlines,
        )

        layout.addWidget(self.canvasA)
        layout.addWidget(self.canvasB)

        self.setCentralWidget(central)
        self._build_toolbar()
        self._build_menu()
        self._update_status()
        self._update_undo_redo_actions()

    def _build_menu(self):
        menubar = self.menuBar()
        file_menu = menubar.addMenu("&File")
        edit_menu = menubar.addMenu("&Edit")
        view_menu = menubar.addMenu("&View")

        act_perm = QAction("Load permutation...", self)
        act_perm.triggered.connect(self._load_perm)
        file_menu.addAction(act_perm)

        act_loadA = QAction("Load image into A...", self)
        act_loadA.triggered.connect(self._load_image_A)
        file_menu.addAction(act_loadA)

        act_loadB = QAction("Load image into B...", self)
        act_loadB.triggered.connect(self._load_image_B)
        file_menu.addAction(act_loadB)

        act_saveA = QAction("Save canvas A...", self)
        act_saveA.triggered.connect(self._save_image_A)
        file_menu.addAction(act_saveA)

        act_saveB = QAction("Save canvas B...", self)
        act_saveB.triggered.connect(self._save_image_B)
        file_menu.addAction(act_saveB)

        file_menu.addSeparator()

        act_quit = QAction("Quit", self)
        act_quit.triggered.connect(self.close)
        file_menu.addAction(act_quit)

        act_undo = QAction("Undo", self)
        act_undo.setShortcut("Ctrl+Z")
        act_undo.triggered.connect(self._undo)
        edit_menu.addAction(act_undo)

        act_redo = QAction("Redo", self)
        act_redo.setShortcut("Ctrl+Y")
        act_redo.triggered.connect(self._redo)
        edit_menu.addAction(act_redo)

        self._act_undo = act_undo
        self._act_redo = act_redo

        act_outlines = QAction("Show Piece Outlines", self)
        act_outlines.setCheckable(True)
        act_outlines.setChecked(self._show_piece_outlines)
        act_outlines.triggered.connect(self._toggle_piece_outlines)
        view_menu.addAction(act_outlines)
        self._act_outlines = act_outlines

    def _build_toolbar(self):
        toolbar = QToolBar("Tools", self)
        self.addToolBar(toolbar)

        act_brush = QAction("Brush", self)
        act_brush.setCheckable(True)
        act_eraser = QAction("Eraser", self)
        act_eraser.setCheckable(True)
        act_dropper = QAction("Eyedropper", self)
        act_dropper.setCheckable(True)

        tool_group = QActionGroup(self)
        for act in (act_brush, act_eraser, act_dropper):
            act.setActionGroup(tool_group)

        act_brush.setChecked(True)
        act_brush.triggered.connect(lambda: self._set_tool(Tool.BRUSH))
        act_eraser.triggered.connect(lambda: self._set_tool(Tool.ERASER))
        act_dropper.triggered.connect(lambda: self._set_tool(Tool.EYEDROPPER))

        toolbar.addAction(act_brush)
        toolbar.addAction(act_eraser)
        toolbar.addAction(act_dropper)

        self._act_brush = act_brush
        self._act_eraser = act_eraser
        self._act_dropper = act_dropper

        self._color_button = QPushButton("Color")
        self._color_button.clicked.connect(self._choose_color)
        toolbar.addWidget(self._color_button)
        self._update_color_button(
            QColor(
                int(self.controller.brush_color[0]),
                int(self.controller.brush_color[1]),
                int(self.controller.brush_color[2]),
                int(self.controller.brush_color[3]),
            )
        )

        toolbar.addSeparator()
        toolbar.addWidget(QLabel("Size:"))
        self._brush_slider = QSlider(Qt.Orientation.Horizontal)
        self._brush_slider.setMinimum(1)
        self._brush_slider.setMaximum(50)
        self._brush_slider.setValue(self.controller.brush_radius)
        self._brush_slider.setFixedWidth(100)
        self._brush_slider.valueChanged.connect(self._brush_size_changed_from_slider)

        self._brush_spin = QSpinBox()
        self._brush_spin.setMinimum(1)
        self._brush_spin.setMaximum(50)
        self._brush_spin.setValue(self.controller.brush_radius)
        self._brush_spin.valueChanged.connect(self._brush_size_changed_from_spinbox)

        toolbar.addWidget(self._brush_slider)
        toolbar.addWidget(self._brush_spin)
        toolbar.addWidget(QLabel("Opacity:"))
        self._opacity_slider = QSlider(Qt.Orientation.Horizontal)
        self._opacity_slider.setMinimum(0)
        self._opacity_slider.setMaximum(100)
        self._opacity_slider.setValue(self._current_opacity_percent())
        self._opacity_slider.setFixedWidth(100)
        self._opacity_slider.valueChanged.connect(self._opacity_changed_from_slider)

        self._opacity_spin = QSpinBox()
        self._opacity_spin.setMinimum(0)
        self._opacity_spin.setMaximum(100)
        self._opacity_spin.setSuffix("%")
        self._opacity_spin.setValue(self._current_opacity_percent())
        self._opacity_spin.valueChanged.connect(self._opacity_changed_from_spinbox)

        toolbar.addWidget(self._opacity_slider)
        toolbar.addWidget(self._opacity_spin)

        toolbar.addSeparator()
        act_outline_toggle = QAction("Piece Outlines", self)
        act_outline_toggle.setCheckable(True)
        act_outline_toggle.setChecked(self._show_piece_outlines)
        act_outline_toggle.triggered.connect(self._toggle_piece_outlines)
        toolbar.addAction(act_outline_toggle)
        self._act_outline_toggle = act_outline_toggle

    def _set_tool(self, tool: Tool):
        self.controller.set_tool(tool)
        self._update_status()

    def _choose_color(self):
        initial = QColor(
            int(self.controller.brush_color[0]),
            int(self.controller.brush_color[1]),
            int(self.controller.brush_color[2]),
            int(self.controller.brush_color[3]),
        )
        color = QColorDialog.getColor(initial, self, "Select brush color")
        if color.isValid():
            rgba = np.array([color.red(), color.green(), color.blue(), color.alpha()], dtype=np.uint8)
            self.controller.set_brush_color(rgba)
            self._update_color_button(color)
            self._update_status()

    def _update_color_button(self, color: QColor):
        qss = f"background-color: rgba({color.red()},{color.green()},{color.blue()},{color.alpha()});"
        self._color_button.setStyleSheet(qss)
        self._sync_opacity_controls_from_color()

    def _brush_size_changed_from_slider(self, value: int):
        self._brush_spin.blockSignals(True)
        self._brush_spin.setValue(value)
        self._brush_spin.blockSignals(False)
        self.controller.set_brush_radius(value)
        self._update_status()

    def _brush_size_changed_from_spinbox(self, value: int):
        self._brush_slider.blockSignals(True)
        self._brush_slider.setValue(value)
        self._brush_slider.blockSignals(False)
        self.controller.set_brush_radius(value)
        self._update_status()

    def _current_opacity_percent(self) -> int:
        return int(self.controller.brush_opacity_percent)

    def _sync_opacity_controls_from_color(self):
        if not hasattr(self, "_opacity_slider") or not hasattr(self, "_opacity_spin"):
            return
        opacity = self._current_opacity_percent()
        self._opacity_slider.blockSignals(True)
        self._opacity_slider.setValue(opacity)
        self._opacity_slider.blockSignals(False)
        self._opacity_spin.blockSignals(True)
        self._opacity_spin.setValue(opacity)
        self._opacity_spin.blockSignals(False)

    def _opacity_changed_from_slider(self, value: int):
        self._opacity_spin.blockSignals(True)
        self._opacity_spin.setValue(value)
        self._opacity_spin.blockSignals(False)
        self.controller.set_brush_opacity_percent(value)
        self._refresh_color_button_from_controller()
        self._update_status()

    def _opacity_changed_from_spinbox(self, value: int):
        self._opacity_slider.blockSignals(True)
        self._opacity_slider.setValue(value)
        self._opacity_slider.blockSignals(False)
        self.controller.set_brush_opacity_percent(value)
        self._refresh_color_button_from_controller()
        self._update_status()

    def _stroke_begin_A(self, y: int, x: int):
        if self.controller.permutation is None:
            return
        self.controller.begin_stroke()
        self.controller.apply_brush_A(y, x)
        self.canvasA.update()
        self.canvasB.update()
        if self.controller.current_tool == Tool.EYEDROPPER:
            self._refresh_color_button_from_controller()
        self._update_status(y, x, from_canvas="A")

    def _stroke_move_A(self, y: int, x: int):
        if self.controller.permutation is None:
            return
        self.controller.apply_brush_A(y, x)
        self.canvasA.update()
        self.canvasB.update()
        if self.controller.current_tool == Tool.EYEDROPPER:
            self._refresh_color_button_from_controller()
        self._update_status(y, x, from_canvas="A")

    def _stroke_end_A(self):
        if self.controller.permutation is None:
            return
        self.controller.end_stroke()
        self._update_undo_redo_actions()
        self.canvasA.update()
        self.canvasB.update()
        self._update_status()

    def _stroke_begin_B(self, y: int, x: int):
        if self.controller.permutation is None:
            return
        self.controller.begin_stroke()
        self.controller.apply_brush_B(y, x)
        self.canvasA.update()
        self.canvasB.update()
        if self.controller.current_tool == Tool.EYEDROPPER:
            self._refresh_color_button_from_controller()
        self._update_status(y, x, from_canvas="B")

    def _stroke_move_B(self, y: int, x: int):
        if self.controller.permutation is None:
            return
        self.controller.apply_brush_B(y, x)
        self.canvasA.update()
        self.canvasB.update()
        if self.controller.current_tool == Tool.EYEDROPPER:
            self._refresh_color_button_from_controller()
        self._update_status(y, x, from_canvas="B")

    def _stroke_end_B(self):
        if self.controller.permutation is None:
            return
        self.controller.end_stroke()
        self._update_undo_redo_actions()
        self.canvasA.update()
        self.canvasB.update()
        self._update_status()

    def _refresh_color_button_from_controller(self):
        col = self.controller.brush_color
        color = QColor(int(col[0]), int(col[1]), int(col[2]), int(col[3]))
        self._update_color_button(color)

    def _toggle_piece_outlines(self, checked: bool):
        self._show_piece_outlines = checked
        if hasattr(self, "_act_outlines"):
            self._act_outlines.blockSignals(True)
            self._act_outlines.setChecked(checked)
            self._act_outlines.blockSignals(False)
        if hasattr(self, "_act_outline_toggle"):
            self._act_outline_toggle.blockSignals(True)
            self._act_outline_toggle.setChecked(checked)
            self._act_outline_toggle.blockSignals(False)
        self.canvasA.update()
        self.canvasB.update()
        self._update_status()

    def _load_perm(self):
        path, _ = QFileDialog.getOpenFileName(self, "Load permutation", "", "NumPy files (*.npy)")
        if path:
            self.controller.load_permutation(path)
            self.canvasA.update()
            self.canvasB.update()
            self._update_status()
            self._update_undo_redo_actions()

    def _load_image_A(self):
        path, _ = QFileDialog.getOpenFileName(self, "Load image into A", "", "Images (*.png *.jpg *.jpeg)")
        if path:
            self.controller.load_image_into_A(path)
            self.canvasA.update()
            self.canvasB.update()
            self._update_undo_redo_actions()

    def _load_image_B(self):
        path, _ = QFileDialog.getOpenFileName(self, "Load image into B", "", "Images (*.png *.jpg *.jpeg)")
        if path:
            self.controller.load_image_into_B(path)
            self.canvasA.update()
            self.canvasB.update()
            self._update_undo_redo_actions()

    def _save_image_A(self):
        path, _ = QFileDialog.getSaveFileName(self, "Save canvas A", "", "PNG (*.png)")
        if path:
            self.controller.save_image_A(path)

    def _save_image_B(self):
        path, _ = QFileDialog.getSaveFileName(self, "Save canvas B", "", "PNG (*.png)")
        if path:
            self.controller.save_image_B(path)

    def _hover_A(self, y: int, x: int):
        self._update_status(y, x, from_canvas="A")

    def _hover_B(self, y: int, x: int):
        self._update_status(y, x, from_canvas="B")

    def _undo(self):
        if self.controller.can_undo():
            self.controller.undo()
            self.canvasA.update()
            self.canvasB.update()
        self._update_undo_redo_actions()
        self._update_status()

    def _redo(self):
        if self.controller.can_redo():
            self.controller.redo()
            self.canvasA.update()
            self.canvasB.update()
        self._update_undo_redo_actions()
        self._update_status()

    def _update_undo_redo_actions(self):
        if hasattr(self, "_act_undo"):
            self._act_undo.setEnabled(self.controller.can_undo())
        if hasattr(self, "_act_redo"):
            self._act_redo.setEnabled(self.controller.can_redo())

    def _update_status(self, y: int | None = None, x: int | None = None, from_canvas: str | None = None):
        tool = self.controller.current_tool.name
        size = self.controller.brush_radius
        col = self.controller.brush_color
        color_desc = f"rgba({int(col[0])},{int(col[1])},{int(col[2])},{int(col[3])})"
        coord_desc = ""
        if from_canvas and y is not None and x is not None and self.controller.permutation is not None:
            try:
                if from_canvas == "A":
                    yB, xB = self.controller.permutation.map_coords_A_to_B(y, x)
                    coord_desc = f" | A({y},{x}) -> B({yB},{xB})"
                elif from_canvas == "B":
                    yA, xA = self.controller.permutation.map_coords_B_to_A(y, x)
                    coord_desc = f" | B({y},{x}) -> A({yA},{xA})"
            except Exception:
                coord_desc = ""
        self.statusBar().showMessage(f"Tool: {tool}, size: {size}, color: {color_desc}{coord_desc}")


def main():
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
