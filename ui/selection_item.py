"""
Paint Pro - Selection & Floating Marquee Item
MS Paint style rectangular area selection tool with floating drag,
transparent selection, and clipboard operations (Cut, Copy, Paste, Delete).
"""
from typing import Optional, Callable
from PyQt6.QtWidgets import QGraphicsItem, QStyleOptionGraphicsItem, QWidget
from PyQt6.QtCore import Qt, QRectF, QPointF
from PyQt6.QtGui import (
    QPainter, QPen, QBrush, QColor, QPixmap, QCursor
)
from ui.shape_items import HandleType


class FloatingSelectionItem(QGraphicsItem):
    """
    Represents the floating pixel selection cut from the raster layer.
    Allows moving, cutting, copying, deleting, and stamping back down.
    """
    def __init__(
        self,
        pixmap: QPixmap,
        initial_pos: QPointF,
        on_commit_cb: Optional[Callable[['FloatingSelectionItem'], None]] = None,
        on_delete_cb: Optional[Callable[['FloatingSelectionItem'], None]] = None,
        parent=None
    ):
        super().__init__(parent)
        self.pixmap = pixmap
        self.setPos(QPointF(initial_pos))
        self.on_commit_cb = on_commit_cb
        self.on_delete_cb = on_delete_cb

        self.setFlags(
            QGraphicsItem.GraphicsItemFlag.ItemIsSelectable |
            QGraphicsItem.GraphicsItemFlag.ItemIsMovable |
            QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges
        )
        self.setSelected(True)
        self.setCursor(QCursor(Qt.CursorShape.SizeAllCursor))

    def boundingRect(self) -> QRectF:
        return QRectF(0, 0, self.pixmap.width(), self.pixmap.height()).adjusted(-2, -2, 2, 2)

    def paint(self, painter: QPainter, option: QStyleOptionGraphicsItem, widget: Optional[QWidget] = None):
        painter.drawPixmap(0, 0, self.pixmap)

        # Draw dashed marching ants selection border
        pen = QPen(QColor(37, 99, 235), 1.0, Qt.PenStyle.DashLine)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRect(0, 0, self.pixmap.width(), self.pixmap.height())

    def commit_to_raster(self):
        """Bakes floating pixels down to the canvas layer."""
        if self.on_commit_cb:
            self.on_commit_cb(self)


