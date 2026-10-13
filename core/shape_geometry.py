"""
Paint Essential - Vector Shape Geometry Engine
LJack Protocol: Mathematical geometry primitives for straight & curved arrows,
rounded rectangles, and vector shapes across interactive items and raster baking.
"""
import math
from typing import Optional, Dict, Any
from PyQt6.QtCore import QPointF, QRectF
from PyQt6.QtGui import QPainterPath, QPolygonF


def create_arrow_path(
    width: float,
    height: float,
    arrow_mode: str = "single",
    meta: Optional[Dict[str, Any]] = None
) -> QPainterPath:
    """
    Generates a QPainterPath for an arrow centered at (0, 0) inside [-w/2, -h/2, w, h].
    Supported arrow_modes:
    - 'single': Straight arrow pointing right (default)
    - 'double': Straight double-headed arrow pointing both left and right
    - 'curved_single': Smooth curved ribbon arrow with right head and adjustable curvature
    - 'curved_double': Smooth curved ribbon arrow with both left and right heads
    """
    meta = meta or {}
    w = max(16.0, float(width))
    h = max(10.0, float(height))
    w2 = w / 2.0
    h2 = h / 2.0

    path = QPainterPath()

    if arrow_mode == "double":
        head_len = min(w * 0.35, max(h * 0.8, 12.0))
        stem_h2 = min(h2 * 0.4, 8.0) if h > 16.0 else h2 * 0.4
        if stem_h2 < 2.0:
            stem_h2 = max(1.5, h2 * 0.5)

        poly = QPolygonF([
            QPointF(-w2, 0),                       # Left head tip
            QPointF(-w2 + head_len, -h2),          # Left top barb
            QPointF(-w2 + head_len, -stem_h2),     # Left upper stem corner
            QPointF(w2 - head_len, -stem_h2),      # Right upper stem corner
            QPointF(w2 - head_len, -h2),           # Right top barb
            QPointF(w2, 0),                        # Right head tip
            QPointF(w2 - head_len, h2),            # Right bottom barb
            QPointF(w2 - head_len, stem_h2),       # Right lower stem corner
            QPointF(-w2 + head_len, stem_h2),      # Left lower stem corner
            QPointF(-w2 + head_len, h2),           # Left bottom barb
        ])
        path.addPolygon(poly)
        path.closeSubpath()
        return path

    elif arrow_mode in ("curved_single", "curved_double"):
        # Ribbon curved arrow
        curve_y = float(meta.get("curve_y", -h2 * 0.7))
        curve_x = float(meta.get("curve_x", 0.0))

        head_len = min(w * 0.35, max(h * 0.75, 12.0))
        stem_h2 = min(h2 * 0.35, 7.0) if h > 16.0 else h2 * 0.35
        if stem_h2 < 2.0:
            stem_h2 = max(1.5, h2 * 0.5)

        p_start = QPointF(-w2, h2 * 0.5)
        p_end = QPointF(w2, -h2 * 0.3)
        p_ctrl = QPointF(curve_x, curve_y)

        if arrow_mode == "curved_single":
            head_base = QPointF(w2 - head_len * 0.8, -h2 * 0.3 + head_len * 0.25)
            path.moveTo(p_start.x(), p_start.y() - stem_h2)
            path.quadTo(p_ctrl.x(), p_ctrl.y() - stem_h2, head_base.x() - stem_h2 * 0.5, head_base.y() - stem_h2)
            path.lineTo(head_base.x() - h2 * 0.5, head_base.y() - h2 * 0.7)
            path.lineTo(p_end.x(), p_end.y())
            path.lineTo(head_base.x() + h2 * 0.5, head_base.y() + h2 * 0.5)
            path.lineTo(head_base.x() + stem_h2 * 0.5, head_base.y() + stem_h2)
            path.quadTo(p_ctrl.x(), p_ctrl.y() + stem_h2, p_start.x(), p_start.y() + stem_h2)
            path.closeSubpath()
            return path
        else:  # curved_double
            head_base_r = QPointF(w2 - head_len * 0.8, -h2 * 0.3 + head_len * 0.25)
            head_base_l = QPointF(-w2 + head_len * 0.8, h2 * 0.5 - head_len * 0.25)

            path.moveTo(p_start.x(), p_start.y())
            path.lineTo(head_base_l.x() - h2 * 0.5, head_base_l.y() - h2 * 0.6)
            path.lineTo(head_base_l.x(), head_base_l.y() - stem_h2)
            path.quadTo(p_ctrl.x(), p_ctrl.y() - stem_h2, head_base_r.x() - stem_h2 * 0.5, head_base_r.y() - stem_h2)
            path.lineTo(head_base_r.x() - h2 * 0.5, head_base_r.y() - h2 * 0.7)
            path.lineTo(p_end.x(), p_end.y())
            path.lineTo(head_base_r.x() + h2 * 0.5, head_base_r.y() + h2 * 0.5)
            path.lineTo(head_base_r.x() + stem_h2 * 0.5, head_base_r.y() + stem_h2)
            path.quadTo(p_ctrl.x(), p_ctrl.y() + stem_h2, head_base_l.x(), head_base_l.y() + stem_h2)
            path.lineTo(head_base_l.x() + h2 * 0.5, head_base_l.y() + h2 * 0.6)
            path.closeSubpath()
            return path

    else:
        # Default single straight arrow
        head_len = min(w * 0.45, max(h * 0.8, 12.0))
        stem_h2 = min(h2 * 0.4, 8.0) if h > 16.0 else h2 * 0.4
        if stem_h2 < 2.0:
            stem_h2 = max(1.5, h2 * 0.5)

        poly = QPolygonF([
            QPointF(-w2, -stem_h2),
            QPointF(w2 - head_len, -stem_h2),
            QPointF(w2 - head_len, -h2),
            QPointF(w2, 0),
            QPointF(w2 - head_len, h2),
            QPointF(w2 - head_len, stem_h2),
            QPointF(-w2, stem_h2),
        ])
        path.addPolygon(poly)
        path.closeSubpath()
        return path


def create_rounded_rect_path(
    width: float,
    height: float,
    corner_radius: float = 12.0
) -> QPainterPath:
    """Creates a rounded rectangle path centered at (0, 0)."""
    w2 = float(width) / 2.0
    h2 = float(height) / 2.0
    r = min(w2, min(h2, max(1.0, float(corner_radius))))
    path = QPainterPath()
    path.addRoundedRect(QRectF(-w2, -h2, float(width), float(height)), r, r)
    return path
