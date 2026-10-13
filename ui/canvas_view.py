"""
Paint Pro - Canvas View Rig
LJack Protocol Pillar 5, 6 & 8: High-DPI Precision, Checkerboard Transparency,
PowerPoint-style Transformable Shapes, MS Paint Marquee Area Selection,
Pixel-perfect Pencil Eraser, and Flood Fill.
"""
from typing import Optional, Dict
import math
import numpy as np
from PyQt6.QtWidgets import (
    QGraphicsView, QGraphicsScene, QGraphicsPixmapItem,
    QGraphicsItem, QApplication, QMenu, QFrame
)
from PyQt6.QtCore import (
    Qt, QPointF, pyqtSignal, QRectF, QLineF, QRect, QPoint,
    QBuffer, QByteArray, QMimeData, QIODevice
)
from PyQt6.QtGui import (
    QPainter, QPen, QBrush, QColor, QPixmap, QImage,
    QMouseEvent, QKeyEvent, QWheelEvent,
    QPainterPath, QTransform, QPolygonF, QFont
)
from core.layer_manager import LayerManager, LayerType, ShapeItemData
from core.input_safety import InputSafetyTracker, InputMode
from core.history_manager import HistoryManager
from core.image_processor import ImageProcessor
from ui.shape_items import TransformableShapeItem, HandleType
from ui.selection_item import MarqueeSelectionBox, FloatingSelectionItem
from ui.canvas_hud import CanvasHudOverlay
from ui.toast_overlay import ToastOverlay
from core.shape_geometry import create_arrow_path, create_rounded_rect_path
from core.i18n import I18N