class MarqueeSelectionBox(QGraphicsItem):
    """
    Interactive selection bounding box with 8 PowerPoint/Photoshop-style handles
    for fine-tuning selection boundaries, body dragging, and context menu.
    """
    HANDLE_SIZE = 7.0

    def __init__(
        self,
        rect: QRectF,
        on_rect_changed_cb: Optional[Callable[[QRectF], None]] = None,
        on_context_menu_cb: Optional[Callable[[QPointF], None]] = None,
        parent=None
    ):
        super().__init__(parent)
        self.rect = rect
        self.on_rect_changed_cb = on_rect_changed_cb
        self.on_context_menu_cb = on_context_menu_cb
        self.setZValue(9998)
        self.setAcceptHoverEvents(True)

        self.active_handle = HandleType.NONE
        self.is_dragging_body = False
        self.is_inverted = False
        self.drag_start_scene_pt = QPointF()
        self.orig_rect = QRectF(rect)

    def set_rect(self, rect: QRectF):
        self.prepareGeometryChange()
        self.rect = rect
        self.update()

    def set_inverted(self, inverted: bool):
        self.is_inverted = inverted
        self.update()

    def boundingRect(self) -> QRectF:
        pad = self.HANDLE_SIZE + 2.0
        return self.rect.normalized().adjusted(-pad, -pad, pad, pad)

    def _get_handles(self):
        r = self.rect.normalized()
        x1, y1, x2, y2 = r.left(), r.top(), r.right(), r.bottom()
        mx, my = r.center().x(), r.center().y()
        return {
            HandleType.TOP_LEFT: QPointF(x1, y1),
            HandleType.TOP_MID: QPointF(mx, y1),
            HandleType.TOP_RIGHT: QPointF(x2, y1),
            HandleType.MID_LEFT: QPointF(x1, my),
            HandleType.MID_RIGHT: QPointF(x2, my),
            HandleType.BOT_LEFT: QPointF(x1, y2),
            HandleType.BOT_MID: QPointF(mx, y2),
            HandleType.BOT_RIGHT: QPointF(x2, y2),
        }

    def _hit_test_handle(self, pt: QPointF) -> HandleType:
        hs = self.HANDLE_SIZE + 2.0
        for h_type, pos in self._get_handles().items():
            if QRectF(pos.x() - hs / 2, pos.y() - hs / 2, hs, hs).contains(pt):
                return h_type
        return HandleType.NONE

    def _hit_test_border(self, pt: QPointF, border_width: float = 6.0) -> bool:
        """Returns True if point is on or within border_width pixels of the bounding box edge."""
        r = self.rect.normalized()
        bw = border_width
        r_outer = r.adjusted(-bw, -bw, bw, bw)
        r_inner = r.adjusted(bw, bw, -bw, -bw)
        if r.width() <= 2 * bw or r.height() <= 2 * bw:
            return r_outer.contains(pt)
        return r_outer.contains(pt) and not r_inner.contains(pt)

    def hoverMoveEvent(self, event):
        pt = event.pos()
        h_type = self._hit_test_handle(pt)
        if h_type in (HandleType.TOP_LEFT, HandleType.BOT_RIGHT):
            self.setCursor(QCursor(Qt.CursorShape.SizeFDiagCursor))
        elif h_type in (HandleType.TOP_RIGHT, HandleType.BOT_LEFT):
            self.setCursor(QCursor(Qt.CursorShape.SizeBDiagCursor))
        elif h_type in (HandleType.TOP_MID, HandleType.BOT_MID):
            self.setCursor(QCursor(Qt.CursorShape.SizeVerCursor))
        elif h_type in (HandleType.MID_LEFT, HandleType.MID_RIGHT):
            self.setCursor(QCursor(Qt.CursorShape.SizeHorCursor))
        elif self._hit_test_border(pt):
            self.setCursor(QCursor(Qt.CursorShape.SizeAllCursor))
        else:
            self.setCursor(QCursor(Qt.CursorShape.CrossCursor))
        super().hoverMoveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.RightButton:
            if self.on_context_menu_cb:
                self.on_context_menu_cb(event.screenPos())
            event.accept()
            return

        if event.button() == Qt.MouseButton.LeftButton:
            pt = event.pos()
            h_type = self._hit_test_handle(pt)
            if h_type != HandleType.NONE:
                self.active_handle = h_type
                self.drag_start_scene_pt = event.scenePos()
                self.orig_rect = QRectF(self.rect.normalized())
                event.accept()
                return
            elif self._hit_test_border(pt):
                self.is_dragging_body = True
                self.drag_start_scene_pt = event.scenePos()
                self.orig_rect = QRectF(self.rect.normalized())
                event.accept()
                return
            else:
                # Interior click: ignore so drawing tools can draw inside selection!
                event.ignore()
                return

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.active_handle != HandleType.NONE:
            delta = event.scenePos() - self.drag_start_scene_pt
            dx, dy = delta.x(), delta.y()
            r0 = self.orig_rect
            mods = event.modifiers()
            is_ctrl = bool(mods & Qt.KeyboardModifier.ControlModifier)
            is_shift = bool(mods & Qt.KeyboardModifier.ShiftModifier)

            x1, y1, x2, y2 = r0.left(), r0.top(), r0.right(), r0.bottom()

            if is_ctrl:
                # Symmetric expansion
                if self.active_handle == HandleType.MID_RIGHT:
                    x2 += dx
                    x1 -= dx
                elif self.active_handle == HandleType.MID_LEFT:
                    x1 += dx
                    x2 -= dx
                elif self.active_handle == HandleType.BOT_MID:
                    y2 += dy
                    y1 -= dy
                elif self.active_handle == HandleType.TOP_MID:
                    y1 += dy
                    y2 -= dy
                elif self.active_handle == HandleType.BOT_RIGHT:
                    x2 += dx; x1 -= dx
                    y2 += dy; y1 -= dy
                elif self.active_handle == HandleType.TOP_LEFT:
                    x1 += dx; x2 -= dx
                    y1 += dy; y2 -= dy
                elif self.active_handle == HandleType.TOP_RIGHT:
                    x2 += dx; x1 -= dx
                    y1 += dy; y2 -= dy
                elif self.active_handle == HandleType.BOT_LEFT:
                    x1 += dx; x2 -= dx
                    y2 += dy; y1 -= dy
            else:
                # Opposite anchor fixed
                if self.active_handle == HandleType.MID_RIGHT:
                    x2 += dx
                elif self.active_handle == HandleType.MID_LEFT:
                    x1 += dx
                elif self.active_handle == HandleType.BOT_MID:
                    y2 += dy
                elif self.active_handle == HandleType.TOP_MID:
                    y1 += dy
                elif self.active_handle == HandleType.BOT_RIGHT:
                    x2 += dx
                    y2 += dy
                elif self.active_handle == HandleType.TOP_LEFT:
                    x1 += dx
                    y1 += dy
                elif self.active_handle == HandleType.TOP_RIGHT:
                    x2 += dx
                    y1 += dy
                elif self.active_handle == HandleType.BOT_LEFT:
                    x1 += dx
                    y2 += dy

            # Maintain aspect ratio with Shift
            if is_shift and r0.width() > 0 and r0.height() > 0:
                aspect = r0.width() / r0.height()
                cur_w = abs(x2 - x1)
                cur_h = abs(y2 - y1)
                if cur_w / aspect > cur_h:
                    if self.active_handle in (HandleType.BOT_RIGHT, HandleType.BOT_LEFT):
                        y2 = y1 + (cur_w / aspect) * (1 if y2 >= y1 else -1)
                    elif self.active_handle in (HandleType.TOP_RIGHT, HandleType.TOP_LEFT):
                        y1 = y2 - (cur_w / aspect) * (1 if y2 >= y1 else -1)
                else:
                    if self.active_handle in (HandleType.BOT_RIGHT, HandleType.TOP_RIGHT):
                        x2 = x1 + (cur_h * aspect) * (1 if x2 >= x1 else -1)
                    elif self.active_handle in (HandleType.BOT_LEFT, HandleType.TOP_LEFT):
                        x1 = x2 - (cur_h * aspect) * (1 if x2 >= x1 else -1)

            # Prevent collapsing smaller than 4x4
            new_r = QRectF(min(x1, x2), min(y1, y2), max(4.0, abs(x2 - x1)), max(4.0, abs(y2 - y1)))
            self.set_rect(new_r)
            if self.on_rect_changed_cb:
                self.on_rect_changed_cb(new_r)
            event.accept()
            return

        elif self.is_dragging_body:
            delta = event.scenePos() - self.drag_start_scene_pt
            new_r = self.orig_rect.translated(delta.x(), delta.y())
            self.set_rect(new_r)
            if self.on_rect_changed_cb:
                self.on_rect_changed_cb(new_r)
            event.accept()
            return

        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self.active_handle = HandleType.NONE
        self.is_dragging_body = False
        super().mouseReleaseEvent(event)

    def paint(self, painter: QPainter, option: QStyleOptionGraphicsItem, widget: Optional[QWidget] = None):
        r = self.rect.normalized()

        # 1. Subtle translucent selection background
        fill_color = QColor(220, 38, 38, 25) if self.is_inverted else QColor(37, 99, 235, 25)
        painter.fillRect(r, fill_color)

        # 2. Dual-color marching ants selection border
        pen_black = QPen(QColor(0, 0, 0), 1.0, Qt.PenStyle.SolidLine)
        pen_white = QPen(QColor(255, 255, 255), 1.0, Qt.PenStyle.DashLine)
        pen_white.setDashPattern([4, 4])

        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(pen_black)
        painter.drawRect(r)
        painter.setPen(pen_white)
        painter.drawRect(r)

        # 3. 8 Interactive Handles
        hs = self.HANDLE_SIZE
        h_pen = QPen(QColor(37, 99, 235), 1.2)
        h_brush = QBrush(QColor(255, 255, 255))
        painter.setPen(h_pen)
        painter.setBrush(h_brush)

        for pos in self._get_handles().values():
            painter.drawRect(QRectF(pos.x() - hs / 2, pos.y() - hs / 2, hs, hs))
