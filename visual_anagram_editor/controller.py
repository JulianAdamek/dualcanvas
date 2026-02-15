import numpy as np
from PIL import Image
from dataclasses import dataclass
from enum import Enum, auto
from typing import List, Optional

from .permutation_model import PermutationModel


@dataclass
class PixelChange:
    yA: int
    xA: int
    oldA: np.ndarray
    newA: np.ndarray
    yB: int
    xB: int
    oldB: np.ndarray
    newB: np.ndarray


@dataclass
class Stroke:
    changes: List[PixelChange]


class Tool(Enum):
    BRUSH = auto()
    ERASER = auto()
    EYEDROPPER = auto()


class VisualAnagramController:
    def __init__(self):
        self.permutation: Optional[PermutationModel] = None
        self.imgA: Optional[np.ndarray] = None
        self.imgB: Optional[np.ndarray] = None
        self.current_tool = Tool.BRUSH
        self.brush_color = np.array([0, 0, 0, 255], dtype=np.uint8)  # default black
        self.brush_opacity_percent = 100
        self.brush_radius = 4  # default size
        self.eraser_color = np.array([0, 0, 0, 0], dtype=np.uint8)  # transparent erase
        self.undo_stack: List[Stroke] = []
        self.redo_stack: List[Stroke] = []
        self.current_stroke: Optional[Stroke] = None
        self.max_undo = 50  # default limit
        self.flagged_pixels_A: List[tuple[int, int]] = []
        self.flagged_mask_A: Optional[np.ndarray] = None
        self.flagged_mask_B: Optional[np.ndarray] = None
        self._stroke_touched_A: Optional[set[tuple[int, int]]] = None

    def load_permutation(self, path: str):
        perm_model = PermutationModel.from_npy(path)
        self.permutation = perm_model
        H, W = perm_model.H, perm_model.W
        self.imgA = np.zeros((H, W, 4), dtype=np.uint8)
        self.imgB = np.zeros((H, W, 4), dtype=np.uint8)
        self.undo_stack.clear()
        self.redo_stack.clear()
        self.current_stroke = None
        self._compute_piece_outline_flags()

    def _load_image(self, path: str) -> np.ndarray:
        if self.permutation is None:
            raise ValueError("Permutation must be loaded before loading images")
        with Image.open(path) as im:
            im = im.convert("RGBA")
            im = im.resize((self.permutation.W, self.permutation.H), Image.Resampling.LANCZOS)
            arr = np.array(im, dtype=np.uint8)
        return arr

    def load_image_into_A(self, path: str):
        arr = self._load_image(path)
        self.imgA = arr
        self._propagate_A_to_B()
        self.undo_stack.clear()
        self.redo_stack.clear()
        self.current_stroke = None

    def load_image_into_B(self, path: str):
        arr = self._load_image(path)
        self.imgB = arr
        self._propagate_B_to_A()
        self.undo_stack.clear()
        self.redo_stack.clear()
        self.current_stroke = None

    def save_image_A(self, path: str):
        if self.imgA is None:
            raise ValueError("Canvas A is empty")
        Image.fromarray(self.imgA, mode="RGBA").save(path)

    def save_image_B(self, path: str):
        if self.imgB is None:
            raise ValueError("Canvas B is empty")
        Image.fromarray(self.imgB, mode="RGBA").save(path)

    def _propagate_A_to_B(self):
        if self.permutation is None or self.imgA is None:
            raise ValueError("Permutation and image must be loaded")
        H, W = self.permutation.H, self.permutation.W
        flatA = self.imgA.reshape(-1, 4)
        flatB = np.empty_like(flatA)
        flatB[self.permutation.perm] = flatA
        self.imgB = flatB.reshape(H, W, 4)

    def _propagate_B_to_A(self):
        if self.permutation is None or self.imgB is None:
            raise ValueError("Permutation and image must be loaded")
        H, W = self.permutation.H, self.permutation.W
        flatB = self.imgB.reshape(-1, 4)
        flatA = np.empty_like(flatB)
        flatA[self.permutation.inv_perm] = flatB
        self.imgA = flatA.reshape(H, W, 4)

    def set_tool(self, tool: Tool):
        self.current_tool = tool

    def set_brush_color(self, rgba: np.ndarray):
        self.brush_color = rgba.copy()
        # Keep alpha opaque; brush opacity is controlled separately.
        self.brush_color[3] = np.uint8(255)

    def set_brush_radius(self, radius: int):
        self.brush_radius = max(1, int(radius))

    def set_brush_opacity_percent(self, opacity_percent: int):
        self.brush_opacity_percent = max(0, min(100, int(opacity_percent)))

    def _blend_with_brush(self, base_pixel: np.ndarray) -> np.ndarray:
        """Blend RGB with brush color using brush_opacity_percent. Preserve alpha."""
        opacity = self.brush_opacity_percent
        if opacity <= 0:
            return base_pixel.copy()
        if opacity >= 100:
            out = self.brush_color.copy()
            out[3] = base_pixel[3]
            return out
        out = base_pixel.copy()
        old_rgb = base_pixel[:3].astype(np.float32)
        brush_rgb = self.brush_color[:3].astype(np.float32)
        blended = ((100 - opacity) * old_rgb + opacity * brush_rgb) / 100.0
        out[:3] = np.round(blended).astype(np.uint8)
        return out

    def _set_pixel_A_and_B(self, yA: int, xA: int, color: np.ndarray, blend: bool = False):
        if self.permutation is None or self.imgA is None or self.imgB is None:
            return

        H, W = self.permutation.H, self.permutation.W
        if not (0 <= yA < H and 0 <= xA < W):
            return

        yB, xB = self.permutation.map_coords_A_to_B(yA, xA)
        if not (0 <= yB < H and 0 <= xB < W):
            return

        key = (yA, xA)
        if self.current_stroke is not None and self._stroke_touched_A is not None and key in self._stroke_touched_A:
            # Apply each pixel at most once per stroke to avoid compounding blend.
            return

        oldA = self.imgA[yA, xA].copy()
        oldB = self.imgB[yB, xB].copy()
        new_color = self._blend_with_brush(oldA) if blend else color.copy()

        if self.current_stroke is not None:
            newA = new_color
            newB = new_color
            if not np.array_equal(oldA, newA) or not np.array_equal(oldB, newB):
                self.current_stroke.changes.append(
                    PixelChange(
                        yA=yA,
                        xA=xA,
                        oldA=oldA,
                        newA=newA.copy(),
                        yB=yB,
                        xB=xB,
                        oldB=oldB,
                        newB=newB.copy(),
                    )
                )
            if self._stroke_touched_A is not None:
                self._stroke_touched_A.add(key)

        self.imgA[yA, xA] = new_color
        self.imgB[yB, xB] = new_color

    def _set_pixel_B_and_A(self, yB: int, xB: int, color: np.ndarray, blend: bool = False):
        if self.permutation is None or self.imgA is None or self.imgB is None:
            return

        H, W = self.permutation.H, self.permutation.W
        if not (0 <= yB < H and 0 <= xB < W):
            return

        yA, xA = self.permutation.map_coords_B_to_A(yB, xB)
        if not (0 <= yA < H and 0 <= xA < W):
            return

        key = (yA, xA)
        if self.current_stroke is not None and self._stroke_touched_A is not None and key in self._stroke_touched_A:
            # Apply each pixel at most once per stroke to avoid compounding blend.
            return

        oldA = self.imgA[yA, xA].copy()
        oldB = self.imgB[yB, xB].copy()
        new_color = self._blend_with_brush(oldB) if blend else color.copy()

        if self.current_stroke is not None:
            newA = new_color
            newB = new_color
            if not np.array_equal(oldA, newA) or not np.array_equal(oldB, newB):
                self.current_stroke.changes.append(
                    PixelChange(
                        yA=yA,
                        xA=xA,
                        oldA=oldA,
                        newA=newA.copy(),
                        yB=yB,
                        xB=xB,
                        oldB=oldB,
                        newB=newB.copy(),
                    )
                )
            if self._stroke_touched_A is not None:
                self._stroke_touched_A.add(key)

        self.imgB[yB, xB] = new_color
        self.imgA[yA, xA] = new_color

    def apply_brush_A(self, y: int, x: int):
        if self.permutation is None or self.imgA is None or self.imgB is None:
            return
        H, W = self.permutation.H, self.permutation.W
        radius2 = self.brush_radius * self.brush_radius

        if self.current_tool in (Tool.BRUSH, Tool.ERASER):
            is_brush = self.current_tool == Tool.BRUSH
            color = self.brush_color if is_brush else self.eraser_color
            for dy in range(-self.brush_radius, self.brush_radius + 1):
                for dx in range(-self.brush_radius, self.brush_radius + 1):
                    if dy * dy + dx * dx <= radius2:
                        yy = y + dy
                        xx = x + dx
                        self._set_pixel_A_and_B(yy, xx, color, blend=is_brush)
        elif self.current_tool == Tool.EYEDROPPER:
            if 0 <= y < H and 0 <= x < W:
                picked = self.imgA[y, x].copy()
                picked[3] = np.uint8(255)
                self.set_brush_color(picked)

    def apply_brush_B(self, y: int, x: int):
        if self.permutation is None or self.imgA is None or self.imgB is None:
            return
        H, W = self.permutation.H, self.permutation.W
        radius2 = self.brush_radius * self.brush_radius

        if self.current_tool in (Tool.BRUSH, Tool.ERASER):
            is_brush = self.current_tool == Tool.BRUSH
            color = self.brush_color if is_brush else self.eraser_color
            for dy in range(-self.brush_radius, self.brush_radius + 1):
                for dx in range(-self.brush_radius, self.brush_radius + 1):
                    if dy * dy + dx * dx <= radius2:
                        yy = y + dy
                        xx = x + dx
                        self._set_pixel_B_and_A(yy, xx, color, blend=is_brush)
        elif self.current_tool == Tool.EYEDROPPER:
            if 0 <= y < H and 0 <= x < W:
                picked = self.imgB[y, x].copy()
                picked[3] = np.uint8(255)
                self.set_brush_color(picked)

    def begin_stroke(self):
        self.current_stroke = Stroke(changes=[])
        self.redo_stack.clear()
        self._stroke_touched_A = set()

    def end_stroke(self):
        if self.current_stroke is not None and self.current_stroke.changes:
            self.undo_stack.append(self.current_stroke)
            if len(self.undo_stack) > self.max_undo:
                self.undo_stack.pop(0)
        self.current_stroke = None
        self._stroke_touched_A = None

    def can_undo(self) -> bool:
        return len(self.undo_stack) > 0

    def can_redo(self) -> bool:
        return len(self.redo_stack) > 0

    def undo(self):
        if not self.can_undo():
            return
        stroke = self.undo_stack.pop()
        for change in reversed(stroke.changes):
            self.imgA[change.yA, change.xA] = change.oldA
            self.imgB[change.yB, change.xB] = change.oldB
        self.redo_stack.append(stroke)

    def redo(self):
        if not self.can_redo():
            return
        stroke = self.redo_stack.pop()
        for change in stroke.changes:
            self.imgA[change.yA, change.xA] = change.newA
            self.imgB[change.yB, change.xB] = change.newB
        self.undo_stack.append(stroke)

    def _compute_piece_outline_flags(self):
        if self.permutation is None:
            self.flagged_pixels_A = []
            self.flagged_mask_A = None
            self.flagged_mask_B = None
            return

        H, W = self.permutation.H, self.permutation.W
        flagged_A = np.zeros((H, W), dtype=bool)

        neighbors = [(-1, 0), (1, 0), (0, -1), (0, 1)]
        for y in range(H):
            for x in range(W):
                yB, xB = self.permutation.map_coords_A_to_B(y, x)
                is_boundary = False
                for dy, dx in neighbors:
                    yn = y + dy
                    xn = x + dx
                    if not (0 <= yn < H and 0 <= xn < W):
                        continue
                    ynB, xnB = self.permutation.map_coords_A_to_B(yn, xn)
                    manhattan = abs(ynB - yB) + abs(xnB - xB)
                    if manhattan != 1:
                        is_boundary = True
                        break
                flagged_A[y, x] = is_boundary

        flagged_indices_A = np.flatnonzero(flagged_A.reshape(-1))
        flagged_B_flat = np.zeros(H * W, dtype=bool)
        if flagged_indices_A.size > 0:
            flagged_indices_B = self.permutation.perm[flagged_indices_A]
            flagged_B_flat[flagged_indices_B] = True

        self.flagged_mask_A = flagged_A
        self.flagged_mask_B = flagged_B_flat.reshape(H, W)
        ys, xs = np.where(flagged_A)
        self.flagged_pixels_A = list(zip(ys.tolist(), xs.tolist()))
