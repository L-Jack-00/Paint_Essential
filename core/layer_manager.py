"""
Paint Pro - Layer Manager (Core Harness)
LJack Protocol Pillar 1 & 3: Decoupled State & FSM
Manages raster drawing layers and dedicated vector shape layers,
with auto-numbering, shape reordering, and rasterization merging.
"""
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional
import uuid
from PyQt6.QtGui import QImage, QPainter, QColor, QPen, QBrush, QPainterPath, QPolygonF, QFont
from PyQt6.QtCore import QPointF, QRectF, Qt
from core.shape_geometry import create_arrow_path, create_rounded_rect_path


class LayerType(Enum):
    RASTER = "raster"
    SHAPE = "shape"


@dataclass
class ShapeItemData:
    """Represents an editable vector shape object in the shape layer."""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    shape_type: str = "rect"  # 'rect', 'ellipse', 'line'
    x: float = 0.0
    y: float = 0.0
    width: float = 100.0
    height: float = 100.0
    stroke_color: str = "#000000"
    fill_color: str = "#ffffff"
    stroke_width: int = 2
    # Custom metadata: rotation, line endpoints, name, etc.
    meta: dict = field(default_factory=dict)


@dataclass
class Layer:
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = "새 레이어"
    layer_type: LayerType = LayerType.RASTER
    visible: bool = True
    opacity: float = 1.0
    raster_image: Optional[QImage] = None
    shapes: List[ShapeItemData] = field(default_factory=list)
    parent_id: Optional[str] = None


class ShapesListProxy(list):
    """Proxy list aggregating all shapes from LayerManager's shape layers."""
    def __init__(self, layer_manager: 'LayerManager'):
        super().__init__()
        self.layer_manager = layer_manager

    def _get_all_shapes(self) -> List[ShapeItemData]:
        res = []
        for l in self.layer_manager.layers:
            if l.layer_type == LayerType.SHAPE:
                res.extend(l.shapes)
        return res

    def __len__(self) -> int:
        return len(self._get_all_shapes())

    def __iter__(self):
        return iter(self._get_all_shapes())

    def __getitem__(self, idx):
        return self._get_all_shapes()[idx]

    def __bool__(self) -> bool:
        return len(self._get_all_shapes()) > 0

    def __contains__(self, item) -> bool:
        return item in self._get_all_shapes()

    def append(self, shape: ShapeItemData):
        self.layer_manager.add_shape_layer(shape)

    def extend(self, shapes):
        for s in shapes:
            self.layer_manager.add_shape_layer(s)

    def remove(self, shape: ShapeItemData):
        for l in list(self.layer_manager.layers):
            if l.layer_type == LayerType.SHAPE and shape in l.shapes:
                l.shapes.remove(shape)
                if not l.shapes:
                    if not self.layer_manager.remove_layer(l.id):
                        if l in self.layer_manager.layers:
                            self.layer_manager.layers.remove(l)
                    if self.layer_manager.active_layer_id == l.id:
                        self.layer_manager.active_layer_id = self.layer_manager.layers[-1].id if self.layer_manager.layers else None
                break

    def clear(self):
        for l in list(self.layer_manager.layers):
            if l.layer_type == LayerType.SHAPE:
                self.layer_manager.layers.remove(l)


class DefaultShapeLayerProxy(Layer):
    """Virtual shape layer providing unified access to all independent shape layers."""
    def __init__(self, layer_manager: 'LayerManager'):
        self.layer_manager = layer_manager
        self.id = "default_shape_layer"
        self.name = "도형 레이어"
        self.layer_type = LayerType.SHAPE
        self.parent_id = None
        self.raster_image = None
        self.opacity = 1.0
        self.is_collapsed = False

    @property
    def shapes(self) -> ShapesListProxy:
        return ShapesListProxy(self.layer_manager)

    @shapes.setter
    def shapes(self, new_shapes):
        for l in list(self.layer_manager.layers):
            if l.layer_type == LayerType.SHAPE:
                self.layer_manager.layers.remove(l)
        if isinstance(new_shapes, (list, tuple)):
            for s in new_shapes:
                self.layer_manager.add_shape_layer(s)

    @property
    def visible(self) -> bool:
        shape_layers = [l for l in self.layer_manager.layers if l.layer_type == LayerType.SHAPE]
        return any(l.visible for l in shape_layers) if shape_layers else True

    @visible.setter
    def visible(self, val: bool):
        for l in self.layer_manager.layers:
            if l.layer_type == LayerType.SHAPE:
                l.visible = val


