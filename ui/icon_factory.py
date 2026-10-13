"""
Paint Pro - Vector Icon Factory
LJack Protocol: Eliminates Tofu (Missing Font Glyphs) completely by rendering
crisp, high-DPI, DPI-aware vector icons via QPainter directly into QIcon.
"""
from PyQt6.QtGui import (
    QIcon, QPixmap, QPainter, QColor, QPen, QBrush, QPolygonF, QFont, QImage
)
from PyQt6.QtCore import Qt, QPointF, QRectF


class IconFactory:
    """Generates crisp 24x24 / 32x32 vector icons for all tools and actions."""

    COLOR_PRIMARY = QColor(30, 41, 59)      # Slate-800
    COLOR_ACCENT = QColor(37, 99, 235)      # Blue-600
    COLOR_MUTED = QColor(100, 116, 139)     # Slate-500
    COLOR_HIGHLIGHT = QColor(239, 68, 68)   # Red-500

    _icon_cache = {}

    @classmethod
    def add_light_gray_outline(cls, src_pix: QPixmap, outline_color: QColor = QColor(210, 220, 235, 220)) -> QPixmap:
        """
        Adds a crisp 1px light gray outline around the non-transparent contour
        of the icon for high visibility across dark mode surfaces.
        """
        img = src_pix.toImage().convertToFormat(QImage.Format.Format_ARGB32_Premultiplied)
        w, h = img.width(), img.height()

        tinted = QImage(w, h, QImage.Format.Format_ARGB32_Premultiplied)
        tinted.fill(0)
        p_t = QPainter(tinted)
        p_t.drawImage(0, 0, img)
        p_t.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
        p_t.fillRect(tinted.rect(), outline_color)
        p_t.end()

        out_img = QImage(w, h, QImage.Format.Format_ARGB32_Premultiplied)
        out_img.fill(0)
        p = QPainter(out_img)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (-1, 1), (1, -1), (1, 1)):
            p.drawImage(dx, dy, tinted)
        p.drawImage(0, 0, img)
        p.end()
        return QPixmap.fromImage(out_img)

    @classmethod
    def get_app_icon(cls) -> QIcon:
        """
        Returns the high-DPI multi-resolution application icon (from .ico or .png).
        """
        from pathlib import Path
        assets_dir = Path(__file__).parent / "assets"
        ico_path = assets_dir / "app_icon.ico"
        png_path = assets_dir / "app_icon.png"
        if ico_path.exists():
            ico = QIcon(str(ico_path))
            if not ico.isNull():
                return ico
        if png_path.exists():
            ico = QIcon(str(png_path))
            if not ico.isNull():
                return ico
        return cls.create_icon("app_icon", size=64, outline=False)

    @classmethod
    def create_icon(cls, icon_type: str, size: int = 24, outline: bool = True) -> QIcon:
        cache_key = (icon_type, size, outline)
        if cache_key in cls._icon_cache:
            return cls._icon_cache[cache_key]

        if icon_type == "app_icon":
            from pathlib import Path
            png_path = Path(__file__).parent / "assets" / "app_icon.png"
            if png_path.exists():
                src_pix = QPixmap(str(png_path))
                if not src_pix.isNull():
                    scaled_pix = src_pix.scaled(
                        size, size,
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation
                    )
                    if outline:
                        scaled_pix = cls.add_light_gray_outline(scaled_pix)
                    icon = QIcon(scaled_pix)
                    cls._icon_cache[cache_key] = icon
                    return icon

        pix = QPixmap(size, size)
        pix.fill(Qt.GlobalColor.transparent)
        p = QPainter(pix)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        s = float(size)
        c_pri = cls.COLOR_PRIMARY
        c_acc = cls.COLOR_ACCENT
        c_mut = cls.COLOR_MUTED

        if icon_type == "app_icon":
            # Vector fallback: Wide flat doodle paint brush with paint at top and cute face
            # Wooden handle
            p.setPen(QPen(QColor(180, 83, 9), 1.5))
            p.setBrush(QBrush(QColor(217, 119, 6)))
            p.drawRoundedRect(QRectF(s * 0.38, s * 0.70, s * 0.24, s * 0.26), 2, 2)
            # Silver ferrule
            p.setPen(QPen(QColor(71, 85, 105), 1.5))
            p.setBrush(QBrush(QColor(203, 213, 225)))
            p.drawRect(QRectF(s * 0.18, s * 0.44, s * 0.64, s * 0.26))
            # Cute eyes and smile on ferrule
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QBrush(QColor(30, 41, 59)))
            p.drawEllipse(QRectF(s * 0.30, s * 0.52, s * 0.08, s * 0.08))
            p.drawEllipse(QRectF(s * 0.62, s * 0.52, s * 0.08, s * 0.08))
            p.setPen(QPen(QColor(30, 41, 59), 1.2))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawArc(int(s * 0.42), int(s * 0.53), int(s * 0.08), int(s * 0.08), 180 * 16, 180 * 16)
            p.drawArc(int(s * 0.50), int(s * 0.53), int(s * 0.08), int(s * 0.08), 180 * 16, 180 * 16)
            # Bristles (tan)
            p.setPen(QPen(QColor(161, 98, 7), 1.2))
            p.setBrush(QBrush(QColor(254, 243, 199)))
            p.drawRect(QRectF(s * 0.20, s * 0.12, s * 0.60, s * 0.32))
            # Top paint (cyan dripping paint at the top)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QBrush(QColor(6, 182, 212)))
            paint_poly = QPolygonF([
                QPointF(s * 0.20, s * 0.12),
                QPointF(s * 0.80, s * 0.12),
                QPointF(s * 0.80, s * 0.28),
                QPointF(s * 0.68, s * 0.36),
                QPointF(s * 0.56, s * 0.26),
                QPointF(s * 0.44, s * 0.38),
                QPointF(s * 0.32, s * 0.26),
                QPointF(s * 0.20, s * 0.32),
            ])
            p.drawPolygon(paint_poly)

        elif icon_type == "new":
            # Document page with folded top-right corner
            p.setPen(QPen(c_pri, 1.5))
            p.setBrush(QBrush(QColor(255, 255, 255)))
            poly = QPolygonF([
                QPointF(4, 3), QPointF(s - 8, 3), QPointF(s - 4, 7),
                QPointF(s - 4, s - 3), QPointF(4, s - 3)
            ])
            p.drawPolygon(poly)
            # Fold line
            p.drawLine(QPointF(s - 8, 3), QPointF(s - 8, 7))
            p.drawLine(QPointF(s - 8, 7), QPointF(s - 4, 7))
            # Text lines
            p.setPen(QPen(c_mut, 1.2))
            p.drawLine(QPointF(7, 11), QPointF(s - 8, 11))
            p.drawLine(QPointF(7, 15), QPointF(s - 8, 15))

        elif icon_type == "open":
            # Folder icon
            p.setPen(QPen(QColor(217, 119, 6), 1.5))  # Amber-600
            p.setBrush(QBrush(QColor(254, 243, 199))) # Amber-100
            poly = QPolygonF([
                QPointF(3, 7), QPointF(9, 7), QPointF(11, 9),
                QPointF(s - 3, 9), QPointF(s - 3, s - 4), QPointF(3, s - 4)
            ])
            p.drawPolygon(poly)
            # Folder front flap
            p.setBrush(QBrush(QColor(251, 191, 36)))
            flap = QPolygonF([
                QPointF(2, 11), QPointF(s - 5, 11), QPointF(s - 3, s - 4), QPointF(4, s - 4)
            ])
            p.drawPolygon(flap)

        elif icon_type == "save":
            # Floppy disk icon
            p.setPen(QPen(c_acc, 1.5))
            p.setBrush(QBrush(QColor(239, 246, 255)))
            poly = QPolygonF([
                QPointF(3, 3), QPointF(s - 7, 3), QPointF(s - 3, 7),
                QPointF(s - 3, s - 3), QPointF(3, s - 3)
            ])
            p.drawPolygon(poly)
            # Shutter label
            p.setBrush(QBrush(c_acc))
            p.drawRect(QRectF(6, 4, s - 12, 6))
            # Bottom white area
            p.setBrush(QBrush(QColor(255, 255, 255)))
            p.drawRect(QRectF(6, 12, s - 12, 8))

        elif icon_type == "undo":
            # Curved left arrow
            p.setPen(QPen(c_pri, 2.0, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            # Arrow head
            arrow = QPolygonF([QPointF(4, 11), QPointF(9, 7), QPointF(9, 15)])
            p.setBrush(QBrush(c_pri))
            p.drawPolygon(arrow)
            # Arc
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawArc(QRectF(7, 9, s - 11, s - 11), 0 * 16, 180 * 16)

        elif icon_type == "redo":
            # Curved right arrow
            p.setPen(QPen(c_pri, 2.0, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            arrow = QPolygonF([QPointF(s - 4, 11), QPointF(s - 9, 7), QPointF(s - 9, 15)])
            p.setBrush(QBrush(c_pri))
            p.drawPolygon(arrow)
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawArc(QRectF(4, 9, s - 11, s - 11), 0 * 16, 180 * 16)

        elif icon_type == "select":
            # Pointer arrow (cursor)
            p.setPen(QPen(c_pri, 1.5))
            p.setBrush(QBrush(c_acc))
            pointer = QPolygonF([
                QPointF(5, 3), QPointF(5, s - 5), QPointF(10, s - 9),
                QPointF(14, s - 3), QPointF(16, s - 5), QPointF(12, s - 11),
                QPointF(s - 6, s - 11)
            ])
            p.drawPolygon(pointer)

        elif icon_type == "select_area":
            # Marquee dashed box with scissors
            pen = QPen(c_acc, 1.5, Qt.PenStyle.DashLine)
            p.setPen(pen)
            p.setBrush(QBrush(QColor(59, 130, 246, 25)))
            p.drawRect(QRectF(3, 3, s - 6, s - 6))
            # Mini scissors or center cross
            p.setPen(QPen(c_pri, 1.5))
            p.drawLine(QPointF(s / 2 - 3, s / 2), QPointF(s / 2 + 3, s / 2))
            p.drawLine(QPointF(s / 2, s / 2 - 3), QPointF(s / 2, s / 2 + 3))

        elif icon_type == "select_lasso":
            # Freehand lasso loop with knot
            pen = QPen(c_acc, 1.5, Qt.PenStyle.DashLine)
            p.setPen(pen)
            p.setBrush(QBrush(QColor(59, 130, 246, 25)))
            p.drawEllipse(QRectF(3, 3, s - 8, s - 8))
            p.setPen(QPen(QColor(217, 119, 6), 1.8))
            p.drawLine(QPointF(s - 7, s - 7), QPointF(s - 2, s - 2))
            p.drawLine(QPointF(s - 4, s - 7), QPointF(s - 7, s - 4))

        elif icon_type == "select_wand":
            # Magic wand with sparkle
            p.setPen(QPen(QColor(100, 116, 139), 2.0, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            p.drawLine(QPointF(5, s - 5), QPointF(s - 8, 8))
            p.setPen(QPen(QColor(245, 158, 11), 2.5, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            p.drawLine(QPointF(s - 8, 8), QPointF(s - 6, 6))
            p.setPen(QPen(QColor(234, 179, 8), 1.5))
            p.drawLine(QPointF(s - 5, 3), QPointF(s - 5, 7))
            p.drawLine(QPointF(s - 7, 5), QPointF(s - 3, 5))

        elif icon_type == "brush":
            # Paintbrush
            p.setPen(QPen(QColor(180, 83, 9), 2.0, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            # Handle
            p.drawLine(QPointF(s - 5, 5), QPointF(11, s - 11))
            # Ferrule (silver)
            p.setPen(QPen(QColor(148, 163, 184), 2.5))
            p.drawLine(QPointF(11, s - 11), QPointF(8, s - 8))
            # Bristles (accent color tip)
            p.setPen(QPen(c_acc, 3.5, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            p.drawLine(QPointF(7, s - 7), QPointF(4, s - 4))

        elif icon_type == "pencil":
            # Pencil
            p.setPen(QPen(QColor(202, 138, 4), 1.5))
            p.setBrush(QBrush(QColor(253, 224, 71)))
            poly = QPolygonF([
                QPointF(s - 5, 7), QPointF(s - 7, 5),
                QPointF(7, s - 9), QPointF(9, s - 7)
            ])
            p.drawPolygon(poly)
            # Tip
            p.setPen(QPen(c_pri, 1.0))
            p.setBrush(QBrush(c_pri))
            tip = QPolygonF([QPointF(7, s - 9), QPointF(9, s - 7), QPointF(3, s - 3)])
            p.drawPolygon(tip)
            # Eraser end
            p.setPen(QPen(QColor(244, 63, 94), 1.0))
            p.setBrush(QBrush(QColor(244, 63, 94)))
            p.drawEllipse(QRectF(s - 7, 3, 5, 5))

        elif icon_type == "eraser":
            # Pink / white angled eraser
            p.setPen(QPen(QColor(225, 29, 72), 1.5))
            p.setBrush(QBrush(QColor(251, 113, 133)))
            poly = QPolygonF([
                QPointF(6, 6), QPointF(s - 6, 6), QPointF(s - 10, s - 5), QPointF(2, s - 5)
            ])
            p.drawPolygon(poly)
            p.setPen(QPen(QColor(203, 213, 225), 1.0))
            p.setBrush(QBrush(QColor(241, 245, 249)))
            p.drawRect(QRectF(s / 2 - 2, 7, s / 2 - 5, s - 13))

        elif icon_type == "flood_fill":
            # Paint bucket pouring
            p.setPen(QPen(c_pri, 1.5))
            p.setBrush(QBrush(QColor(226, 232, 240)))
            # Tilted bucket
            bucket = QPolygonF([
                QPointF(6, 6), QPointF(15, 4), QPointF(17, 14), QPointF(8, 16)
            ])
            p.drawPolygon(bucket)
            # Paint spilling
            p.setPen(QPen(c_acc, 2.0))
            p.drawLine(QPointF(6, 6), QPointF(4, 12))
            # Droplet
            p.setBrush(QBrush(c_acc))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawEllipse(QRectF(3, 14, 5, 6))

        elif icon_type == "eyedropper":
            # Pipette
            p.setPen(QPen(c_pri, 1.5))
            p.setBrush(QBrush(QColor(203, 213, 225)))
            tube = QPolygonF([
                QPointF(s - 7, 7), QPointF(s - 9, 5), QPointF(8, s - 10), QPointF(10, s - 8)
            ])
            p.drawPolygon(tube)
            # Squeeze bulb
            p.setBrush(QBrush(c_acc))
            p.drawEllipse(QRectF(s - 9, 3, 6, 6))
            # Drop at tip
            p.setPen(QPen(c_acc, 2.0))
            p.drawLine(QPointF(8, s - 10), QPointF(4, s - 4))

        elif icon_type == "shape_rect":
            # Rectangle with 4 corner handle dots
            p.setPen(QPen(c_acc, 1.8))
            p.setBrush(QBrush(QColor(59, 130, 246, 20)))
            p.drawRect(QRectF(4, 6, s - 8, s - 12))
            p.setBrush(QBrush(QColor(255, 255, 255)))
            p.setPen(QPen(c_acc, 1.0))
            for pt in [(4, 6), (s - 4, 6), (4, s - 6), (s - 4, s - 6)]:
                p.drawRect(QRectF(pt[0] - 1.5, pt[1] - 1.5, 3, 3))

        elif icon_type == "shape_ellipse":
            # Ellipse with corner handle points
            p.setPen(QPen(c_acc, 1.8))
            p.setBrush(QBrush(QColor(59, 130, 246, 20)))
            p.drawEllipse(QRectF(4, 4, s - 8, s - 8))
            p.setBrush(QBrush(QColor(255, 255, 255)))
            p.setPen(QPen(c_acc, 1.0))
            for pt in [(s / 2, 4), (s / 2, s - 4), (4, s / 2), (s - 4, s / 2)]:
                p.drawEllipse(QRectF(pt[0] - 1.5, pt[1] - 1.5, 3, 3))

        elif icon_type == "shape_line":
            # Diagonal line with circular endpoint handles
            p.setPen(QPen(c_acc, 2.0))
            p.drawLine(QPointF(5, s - 5), QPointF(s - 5, 5))
            p.setBrush(QBrush(QColor(255, 255, 255)))
            p.setPen(QPen(c_acc, 1.2))
            p.drawEllipse(QRectF(3.5, s - 6.5, 4, 4))
            p.drawEllipse(QRectF(s - 7.5, 3.5, 4, 4))

        elif icon_type == "shape_rounded_rect":
            # Rounded rectangle with 4 corner handle dots
            p.setPen(QPen(c_acc, 1.8))
            p.setBrush(QBrush(QColor(59, 130, 246, 20)))
            p.drawRoundedRect(QRectF(4, 6, s - 8, s - 12), 4, 4)
            p.setBrush(QBrush(QColor(255, 255, 255)))
            p.setPen(QPen(c_acc, 1.0))
            for pt in [(4, 6), (s - 4, 6), (4, s - 6), (s - 4, s - 6)]:
                p.drawRect(QRectF(pt[0] - 1.5, pt[1] - 1.5, 3, 3))

        elif icon_type in ("shape_arrow", "arrow_single"):
            # Right-pointing vector arrow with handle dots
            p.setPen(QPen(c_acc, 1.5))
            p.setBrush(QBrush(QColor(59, 130, 246, 25)))
            arrow_poly = QPolygonF([
                QPointF(4, s * 0.38),
                QPointF(s - 9, s * 0.38),
                QPointF(s - 9, s * 0.22),
                QPointF(s - 3, s * 0.50),
                QPointF(s - 9, s * 0.78),
                QPointF(s - 9, s * 0.62),
                QPointF(4, s * 0.62),
            ])
            p.drawPolygon(arrow_poly)
            p.setBrush(QBrush(QColor(255, 255, 255)))
            p.setPen(QPen(c_acc, 1.0))
            p.drawRect(QRectF(3, s * 0.5 - 1.5, 3, 3))
            p.drawRect(QRectF(s - 4.5, s * 0.5 - 1.5, 3, 3))

        elif icon_type == "arrow_double":
            # Two-headed straight arrow
            p.setPen(QPen(c_acc, 1.4))
            p.setBrush(QBrush(QColor(59, 130, 246, 25)))
            poly = QPolygonF([
                QPointF(3, s * 0.5),
                QPointF(8, s * 0.25),
                QPointF(8, s * 0.40),
                QPointF(s - 8, s * 0.40),
                QPointF(s - 8, s * 0.25),
                QPointF(s - 3, s * 0.5),
                QPointF(s - 8, s * 0.75),
                QPointF(s - 8, s * 0.60),
                QPointF(8, s * 0.60),
                QPointF(8, s * 0.75)
            ])
            p.drawPolygon(poly)
            p.setBrush(QBrush(QColor(255, 255, 255)))
            p.setPen(QPen(c_acc, 1.0))
            p.drawRect(QRectF(2, s * 0.5 - 1.5, 3, 3))
            p.drawRect(QRectF(s - 5, s * 0.5 - 1.5, 3, 3))

        elif icon_type == "arrow_curved_single":
            # Single curved ribbon arrow
            p.setPen(QPen(c_acc, 2.0, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawArc(QRectF(4, 7, s - 10, s - 10), 0 * 16, 180 * 16)
            arrow = QPolygonF([QPointF(s - 3, 10), QPointF(s - 8, 6), QPointF(s - 8, 14)])
            p.setBrush(QBrush(c_acc))
            p.drawPolygon(arrow)

        elif icon_type == "arrow_curved_double":
            # Circular two-headed arrow
            p.setPen(QPen(c_acc, 2.0, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawArc(QRectF(4, 5, s - 8, s - 8), 25 * 16, 130 * 16)
            p.drawArc(QRectF(4, 5, s - 8, s - 8), 205 * 16, 130 * 16)
            arr1 = QPolygonF([QPointF(s - 3, s * 0.35), QPointF(s - 8, s * 0.2), QPointF(s - 8, s * 0.5)])
            arr2 = QPolygonF([QPointF(3, s * 0.65), QPointF(8, s * 0.5), QPointF(8, s * 0.8)])
            p.setBrush(QBrush(c_acc))
            p.drawPolygon(arr1)
            p.drawPolygon(arr2)

        elif icon_type == "mosaic":
            # Pixelate mosaic / blur icon
            tile_size = s / 4.0
            shades = [
                QColor(59, 130, 246), QColor(96, 165, 250), QColor(147, 197, 253), QColor(37, 99, 235),
                QColor(147, 197, 253), QColor(59, 130, 246), QColor(37, 99, 235), QColor(96, 165, 250),
                QColor(96, 165, 250), QColor(37, 99, 235), QColor(59, 130, 246), QColor(147, 197, 253),
                QColor(37, 99, 235), QColor(147, 197, 253), QColor(96, 165, 250), QColor(59, 130, 246)
            ]
            idx = 0
            for r in range(4):
                for col in range(4):
                    p.fillRect(QRectF(col * tile_size, r * tile_size, tile_size - 0.5, tile_size - 0.5), shades[idx % len(shades)])
                    idx += 1
            p.setPen(QPen(QColor(30, 41, 59, 100), 1.0))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawRect(QRectF(0.5, 0.5, s - 1, s - 1))

        elif icon_type == "step_badge":
            # Number badge circle with digit '1'
            p.setPen(QPen(c_acc, 1.8))
            p.setBrush(QBrush(c_acc))
            p.drawEllipse(QRectF(3, 3, s - 6, s - 6))
            p.setPen(QPen(QColor(255, 255, 255)))
            font = QFont("Malgun Gothic", int(s * 0.45), QFont.Weight.Bold)
            p.setFont(font)
            p.drawText(QRectF(3, 2, s - 6, s - 6), Qt.AlignmentFlag.AlignCenter, "1")

        elif icon_type == "trans_select":
            # Checkerboard layer icon for transparent selection
            for y in range(4, int(s - 4), 4):
                for x in range(4, int(s - 4), 4):
                    c = QColor(255, 255, 255) if ((x // 4 + y // 4) % 2 == 0) else QColor(203, 213, 225)
                    p.fillRect(x, y, 4, 4, c)
            p.setPen(QPen(c_acc, 1.5))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawRect(QRectF(4, 4, s - 8, s - 8))
            # Magic wand / star in corner
            p.setPen(QPen(QColor(245, 158, 11), 1.5))
            p.drawLine(QPointF(s - 7, s - 7), QPointF(s - 3, s - 3))

        elif icon_type == "pixel_snap":
            # Grid with magnet
            p.setPen(QPen(c_mut, 1.0, Qt.PenStyle.DotLine))
            p.drawLine(QPointF(4, s / 2), QPointF(s - 4, s / 2))
            p.drawLine(QPointF(s / 2, 4), QPointF(s / 2, s - 4))
            # Magnet
            p.setPen(QPen(QColor(239, 68, 68), 2.0))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawArc(QRectF(5, 5, 12, 12), 0 * 16, 180 * 16)
            p.setPen(QPen(QColor(59, 130, 246), 2.0))
            p.drawLine(QPointF(5, 11), QPointF(5, 15))
            p.drawLine(QPointF(17, 11), QPointF(17, 15))

        elif icon_type == "grid":
            # 3x3 Grid
            p.setPen(QPen(c_acc, 1.2))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawRect(QRectF(4, 4, s - 8, s - 8))
            p.drawLine(QPointF(4 + (s - 8) / 3, 4), QPointF(4 + (s - 8) / 3, s - 4))
            p.drawLine(QPointF(4 + 2 * (s - 8) / 3, 4), QPointF(4 + 2 * (s - 8) / 3, s - 4))
            p.drawLine(QPointF(4, 4 + (s - 8) / 3), QPointF(s - 4, 4 + (s - 8) / 3))
            p.drawLine(QPointF(4, 4 + 2 * (s - 8) / 3), QPointF(s - 4, 4 + 2 * (s - 8) / 3))

        elif icon_type == "canvas_size":
            # Ruler / canvas frame
            p.setPen(QPen(c_acc, 1.5))
            p.setBrush(QBrush(QColor(241, 245, 249)))
            p.drawRect(QRectF(4, 4, s - 8, s - 8))
            # Ruler ticks
            p.setPen(QPen(c_mut, 1.0))
            for i in range(1, 4):
                pos = 4 + i * (s - 8) / 4
                p.drawLine(QPointF(pos, 4), QPointF(pos, 7))
                p.drawLine(QPointF(4, pos), QPointF(7, pos))

        elif icon_type == "adjust_colors":
            # Color palette
            p.setPen(QPen(c_pri, 1.5))
            p.setBrush(QBrush(QColor(254, 243, 199)))
            p.drawEllipse(QRectF(3, 4, s - 6, s - 8))
            colors = [QColor(239, 68, 68), QColor(59, 130, 246), QColor(34, 197, 94), QColor(234, 179, 8)]
            for idx, pt in enumerate([(7, 8), (14, 7), (16, 13), (9, 15)]):
                p.setBrush(QBrush(colors[idx % len(colors)]))
                p.setPen(Qt.PenStyle.NoPen)
                p.drawEllipse(QRectF(pt[0], pt[1], 3.5, 3.5))

        elif icon_type == "rotate":
            # Circular 90 degree rotate arrow
            p.setPen(QPen(c_acc, 2.0, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawArc(QRectF(4, 4, s - 8, s - 8), -45 * 16, 270 * 16)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QBrush(c_acc))
            arrow = QPolygonF([QPointF(s - 2, s / 2 - 1), QPointF(s - 7, s / 2 - 5), QPointF(s - 7, s / 2 + 3)])
            p.drawPolygon(arrow)

        elif icon_type == "flip_h":
            # Horizontal Flip: Mirrored Left/Right Triangles across Vertical Axis
            mid_x = s / 2.0
            # Center vertical dashed mirror axis
            p.setPen(QPen(QColor(100, 116, 139), 1.2, Qt.PenStyle.DashLine))
            p.drawLine(QPointF(mid_x, 2), QPointF(mid_x, s - 2))

            # Left solid triangle (Facing mirror)
            p.setPen(QPen(c_acc, 1.2))
            p.setBrush(QBrush(c_acc))
            tri_left = QPolygonF([
                QPointF(mid_x - 1.5, 3),
                QPointF(2.5, mid_x),
                QPointF(mid_x - 1.5, s - 3)
            ])
            p.drawPolygon(tri_left)

            # Right mirrored triangle (Outline / Light tint)
            p.setPen(QPen(c_acc, 1.4))
            p.setBrush(QBrush(QColor(191, 219, 254, 180)))
            tri_right = QPolygonF([
                QPointF(mid_x + 1.5, 3),
                QPointF(s - 2.5, mid_x),
                QPointF(mid_x + 1.5, s - 3)
            ])
            p.drawPolygon(tri_right)

        elif icon_type == "flip_v":
            # Vertical Flip: Mirrored Top/Bottom Triangles across Horizontal Axis
            mid_y = s / 2.0
            # Center horizontal dashed mirror axis
            p.setPen(QPen(QColor(100, 116, 139), 1.2, Qt.PenStyle.DashLine))
            p.drawLine(QPointF(2, mid_y), QPointF(s - 2, mid_y))

            # Top solid triangle (Facing mirror)
            p.setPen(QPen(c_acc, 1.2))
            p.setBrush(QBrush(c_acc))
            tri_top = QPolygonF([
                QPointF(3, mid_y - 1.5),
                QPointF(mid_y, 2.5),
                QPointF(s - 3, mid_y - 1.5)
            ])
            p.drawPolygon(tri_top)

            # Bottom mirrored triangle (Outline / Light tint)
            p.setPen(QPen(c_acc, 1.4))
            p.setBrush(QBrush(QColor(191, 219, 254, 180)))
            tri_bottom = QPolygonF([
                QPointF(3, mid_y + 1.5),
                QPointF(mid_y, s - 2.5),
                QPointF(s - 3, mid_y + 1.5)
            ])
            p.drawPolygon(tri_bottom)

        elif icon_type == "zoom_in":
            # Magnifying glass with plus
            p.setPen(QPen(c_pri, 1.8))
            p.setBrush(QBrush(QColor(241, 245, 249)))
            p.drawEllipse(QRectF(4, 4, 11, 11))
            p.drawLine(QPointF(12, 12), QPointF(s - 4, s - 4))
            p.setPen(QPen(c_acc, 1.5))
            p.drawLine(QPointF(7, 9.5), QPointF(12, 9.5))
            p.drawLine(QPointF(9.5, 7), QPointF(9.5, 12))

        elif icon_type == "zoom_out":
            # Magnifying glass with minus
            p.setPen(QPen(c_pri, 1.8))
            p.setBrush(QBrush(QColor(241, 245, 249)))
            p.drawEllipse(QRectF(4, 4, 11, 11))
            p.drawLine(QPointF(12, 12), QPointF(s - 4, s - 4))
            p.setPen(QPen(c_acc, 1.5))
            p.drawLine(QPointF(7, 9.5), QPointF(12, 9.5))

        elif icon_type == "zoom_reset":
            # 1:1 view reset
            p.setPen(QPen(c_acc, 1.5))
            p.setBrush(QBrush(QColor(239, 246, 255)))
            p.drawRect(QRectF(4, 5, s - 8, s - 10))
            p.setPen(QPen(c_acc, 1.5))
            font = QFont("Arial", 8, QFont.Weight.Bold)
            p.setFont(font)
            p.drawText(QRectF(4, 5, s - 8, s - 10), Qt.AlignmentFlag.AlignCenter, "1:1")

        elif icon_type == "settings":
            # Gear / Cog icon
            import math
            cx, cy = s / 2.0, s / 2.0
            r_out = s / 2.0 - 2.5
            r_in = s / 2.0 - 4.5
            p.setPen(QPen(c_pri, 1.5))
            p.setBrush(QBrush(QColor(226, 232, 240)))
            p.drawEllipse(QRectF(cx - r_out, cy - r_out, r_out * 2, r_out * 2))
            p.setBrush(QBrush(QColor(255, 255, 255)))
            p.drawEllipse(QRectF(cx - 3, cy - 3, 6, 6))
            p.setPen(QPen(c_pri, 2.0, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            for i in range(8):
                ang = i * (math.pi / 4)
                p.drawLine(
                    QPointF(cx + (r_out - 1) * math.cos(ang), cy + (r_out - 1) * math.sin(ang)),
                    QPointF(cx + (r_out + 1.8) * math.cos(ang), cy + (r_out + 1.8) * math.sin(ang))
                )

        p.end()

        if outline:
            pix = cls.add_light_gray_outline(pix)

        icon = QIcon(pix)
        cls._icon_cache[cache_key] = icon
        return icon

    @classmethod
    def ensure_spinbox_arrows(cls) -> tuple[str, str]:
        """
        Ensures crisp, anti-aliased vector PNG arrow assets exist for QSS spinbox rendering.
        Returns forward-slash paths (up_arrow_path, down_arrow_path).
        """
        from pathlib import Path
        assets_dir = Path(__file__).parent / "assets"
        assets_dir.mkdir(parents=True, exist_ok=True)
        up_path = assets_dir / "spin_up.png"
        down_path = assets_dir / "spin_down.png"

        # Render up arrow: 10x6
        up_pix = QPixmap(10, 6)
        up_pix.fill(Qt.GlobalColor.transparent)
        p = QPainter(up_pix)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(QColor(71, 85, 105)))
        p.drawPolygon(QPolygonF([QPointF(5, 1), QPointF(1, 5), QPointF(9, 5)]))
        p.end()
        up_pix.save(str(up_path), "PNG")

        # Render down arrow: 10x6
        down_pix = QPixmap(10, 6)
        down_pix.fill(Qt.GlobalColor.transparent)
        p = QPainter(down_pix)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(QColor(71, 85, 105)))
        p.drawPolygon(QPolygonF([QPointF(1, 1), QPointF(9, 1), QPointF(5, 5)]))
        p.end()
        down_pix.save(str(down_path), "PNG")

        return up_path.as_posix(), down_path.as_posix()

