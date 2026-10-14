"""
Paint Pro - Transformable Shape Item
PowerPoint-style interactive vector shape with 8 resize handles, rotation knob,
true line endpoints, and context menu support.
"""
import math
from enum import Enum
from typing import Optional, Callable
from PyQt6.QtWidgets import (
    QGraphicsItem, QStyleOptionGraphicsItem, QWidget, QMenu
)
from PyQt6.QtCore import Qt, QRectF, QPointF
from PyQt6.QtGui import QPainter, QPen, QBrush, QColor, QCursor, QPainterPath, QPolygonF, QFont
from core.layer_manager import ShapeItemData
from core.shape_geometry import create_arrow_path, create_rounded_rect_path
from core.i18n import I18N


class HandleType(Enum):
    NONE = 0
    TOP_LEFT = 1
    TOP_MID = 2
    TOP_RIGHT = 3
    MID_LEFT = 4
    MID_RIGHT = 5
    BOT_LEFT = 6
    BOT_MID = 7
    BOT_RIGHT = 8
    ROTATE = 9
    LINE_P1 = 10
    LINE_P2 = 11
    CURVE = 12


HANDLE_SIZE = 8.0
ROTATE_OFFSET = 24.0


class TransformableShapeItem(QGraphicsItem):
    def __init__(
        self,
        shape_data: ShapeItemData,
        on_merge_raster_cb: Optional[Callable[['TransformableShapeItem'], None]] = None,
        on_delete_cb: Optional[Callable[['TransformableShapeItem'], None]] = None,
        on_reorder_cb: Optional[Callable[['TransformableShapeItem', str], None]] = None,
        on_edit_text_cb: Optional[Callable[['TransformableShapeItem'], None]] = None,
        parent=None
    ):
        super().__init__(parent)
        self.shape_data = shape_data
        self.shape_type = shape_data.shape_type  # 'rect', 'ellipse', 'line', 'text'
        self.on_merge_raster_cb = on_merge_raster_cb
        self.on_delete_cb = on_delete_cb
        self.on_reorder_cb = on_reorder_cb
        self.on_edit_text_cb = on_edit_text_cb

        # Geometry in local space
        if self.shape_type == "line":
            p1_x = float(shape_data.meta.get("p1_x", -50.0))
            p1_y = float(shape_data.meta.get("p1_y", -50.0))
            p2_x = float(shape_data.meta.get("p2_x", 50.0))
            p2_y = float(shape_data.meta.get("p2_y", 50.0))
            self.p1_local = QPointF(p1_x, p1_y)
            self.p2_local = QPointF(p2_x, p2_y)
            self.width = max(10.0, abs(p2_x - p1_x))
            self.height = max(10.0, abs(p2_y - p1_y))
        else:
            self.width = max(10.0, float(shape_data.width))
            self.height = max(10.0, float(shape_data.height))
            self.p1_local = QPointF(-self.width / 2.0, -self.height / 2.0)
            self.p2_local = QPointF(self.width / 2.0, self.height / 2.0)

        cx = float(shape_data.x) + float(shape_data.width) / 2.0
        cy = float(shape_data.y) + float(shape_data.height) / 2.0
        self.setPos(cx, cy)

        init_rot = float(shape_data.meta.get("rotation", 0.0))
        self.setRotation(init_rot)

        self.setFlags(
            QGraphicsItem.GraphicsItemFlag.ItemIsSelectable |
            QGraphicsItem.GraphicsItemFlag.ItemIsMovable |
            QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges
        )
        self.setAcceptHoverEvents(True)

        self.active_handle = HandleType.NONE
        self.drag_start_pos = QPointF()
        self.drag_start_scene_pos = QPointF()
        self.orig_width = self.width
        self.orig_height = self.height
        self.orig_pos = self.pos()
        self.orig_rotation = self.rotation()
        self.orig_p1_local = self.p1_local
        self.orig_p2_local = self.p2_local
        self.is_dimmed = False

    def set_dimmed(self, dimmed: bool):
        """Dims selection outline & handles to 30% during ghost preview."""
        if getattr(self, "is_dimmed", False) != dimmed:
            self.is_dimmed = dimmed
            self.update()

    def sync_to_data(self):
        """Synchronizes current transform back to ShapeItemData."""
        cx, cy = self.pos().x(), self.pos().y()
        self.shape_data.width = self.width
        self.shape_data.height = self.height
        self.shape_data.x = cx - self.width / 2.0
        self.shape_data.y = cy - self.height / 2.0
        self.shape_data.meta["rotation"] = self.rotation()
        if self.shape_type == "line":
            self.shape_data.meta["p1_x"] = self.p1_local.x()
            self.shape_data.meta["p1_y"] = self.p1_local.y()
            self.shape_data.meta["p2_x"] = self.p2_local.x()
            self.shape_data.meta["p2_y"] = self.p2_local.y()
            self.shape_data.meta["p1_local"] = [self.p1_local.x(), self.p1_local.y()]
            self.shape_data.meta["p2_local"] = [self.p2_local.x(), self.p2_local.y()]

    def local_rect(self) -> QRectF:
        if self.shape_type == "line":
            return QRectF(self.p1_local, self.p2_local).normalized()
        return QRectF(-self.width / 2.0, -self.height / 2.0, self.width, self.height)

    def boundingRect(self) -> QRectF:
        pad = HANDLE_SIZE + ROTATE_OFFSET + 8.0
        return self.local_rect().adjusted(-pad, -pad, pad, pad)

    def _get_handle_rects(self):
        hs = HANDLE_SIZE
        hs2 = hs / 2.0

        if self.shape_type == "line":
            mid_x = (self.p1_local.x() + self.p2_local.x()) / 2.0
            top_y = min(self.p1_local.y(), self.p2_local.y())
            return {
                HandleType.LINE_P1: QRectF(self.p1_local.x() - hs2, self.p1_local.y() - hs2, hs, hs),
                HandleType.LINE_P2: QRectF(self.p2_local.x() - hs2, self.p2_local.y() - hs2, hs, hs),
                HandleType.ROTATE: QRectF(mid_x - hs2, top_y - ROTATE_OFFSET - hs2, hs, hs),
            }

        lr = self.local_rect()
        w2 = lr.width() / 2.0
        h2 = lr.height() / 2.0

        handles = {
            HandleType.TOP_LEFT: QRectF(-w2 - hs2, -h2 - hs2, hs, hs),
            HandleType.TOP_MID: QRectF(-hs2, -h2 - hs2, hs, hs),
            HandleType.TOP_RIGHT: QRectF(w2 - hs2, -h2 - hs2, hs, hs),
            HandleType.MID_LEFT: QRectF(-w2 - hs2, -hs2, hs, hs),
            HandleType.MID_RIGHT: QRectF(w2 - hs2, -hs2, hs, hs),
            HandleType.BOT_LEFT: QRectF(-w2 - hs2, h2 - hs2, hs, hs),
            HandleType.BOT_MID: QRectF(-hs2, h2 - hs2, hs, hs),
            HandleType.BOT_RIGHT: QRectF(w2 - hs2, h2 - hs2, hs, hs),
            HandleType.ROTATE: QRectF(-hs2, -h2 - ROTATE_OFFSET - hs2, hs, hs),
        }
        if self.shape_type == "arrow" and self.shape_data.meta.get("arrow_mode", "single") in ("curved_single", "curved_double"):
            cx = float(self.shape_data.meta.get("curve_x", 0.0))
            cy = float(self.shape_data.meta.get("curve_y", -h2 * 0.7))
            handles[HandleType.CURVE] = QRectF(cx - hs2, cy - hs2, hs, hs)

        return handles

    def _hit_test_handle(self, pt: QPointF) -> HandleType:
        if not self.isSelected():
            return HandleType.NONE
        handles = self._get_handle_rects()
        rot_rect = handles[HandleType.ROTATE].adjusted(-6, -6, 6, 6)
        if rot_rect.contains(pt):
            return HandleType.ROTATE

        for ht, rect in handles.items():
            if rect.adjusted(-5, -5, 5, 5).contains(pt):
                return ht
        return HandleType.NONE

    def paint(self, painter: QPainter, option: QStyleOptionGraphicsItem, widget: Optional[QWidget] = None):
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        # Approach 2: Vector Clipping Mask (Clipper)
        has_clip = "clip_rect" in self.shape_data.meta and self.shape_data.meta["clip_rect"] is not None
        if has_clip:
            painter.save()
            cr = self.shape_data.meta["clip_rect"]
            scene_cr = QRectF(float(cr[0]), float(cr[1]), float(cr[2]), float(cr[3]))
            clip_path = QPainterPath()
            clip_path.addRect(scene_cr)
            local_clip_path = self.mapFromScene(clip_path)
            painter.setClipPath(local_clip_path)

        pen = QPen(QColor(self.shape_data.stroke_color), self.shape_data.stroke_width)
        fill_c = QColor(self.shape_data.fill_color) if self.shape_data.fill_color != "transparent" else QColor(0, 0, 0, 0)
        brush = QBrush(fill_c)

        painter.setPen(pen)
        painter.setBrush(brush)

        lr = self.local_rect()

        if self.shape_type == "rect":
            painter.drawRect(lr)
        elif self.shape_type in ("rounded_rect", "shape_rounded_rect") or (self.shape_type == "rect" and self.shape_data.meta.get("corner_radius", 0) > 0):
            r = float(self.shape_data.meta.get("corner_radius", 12.0))
            path = create_rounded_rect_path(self.width, self.height, r)
            painter.drawPath(path)
        elif self.shape_type == "ellipse":
            painter.drawEllipse(lr)
        elif self.shape_type == "line":
            # True vector line connecting p1 to p2
            painter.drawLine(self.p1_local, self.p2_local)
        elif self.shape_type == "arrow":
            arr_mode = self.shape_data.meta.get("arrow_mode", "single")
            path = create_arrow_path(self.width, self.height, arr_mode, self.shape_data.meta)
            painter.drawPath(path)
        elif self.shape_type == "text":
            text_str = self.shape_data.meta.get("text", "")
            font_size = int(self.shape_data.meta.get("font_size", 24))
            font_family = self.shape_data.meta.get("font_family", "Malgun Gothic")
            font_bold = self.shape_data.meta.get("font_bold", False)
            font_italic = self.shape_data.meta.get("font_italic", False)
            font = QFont(font_family, font_size)
            font.setBold(font_bold)
            font.setItalic(font_italic)
            painter.setFont(font)
            painter.setPen(pen)
            if fill_c.alpha() > 0:
                painter.fillRect(lr, brush)
            painter.drawText(lr, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop, text_str)

        if has_clip:
            painter.restore()

        # PowerPoint-style handles (drawn unclipped so user can always see and manipulate handles!)
        if self.isSelected():
            dim_alpha = 76 if getattr(self, "is_dimmed", False) else 255
            border_pen = QPen(QColor(37, 99, 235, dim_alpha), 1.0, Qt.PenStyle.DashLine)
            painter.setPen(border_pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRect(lr)

            if self.shape_type == "line":
                mid_x = (self.p1_local.x() + self.p2_local.x()) / 2.0
                top_y = min(self.p1_local.y(), self.p2_local.y())
                rot_top = QPointF(mid_x, top_y)
                rot_center = QPointF(mid_x, top_y - ROTATE_OFFSET)
            else:
                rot_top = QPointF(0, lr.top())
                rot_center = QPointF(0, lr.top() - ROTATE_OFFSET)
            painter.setPen(QPen(QColor(37, 99, 235, dim_alpha), 1.0))
            painter.drawLine(rot_top, rot_center)

            handle_pen = QPen(QColor(37, 99, 235, dim_alpha), 1.5)
            handle_brush = QBrush(QColor(255, 255, 255, dim_alpha))
            painter.setPen(handle_pen)
            painter.setBrush(handle_brush)

            handles = self._get_handle_rects()
            for ht, rect in handles.items():
                if ht == HandleType.ROTATE:
                    painter.setBrush(QBrush(QColor(34, 197, 94, dim_alpha)))
                    painter.drawEllipse(rect)
                    painter.setBrush(handle_brush)
                elif ht in (HandleType.LINE_P1, HandleType.LINE_P2):
                    painter.setBrush(QBrush(QColor(239, 68, 68, dim_alpha)))  # Red circular knobs for line endpoints
                    painter.drawEllipse(rect)
                    painter.setBrush(handle_brush)
                elif ht == HandleType.CURVE:
                    painter.setBrush(QBrush(QColor(245, 158, 11, dim_alpha)))  # Amber knob for curvature control
                    painter.drawEllipse(rect)
                    painter.setBrush(handle_brush)
                else:
                    painter.drawRect(rect)

    def contextMenuEvent(self, event):
        """Context menu on shape right-click."""
        menu = QMenu()
        edit_text_act = None
        if self.shape_type == "text":
            edit_text_act = menu.addAction(I18N.tr("menu_edit_text"))
            menu.addSeparator()
        merge_act = menu.addAction(I18N.tr("menu_merge_raster"))
        menu.addSeparator()
        front_act = menu.addAction(I18N.tr("menu_bring_front"))
        back_act = menu.addAction(I18N.tr("menu_send_back"))
        menu.addSeparator()
        del_act = menu.addAction(I18N.tr("menu_del_shape"))

        screen_pos = event.screenPos() if hasattr(event, "screenPos") else (event.globalPos() if hasattr(event, "globalPos") else event.pos())
        chosen = menu.exec(screen_pos)
        if not chosen:
            event.accept()
            return

        if edit_text_act is not None and chosen == edit_text_act and self.on_edit_text_cb:
            self.on_edit_text_cb(self)
        elif chosen == merge_act and self.on_merge_raster_cb:
            self.on_merge_raster_cb(self)
        elif chosen == front_act and self.on_reorder_cb:
            self.on_reorder_cb(self, "front")
        elif chosen == back_act and self.on_reorder_cb:
            self.on_reorder_cb(self, "back")
        elif chosen == del_act and self.on_delete_cb:
            self.on_delete_cb(self)
        event.accept()

    def mouseDoubleClickEvent(self, event):
        """Double-clicking shape immediately commits and merges it to the active raster layer, or opens text editor."""
        if event.button() == Qt.MouseButton.LeftButton:
            if self.shape_type == "text" and self.on_edit_text_cb:
                self.on_edit_text_cb(self)
                event.accept()
                return
            elif self.on_merge_raster_cb:
                self.on_merge_raster_cb(self)
                event.accept()
                return
        super().mouseDoubleClickEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            handle = self._hit_test_handle(event.pos())
            if handle != HandleType.NONE:
                self.active_handle = handle
                self.drag_start_pos = event.pos()
                self.drag_start_scene_pos = event.scenePos()
                self.orig_width = self.width
                self.orig_height = self.height
                self.orig_pos = self.pos()
                self.orig_rotation = self.rotation()
                self.orig_p1_local = QPointF(self.p1_local)
                self.orig_p2_local = QPointF(self.p2_local)
                event.accept()
                return
            else:
                self.active_handle = HandleType.NONE
                self.drag_start_pos = event.pos()
                self.drag_start_scene_pos = event.scenePos()
                self.orig_pos = self.pos()
                event.accept()
                try:
                    super().mousePressEvent(event)
                except Exception:
                    pass
                return

        self.active_handle = HandleType.NONE
        try:
            super().mousePressEvent(event)
        except Exception:
            pass

    def mouseMoveEvent(self, event):
        if self.active_handle != HandleType.NONE:
            if self.active_handle == HandleType.ROTATE:
                scene_pos = event.scenePos()
                item_center = self.pos()
                dx = scene_pos.x() - item_center.x()
                dy = scene_pos.y() - item_center.y()
                angle_deg = math.degrees(math.atan2(dy, dx)) + 90.0
                if event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
                    angle_deg = round(angle_deg / 15.0) * 15.0
                self.setRotation(angle_deg)
                self.sync_to_data()
                self.update()
                event.accept()
                return

            elif self.active_handle == HandleType.LINE_P1:
                self.prepareGeometryChange()
                target_pt = event.pos()
                if event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
                    dx = target_pt.x() - self.p2_local.x()
                    dy = target_pt.y() - self.p2_local.y()
                    angle = math.atan2(dy, dx)
                    snapped = round(angle / (math.pi / 4.0)) * (math.pi / 4.0)
                    dist = math.hypot(dx, dy)
                    target_pt = QPointF(self.p2_local.x() + dist * math.cos(snapped),
                                        self.p2_local.y() + dist * math.sin(snapped))
                self.p1_local = target_pt
                self.width = max(10.0, abs(self.p2_local.x() - self.p1_local.x()))
                self.height = max(10.0, abs(self.p2_local.y() - self.p1_local.y()))
                self.sync_to_data()
                self.update()
                event.accept()
                return

            elif self.active_handle == HandleType.LINE_P2:
                self.prepareGeometryChange()
                target_pt = event.pos()
                if event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
                    dx = target_pt.x() - self.p1_local.x()
                    dy = target_pt.y() - self.p1_local.y()
                    angle = math.atan2(dy, dx)
                    snapped = round(angle / (math.pi / 4.0)) * (math.pi / 4.0)
                    dist = math.hypot(dx, dy)
                    target_pt = QPointF(self.p1_local.x() + dist * math.cos(snapped),
                                        self.p1_local.y() + dist * math.sin(snapped))
                self.p2_local = target_pt
                self.width = max(10.0, abs(self.p2_local.x() - self.p1_local.x()))
                self.height = max(10.0, abs(self.p2_local.y() - self.p1_local.y()))
                self.sync_to_data()
                self.update()
                event.accept()
                return

            elif self.active_handle == HandleType.CURVE:
                self.prepareGeometryChange()
                target_pt = event.pos()
                self.shape_data.meta["curve_x"] = target_pt.x()
                self.shape_data.meta["curve_y"] = target_pt.y()
                self.sync_to_data()
                self.update()
                event.accept()
                return

            else:
                cur_scene_pos = event.scenePos()
                delta_scene = cur_scene_pos - self.drag_start_scene_pos

                # Project scene delta into unrotated local coordinate frame
                rad = math.radians(self.orig_rotation)
                cos_a = math.cos(rad)
                sin_a = math.sin(rad)
                dx = delta_scene.x() * cos_a + delta_scene.y() * sin_a
                dy = -delta_scene.x() * sin_a + delta_scene.y() * cos_a

                ht = self.active_handle
                affects_left = ht in (HandleType.TOP_LEFT, HandleType.MID_LEFT, HandleType.BOT_LEFT)
                affects_right = ht in (HandleType.TOP_RIGHT, HandleType.MID_RIGHT, HandleType.BOT_RIGHT)
                affects_top = ht in (HandleType.TOP_LEFT, HandleType.TOP_MID, HandleType.TOP_RIGHT)
                affects_bottom = ht in (HandleType.BOT_LEFT, HandleType.BOT_MID, HandleType.BOT_RIGHT)

                is_ctrl = bool(event.modifiers() & Qt.KeyboardModifier.ControlModifier)
                is_shift = bool(event.modifiers() & Qt.KeyboardModifier.ShiftModifier)

                if is_ctrl:
                    # Symmetric center-out scaling: center remains stationary
                    raw_w = self.orig_width
                    raw_h = self.orig_height

                    if affects_right:
                        raw_w = self.orig_width + dx * 2.0
                    elif affects_left:
                        raw_w = self.orig_width - dx * 2.0

                    if affects_bottom:
                        raw_h = self.orig_height + dy * 2.0
                    elif affects_top:
                        raw_h = self.orig_height - dy * 2.0

                    if is_shift:
                        ratio = self.orig_height / max(1.0, self.orig_width)
                        if abs(raw_w - self.orig_width) > abs(raw_h - self.orig_height):
                            raw_h = raw_w * ratio
                        else:
                            raw_w = raw_h / ratio

                        min_dim = 6.0
                        if ratio >= 1.0:
                            min_w = min_dim
                            min_h = min_dim * ratio
                        else:
                            min_h = min_dim
                            min_w = min_dim / ratio

                        if raw_w < min_w or raw_h < min_h:
                            new_w = min_w
                            new_h = min_h
                        else:
                            new_w = raw_w
                            new_h = raw_h
                    else:
                        new_w = max(6.0, raw_w)
                        new_h = max(6.0, raw_h)

                    new_pos = self.orig_pos
                else:
                    # PowerPoint default: Opposite edge/corner is stationary
                    dw = 0.0
                    dh = 0.0

                    if affects_right:
                        dw = dx
                    elif affects_left:
                        dw = -dx

                    if affects_bottom:
                        dh = dy
                    elif affects_top:
                        dh = -dy

                    # Handle Shift aspect ratio constraint for corner handles
                    if is_shift and (affects_left or affects_right) and (affects_top or affects_bottom):
                        ratio = self.orig_height / max(1.0, self.orig_width)
                        if abs(dw) >= abs(dh) / ratio:
                            dh = math.copysign(abs(dw) * ratio, dh if dh != 0 else dw)
                        else:
                            dw = math.copysign(abs(dh) / ratio, dw if dw != 0 else dh)

                    raw_w = self.orig_width + dw
                    raw_h = self.orig_height + dh

                    if is_shift and (affects_left or affects_right) and (affects_top or affects_bottom):
                        ratio = self.orig_height / max(1.0, self.orig_width)
                        min_dim = 6.0
                        if ratio >= 1.0:
                            min_w = min_dim
                            min_h = min_dim * ratio
                        else:
                            min_h = min_dim
                            min_w = min_dim / ratio

                        if raw_w < min_w or raw_h < min_h:
                            new_w = min_w
                            new_h = min_h
                        else:
                            new_w = raw_w
                            new_h = raw_h
                    else:
                        new_w = max(6.0, raw_w)
                        new_h = max(6.0, raw_h)

                    # Compute center shift in local frame
                    actual_dw = new_w - self.orig_width
                    actual_dh = new_h - self.orig_height

                    dc_local_x = 0.0
                    if affects_right:
                        dc_local_x = actual_dw / 2.0
                    elif affects_left:
                        dc_local_x = -actual_dw / 2.0

                    dc_local_y = 0.0
                    if affects_bottom:
                        dc_local_y = actual_dh / 2.0
                    elif affects_top:
                        dc_local_y = -actual_dh / 2.0

                    # Convert local center shift to scene coordinates
                    dc_scene_x = dc_local_x * cos_a - dc_local_y * sin_a
                    dc_scene_y = dc_local_x * sin_a + dc_local_y * cos_a

                    new_pos = QPointF(self.orig_pos.x() + dc_scene_x, self.orig_pos.y() + dc_scene_y)

                self.prepareGeometryChange()
                self.setPos(new_pos)
                self.width = new_w
                self.height = new_h
                self.p1_local = QPointF(-self.width / 2.0, -self.height / 2.0)
                self.p2_local = QPointF(self.width / 2.0, self.height / 2.0)
                self.sync_to_data()
                self.update()
                event.accept()
                return

        # Moving the shape body
        if getattr(self, "drag_start_scene_pos", None) is not None:
            delta = event.scenePos() - self.drag_start_scene_pos
            self.setPos(self.orig_pos + delta)
            self.sync_to_data()
            self.update()
            event.accept()
            return

        try:
            super().mouseMoveEvent(event)
        except Exception:
            pass
        self.sync_to_data()

    def mouseReleaseEvent(self, event):
        self.drag_start_scene_pos = None
        if self.active_handle != HandleType.NONE:
            self.active_handle = HandleType.NONE
            self.sync_to_data()
            event.accept()
            return
        try:
            super().mouseReleaseEvent(event)
        except Exception:
            pass
        self.sync_to_data()

    def hoverMoveEvent(self, event):
        handle = self._hit_test_handle(event.pos())
        if handle == HandleType.ROTATE:
            self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        elif handle == HandleType.CURVE:
            self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        elif handle in (HandleType.LINE_P1, HandleType.LINE_P2):
            self.setCursor(QCursor(Qt.CursorShape.CrossCursor))
        elif handle in (HandleType.TOP_LEFT, HandleType.BOT_RIGHT):
            self.setCursor(QCursor(Qt.CursorShape.SizeFDiagCursor))
        elif handle in (HandleType.TOP_RIGHT, HandleType.BOT_LEFT):
            self.setCursor(QCursor(Qt.CursorShape.SizeBDiagCursor))
        elif handle in (HandleType.TOP_MID, HandleType.BOT_MID):
            self.setCursor(QCursor(Qt.CursorShape.SizeVerCursor))
        elif handle in (HandleType.MID_LEFT, HandleType.MID_RIGHT):
            self.setCursor(QCursor(Qt.CursorShape.SizeHorCursor))
        else:
            self.setCursor(QCursor(Qt.CursorShape.SizeAllCursor))
        try:
            super().hoverMoveEvent(event)
        except TypeError:
            pass

    def hoverLeaveEvent(self, event):
        self.unsetCursor()
        try:
            super().hoverLeaveEvent(event)
        except TypeError:
            pass