class CanvasView(QGraphicsView):
    color_picked = pyqtSignal(QColor)
    secondary_color_picked = pyqtSignal(QColor)
    status_message = pyqtSignal(str)
    canvas_modified = pyqtSignal()
    stroke_width_changed = pyqtSignal(int)
    zoom_changed = pyqtSignal(float)
    adjustment_requested = pyqtSignal(QRect)
    rotate_canvas_requested = pyqtSignal()
    flip_h_canvas_requested = pyqtSignal()
    flip_v_canvas_requested = pyqtSignal()

    def __init__(
        self,
        layer_manager: LayerManager,
        input_safety: InputSafetyTracker,
        history_manager: HistoryManager,
        parent=None
    ):
        super().__init__(parent)
        self.layer_manager = layer_manager
        self.input_safety = input_safety
        self.history_manager = history_manager

        # Drawing settings
        self.primary_color = QColor(0, 0, 0, 255)
        self.secondary_color = QColor(255, 255, 255, 255)
        self.stroke_width = 3
        self.pixel_snap_enabled = True
        self.transparent_selection_enabled = False  # MS Paint transparent selection
        self.fill_tolerance: int = 32
        self.fill_alpha_threshold: int = 0  # Fill semi-transparent pixels up to n% alpha
        self.fill_sample_all_layers: bool = False  # Sample all visible layers for boundary detection (Photoshop style)

        # Zoom & Grid settings
        self.zoom_level: float = 1.0
        self.grid_visible: bool = False
        self.grid_spacing: int = 32
        self.pixel_grid_enabled: bool = True
        self.pixel_grid_threshold: float = 8.0  # Appears at >= 800% zoom (much closer)

        # State tracking
        self.last_scene_pt: Optional[QPointF] = None
        self.shape_preview_item: Optional[QGraphicsItem] = None
        self.drag_start_pt: Optional[QPointF] = None
        self.stroke_before_image: Optional[QImage] = None
        self.lasso_points = []
        self.lasso_preview_item: Optional[QGraphicsItem] = None
        self.mosaic_preview_item: Optional[QGraphicsItem] = None
        self.current_step_badge: int = 1
        self.step_badge_start: int = 1
        self.step_badge_type: str = "number"  # "number", "alpha_upper", "alpha_lower"
        self.mosaic_block_size: int = 12
        self.rect_corner_radius: int = 12
        self.current_arrow_mode: str = "single"  # "single", "double", "curved_single", "curved_double"
        self._loupe_cursor_pos: Optional[QPoint] = None
        self._loupe_scene_pt: Optional[QPointF] = None
        self.toast_overlay: Optional[ToastOverlay] = None
        try:
            self.toast_overlay = ToastOverlay(self.viewport())
        except Exception:
            pass

        # Selection tool items
        self.marquee_box: Optional[MarqueeSelectionBox] = None
        self.floating_selection: Optional[FloatingSelectionItem] = None
        self.selection_rect: Optional[QRectF] = None
        self.is_selection_inverted: bool = False

        # Interaction flags
        self.is_middle_panning = False
        self.pan_last_pos = QPointF()
        self.is_right_erasing = False
        self.is_shape_swapped = False
        self.is_shape_handle_dragging = False

        # Scene and Layer Items
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)
        self.raster_items: Dict[str, QGraphicsPixmapItem] = {}
        self.shape_items: Dict[str, TransformableShapeItem] = {}

        # View configuration
        self.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        self.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.current_theme = "light"

        # Outer canvas neutral background
        self.setBackgroundBrush(QBrush(QColor(210, 215, 220)))

        # Register emergency release with input safety tracker
        self.input_safety.register_emergency_release_callback(self._on_emergency_release)

        self.rebuild_scene()

        # Canvas bottom floating HUD overlay (Parented to CanvasView itself, immune to scroll)
        self.hud = CanvasHudOverlay(self)
        self.hud.zoom_in_requested.connect(self.zoom_in)
        self.hud.zoom_out_requested.connect(self.zoom_out)
        self.hud.zoom_reset_requested.connect(self.reset_view)
        self.hud.grid_toggle_requested.connect(self.set_grid_visible)
        self.hud.grid_spacing_changed.connect(self.set_grid_spacing)
        self.hud.rotate_requested.connect(self.rotate_canvas_requested.emit)
        self.hud.flip_h_requested.connect(self.flip_h_canvas_requested.emit)
        self.hud.flip_v_requested.connect(self.flip_v_canvas_requested.emit)
        self.hud.reposition(self.size())

        self.setMouseTracking(True)
        self.viewport().setMouseTracking(True)
        self.horizontalScrollBar().valueChanged.connect(lambda _: self.hud.activate_hud())
        self.verticalScrollBar().valueChanged.connect(lambda _: self.hud.activate_hud())
        self.zoom_changed.connect(self.hud.update_zoom)

    @property
    def toast(self):
        return self.toast_overlay

    @property
    def step_badge_count(self) -> int:
        return self.current_step_badge

    @step_badge_count.setter
    def step_badge_count(self, val: int):
        self.current_step_badge = val

    @property
    def step_badge_mode(self) -> str:
        return self.step_badge_type

    @step_badge_mode.setter
    def step_badge_mode(self, val: str):
        self.step_badge_type = val

    @property
    def arrow_mode(self) -> str:
        return self.current_arrow_mode

    @arrow_mode.setter
    def arrow_mode(self, val: str):
        self.current_arrow_mode = val

    def show_toast(self, message: str, duration_ms: int = 1200):
        if getattr(self, "toast_overlay", None):
            self.toast_overlay.show_toast(message, duration_ms)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, "hud"):
            self.hud.reposition(event.size())
        if getattr(self, "toast_overlay", None):
            self.toast_overlay._reposition()

    def paintEvent(self, event):
        super().paintEvent(event)
        if (self.input_safety.current_mode == InputMode.EYEDROPPER
                and self._loupe_cursor_pos is not None
                and self._loupe_scene_pt is not None):
            self._draw_pixel_loupe()

    def _draw_pixel_loupe(self):
        """
        Renders a pixel magnifying loupe bubble near cursor,
        showing 11x11 surrounding pixels at 9x zoom, center crosshair, and real-time #RRGGBB code.
        """
        if not self._loupe_cursor_pos or not self._loupe_scene_pt:
            return

        pos = self._loupe_cursor_pos
        sc_pt = self._loupe_scene_pt
        sc_x = int(math.floor(sc_pt.x()))
        sc_y = int(math.floor(sc_pt.y()))

        composite = self.layer_manager.composite_to_image()
        c_w, c_h = composite.width(), composite.height()

        grid_dim = 11
        half_dim = grid_dim // 2
        px_size = 9
        view_w = grid_dim * px_size
        view_h = grid_dim * px_size
        bubble_w = view_w + 10
        bubble_h = view_h + 34

        vp_rect = self.viewport().rect()
        lx = pos.x() + 20
        ly = pos.y() - bubble_h - 10
        if lx + bubble_w > vp_rect.right() - 8:
            lx = pos.x() - bubble_w - 20
        if lx < 8:
            lx = 8
        if ly < 8:
            ly = pos.y() + 25
        if ly + bubble_h > vp_rect.bottom() - 8:
            ly = vp_rect.bottom() - bubble_h - 8

        painter = QPainter(self.viewport())
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        bubble_rect = QRectF(lx, ly, bubble_w, bubble_h)
        painter.setPen(QPen(QColor(15, 23, 42, 200), 1.5))
        painter.setBrush(QBrush(QColor(15, 23, 42, 240)))
        painter.drawRoundedRect(bubble_rect, 8.0, 8.0)

        grid_top_left_x = lx + 5
        grid_top_left_y = ly + 5
        grid_rect = QRectF(grid_top_left_x, grid_top_left_y, view_w, view_h)

        painter.save()
        painter.setClipRect(grid_rect)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)

        center_color = QColor(0, 0, 0, 0)
        for dy in range(-half_dim, half_dim + 1):
            for dx in range(-half_dim, half_dim + 1):
                cur_x = sc_x + dx
                cur_y = sc_y + dy
                bx = grid_top_left_x + (dx + half_dim) * px_size
                by = grid_top_left_y + (dy + half_dim) * px_size

                if 0 <= cur_x < c_w and 0 <= cur_y < c_h:
                    col = composite.pixelColor(cur_x, cur_y)
                    if dx == 0 and dy == 0:
                        center_color = col
                    if col.alpha() < 255:
                        check_c = QColor(255, 255, 255) if ((cur_x + cur_y) % 2 == 0) else QColor(220, 220, 220)
                        painter.fillRect(QRectF(bx, by, px_size, px_size), check_c)
                    painter.fillRect(QRectF(bx, by, px_size, px_size), col)
                else:
                    painter.fillRect(QRectF(bx, by, px_size, px_size), QColor(200, 205, 210))

                painter.setPen(QPen(QColor(255, 255, 255, 40), 1))
                painter.drawRect(QRectF(bx, by, px_size, px_size))

        cx_box = QRectF(grid_top_left_x + half_dim * px_size, grid_top_left_y + half_dim * px_size, px_size, px_size)
        painter.setPen(QPen(QColor(239, 68, 68), 1.5))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRect(cx_box)
        painter.restore()

        painter.setPen(QPen(QColor(59, 130, 246), 1.5))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRect(grid_rect)

        hex_text = f"#{center_color.red():02X}{center_color.green():02X}{center_color.blue():02X}"
        swatch_x = lx + 8
        swatch_y = ly + view_h + 10
        painter.setPen(QPen(QColor(255, 255, 255, 200), 1.0))
        painter.setBrush(QBrush(center_color))
        painter.drawRoundedRect(QRectF(swatch_x, swatch_y, 14, 14), 2.0, 2.0)

        painter.setPen(QPen(QColor(241, 245, 249)))
        font = QFont("Consolas", 9, QFont.Weight.Bold)
        painter.setFont(font)
        painter.drawText(
            QRectF(swatch_x + 20, swatch_y - 2, bubble_w - 32, 18),
            Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
            hex_text
        )

        painter.end()

    _checker_brush_cache = {}

    @classmethod
    def create_checkerboard_brush(cls, size: int = 16) -> QBrush:
        """Photoshop-style alternating checkerboard pattern for transparent regions."""
        if size not in cls._checker_brush_cache:
            pm = QPixmap(size * 2, size * 2)
            p = QPainter(pm)
            p.fillRect(0, 0, size, size, QColor(255, 255, 255))
            p.fillRect(size, 0, size, size, QColor(220, 224, 230))
            p.fillRect(0, size, size, size, QColor(220, 224, 230))
            p.fillRect(size, size, size, size, QColor(255, 255, 255))
            p.end()
            cls._checker_brush_cache[size] = QBrush(pm)
        return cls._checker_brush_cache[size]

    def snap_coordinate(self, pt: QPointF) -> QPointF:
        """Aligns coordinates to pixel grid to eliminate High-DPI drift."""
        if not self.pixel_snap_enabled:
            return pt
        offset = 0.5 if (self.stroke_width % 2 != 0) else 0.0
        return QPointF(math.floor(pt.x()) + offset, math.floor(pt.y()) + offset)

    def rebuild_scene(self):
        """Synchronizes QGraphicsScene with current LayerManager state."""
        saved_selection_rect = self.selection_rect
        saved_inverted = self.is_selection_inverted

        self.commit_floating_selection_if_any()
        if self.marquee_box and self.marquee_box in self.scene.items():
            self.scene.removeItem(self.marquee_box)
        self.marquee_box = None

        self.scene.clear()
        self.raster_items.clear()
        self.shape_items.clear()
        self.shape_preview_item = None

        w, h = self.layer_manager.width, self.layer_manager.height
        self.scene.setSceneRect(0, 0, w, h)

        # 1. Canvas checkerboard background inside canvas rect
        checker_bg = self.scene.addRect(
            QRectF(0, 0, w, h),
            QPen(Qt.PenStyle.NoPen),
            self.create_checkerboard_brush(16)
        )
        checker_bg.setZValue(-100)

        # 2. Canvas boundary border (Theme-aware, subtle in dark mode)
        border_color = QColor(52, 68, 96) if getattr(self, "current_theme", "light") == "dark" else QColor(160, 165, 175)
        self.border_rect = self.scene.addRect(
            QRectF(0, 0, w, h),
            QPen(border_color, 1),
            QBrush(Qt.BrushStyle.NoBrush)
        )
        self.border_rect.setZValue(9999)

        # 3. Build items from layers bottom to top
        for idx, layer in enumerate(self.layer_manager.layers):
            eff_vis = self.layer_manager.is_layer_effectively_visible(layer.id)
            if layer.layer_type == LayerType.RASTER and layer.raster_image is not None:
                pix = QPixmap.fromImage(layer.raster_image)
                item = self.scene.addPixmap(pix)
                item.setZValue(idx * 10)
                item.setVisible(eff_vis)
                item.setOpacity(layer.opacity)
                self.raster_items[layer.id] = item

            elif layer.layer_type == LayerType.SHAPE:
                for shape_data in layer.shapes:
                    shape_item = self._create_shape_graphics_item(
                        shape_data, z_value=idx * 10 + 5, visible=eff_vis
                    )
                    self.shape_items[shape_data.id] = shape_item

        # 4. Restore selection marquee if active (prevents selection from dropping on layer switch)
        if saved_selection_rect and not saved_selection_rect.isEmpty():
            self.selection_rect = saved_selection_rect
            self.is_selection_inverted = saved_inverted
            self.marquee_box = MarqueeSelectionBox(
                saved_selection_rect,
                on_rect_changed_cb=self._on_marquee_rect_changed,
                on_context_menu_cb=self._show_selection_context_menu
            )
            self.marquee_box.set_inverted(saved_inverted)
            self.scene.addItem(self.marquee_box)

        self.canvas_modified.emit()

    @property
    def zoom_factor(self) -> float:
        return self.zoom_level

    def apply_theme(self, theme: str):
        self.current_theme = theme
        if theme == "dark":
            self.setBackgroundBrush(QBrush(QColor(24, 32, 48)))
            if hasattr(self, "border_rect") and self.border_rect:
                self.border_rect.setPen(QPen(QColor(52, 68, 96), 1))
        else:
            self.setBackgroundBrush(QBrush(QColor(210, 215, 220)))
            if hasattr(self, "border_rect") and self.border_rect:
                self.border_rect.setPen(QPen(QColor(160, 165, 175), 1))
        if hasattr(self, "hud"):
            self.hud.apply_theme(theme)

    def set_view_mode(self, rotation: int, flip_h: bool, flip_v: bool):
        """Updates canvas view orientation indicators in HUD."""
        if hasattr(self, "hud"):
            self.hud.update_view_mode(rotation, flip_h, flip_v)

    def _create_shape_graphics_item(
        self, shape_data: ShapeItemData, z_value: float = 100, visible: bool = True
    ) -> TransformableShapeItem:
        """Creates an interactive PowerPoint-style vector shape item with handles."""
        item = TransformableShapeItem(
            shape_data,
            on_merge_raster_cb=self._on_shape_merge_requested,
            on_delete_cb=self._on_shape_delete_requested,
            on_reorder_cb=self._on_shape_reorder_requested
        )
        item.setZValue(z_value)
        item.setVisible(visible)
        item.setData(0, shape_data.id)
        self.shape_items[shape_data.id] = item
        self.scene.addItem(item)
        return item

    def update_raster_pixmap(self, layer_id: str):
        layer = self.layer_manager.get_layer(layer_id)
        if layer and layer.raster_image and layer.id in self.raster_items:
            eff_vis = self.layer_manager.is_layer_effectively_visible(layer.id)
            pix = QPixmap.fromImage(layer.raster_image)
            self.raster_items[layer.id].setPixmap(pix)
            self.raster_items[layer.id].setVisible(eff_vis)
            self.canvas_modified.emit()

    # --- Mouse & Keyboard Event Handlers ---

    def mousePressEvent(self, event: QMouseEvent):
        # 1. Middle Button Pan (Hand tool)
        if event.button() == Qt.MouseButton.MiddleButton or (
            event.button() == Qt.MouseButton.LeftButton and self.input_safety.is_space_pressed
        ):
            self.is_middle_panning = True
            self.pan_last_pos = event.pos()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            event.accept()
            return

        raw_scene_pt = self.mapToScene(event.pos())
        scene_pt = self.snap_coordinate(raw_scene_pt)

        # 2. Right Click Handling (Dedicated Tool Actions vs Context Menu)
        if event.button() == Qt.MouseButton.RightButton:
            mode = self.input_safety.current_mode

            # Brush: Soft Eraser
            if mode == InputMode.BRUSH:
                self.is_right_erasing = True
                self.eraser_type = "soft"
                self.input_safety.set_mouse_down(True)
                self.drag_start_pt = scene_pt
                self.last_scene_pt = scene_pt
                active_layer = self.layer_manager.get_active_layer()
                if active_layer and active_layer.layer_type == LayerType.RASTER and active_layer.raster_image:
                    self.stroke_before_image = active_layer.raster_image.copy()
                    self._draw_raster_point(scene_pt)
                event.accept()
                return

            # Pencil: Pixel Eraser
            elif mode == InputMode.PENCIL:
                self.is_right_erasing = True
                self.eraser_type = "pixel"
                self.input_safety.set_mouse_down(True)
                self.drag_start_pt = scene_pt
                self.last_scene_pt = scene_pt
                active_layer = self.layer_manager.get_active_layer()
                if active_layer and active_layer.layer_type == LayerType.RASTER and active_layer.raster_image:
                    self.stroke_before_image = active_layer.raster_image.copy()
                    self._draw_raster_point(scene_pt)
                event.accept()
                return

            # Eraser Tool: Left = Soft Eraser, Right = Pixel Eraser
            elif mode == InputMode.ERASER:
                self.is_right_erasing = True
                self.eraser_type = "pixel"
                self.input_safety.set_mouse_down(True)
                self.drag_start_pt = scene_pt
                self.last_scene_pt = scene_pt
                active_layer = self.layer_manager.get_active_layer()
                if active_layer and active_layer.layer_type == LayerType.RASTER and active_layer.raster_image:
                    self.stroke_before_image = active_layer.raster_image.copy()
                    self._draw_raster_point(scene_pt)
                event.accept()
                return

            # Flood Fill: Right click fills with secondary color!
            elif mode == InputMode.FLOOD_FILL:
                self.commit_floating_selection_if_any()
                self._apply_flood_fill(scene_pt, is_secondary=True)
                event.accept()
                return

            # Eyedropper: Right click picks into secondary color!
            elif mode == InputMode.EYEDROPPER:
                self._pick_color_at(scene_pt, is_secondary=True)
                event.accept()
                return

            # Vector Shapes: Right drag swaps stroke and fill colors!
            elif mode in (InputMode.SHAPE_RECT, InputMode.SHAPE_ROUNDED_RECT, InputMode.SHAPE_ELLIPSE, InputMode.SHAPE_LINE, InputMode.SHAPE_ARROW):
                self.is_shape_swapped = True
                self.input_safety.set_mouse_down(True)
                self.drag_start_pt = scene_pt
                self.last_scene_pt = scene_pt
                event.accept()
                return

            # Step Badge: Right click resets badge counter to start value
            elif mode == InputMode.STEP_BADGE:
                start_val = getattr(self, "step_badge_start", 1)
                self.current_step_badge = start_val
                b_type = getattr(self, "step_badge_type", "number")
                disp = self.format_step_badge(start_val, b_type)
                self.status_message.emit(f"스텝 배지 번호가 {disp}(으)로 초기화되었습니다.")
                event.accept()
                return

            # Context Menu is ONLY shown for selection tools (or tools without dedicated right-click)
            elif self.selection_rect or mode in (InputMode.SELECT, InputMode.SELECT_AREA, InputMode.SELECT_LASSO, InputMode.SELECT_WAND):
                self._show_selection_context_menu(event.globalPosition().toPoint())
                event.accept()
                return

        # 3. Left Click Actions
        if event.button() == Qt.MouseButton.LeftButton:
            self.is_right_erasing = False
            self.is_shape_swapped = False

            # Check if user clicked on any handle or body of any selected shape or marquee box!
            selected_shapes = [item for item in self.scene.selectedItems() if isinstance(item, TransformableShapeItem)]
            hit_handle = False
            hit_shape_body = False
            for s_item in selected_shapes:
                local_pt = s_item.mapFromScene(raw_scene_pt)
                if s_item._hit_test_handle(local_pt) != HandleType.NONE:
                    hit_handle = True
                    break
                if s_item.contains(local_pt):
                    hit_shape_body = True
                    break

            if self.marquee_box:
                m_handle = self.marquee_box._hit_test_handle(raw_scene_pt)
                m_border = self.marquee_box._hit_test_border(raw_scene_pt)
                if m_handle != HandleType.NONE or m_border:
                    hit_handle = True

            if hit_handle:
                self.is_shape_handle_dragging = True
                super().mousePressEvent(event)
                event.accept()
                return

            # Clicking outside of selected shapes deselects them without auto-rasterizing
            if selected_shapes and not hit_shape_body and not hit_handle:
                self.scene.clearSelection()

            self.input_safety.set_mouse_down(True)
            self.drag_start_pt = scene_pt
            self.last_scene_pt = scene_pt
            mode = self.input_safety.current_mode

            if mode in (InputMode.BRUSH, InputMode.PENCIL, InputMode.ERASER):
                self.commit_floating_selection_if_any()
                if mode == InputMode.ERASER:
                    self.eraser_type = "soft"  # Left click eraser is Soft Eraser
                active_layer = self.layer_manager.get_active_layer()
                if active_layer and active_layer.layer_type == LayerType.RASTER and active_layer.raster_image:
                    self.stroke_before_image = active_layer.raster_image.copy()
                    self._draw_raster_point(scene_pt)

            elif mode == InputMode.FLOOD_FILL:
                self.commit_floating_selection_if_any()
                self._apply_flood_fill(scene_pt, is_secondary=False)

            elif mode == InputMode.EYEDROPPER:
                self._pick_color_at(scene_pt, is_secondary=False)

            elif mode == InputMode.STEP_BADGE:
                self.commit_floating_selection_if_any()
                self._apply_step_badge(scene_pt)
                event.accept()
                return

            elif mode == InputMode.MOSAIC:
                self.commit_floating_selection_if_any()
                active_layer = self.layer_manager.get_active_layer()
                if active_layer and active_layer.layer_type == LayerType.RASTER and active_layer.raster_image:
                    self.stroke_before_image = active_layer.raster_image.copy()

            elif mode in (InputMode.SHAPE_RECT, InputMode.SHAPE_ROUNDED_RECT, InputMode.SHAPE_ELLIPSE, InputMode.SHAPE_LINE, InputMode.SHAPE_ARROW):
                self.commit_floating_selection_if_any()

            elif mode == InputMode.SELECT_AREA:
                if self.selection_rect and self.selection_rect.contains(scene_pt) and not self.floating_selection:
                    self._create_floating_selection_from_rect(self.selection_rect)
                elif not (self.floating_selection and self.floating_selection.sceneBoundingRect().contains(scene_pt)):
                    self.commit_floating_selection_if_any()
                    self.clear_selection_marquee()
                super().mousePressEvent(event)

            elif mode == InputMode.SELECT_LASSO:
                self.commit_floating_selection_if_any()
                self.clear_selection_marquee()
                self.lasso_points = [scene_pt]
                path = QPainterPath()
                path.moveTo(scene_pt)
                pen = QPen(QColor(0, 0, 0), 1.5, Qt.PenStyle.DashLine)
                if self.lasso_preview_item and self.lasso_preview_item in self.scene.items():
                    self.scene.removeItem(self.lasso_preview_item)
                self.lasso_preview_item = self.scene.addPath(path, pen)
                self.lasso_preview_item.setZValue(9999)

            elif mode == InputMode.SELECT_WAND:
                self.commit_floating_selection_if_any()
                self.clear_selection_marquee()
                active_layer = self.layer_manager.get_active_layer()
                if active_layer and active_layer.raster_image:
                    sample_img = self.layer_manager.composite_to_image() if self.fill_sample_all_layers else None
                    mask = ImageProcessor.find_wand_mask(
                        active_layer.raster_image, int(scene_pt.x()), int(scene_pt.y()),
                        tolerance=self.fill_tolerance, alpha_threshold=self.fill_alpha_threshold,
                        sample_img=sample_img
                    )
                    if mask is not None and np.any(mask):
                        ys, xs = np.where(mask)
                        min_x, max_x = int(np.min(xs)), int(np.max(xs))
                        min_y, max_y = int(np.min(ys)), int(np.max(ys))
                        rect = QRectF(min_x, min_y, max(4.0, max_x - min_x + 1), max(4.0, max_y - min_y + 1))
                        self._finalize_marquee(rect.topLeft(), rect.bottomRight())
                        self._update_marquee_preview(rect.topLeft(), rect.bottomRight())

            elif mode == InputMode.SELECT:
                self.commit_floating_selection_if_any()
                super().mousePressEvent(event)

            event.accept()
            return

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent):
        if self.is_middle_panning:
            delta = event.pos() - self.pan_last_pos
            self.pan_last_pos = event.pos()
            self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() - delta.x())
            self.verticalScrollBar().setValue(self.verticalScrollBar().value() - delta.y())
            if hasattr(self, "hud"):
                self.hud.activate_hud()
            event.accept()
            return

        if self.is_shape_handle_dragging:
            super().mouseMoveEvent(event)
            event.accept()
            return

        raw_scene_pt = self.mapToScene(event.pos())
        scene_pt = self.snap_coordinate(raw_scene_pt)
        self.status_message.emit(f"X: {int(scene_pt.x())}, Y: {int(scene_pt.y())} px")

        # Eyedropper Loupe overlay tracking
        if self.input_safety.current_mode == InputMode.EYEDROPPER:
            self._loupe_cursor_pos = event.pos()
            self._loupe_scene_pt = scene_pt
            self.viewport().update()
        elif self._loupe_cursor_pos is not None:
            self._loupe_cursor_pos = None
            self._loupe_scene_pt = None
            self.viewport().update()

        if self.input_safety.is_mouse_down:
            mode = self.input_safety.current_mode

            if mode in (InputMode.BRUSH, InputMode.PENCIL, InputMode.ERASER) or self.is_right_erasing:
                if self.last_scene_pt is not None:
                    self._draw_raster_line(self.last_scene_pt, scene_pt)
                self.last_scene_pt = scene_pt

            elif mode in (InputMode.SHAPE_RECT, InputMode.SHAPE_ROUNDED_RECT, InputMode.SHAPE_ELLIPSE, InputMode.SHAPE_LINE, InputMode.SHAPE_ARROW):
                self._update_shape_preview(self.drag_start_pt, scene_pt, mode, event.modifiers(), is_swapped=self.is_shape_swapped)

            elif mode == InputMode.MOSAIC:
                if self.drag_start_pt:
                    self._update_mosaic_preview(self.drag_start_pt, scene_pt)

            elif mode == InputMode.SELECT_AREA:
                if not self.floating_selection:
                    self._update_marquee_preview(self.drag_start_pt, scene_pt)
                else:
                    super().mouseMoveEvent(event)

            elif mode == InputMode.SELECT_LASSO:
                self.lasso_points.append(scene_pt)
                if len(self.lasso_points) > 1 and self.lasso_preview_item:
                    path = QPainterPath()
                    path.moveTo(self.lasso_points[0])
                    for p in self.lasso_points[1:]:
                        path.lineTo(p)
                    self.lasso_preview_item.setPath(path)

            elif mode == InputMode.SELECT:
                super().mouseMoveEvent(event)
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent):
        if self.is_middle_panning:
            self.is_middle_panning = False
            self.setCursor(Qt.CursorShape.ArrowCursor)
            event.accept()
            return

        if self.is_shape_handle_dragging:
            self.is_shape_handle_dragging = False
            self.input_safety.set_mouse_down(False)
            super().mouseReleaseEvent(event)
            self.canvas_modified.emit()
            event.accept()
            return

        raw_scene_pt = self.mapToScene(event.pos())
        scene_pt = self.snap_coordinate(raw_scene_pt)

        if event.button() in (Qt.MouseButton.LeftButton, Qt.MouseButton.RightButton):
            self.input_safety.set_mouse_down(False)
            mode = self.input_safety.current_mode

            if (mode in (InputMode.BRUSH, InputMode.PENCIL, InputMode.ERASER)) or self.is_right_erasing:
                self._commit_raster_stroke()
                self.is_right_erasing = False

            elif mode in (InputMode.SHAPE_RECT, InputMode.SHAPE_ROUNDED_RECT, InputMode.SHAPE_ELLIPSE, InputMode.SHAPE_LINE, InputMode.SHAPE_ARROW):
                self._commit_shape(self.drag_start_pt, scene_pt, mode, event.modifiers(), is_swapped=self.is_shape_swapped)
                self.is_shape_swapped = False

            elif mode == InputMode.MOSAIC:
                if self.drag_start_pt:
                    self._finalize_mosaic(self.drag_start_pt, scene_pt)

            elif mode == InputMode.SELECT_AREA:
                if not self.floating_selection and self.drag_start_pt:
                    self._finalize_marquee(self.drag_start_pt, scene_pt)

            elif mode == InputMode.SELECT_LASSO:
                if self.lasso_preview_item and self.lasso_preview_item in self.scene.items():
                    self.scene.removeItem(self.lasso_preview_item)
                self.lasso_preview_item = None

                if len(self.lasso_points) > 2:
                    xs = [p.x() for p in self.lasso_points]
                    ys = [p.y() for p in self.lasso_points]
                    min_x, max_x = min(xs), max(xs)
                    min_y, max_y = min(ys), max(ys)
                    w = max_x - min_x
                    h = max_y - min_y
                    if w > 2 and h > 2:
                        self.selection_rect = QRectF(min_x, min_y, w, h)
                        self.marquee_box = MarqueeSelectionBox(
                            self.selection_rect,
                            on_rect_changed_cb=self._on_marquee_rect_changed,
                            on_context_menu_cb=self._show_selection_context_menu
                        )
                        self.scene.addItem(self.marquee_box)
                self.lasso_points = []

            elif mode == InputMode.SELECT:
                super().mouseReleaseEvent(event)

        self.last_scene_pt = None
        self.drag_start_pt = None
        super().mouseReleaseEvent(event)

    def leaveEvent(self, event):
        self._loupe_cursor_pos = None
        self._loupe_scene_pt = None
        self.viewport().update()
        if self.input_safety.is_mouse_down or self.is_middle_panning:
            self._on_emergency_release()
        super().leaveEvent(event)

    def focusOutEvent(self, event):
        self._on_emergency_release()
        super().focusOutEvent(event)

    def _on_emergency_release(self):
        """Emergency release callback from LJack input safety tracker."""
        self.is_middle_panning = False
        self.is_right_erasing = False
        self.is_shape_swapped = False
        self.is_shape_handle_dragging = False
        self._loupe_cursor_pos = None
        self._loupe_scene_pt = None
        if self.shape_preview_item and self.shape_preview_item in self.scene.items():
            self.scene.removeItem(self.shape_preview_item)
        self.shape_preview_item = None
        if self.mosaic_preview_item and self.mosaic_preview_item in self.scene.items():
            self.scene.removeItem(self.mosaic_preview_item)
        self.mosaic_preview_item = None
        if self.lasso_preview_item and self.lasso_preview_item in self.scene.items():
            self.scene.removeItem(self.lasso_preview_item)
        self.lasso_preview_item = None
        self.last_scene_pt = None
        self.drag_start_pt = None
        self.setCursor(Qt.CursorShape.ArrowCursor)
        self.viewport().update()

    # --- Drawing Logic: Brush vs Pencil vs Eraser ---

    def _draw_raster_point(self, pt: QPointF):
        self._draw_raster_line(pt, pt)

    def _draw_raster_line(self, p1: QPointF, p2: QPointF):
        active_layer = self.layer_manager.get_active_layer()
        if not active_layer or active_layer.layer_type != LayerType.RASTER or not active_layer.raster_image:
            return

        painter = QPainter(active_layer.raster_image)
        mode = self.input_safety.current_mode

        # User requirement 9: Restrict drawing to active selection bounds
        if self.selection_rect:
            if self.is_selection_inverted:
                path = QPainterPath()
                path.setFillRule(Qt.FillRule.OddEvenFill)
                path.addRect(QRectF(0, 0, self.layer_manager.width, self.layer_manager.height))
                path.addRect(self.selection_rect.normalized())
                painter.setClipPath(path)
            else:
                painter.setClipRect(self.selection_rect.normalized().toRect())
            painter.setClipping(True)

        # Right click or Eraser tool
        if self.is_right_erasing or mode == InputMode.ERASER:
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Clear)
            is_pixel_eraser = (getattr(self, "eraser_type", "soft") == "pixel") or (mode == InputMode.PENCIL)
            if is_pixel_eraser:
                painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)
                pen = QPen(QColor(0, 0, 0, 0), self.stroke_width, Qt.PenStyle.SolidLine, Qt.PenCapStyle.SquareCap, Qt.PenJoinStyle.MiterJoin)
            else:
                painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
                pen = QPen(QColor(0, 0, 0, 0), self.stroke_width * 2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)

        elif mode == InputMode.PENCIL:
            # Pencil: MS Paint style hard aliased pixels, no smooth edge!
            painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)
            pen = QPen(self.primary_color, self.stroke_width, Qt.PenStyle.SolidLine, Qt.PenCapStyle.SquareCap, Qt.PenJoinStyle.MiterJoin)

        else:  # BRUSH
            # Brush: Photoshop style anti-aliased smooth edge!
            painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
            pen = QPen(self.primary_color, self.stroke_width, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)

        painter.setPen(pen)
        painter.drawLine(p1.toPoint(), p2.toPoint())
        painter.end()

        self.update_raster_pixmap(active_layer.id)

    def _commit_raster_stroke(self):
        active_layer = self.layer_manager.get_active_layer()
        if not active_layer or self.stroke_before_image is None or not active_layer.raster_image:
            return

        old_img = self.stroke_before_image
        new_img = active_layer.raster_image.copy()
        layer_id = active_layer.id
        estimated_bytes = new_img.width() * new_img.height() * 4

        def undo():
            lay = self.layer_manager.get_layer(layer_id)
            if lay:
                lay.raster_image = old_img.copy()
                self.update_raster_pixmap(layer_id)

        def redo():
            lay = self.layer_manager.get_layer(layer_id)
            if lay:
                lay.raster_image = new_img.copy()
                self.update_raster_pixmap(layer_id)

        self.history_manager.record_step("드로잉 스트로크", undo, redo, estimated_bytes=estimated_bytes)
        self.stroke_before_image = None

    # --- Flood Fill ---

    def _apply_flood_fill(self, pt: QPointF, is_secondary: bool = False):
        active_layer = self.layer_manager.get_active_layer()
        if not active_layer or active_layer.layer_type != LayerType.RASTER or not active_layer.raster_image:
            return

        # Restrict flood fill to active selection
        if self.selection_rect:
            in_sel = self.selection_rect.normalized().contains(pt)
            if self.is_selection_inverted and in_sel:
                return
            elif not self.is_selection_inverted and not in_sel:
                return

        x, y = int(pt.x()), int(pt.y())
        old_img = active_layer.raster_image.copy()
        fill_c = self.secondary_color if is_secondary else self.primary_color
        clip_rect = None
        if self.selection_rect and not self.is_selection_inverted:
            clip_rect = self.selection_rect.normalized().toRect()

        sample_img = self.layer_manager.composite_to_image() if self.fill_sample_all_layers else None

        new_img = ImageProcessor.flood_fill(
            active_layer.raster_image, x, y, fill_c,
            tolerance=self.fill_tolerance,
            alpha_threshold=self.fill_alpha_threshold,
            clip_rect=clip_rect,
            sample_img=sample_img
        )
        active_layer.raster_image = new_img
        self.update_raster_pixmap(active_layer.id)

        layer_id = active_layer.id
        estimated_bytes = new_img.width() * new_img.height() * 4

        def undo():
            lay = self.layer_manager.get_layer(layer_id)
            if lay:
                lay.raster_image = old_img.copy()
                self.update_raster_pixmap(layer_id)

        def redo():
            lay = self.layer_manager.get_layer(layer_id)
            if lay:
                lay.raster_image = new_img.copy()
                self.update_raster_pixmap(layer_id)

        self.history_manager.record_step("페인트통 채우기", undo, redo, estimated_bytes=estimated_bytes)

    # --- Shape Insertion with True Vector Lines & Constraints ---

    def _calc_shape_bounds(
        self, p1: QPointF, p2: QPointF, mode: InputMode, modifiers: Qt.KeyboardModifier = Qt.KeyboardModifier.NoModifier
    ):
        dx = p2.x() - p1.x()
        dy = p2.y() - p1.y()

        if mode in (InputMode.SHAPE_LINE, InputMode.SHAPE_ARROW):
            # Shift snaps line/arrow to horizontal, vertical, or 45 degrees
            if modifiers & Qt.KeyboardModifier.ShiftModifier:
                angle = math.atan2(dy, dx)
                snapped_angle = round(angle / (math.pi / 4.0)) * (math.pi / 4.0)
                length = math.hypot(dx, dy)
                dx = length * math.cos(snapped_angle)
                dy = length * math.sin(snapped_angle)
            return p1.x(), p1.y(), dx, dy

        # Rect / Ellipse
        if modifiers & Qt.KeyboardModifier.ShiftModifier:
            size = max(abs(dx), abs(dy))
            dx = math.copysign(size, dx)
            dy = math.copysign(size, dy)

        if modifiers & Qt.KeyboardModifier.ControlModifier:
            # Center-out symmetric expansion
            x = p1.x() - abs(dx)
            y = p1.y() - abs(dy)
            w = abs(dx) * 2.0
            h = abs(dy) * 2.0
            return x, y, w, h
        else:
            x = min(p1.x(), p1.x() + dx)
            y = min(p1.y(), p1.y() + dy)
            w = abs(dx)
            h = abs(dy)
            return x, y, w, h

    def _update_shape_preview(
        self, p1: QPointF, p2: QPointF, mode: InputMode, modifiers: Qt.KeyboardModifier = Qt.KeyboardModifier.NoModifier,
        is_swapped: bool = False
    ):
        if not p1 or not p2:
            return

        if self.shape_preview_item:
            self.scene.removeItem(self.shape_preview_item)
            self.shape_preview_item = None

        x, y, w, h = self._calc_shape_bounds(p1, p2, mode, modifiers)

        stroke_c = self.secondary_color if is_swapped else self.primary_color
        fill_c = self.primary_color if is_swapped else self.secondary_color

        pen = QPen(stroke_c, self.stroke_width, Qt.PenStyle.DashLine)
        brush = QBrush(fill_c)

        if mode == InputMode.SHAPE_RECT:
            self.shape_preview_item = self.scene.addRect(x, y, w, h, pen, brush)
        elif mode == InputMode.SHAPE_ROUNDED_RECT:
            r = float(getattr(self, "rect_corner_radius", 12.0))
            path = QPainterPath()
            path.addRoundedRect(QRectF(x, y, w, h), r, r)
            self.shape_preview_item = self.scene.addPath(path, pen, brush)
        elif mode == InputMode.SHAPE_ELLIPSE:
            self.shape_preview_item = self.scene.addEllipse(x, y, w, h, pen, brush)
        elif mode == InputMode.SHAPE_LINE:
            # Real vector line from p1 to (p1.x + dx, p1.y + dy)
            self.shape_preview_item = self.scene.addLine(QLineF(x, y, x + w, y + h), pen)
        elif mode == InputMode.SHAPE_ARROW:
            # Real-time preview of vector arrow pointing from p1 towards p2
            dx = w
            dy = h
            length = max(16.0, math.hypot(dx, dy))
            thickness = max(16.0, float(self.stroke_width * 4.0))
            angle = math.degrees(math.atan2(dy, dx))
            cx = x + dx / 2.0
            cy = y + dy / 2.0
            arr_mode = getattr(self, "current_arrow_mode", "single")
            meta = {}
            if arr_mode in ("curved_single", "curved_double"):
                meta["curve_y"] = -thickness * 0.7
            local_path = create_arrow_path(length, thickness, arr_mode, meta)
            tr = QTransform().translate(cx, cy).rotate(angle)
            preview_path = tr.map(local_path)
            self.shape_preview_item = self.scene.addPath(preview_path, pen, brush)

        if self.shape_preview_item:
            self.shape_preview_item.setZValue(999)

    def _commit_shape(
        self, p1: QPointF, p2: QPointF, mode: InputMode, modifiers: Qt.KeyboardModifier = Qt.KeyboardModifier.NoModifier,
        is_swapped: bool = False
    ):
        if not p1 or not p2:
            return

        if self.shape_preview_item:
            self.scene.removeItem(self.shape_preview_item)
            self.shape_preview_item = None

        x, y, w, h = self._calc_shape_bounds(p1, p2, mode, modifiers)
        if abs(w) < 2 and abs(h) < 2:
            return

        if mode == InputMode.SHAPE_RECT:
            s_type = "rect"
        elif mode == InputMode.SHAPE_ROUNDED_RECT:
            s_type = "rounded_rect"
        elif mode == InputMode.SHAPE_ELLIPSE:
            s_type = "ellipse"
        elif mode == InputMode.SHAPE_LINE:
            s_type = "line"
        elif mode == InputMode.SHAPE_ARROW:
            s_type = "arrow"
        else:
            s_type = "rect"

        stroke_c = self.secondary_color if is_swapped else self.primary_color
        fill_c = self.primary_color if is_swapped else self.secondary_color

        if s_type == "line":
            dx = w
            dy = h
            cx = x + dx / 2.0
            cy = y + dy / 2.0
            shape_data = ShapeItemData(
                shape_type="line",
                x=cx - abs(dx) / 2.0,
                y=cy - abs(dy) / 2.0,
                width=max(10.0, abs(dx)),
                height=max(10.0, abs(dy)),
                stroke_color=stroke_c.name(),
                fill_color=fill_c.name(),
                stroke_width=self.stroke_width,
                meta={
                    "p1_x": -dx / 2.0, "p1_y": -dy / 2.0,
                    "p2_x": dx / 2.0, "p2_y": dy / 2.0,
                    "p1_local": [-dx / 2.0, -dy / 2.0],
                    "p2_local": [dx / 2.0, dy / 2.0],
                }
            )
        elif s_type == "arrow":
            dx = w
            dy = h
            length = max(16.0, math.hypot(dx, dy))
            thickness = max(16.0, float(self.stroke_width * 4.0))
            angle = math.degrees(math.atan2(dy, dx))
            cx = x + dx / 2.0
            cy = y + dy / 2.0
            arr_mode = getattr(self, "current_arrow_mode", "single")
            meta = {
                "rotation": angle,
                "arrow_mode": arr_mode,
            }
            if arr_mode in ("curved_single", "curved_double"):
                meta["curve_x"] = 0.0
                meta["curve_y"] = -thickness * 0.7
            shape_data = ShapeItemData(
                shape_type="arrow",
                x=cx - length / 2.0,
                y=cy - thickness / 2.0,
                width=length,
                height=thickness,
                stroke_color=stroke_c.name(),
                fill_color=fill_c.name(),
                stroke_width=self.stroke_width,
                meta=meta
            )
        elif s_type == "rounded_rect":
            r = float(getattr(self, "rect_corner_radius", 12.0))
            shape_data = ShapeItemData(
                shape_type="rounded_rect",
                x=x, y=y, width=abs(w), height=abs(h),
                stroke_color=stroke_c.name(),
                fill_color=fill_c.name(),
                stroke_width=self.stroke_width,
                meta={
                    "corner_radius": r
                }
            )
        else:
            shape_data = ShapeItemData(
                shape_type=s_type,
                x=x, y=y, width=abs(w), height=abs(h),
                stroke_color=stroke_c.name(),
                fill_color=fill_c.name(),
                stroke_width=self.stroke_width
            )

        # Approach 2: If there is an active selection rect, associate clip_rect with the shape!
        if self.selection_rect and not self.selection_rect.isEmpty():
            norm_r = self.selection_rect.normalized()
            shape_data.meta["clip_rect"] = [norm_r.x(), norm_r.y(), norm_r.width(), norm_r.height()]

        shape_layer = self.layer_manager.add_shape_to_default_layer(shape_data)
        item = self._create_shape_graphics_item(shape_data, visible=shape_layer.visible)
        self.shape_items[shape_data.id] = item

        self.scene.clearSelection()
        item.setSelected(True)

        def undo():
            lay = self.layer_manager.get_default_shape_layer()
            if shape_data in lay.shapes:
                lay.shapes.remove(shape_data)
            if item in self.scene.items():
                self.scene.removeItem(item)
            if shape_data.id in self.shape_items:
                del self.shape_items[shape_data.id]

        def redo():
            lay = self.layer_manager.get_default_shape_layer()
            lay.shapes.append(shape_data)
            self._create_shape_graphics_item(shape_data, visible=lay.visible)

        self.history_manager.record_step(f"도형 추가: {s_type}", undo, redo, estimated_bytes=1024)
        # Visual status hint when shape is created
        self.status_message.emit(I18N.tr("status_shape_selected"))
        self.canvas_modified.emit()

    def _update_mosaic_preview(self, p1: QPointF, p2: QPointF):
        if not p1 or not p2:
            return
        if self.mosaic_preview_item and self.mosaic_preview_item in self.scene.items():
            self.scene.removeItem(self.mosaic_preview_item)
            self.mosaic_preview_item = None
        r = QRectF(p1, p2).normalized()
        pen = QPen(QColor(37, 99, 235), 1.5, Qt.PenStyle.DashLine)
        brush = QBrush(QColor(59, 130, 246, 35))
        self.mosaic_preview_item = self.scene.addRect(r, pen, brush)
        self.mosaic_preview_item.setZValue(9999)

    @staticmethod
    def format_step_badge(n: int, mode: str = "number") -> str:
        """Formats an integer step badge into numbers, uppercase letters, or lowercase letters."""
        val = max(1, int(n))
        if mode == "alpha_upper":
            res = ""
            while val > 0:
                val, rem = divmod(val - 1, 26)
                res = chr(65 + rem) + res
            return res or "A"
        elif mode == "alpha_lower":
            res = ""
            while val > 0:
                val, rem = divmod(val - 1, 26)
                res = chr(97 + rem) + res
            return res or "a"
        else:
            return str(n)

    def _finalize_mosaic(self, p1: QPointF, p2: QPointF, block_size: Optional[int] = None):
        if self.mosaic_preview_item and self.mosaic_preview_item in self.scene.items():
            self.scene.removeItem(self.mosaic_preview_item)
        self.mosaic_preview_item = None

        r = QRectF(p1, p2).normalized().toRect()
        if r.width() < 4 or r.height() < 4:
            r = QRect(int(p1.x()) - 24, int(p1.y()) - 24, 48, 48)

        active_layer = self.layer_manager.get_active_layer()
        if not active_layer or active_layer.layer_type != LayerType.RASTER or not active_layer.raster_image:
            for l in self.layer_manager.layers:
                if l.layer_type == LayerType.RASTER and l.raster_image:
                    active_layer = l
                    break

        if not active_layer or not active_layer.raster_image:
            return

        bs = block_size if block_size is not None else getattr(self, "mosaic_block_size", 12)
        before_img = self.stroke_before_image or active_layer.raster_image.copy()
        new_img = ImageProcessor.apply_mosaic(active_layer.raster_image, r, block_size=bs)
        active_layer.raster_image = new_img
        self.update_raster_pixmap(active_layer.id)

        after_img = new_img.copy()
        layer_id = active_layer.id

        def undo():
            lay = self.layer_manager.get_layer(layer_id)
            if lay:
                lay.raster_image = before_img.copy()
                self.update_raster_pixmap(layer_id)

        def redo():
            lay = self.layer_manager.get_layer(layer_id)
            if lay:
                lay.raster_image = after_img.copy()
                self.update_raster_pixmap(layer_id)

        self.history_manager.record_step("모자이크 적용", undo, redo, estimated_bytes=before_img.sizeInBytes() * 2)
        self.status_message.emit("선택 영역에 모자이크가 적용되었습니다.")
        self.canvas_modified.emit()

    def _apply_step_badge(self, pt: QPointF):
        """Places an auto-incrementing numbered/lettered badge (①, A, a...) at the clicked position."""
        self.input_safety.current_mode = InputMode.STEP_BADGE
        active_layer = self.layer_manager.get_active_layer()
        if not active_layer or active_layer.layer_type != LayerType.RASTER or not active_layer.raster_image:
            for l in self.layer_manager.layers:
                if l.layer_type == LayerType.RASTER and l.raster_image:
                    active_layer = l
                    break

        if not active_layer or not active_layer.raster_image:
            return

        before_img = active_layer.raster_image.copy()
        radius = max(14, int(self.stroke_width * 2 + 10))
        badge_rect = QRectF(pt.x() - radius, pt.y() - radius, radius * 2, radius * 2)

        p = QPainter(active_layer.raster_image)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        # Subtle shadow
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(QColor(0, 0, 0, 70)))
        p.drawEllipse(badge_rect.translated(1.5, 1.5))

        # Circle background: Primary color (Fallback to Blue if transparent)
        bg_color = self.primary_color if self.primary_color.alpha() > 20 else QColor(37, 99, 235)
        p.setBrush(QBrush(bg_color))
        p.setPen(QPen(QColor(255, 255, 255, 230), 1.8))
        p.drawEllipse(badge_rect)

        # Number or Letter text: Secondary color
        fg_color = self.secondary_color if self.secondary_color != bg_color else QColor(255, 255, 255)
        p.setPen(QPen(fg_color))
        font = QFont("Malgun Gothic", int(radius * 0.95), QFont.Weight.Bold)
        p.setFont(font)
        badge_type = getattr(self, "step_badge_type", "number")
        text = self.format_step_badge(self.current_step_badge, badge_type)
        p.drawText(badge_rect, Qt.AlignmentFlag.AlignCenter, text)
        p.end()

        after_img = active_layer.raster_image.copy()
        layer_id = active_layer.id
        num = self.current_step_badge
        self.current_step_badge += 1
        next_text = self.format_step_badge(self.current_step_badge, badge_type)
        self.update_raster_pixmap(layer_id)

        def undo():
            lay = self.layer_manager.get_layer(layer_id)
            if lay:
                lay.raster_image = before_img.copy()
                self.update_raster_pixmap(layer_id)
            self.current_step_badge = num

        def redo():
            lay = self.layer_manager.get_layer(layer_id)
            if lay:
                lay.raster_image = after_img.copy()
                self.update_raster_pixmap(layer_id)
            self.current_step_badge = num + 1

        self.history_manager.record_step(f"스텝 배지 #{text}", undo, redo, estimated_bytes=before_img.sizeInBytes() * 2)
        self.status_message.emit(f"스텝 배지 #{text} 삽입 완료 (다음: #{next_text}, 우클릭: 시작 번호로 리셋)")
        self.canvas_modified.emit()

    def insert_shape_in_selection(self, shape_type: str = "rect") -> Optional[TransformableShapeItem]:
        """
        Approach 2 (Clipper / Vector Clipping Mask):
        When a selection rect exists, inserts a vector shape with a clipping mask
        matching the selection boundary. The shape is a fully editable vector object,
        and only the region inside the clipping mask is visible/rendered.
        """
        if not self.selection_rect or self.selection_rect.isEmpty():
            return None

        rect = self.selection_rect.normalized()
        x, y, w, h = rect.x(), rect.y(), rect.width(), rect.height()
        if w < 2 or h < 2:
            return None

        p1 = QPointF(x, y)
        p2 = QPointF(x + w, y + h)

        mode_map = {
            "rect": InputMode.SHAPE_RECT,
            "ellipse": InputMode.SHAPE_ELLIPSE,
            "line": InputMode.SHAPE_LINE,
            "arrow": InputMode.SHAPE_ARROW,
        }
        mode = mode_map.get(shape_type, InputMode.SHAPE_RECT)

        # Commit vector shape with clipping mask at the selection bounds
        self._commit_shape(p1, p2, mode)

        # Clear selection marquee
        self.clear_selection_marquee()

        # Switch input mode to SELECT (V) so user can immediately transform the newly inserted shape!
        self.input_safety.current_mode = InputMode.SELECT

        # Find the newly created item
        shape_layer = self.layer_manager.get_default_shape_layer()
        if shape_layer.shapes:
            last_shape = shape_layer.shapes[-1]
            if last_shape.id in self.shape_items:
                item = self.shape_items[last_shape.id]
                self.scene.clearSelection()
                item.setSelected(True)
                return item
        return None

    # --- Shape Callbacks from TransformableShapeItem ---

    def _on_shape_merge_requested(self, item: TransformableShapeItem):
        """Bakes shape down to the active raster layer."""
        shape_id = item.shape_data.id
        self.merge_shape_to_raster(shape_id)

    def merge_shape_to_raster(self, shape_id: str):
        active_layer = self.layer_manager.get_active_layer()
        if not active_layer or active_layer.layer_type != LayerType.RASTER:
            # Fallback to first raster layer
            for l in self.layer_manager.layers:
                if l.layer_type == LayerType.RASTER:
                    active_layer = l
                    break

        if not active_layer or not active_layer.raster_image:
            return

        shape_layer = self.layer_manager.get_default_shape_layer()
        shape_data = None
        for s in shape_layer.shapes:
            if s.id == shape_id:
                shape_data = s
                break

        if not shape_data:
            return

        old_img = active_layer.raster_image.copy()
        target_layer_id = active_layer.id

        if self.layer_manager.merge_shape_into_raster(shape_id, target_layer_id):
            if shape_id in self.shape_items:
                self.scene.removeItem(self.shape_items[shape_id])
                del self.shape_items[shape_id]
            self.update_raster_pixmap(target_layer_id)
            self.canvas_modified.emit()

            new_img = active_layer.raster_image.copy()

            def undo():
                lay = self.layer_manager.get_layer(target_layer_id)
                if lay:
                    lay.raster_image = old_img.copy()
                    self.update_raster_pixmap(target_layer_id)
                s_lay = self.layer_manager.get_default_shape_layer()
                if shape_data not in s_lay.shapes:
                    s_lay.shapes.append(shape_data)
                    self._create_shape_graphics_item(shape_data, visible=s_lay.visible)
                self.canvas_modified.emit()

            def redo():
                self.layer_manager.merge_shape_into_raster(shape_id, target_layer_id)
                if shape_id in self.shape_items:
                    self.scene.removeItem(self.shape_items[shape_id])
                    del self.shape_items[shape_id]
                self.update_raster_pixmap(target_layer_id)
                self.canvas_modified.emit()

            self.history_manager.record_step(
                "도형을 레이어에 고정", undo, redo,
                estimated_bytes=new_img.width() * new_img.height() * 4
            )

    def _on_shape_delete_requested(self, item: TransformableShapeItem):
        shape_id = item.shape_data.id
        shape_layer = self.layer_manager.get_default_shape_layer()
        shape_layer.shapes = [s for s in shape_layer.shapes if s.id != shape_id]
        if item in self.scene.items():
            self.scene.removeItem(item)
        if shape_id in self.shape_items:
            del self.shape_items[shape_id]
        self.canvas_modified.emit()

    def _on_shape_reorder_requested(self, item: TransformableShapeItem, direction: str):
        shape_id = item.shape_data.id
        if direction == "front":
            self.layer_manager.bring_shape_to_front(shape_id)
        elif direction == "back":
            self.layer_manager.send_shape_to_back(shape_id)
        self.rebuild_scene()

    # --- MS Paint Style Marquee Area Selection ---

    def _on_marquee_rect_changed(self, rect: QRectF):
        self.selection_rect = rect

    def _update_marquee_preview(self, p1: QPointF, p2: QPointF):
        x = min(p1.x(), p2.x())
        y = min(p1.y(), p2.y())
        w = abs(p2.x() - p1.x())
        h = abs(p2.y() - p1.y())
        rect = QRectF(x, y, w, h)

        if not self.marquee_box:
            self.marquee_box = MarqueeSelectionBox(
                rect,
                on_rect_changed_cb=self._on_marquee_rect_changed,
                on_context_menu_cb=self._show_selection_context_menu
            )
            self.scene.addItem(self.marquee_box)
        else:
            self.marquee_box.set_rect(rect)

    def _finalize_marquee(self, p1: QPointF, p2: QPointF):
        x = min(p1.x(), p2.x())
        y = min(p1.y(), p2.y())
        w = abs(p2.x() - p1.x())
        h = abs(p2.y() - p1.y())
        if w > 2 and h > 2:
            self.selection_rect = QRectF(x, y, w, h)
        else:
            self.clear_selection_marquee()

    def clear_selection_marquee(self):
        if self.marquee_box and self.marquee_box in self.scene.items():
            self.scene.removeItem(self.marquee_box)
        self.marquee_box = None
        self.selection_rect = None
        self.is_selection_inverted = False

    def _create_floating_selection_from_rect(self, rect: QRectF):
        """Cuts selected pixels from active raster layer into floating selection."""
        active_layer = self.layer_manager.get_active_layer()
        if not active_layer or active_layer.layer_type != LayerType.RASTER or not active_layer.raster_image:
            return

        rx, ry, rw, rh = int(rect.x()), int(rect.y()), int(rect.width()), int(rect.height())
        # Issue 3: Snapshot pre-cut raster & selection rect so the cut/move can be undone atomically
        self._float_origin = {
            "layer_id": active_layer.id,
            "before_img": active_layer.raster_image.copy(),
            "sel_rect": QRectF(rect),
        }
        cut_img = active_layer.raster_image.copy(rx, ry, rw, rh)

        # MS Paint Transparent Selection: key out secondary background color
        if self.transparent_selection_enabled:
            arr = ImageProcessor.qimage_to_numpy(cut_img)
            # Only key out if secondary color is an actual non-transparent color!
            # If secondary color is transparent (alpha <= 10), already-transparent pixels stay transparent
            # and opaque pixels (such as black lines [0,0,0]) must NOT be erased!
            if self.secondary_color.alpha() > 10:
                sec_r = self.secondary_color.red()
                sec_g = self.secondary_color.green()
                sec_b = self.secondary_color.blue()
                diff = np.maximum.reduce([
                    np.abs(arr[:, :, 0].astype(int) - sec_r),
                    np.abs(arr[:, :, 1].astype(int) - sec_g),
                    np.abs(arr[:, :, 2].astype(int) - sec_b),
                ])
                # Key out pixels that match secondary color AND are not already transparent
                mask = (diff <= 24) & (arr[:, :, 3] > 10)
                arr[mask, 3] = 0
                cut_img = ImageProcessor.numpy_to_qimage(arr)

        # Clear cut area on raster layer:
        # In MS Paint style, solid bg_layer always fills secondary background color on cut.
        # Transparent raster layers always punch a transparent hole (CompositionMode_Clear)
        # so transparent areas never turn into opaque secondary background color.
        p = QPainter(active_layer.raster_image)
        if active_layer.id == "bg_layer":
            p.setCompositionMode(QPainter.CompositionMode.CompositionMode_Source)
            p.fillRect(rx, ry, rw, rh, self.secondary_color)
        else:
            p.setCompositionMode(QPainter.CompositionMode.CompositionMode_Clear)
            p.fillRect(rx, ry, rw, rh, QColor(0, 0, 0, 0))
        p.end()
        self.update_raster_pixmap(active_layer.id)

        # Clear marquee box
        self.clear_selection_marquee()

        # Create floating selection item
        self.floating_selection = FloatingSelectionItem(
            QPixmap.fromImage(cut_img),
            rect.topLeft(),
            on_commit_cb=self._on_floating_selection_committed
        )
        self.scene.addItem(self.floating_selection)
        self.scene.clearSelection()
        self.floating_selection.setSelected(True)

    def _on_floating_selection_committed(self, item: FloatingSelectionItem):
        """Bakes floating selection down to the active raster layer."""
        active_layer = self.layer_manager.get_active_layer()
        if active_layer and active_layer.layer_type == LayerType.RASTER and active_layer.raster_image:
            pos = item.pos()
            p = QPainter(active_layer.raster_image)
            p.drawPixmap(int(pos.x()), int(pos.y()), item.pixmap)
            p.end()
            self.update_raster_pixmap(active_layer.id)

        if item in self.scene.items():
            self.scene.removeItem(item)
        self.floating_selection = None
        self._record_float_history("선택 영역 이동/잘라내기")
        self.canvas_modified.emit()

    def commit_floating_selection_if_any(self):
        if self.floating_selection:
            self._on_floating_selection_committed(self.floating_selection)

    def _restore_selection_state(self, rect: Optional[QRectF]):
        """Discards any floating selection and restores marquee to the given rect (or clears it)."""
        if self.floating_selection is not None:
            if self.floating_selection in self.scene.items():
                self.scene.removeItem(self.floating_selection)
            self.floating_selection = None
        self.clear_selection_marquee()
        if rect is not None and not rect.isEmpty():
            self._update_marquee_preview(rect.topLeft(), rect.bottomRight())
            self.selection_rect = QRectF(rect)

    def _record_float_history(self, desc: str):
        """Records an atomic undo step from the floating-selection origin snapshot to the current raster."""
        origin = getattr(self, "_float_origin", None)
        self._float_origin = None
        if not origin or self.history_manager is None:
            return
        layer_id = origin["layer_id"]
        lay = self.layer_manager.get_layer(layer_id)
        if not lay or lay.raster_image is None:
            return
        before_img = origin["before_img"]
        after_img = lay.raster_image.copy()
        sel_rect = origin["sel_rect"]

        def undo():
            l = self.layer_manager.get_layer(layer_id)
            if l:
                l.raster_image = before_img.copy()
                self.update_raster_pixmap(layer_id)
            self._restore_selection_state(sel_rect)
            self.canvas_modified.emit()

        def redo():
            l = self.layer_manager.get_layer(layer_id)
            if l:
                l.raster_image = after_img.copy()
                self.update_raster_pixmap(layer_id)
            self._restore_selection_state(None)
            self.canvas_modified.emit()

        est = after_img.width() * after_img.height() * 4 * 2
        self.history_manager.record_step(desc, undo, redo, estimated_bytes=est)

    def _show_selection_context_menu(self, global_pos):
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: #ffffff;
                color: #1e293b;
                border: 1px solid #cbd5e1;
                border-radius: 6px;
                padding: 4px;
                font-size: 12px;
            }
            QMenu::item {
                padding: 6px 20px 6px 10px;
                border-radius: 4px;
            }
            QMenu::item:selected {
                background-color: #eff6ff;
                color: #2563eb;
            }
            QMenu::separator {
                height: 1px;
                background: #e2e8f0;
                margin: 4px 6px;
            }
        """)
        cut_act = menu.addAction("✂️ 잘라내기 (Ctrl+X)")
        copy_act = menu.addAction("📋 복사 (Ctrl+C)")
        paste_act = menu.addAction("📥 붙여넣기 (Ctrl+V)")
        menu.addSeparator()
        adj_act = menu.addAction("🎨 색상 및 톤 보정...")
        shape_menu = menu.addMenu("🔷 선택 영역에 도형 맞춤 삽입")
        rect_shape_act = shape_menu.addAction("🟩 직사각형 벡터 도형 삽입")
        ellipse_shape_act = shape_menu.addAction("⚪ 타원 벡터 도형 삽입")
        line_shape_act = shape_menu.addAction("📏 대각선 벡터 도형 삽입")
        menu.addSeparator()
        rot_act = menu.addAction("🔄 90° 시계방향 회전")
        fliph_act = menu.addAction("↔️ 좌우 대칭 반전")
        flipv_act = menu.addAction("↕️ 상하 대칭 반전")
        menu.addSeparator()
        inv_act = menu.addAction("🔄 선택 영역 반전 (Ctrl+Shift+I)")
        all_act = menu.addAction("🔳 전체 선택 (Ctrl+A)")
        desel_act = menu.addAction("✖️ 선택 해제 (Ctrl+D)")
        del_act = menu.addAction("🗑️ 삭제 (Delete)")

        pos = global_pos.toPoint() if hasattr(global_pos, "toPoint") else global_pos
        chosen = menu.exec(pos)
        if chosen == cut_act:
            self.cut_selection()
        elif chosen == copy_act:
            self.copy_selection()
        elif chosen == paste_act:
            self.paste_selection()
        elif chosen == adj_act:
            if self.selection_rect:
                self.adjustment_requested.emit(self.selection_rect.normalized().toRect())
            else:
                w, h = self.layer_manager.width, self.layer_manager.height
                self.adjustment_requested.emit(QRect(0, 0, w, h))
        elif chosen == rect_shape_act:
            self.insert_shape_in_selection("rect")
        elif chosen == ellipse_shape_act:
            self.insert_shape_in_selection("ellipse")
        elif chosen == line_shape_act:
            self.insert_shape_in_selection("line")
        elif chosen == rot_act:
            self.rotate_selection_90()
        elif chosen == fliph_act:
            self.flip_selection_horizontal()
        elif chosen == flipv_act:
            self.flip_selection_vertical()
        elif chosen == inv_act:
            self.invert_selection()
        elif chosen == all_act:
            self.select_all()
        elif chosen == desel_act:
            self.deselect()
        elif chosen == del_act:
            self.delete_selection()

    def rotate_selection_90(self):
        if self.selection_rect and not self.floating_selection:
            self._create_floating_selection_from_rect(self.selection_rect)
        if self.floating_selection:
            trans = QTransform().rotate(90)
            self.floating_selection.pixmap = self.floating_selection.pixmap.transformed(trans)
            self.floating_selection.update()
            self.canvas_modified.emit()

    def flip_selection_horizontal(self):
        if self.selection_rect and not self.floating_selection:
            self._create_floating_selection_from_rect(self.selection_rect)
        if self.floating_selection:
            trans = QTransform().scale(-1, 1)
            self.floating_selection.pixmap = self.floating_selection.pixmap.transformed(trans)
            self.floating_selection.update()
            self.canvas_modified.emit()

    def flip_selection_vertical(self):
        if self.selection_rect and not self.floating_selection:
            self._create_floating_selection_from_rect(self.selection_rect)
        if self.floating_selection:
            trans = QTransform().scale(1, -1)
            self.floating_selection.pixmap = self.floating_selection.pixmap.transformed(trans)
            self.floating_selection.update()
            self.canvas_modified.emit()

    def deselect(self):
        self.commit_floating_selection_if_any()
        self.clear_selection_marquee()
        self.is_selection_inverted = False
        self.viewport().update()

    def invert_selection(self):
        if not self.selection_rect:
            self.select_all()
        else:
            self.is_selection_inverted = not self.is_selection_inverted
            if self.marquee_box:
                self.marquee_box.set_inverted(self.is_selection_inverted)
            self.viewport().update()

    # --- Clipboard Operations (LJack Protocol: OS Lock Collision Interlock) ---

    @staticmethod
    def _safe_clipboard_set_pixmap(pixmap: QPixmap, max_retries: int = 3, retry_delay_ms: int = 15) -> bool:
        """Safely sets pixmap with retry interlock to defend against external clipboard locking apps."""
        import time
        cb = QApplication.clipboard()
        for attempt in range(max_retries):
            try:
                cb.setPixmap(pixmap)
                return True
            except Exception:
                if attempt < max_retries - 1:
                    time.sleep(retry_delay_ms / 1000.0)
        return False

    @staticmethod
    def _safe_clipboard_set_image(image: QImage, max_retries: int = 3, retry_delay_ms: int = 15) -> bool:
        """Safely sets QImage with retry interlock against Windows OS clipboard contention."""
        import time
        cb = QApplication.clipboard()
        for attempt in range(max_retries):
            try:
                cb.setImage(image)
                return True
            except Exception:
                if attempt < max_retries - 1:
                    time.sleep(retry_delay_ms / 1000.0)
        return False

    @staticmethod
    def _safe_clipboard_get_image(max_retries: int = 3, retry_delay_ms: int = 15) -> QImage:
        """Safely retrieves QImage with retry interlock against transient clipboard locks."""
        import time
        cb = QApplication.clipboard()
        for attempt in range(max_retries):
            try:
                img = cb.image()
                if not img.isNull():
                    return img
            except Exception:
                pass
            if attempt < max_retries - 1:
                time.sleep(retry_delay_ms / 1000.0)
        return cb.image()

    def cut_selection(self):
        if self.selection_rect and not self.floating_selection:
            self._create_floating_selection_from_rect(self.selection_rect)
        if self.floating_selection:
            CanvasView._safe_clipboard_set_pixmap(self.floating_selection.pixmap)
            self.scene.removeItem(self.floating_selection)
            self.floating_selection = None
            self.clear_selection_marquee()
            self._record_float_history("선택 영역 잘라내기")
            self.canvas_modified.emit()
            self.show_toast("✂️ 선택 영역을 잘라내어 클립보드에 복사했습니다!")

    def copy_selection(self):
        copied = False
        if self.selection_rect and not self.floating_selection:
            active_layer = self.layer_manager.get_active_layer()
            if active_layer and active_layer.raster_image:
                rx, ry, rw, rh = int(self.selection_rect.x()), int(self.selection_rect.y()), int(self.selection_rect.width()), int(self.selection_rect.height())
                img = active_layer.raster_image.copy(rx, ry, rw, rh)
                copied = CanvasView._safe_clipboard_set_image(img)
        elif self.floating_selection:
            copied = CanvasView._safe_clipboard_set_pixmap(self.floating_selection.pixmap)
        else:
            # Copy whole composite image if nothing selected
            img = self.layer_manager.composite_to_image()
            copied = CanvasView._safe_clipboard_set_image(img)
        if copied:
            self.show_toast("📋 이미지가 클립보드에 복사되었습니다!")

    @staticmethod
    def _safe_clipboard_set_png_mime(image: QImage, max_retries: int = 3, retry_delay_ms: int = 15) -> bool:
        """
        Encodes QImage as PNG byte stream and registers 'image/png' MIME data to Windows clipboard,
        preserving alpha transparency across modern apps (Slack, Notion, Discord, Chrome, etc.).
        """
        import time
        byte_array = QByteArray()
        buffer = QBuffer(byte_array)
        buffer.open(QIODevice.OpenModeFlag.WriteOnly)
        image.save(buffer, "PNG")
        buffer.close()

        mime = QMimeData()
        mime.setData("image/png", byte_array)
        mime.setImageData(image)  # Fallback for legacy apps

        cb = QApplication.clipboard()
        for attempt in range(max_retries):
            try:
                cb.setMimeData(mime)
                return True
            except Exception:
                if attempt < max_retries - 1:
                    time.sleep(retry_delay_ms / 1000.0)
        return False

    def copy_selection_transparent(self):
        """
        Copies the selected area or entire canvas to Windows clipboard
        with true alpha transparency preserved via 'image/png' MIME data.
        """
        img = None
        if self.floating_selection:
            img = self.floating_selection.pixmap.toImage()
        elif self.selection_rect and not self.selection_rect.isEmpty():
            active_layer = self.layer_manager.get_active_layer()
            if active_layer and active_layer.raster_image:
                rx = int(self.selection_rect.x())
                ry = int(self.selection_rect.y())
                rw = int(self.selection_rect.width())
                rh = int(self.selection_rect.height())
                img = active_layer.raster_image.copy(rx, ry, rw, rh)
        else:
            img = self.layer_manager.composite_to_image()

        if img and not img.isNull():
            CanvasView._safe_clipboard_set_png_mime(img)
            self.status_message.emit("투명 배경 포함 클립보드 복사 완료 (Ctrl+Shift+C)")
            self.show_toast("📋 투명 PNG 이미지가 클립보드에 복사되었습니다!")

    def paste_selection(self):
        img = CanvasView._safe_clipboard_get_image()
        if not img.isNull():
            self.commit_floating_selection_if_any()
            self.clear_selection_marquee()
            # Issue 3: Snapshot target raster before paste so the baked paste is undoable
            active_layer = self.layer_manager.get_active_layer()
            if active_layer and active_layer.layer_type == LayerType.RASTER and active_layer.raster_image:
                self._float_origin = {
                    "layer_id": active_layer.id,
                    "before_img": active_layer.raster_image.copy(),
                    "sel_rect": None,
                }
            self.floating_selection = FloatingSelectionItem(
                QPixmap.fromImage(img),
                QPointF(20, 20),
                on_commit_cb=self._on_floating_selection_committed
            )
            self.scene.addItem(self.floating_selection)
            self.scene.clearSelection()
            self.floating_selection.setSelected(True)

    def delete_selection(self):
        if self.floating_selection:
            self.scene.removeItem(self.floating_selection)
            self.floating_selection = None
            self._record_float_history("선택 영역 삭제")
            self.canvas_modified.emit()
        elif self.selection_rect:
            active_layer = self.layer_manager.get_active_layer()
            if active_layer and active_layer.raster_image:
                self._float_origin = {
                    "layer_id": active_layer.id,
                    "before_img": active_layer.raster_image.copy(),
                    "sel_rect": QRectF(self.selection_rect),
                }
                rx, ry, rw, rh = int(self.selection_rect.x()), int(self.selection_rect.y()), int(self.selection_rect.width()), int(self.selection_rect.height())
                p = QPainter(active_layer.raster_image)
                p.setCompositionMode(QPainter.CompositionMode.CompositionMode_Clear)
                p.fillRect(rx, ry, rw, rh, QColor(0, 0, 0, 0))
                p.end()
                self.update_raster_pixmap(active_layer.id)
            self.clear_selection_marquee()
            self._record_float_history("선택 영역 삭제")
            self.canvas_modified.emit()

    def select_all(self):
        self.commit_floating_selection_if_any()
        w, h = self.layer_manager.width, self.layer_manager.height
        self._finalize_marquee(QPointF(0, 0), QPointF(w, h))
        self._update_marquee_preview(QPointF(0, 0), QPointF(w, h))

    def _pick_color_at(self, pt: QPointF, is_secondary: bool = False):
        """Samples pixel color from composite layers and emits signal."""
        composite = self.layer_manager.composite_to_image()
        x, y = int(pt.x()), int(pt.y())
        if 0 <= x < composite.width() and 0 <= y < composite.height():
            c = composite.pixelColor(x, y)
            if is_secondary:
                self.secondary_color = c
                self.secondary_color_picked.emit(c)
            else:
                self.primary_color = c
                self.color_picked.emit(c)

    # --- Zoom, View & Grid Controls ---

    def set_zoom_level(self, new_zoom: float):
        new_zoom = max(0.05, min(32.0, new_zoom))
        if abs(new_zoom - self.zoom_level) < 1e-4:
            return
        factor = new_zoom / self.zoom_level
        self.zoom_level = new_zoom
        self.scale(factor, factor)
        self.zoom_changed.emit(self.zoom_level)
        self.viewport().update()
        if hasattr(self, "hud"):
            self.hud.activate_hud()

    def zoom_in(self):
        self.set_zoom_level(self.zoom_level * 1.25)

    def zoom_out(self):
        self.set_zoom_level(self.zoom_level / 1.25)

    def reset_view(self):
        """Resets view scale to 1:1 (100%) and centers the canvas scene."""
        self.resetTransform()
        self.zoom_level = 1.0
        w, h = self.layer_manager.width, self.layer_manager.height
        self.centerOn(w / 2, h / 2)
        self.zoom_changed.emit(self.zoom_level)
        self.viewport().update()
        if hasattr(self, "hud"):
            self.hud.activate_hud()

    def set_grid_visible(self, visible: bool):
        self.grid_visible = visible
        self.viewport().update()

    def set_grid_spacing(self, spacing: int):
        self.grid_spacing = max(2, spacing)
        if self.grid_visible:
            self.viewport().update()

    def set_pixel_grid_enabled(self, enabled: bool):
        self.pixel_grid_enabled = enabled
        self.viewport().update()

    def drawForeground(self, painter: QPainter, rect: QRectF):
        """
        Renders:
        1. Photoshop-style Pixel Grid: At zoom >= 800%, renders subtle gray (800%-1200%) or alternating 50% dotted grid (>=1200%).
        2. Configurable Layout Grid: Minor dotted lines (selectable interval) + Major solid lines (4x interval).
        Optimized with bounding box clipping and batched drawLines.
        """
        super().drawForeground(painter, rect)

        w = self.layer_manager.width
        h = self.layer_manager.height
        canvas_rect = QRectF(0, 0, w, h)
        vis_rect = rect.intersected(canvas_rect)
        if vis_rect.isEmpty():
            return

        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)

        left = max(0.0, vis_rect.left())
        right = min(float(w), vis_rect.right())
        top = max(0.0, vis_rect.top())
        bottom = min(float(h), vis_rect.bottom())

        # 1. Pixel Grid (Photoshop style at >= 800% zoom)
        # User requirement: 임계점을 조절해서 훨씬 더 가까이 볼때에만 보이도록 수정
        if self.pixel_grid_enabled and self.zoom_level >= self.pixel_grid_threshold:
            i_left = int(math.floor(left))
            i_right = int(math.ceil(right))
            i_top = int(math.floor(top))
            i_bottom = int(math.ceil(bottom))

            pixel_lines = []
            for x in range(i_left, i_right + 1):
                if 0 <= x <= w:
                    pixel_lines.append(QLineF(x, top, x, bottom))
            for y in range(i_top, i_bottom + 1):
                if 0 <= y <= h:
                    pixel_lines.append(QLineF(left, y, right, y))

            if pixel_lines:
                if self.zoom_level < 12.0:
                    # Stage 1 (800% <= zoom < 1200%): Subtle, soft light gray solid lines
                    pen_light = QPen(QColor(170, 170, 170, 75), 0, Qt.PenStyle.SolidLine)
                    painter.setPen(pen_light)
                    painter.drawLines(pixel_lines)
                else:
                    # Stage 2 (zoom >= 1200%): High-zoom alternating white and gray 50% opacity dotted dashes
                    # Pass 1: Gray 50% opacity dotted dashes
                    pen_gray = QPen(QColor(130, 130, 130, 128), 0, Qt.PenStyle.CustomDashLine)
                    pen_gray.setDashPattern([2, 2])
                    painter.setPen(pen_gray)
                    painter.drawLines(pixel_lines)

                    # Pass 2: White 50% opacity dotted dashes interleaved
                    pen_white = QPen(QColor(255, 255, 255, 128), 0, Qt.PenStyle.CustomDashLine)
                    pen_white.setDashOffset(2)
                    pen_white.setDashPattern([2, 2])
                    painter.setPen(pen_white)
                    painter.drawLines(pixel_lines)

        # 2. Configurable Layout Grid (Minor dotted thin lines, Major solid lines)
        if self.grid_visible and self.grid_spacing > 0:
            spacing = self.grid_spacing
            major_spacing = spacing * 4

            start_x = int(math.floor(left / spacing)) * spacing
            end_x = int(math.ceil(right / spacing)) * spacing
            start_y = int(math.floor(top / spacing)) * spacing
            end_y = int(math.ceil(bottom / spacing)) * spacing

            minor_lines = []
            major_lines = []

            for x in range(start_x, end_x + 1, spacing):
                if 0 <= x <= w:
                    line = QLineF(x, top, x, bottom)
                    if x % major_spacing == 0:
                        major_lines.append(line)
                    else:
                        minor_lines.append(line)

            for y in range(start_y, end_y + 1, spacing):
                if 0 <= y <= h:
                    line = QLineF(left, y, right, y)
                    if y % major_spacing == 0:
                        major_lines.append(line)
                    else:
                        minor_lines.append(line)

            # Draw minor lines: light blue-gray dotted
            if minor_lines:
                minor_pen = QPen(QColor(70, 130, 200, 80), 0, Qt.PenStyle.DotLine)
                painter.setPen(minor_pen)
                painter.drawLines(minor_lines)

            # Draw major lines: solid crisp darker blue line
            if major_lines:
                major_pen = QPen(QColor(30, 90, 180, 160), 0, Qt.PenStyle.SolidLine)
                painter.setPen(major_pen)
                painter.drawLines(major_lines)

        painter.restore()

    def wheelEvent(self, event: QWheelEvent):
        if event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            delta = event.angleDelta().y()
            factor = 1.15 if delta > 0 else 1.0 / 1.15
            new_zoom = max(0.05, min(32.0, self.zoom_level * factor))
            actual_factor = new_zoom / self.zoom_level
            self.zoom_level = new_zoom
            self.scale(actual_factor, actual_factor)
            self.zoom_changed.emit(self.zoom_level)
            self.viewport().update()
            if hasattr(self, "hud"):
                self.hud.activate_hud()
            event.accept()
        elif event.modifiers() == Qt.KeyboardModifier.ShiftModifier:
            delta = event.angleDelta().y()
            self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() - delta)
            if hasattr(self, "hud"):
                self.hud.activate_hud()
            event.accept()
        else:
            if hasattr(self, "hud"):
                self.hud.activate_hud()
            super().wheelEvent(event)

    def keyPressEvent(self, event: QKeyEvent):
        key = event.key()

        # View reset shortcut: Ctrl+0
        if (key == Qt.Key.Key_0 or key == Qt.Key.Key_ParenRight) and (event.modifiers() & Qt.KeyboardModifier.ControlModifier):
            self.reset_view()
            event.accept()
            return

        # Photoshop shortcut: [ and ] for brush size
        if key == Qt.Key.Key_BracketLeft:
            new_w = max(1, self.stroke_width - 1)
            self.stroke_width = new_w
            self.stroke_width_changed.emit(new_w)
            event.accept()
            return
        elif key == Qt.Key.Key_BracketRight:
            new_w = min(100, self.stroke_width + 1)
            self.stroke_width = new_w
            self.stroke_width_changed.emit(new_w)
            event.accept()
            return

        # Enter / Return: Merge selected shape into raster layer
        if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            selected_shapes = [item for item in self.scene.selectedItems() if isinstance(item, TransformableShapeItem)]
            if selected_shapes:
                for s_item in selected_shapes:
                    self.merge_shape_to_raster(s_item.shape_data.id)
                self.status_message.emit(I18N.tr("status_shape_merged"))
                self.canvas_modified.emit()
                event.accept()
                return

        # Esc: Clear shape selection or marquee
        if key == Qt.Key.Key_Escape:
            self.scene.clearSelection()
            self.clear_selection_marquee()
            self.status_message.emit("선택이 해제되었습니다.")
            event.accept()
            return

        if key == Qt.Key.Key_Space:
            self.input_safety.set_space_pressed(True)
            self.setCursor(Qt.CursorShape.OpenHandCursor)
        elif key == Qt.Key.Key_Delete:
            # Delete selection or selected vector shapes
            if self.floating_selection or self.selection_rect:
                self.delete_selection()
            else:
                selected = self.scene.selectedItems()
                for itm in selected:
                    shape_id = itm.data(0)
                    if shape_id:
                        shape_layer = self.layer_manager.get_default_shape_layer()
                        shape_layer.shapes = [s for s in shape_layer.shapes if s.id != shape_id]
                    self.scene.removeItem(itm)
                self.canvas_modified.emit()
        else:
            super().keyPressEvent(event)

    def keyReleaseEvent(self, event: QKeyEvent):
        if event.key() == Qt.Key.Key_Space:
            self.input_safety.set_space_pressed(False)
            self.setCursor(Qt.CursorShape.ArrowCursor)
        else:
            super().keyReleaseEvent(event)


# Module-level export for helper functions
format_step_badge = CanvasView.format_step_badge