class LayerManager:
    def __init__(self, canvas_width: int = 800, canvas_height: int = 600):
        self.width = canvas_width
        self.height = canvas_height
        self.layers: List[Layer] = []
        self.active_layer_id: Optional[str] = None
        self._init_default_layers()

    def _init_default_layers(self):
        """Initializes default background raster layer. No separate shape layer is created."""
        bg_img = QImage(self.width, self.height, QImage.Format.Format_ARGB32_Premultiplied)
        bg_img.fill(QColor(255, 255, 255, 255))
        bg_layer = Layer(
            id="bg_layer",
            name="배경 레이어",
            layer_type=LayerType.RASTER,
            raster_image=bg_img
        )
        self.layers = [bg_layer]
        self.active_layer_id = bg_layer.id

    def generate_new_layer_name(self, base_name: str = "새 레이어") -> str:
        """
        Generates auto-incremented layer name:
        '새 레이어', '새 레이어 2', '새 레이어 3', ...
        """
        existing_names = {l.name for l in self.layers}
        if base_name not in existing_names:
            return base_name

        num = 2
        while f"{base_name} {num}" in existing_names:
            num += 1
        return f"{base_name} {num}"

    def generate_new_shape_layer_name(self, shape_type: str = "rect") -> str:
        """Generates auto-incremented shape layer name: 직사각형 1, 타원 1, 화살표 1, 직선 1 등"""
        names_map = {
            "rect": "직사각형",
            "rounded_rect": "둥근 직사각형",
            "shape_rounded_rect": "둥근 직사각형",
            "ellipse": "타원",
            "line": "직선",
            "arrow": "화살표",
            "text": "텍스트",
        }
        base_name = names_map.get(shape_type, "도형")
        existing_names = {l.name for l in self.layers}
        num = 1
        while f"{base_name} {num}" in existing_names:
            num += 1
        return f"{base_name} {num}"

    def add_shape_layer(self, shape: ShapeItemData, name: Optional[str] = None) -> Layer:
        """Creates a dedicated Layer for an individual vector shape, acting as its own layer in the stack."""
        if not name:
            name = self.generate_new_shape_layer_name(shape.shape_type)
        shape_layer = Layer(
            id=shape.id,
            name=name,
            layer_type=LayerType.SHAPE,
            shapes=[shape],
            visible=True,
            opacity=1.0
        )
        self.layers.append(shape_layer)
        self.active_layer_id = shape_layer.id
        return shape_layer

    def add_shape_to_default_layer(self, shape: ShapeItemData) -> Layer:
        """Appends a new shape as an independent shape layer."""
        return self.add_shape_layer(shape)

    def get_layer(self, layer_id: str) -> Optional[Layer]:
        for layer in self.layers:
            if layer.id == layer_id:
                return layer
        if layer_id == "default_shape_layer":
            return self.get_default_shape_layer()
        return None

    def get_active_layer(self) -> Optional[Layer]:
        return self.get_layer(self.active_layer_id)

    def set_active_layer(self, layer_id: str):
        if self.get_layer(layer_id):
            self.active_layer_id = layer_id

    def get_default_shape_layer(self) -> Layer:
        """Finds or provides virtual shape layer for unified shape access."""
        return DefaultShapeLayerProxy(self)

    def add_layer(self, name: Optional[str] = None, layer_type: LayerType = LayerType.RASTER) -> Layer:
        if not name:
            name = self.generate_new_layer_name("새 레이어")
        new_layer = Layer(name=name, layer_type=layer_type)
        if layer_type == LayerType.RASTER:
            img = QImage(self.width, self.height, QImage.Format.Format_ARGB32_Premultiplied)
            img.fill(QColor(0, 0, 0, 0))  # Transparent
            new_layer.raster_image = img
        self.layers.append(new_layer)
        self.active_layer_id = new_layer.id
        return new_layer

    def remove_layer(self, layer_id: str) -> bool:
        if len(self.layers) <= 1:
            return False
        layer = self.get_layer(layer_id)
        if not layer:
            return False
        target_parent = layer.parent_id
        if target_parent is not None and not any(l.id == target_parent for l in self.layers if l.id != layer_id):
            target_parent = None
        for l in self.layers:
            if l.parent_id == layer_id:
                l.parent_id = target_parent
        self.layers.remove(layer)
        if self.active_layer_id == layer_id:
            self.active_layer_id = self.layers[-1].id
        return True

    def set_visible(self, layer_id: str, visible: bool):
        layer = self.get_layer(layer_id)
        if layer:
            layer.visible = visible

    def move_layer(self, from_idx: int, to_idx: int):
        if 0 <= from_idx < len(self.layers) and 0 <= to_idx < len(self.layers):
            layer = self.layers.pop(from_idx)
            self.layers.insert(to_idx, layer)

    # --- Shape Reordering & Rasterization ---

    def move_shape(self, shape_id: str, to_idx: int) -> bool:
        for idx, l in enumerate(self.layers):
            if l.id == shape_id or (l.layer_type == LayerType.SHAPE and any(s.id == shape_id for s in l.shapes)):
                layer = self.layers.pop(idx)
                target = max(0, min(to_idx, len(self.layers)))
                self.layers.insert(target, layer)
                return True
        return False

    def bring_shape_to_front(self, shape_id: str) -> bool:
        for idx, l in enumerate(self.layers):
            if l.id == shape_id or (l.layer_type == LayerType.SHAPE and any(s.id == shape_id for s in l.shapes)):
                layer = self.layers.pop(idx)
                self.layers.append(layer)
                return True
        return False

    def send_shape_to_back(self, shape_id: str) -> bool:
        for idx, l in enumerate(self.layers):
            if l.id == shape_id or (l.layer_type == LayerType.SHAPE and any(s.id == shape_id for s in l.shapes)):
                layer = self.layers.pop(idx)
                self.layers.insert(0, layer)
                return True
        return False

    def find_raster_layer_below(self, layer_or_shape_id: str) -> Optional[Layer]:
        """
        Finds the nearest raster layer directly below the specified layer or shape in the stack.
        Skips all shape layers ('도형같은거 말고 꼭 래스터레이어에 병합').
        """
        idx = -1
        for i, l in enumerate(self.layers):
            if l.id == layer_or_shape_id or (l.layer_type == LayerType.SHAPE and any(s.id == layer_or_shape_id for s in l.shapes)):
                idx = i
                break

        if idx == -1:
            return None

        # Search downwards (towards bottom of layer stack, lower z-index)
        for i in range(idx - 1, -1, -1):
            cand = self.layers[i]
            if cand.layer_type == LayerType.RASTER and cand.raster_image is not None:
                return cand

        # Fallback: if none below, search upwards (higher z-index)
        for i in range(idx + 1, len(self.layers)):
            cand = self.layers[i]
            if cand.layer_type == LayerType.RASTER and cand.raster_image is not None:
                return cand

        return None

    def merge_shape_into_raster(self, shape_id: str, target_raster_layer_id: Optional[str] = None) -> bool:
        """
        Bakes a vector shape permanently into the raster layer directly below it (skipping shapes)
        and removes it from shape layer.
        """
        shape_layer = self.get_default_shape_layer()
        target_shape = None
        for s in shape_layer.shapes:
            if s.id == shape_id:
                target_shape = s
                break

        if not target_shape:
            return False

        # Determine target raster layer
        target_layer = None
        if target_raster_layer_id:
            target_layer = self.get_layer(target_raster_layer_id)
        if not target_layer or target_layer.layer_type != LayerType.RASTER or not target_layer.raster_image:
            target_layer = self.find_raster_layer_below(shape_id)
        if not target_layer or not target_layer.raster_image:
            for l in self.layers:
                if l.layer_type == LayerType.RASTER and l.raster_image is not None:
                    target_layer = l
                    break

        if not target_layer or not target_layer.raster_image:
            return False

        # Paint shape onto target raster image
        painter = QPainter(target_layer.raster_image)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        self._render_shape_to_painter(painter, target_shape)
        painter.end()

        # Remove from vector shape layer
        shape_layer.shapes.remove(target_shape)
        self.active_layer_id = target_layer.id
        return True

    def merge_raster_layer_down(self, layer_id: str) -> Optional[str]:
        """
        Merges the specified raster layer down into the nearest raster layer directly below it.
        Skips all shape layers ('도형같은거 말고 꼭 래스터레이어에 병합').
        Returns target_layer_id on success, or None on failure.
        """
        source_layer = self.get_layer(layer_id)
        if not source_layer or source_layer.layer_type != LayerType.RASTER or source_layer.raster_image is None:
            return None

        target_layer = self.find_raster_layer_below(layer_id)
        if not target_layer or target_layer.layer_type != LayerType.RASTER or target_layer.raster_image is None:
            return None

        # Paint source raster image onto target raster image
        painter = QPainter(target_layer.raster_image)
        painter.setOpacity(source_layer.opacity)
        painter.drawImage(0, 0, source_layer.raster_image)
        painter.end()

        # Re-assign any child layers of source_layer to target_layer
        for l in self.layers:
            if l.parent_id == source_layer.id:
                l.parent_id = target_layer.id

        # Remove source layer
        if source_layer in self.layers:
            self.layers.remove(source_layer)
        self.active_layer_id = target_layer.id
        return target_layer.id

    def is_layer_effectively_visible(self, layer_id: str) -> bool:
        """
        Recursively checks visibility up the parent hierarchy.
        Returns False if layer itself or any ancestor is not visible.
        """
        layer = self.get_layer(layer_id)
        if not layer or not layer.visible:
            return False
        curr = layer
        visited = {curr.id}
        while curr.parent_id:
            parent = self.get_layer(curr.parent_id)
            if not parent:
                break
            if not parent.visible:
                return False
            if parent.id in visited:
                break
            visited.add(parent.id)
            curr = parent
        return True

    def composite_to_image(self) -> QImage:
        """Flattens all visible layers into a single composite QImage."""
        result = QImage(self.width, self.height, QImage.Format.Format_ARGB32_Premultiplied)
        result.fill(QColor(0, 0, 0, 0))
        painter = QPainter(result)

        for layer in self.layers:
            if not self.is_layer_effectively_visible(layer.id):
                continue

            painter.setOpacity(layer.opacity)
            if layer.layer_type == LayerType.RASTER and layer.raster_image is not None:
                painter.drawImage(0, 0, layer.raster_image)
            elif layer.layer_type == LayerType.SHAPE:
                for shape in layer.shapes:
                    self._render_shape_to_painter(painter, shape)

        painter.end()
        return result

    def _render_shape_to_painter(self, painter: QPainter, shape: ShapeItemData):
        painter.save()

        # Approach 2: Vector Clipping Mask (Clipper)
        if "clip_rect" in shape.meta and shape.meta["clip_rect"] is not None:
            cr = shape.meta["clip_rect"]
            clip_path = QPainterPath()
            clip_path.addRect(float(cr[0]), float(cr[1]), float(cr[2]), float(cr[3]))
            painter.setClipPath(clip_path)

        cx = float(shape.x) + float(shape.width) / 2.0
        cy = float(shape.y) + float(shape.height) / 2.0
        painter.translate(cx, cy)

        rot = float(shape.meta.get("rotation", 0.0))
        if rot != 0.0:
            painter.rotate(rot)

        pen = QPen(QColor(shape.stroke_color), shape.stroke_width)
        fill_c = QColor(shape.fill_color) if shape.fill_color != "transparent" else QColor(0, 0, 0, 0)
        brush = QBrush(fill_c)
        painter.setPen(pen)
        painter.setBrush(brush)

        w2 = float(shape.width) / 2.0
        h2 = float(shape.height) / 2.0

        if shape.shape_type == "rect":
            painter.drawRect(int(-w2), int(-h2), int(shape.width), int(shape.height))
        elif shape.shape_type in ("rounded_rect", "shape_rounded_rect") or (shape.shape_type == "rect" and shape.meta.get("corner_radius", 0) > 0):
            r = float(shape.meta.get("corner_radius", 12.0))
            path = create_rounded_rect_path(float(shape.width), float(shape.height), r)
            painter.drawPath(path)
        elif shape.shape_type == "ellipse":
            painter.drawEllipse(int(-w2), int(-h2), int(shape.width), int(shape.height))
        elif shape.shape_type == "line":
            p1 = shape.meta.get("p1_local", [-w2, -h2])
            p2 = shape.meta.get("p2_local", [w2, h2])
            painter.drawLine(int(p1[0]), int(p1[1]), int(p2[0]), int(p2[1]))
        elif shape.shape_type == "arrow":
            arr_mode = shape.meta.get("arrow_mode", "single")
            path = create_arrow_path(float(shape.width), float(shape.height), arr_mode, shape.meta)
            painter.drawPath(path)
        elif shape.shape_type == "text":
            text_str = shape.meta.get("text", "")
            font_size = int(shape.meta.get("font_size", 24))
            font_family = shape.meta.get("font_family", "Malgun Gothic")
            font_bold = shape.meta.get("font_bold", False)
            font_italic = shape.meta.get("font_italic", False)
            font = QFont(font_family, font_size)
            font.setBold(font_bold)
            font.setItalic(font_italic)
            painter.setFont(font)
            painter.setPen(pen)
            if fill_c.alpha() > 0:
                painter.fillRect(QRectF(-w2, -h2, float(shape.width), float(shape.height)), brush)
            painter.drawText(QRectF(-w2, -h2, float(shape.width), float(shape.height)), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop, text_str)

        painter.restore()

    def resize_all_layers(self, new_w: int, new_h: int, dx: int, dy: int, bg_color: QColor):
        """Resizes all layer dimensions, offsetting raster images and shapes by (dx, dy)."""
        import gc
        self.width = new_w
        self.height = new_h
        for layer in self.layers:
            if layer.layer_type == LayerType.RASTER and layer.raster_image is not None:
                old_img = layer.raster_image
                new_img = QImage(new_w, new_h, QImage.Format.Format_ARGB32_Premultiplied)
                fill_c = bg_color if layer.id == "bg_layer" else QColor(0, 0, 0, 0)
                new_img.fill(fill_c)
                p = QPainter(new_img)
                p.drawImage(dx, dy, old_img)
                p.end()
                layer.raster_image = new_img
                del old_img
            elif layer.layer_type == LayerType.SHAPE:
                for s in layer.shapes:
                    s.x += dx
                    s.y += dy
        if new_w * new_h >= 2000000:
            gc.collect()

    # --- Whole-Document Geometric Transforms (Issue 4: multi-layer synchronized) ---

    def rotate_all_90(self, clockwise: bool = True):
        """
        Rotates EVERY raster layer and EVERY vector shape by 90 degrees, then swaps canvas dimensions.
        Lossless & exactly invertible: rotate_all_90(not clockwise) restores the original state.
        CW mapping (old canvas W x H):  (x, y) -> (H - y, x)
        CCW mapping:                    (x, y) -> (y, W - x)
        Includes explicit buffer release to minimize peak memory spikes on large multi-layer canvases.
        """
        import gc
        from PyQt6.QtGui import QTransform
        old_w, old_h = self.width, self.height
        tr = QTransform()
        tr.rotate(90 if clockwise else -90)

        for layer in self.layers:
            if layer.layer_type == LayerType.RASTER and layer.raster_image is not None:
                old_img = layer.raster_image
                layer.raster_image = old_img.transformed(tr)
                del old_img
            for s in layer.shapes:
                if clockwise:
                    new_x = old_h - (s.y + s.height)
                    new_y = s.x
                else:
                    new_x = s.y
                    new_y = old_w - (s.x + s.width)
                s.x, s.y = float(new_x), float(new_y)
                s.width, s.height = s.height, s.width
                if "rotation" in s.meta:
                    rot = float(s.meta.get("rotation", 0.0))
                    s.meta["rotation"] = (rot + (90.0 if clockwise else -90.0)) % 360.0
                # Line endpoints are stored in local (center-origin) coordinates
                for key in ("p1_local", "p2_local"):
                    pt = s.meta.get(key)
                    if pt is not None:
                        lx, ly = float(pt[0]), float(pt[1])
                        s.meta[key] = [-ly, lx] if clockwise else [ly, -lx]
                cr = s.meta.get("clip_rect")
                if cr is not None:
                    cx, cy, cw, ch = (float(v) for v in cr)
                    if clockwise:
                        s.meta["clip_rect"] = [old_h - (cy + ch), cx, ch, cw]
                    else:
                        s.meta["clip_rect"] = [cy, old_w - (cx + cw), ch, cw]

        self.width, self.height = old_h, old_w
        if old_w * old_h >= 2000000:
            gc.collect()

    def flip_all(self, horizontal: bool = True):
        """
        Mirrors EVERY raster layer and EVERY vector shape horizontally or vertically.
        Self-inverse: calling flip_all twice with the same axis restores the original state.
        Includes explicit buffer release to prevent memory spikes across multiple layers.
        """
        import gc
        W, H = self.width, self.height
        for layer in self.layers:
            if layer.layer_type == LayerType.RASTER and layer.raster_image is not None:
                old_img = layer.raster_image
                layer.raster_image = old_img.mirrored(horizontal, not horizontal)
                del old_img
            for s in layer.shapes:
                if horizontal:
                    s.x = float(W - (s.x + s.width))
                else:
                    s.y = float(H - (s.y + s.height))
                if "rotation" in s.meta:
                    rot = float(s.meta.get("rotation", 0.0))
                    if horizontal:
                        s.meta["rotation"] = (180.0 - rot) % 360.0
                    else:
                        s.meta["rotation"] = (-rot) % 360.0
                for key in ("p1_local", "p2_local"):
                    pt = s.meta.get(key)
                    if pt is not None:
                        lx, ly = float(pt[0]), float(pt[1])
                        s.meta[key] = [-lx, ly] if horizontal else [lx, -ly]
                cr = s.meta.get("clip_rect")
                if cr is not None:
                    cx, cy, cw, ch = (float(v) for v in cr)
                    if horizontal:
                        s.meta["clip_rect"] = [W - (cx + cw), cy, cw, ch]
                    else:
                        s.meta["clip_rect"] = [cx, H - (cy + ch), cw, ch]

        if W * H >= 2000000:
            gc.collect()
