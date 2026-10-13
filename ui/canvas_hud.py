"""
Paint Pro - Canvas Floating Mini HUD Overlay
LJack Protocol: Compact bottom-center canvas HUD with auto-activation
on pan/zoom/hover and auto-hide timer, eliminating top toolbar overflow.
Features Zoom In/Out, 100% Reset, Grid Toggle, and Editable Direct-Input Grid Spacing.
"""
from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QLabel, QToolButton, QComboBox
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QRectF, QSize
from PyQt6.QtGui import QIntValidator, QPainter, QPen, QBrush, QColor
from ui.icon_factory import IconFactory


class CanvasHudOverlay(QWidget):
    """
    Floating translucent mini control bar anchored at the bottom-center of the canvas.
    Activates when the canvas pans/zooms or when hovered, and auto-hides after N seconds.
    """
    zoom_in_requested = pyqtSignal()
    zoom_out_requested = pyqtSignal()
    zoom_reset_requested = pyqtSignal()
    grid_toggle_requested = pyqtSignal(bool)
    grid_spacing_changed = pyqtSignal(int)
    rotate_requested = pyqtSignal()
    flip_h_requested = pyqtSignal()
    flip_v_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("CanvasHudOverlay")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.hide_timer = QTimer(self)
        self.hide_timer.setSingleShot(True)
        self.hide_timer.timeout.connect(self._on_hide_timer_timeout)

        self.current_rotation = 0
        self.is_flipped_h = False
        self.is_flipped_v = False
        self.is_dark = False

        self._init_ui()
        self._apply_style()
        self.retranslate_ui()
        self.hide()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        rect = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)

        # Soft shadow glow
        glow_color = QColor(15, 23, 42, 60) if self.is_dark else QColor(100, 116, 139, 40)
        painter.setPen(QPen(glow_color, 2.0))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(rect.adjusted(-1, -1, 1, 1), 17, 17)

        # Visible, prominent container background & crisp border
        if self.is_dark:
            painter.setPen(QPen(QColor(36, 54, 86, 230), 1.2))
            painter.setBrush(QBrush(QColor(19, 29, 49, 245)))
        else:
            painter.setPen(QPen(QColor(148, 163, 184, 220), 1.2))
            painter.setBrush(QBrush(QColor(241, 245, 249, 248)))
        painter.drawRoundedRect(rect, 16, 16)
        painter.end()
        super().paintEvent(event)

    def _init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 3, 8, 3)
        layout.setSpacing(4)

        # 1. Zoom Out
        self.zoom_out_btn = QToolButton(self)
        self.zoom_out_btn.setText("－")
        self.zoom_out_btn.setToolTip("캔버스 축소 (Ctrl+-)")
        self.zoom_out_btn.clicked.connect(self.zoom_out_requested.emit)
        layout.addWidget(self.zoom_out_btn)

        # 2. Zoom Level Label
        self.zoom_label = QLabel("100%", self)
        self.zoom_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.zoom_label.setToolTip("현재 캔버스 확대 배율")
        layout.addWidget(self.zoom_label)

        # 3. Zoom In
        self.zoom_in_btn = QToolButton(self)
        self.zoom_in_btn.setText("＋")
        self.zoom_in_btn.setToolTip("캔버스 확대 (Ctrl++)")
        self.zoom_in_btn.clicked.connect(self.zoom_in_requested.emit)
        layout.addWidget(self.zoom_in_btn)

        # 4. View Reset (1:1)
        self.reset_btn = QToolButton(self)
        self.reset_btn.setText("1:1")
        self.reset_btn.setToolTip("시점 초기화 (100% 원본 배율 & 중앙 정렬) [Ctrl+0]")
        self.reset_btn.clicked.connect(self.zoom_reset_requested.emit)
        layout.addWidget(self.reset_btn)

        # Separator Line 1
        sep1 = QLabel("|", self)
        sep1.setStyleSheet("color: rgba(100, 116, 139, 0.4); font-weight: normal; margin: 0 1px;")
        layout.addWidget(sep1)

        # 5. Grid Toggle
        self.grid_btn = QToolButton(self)
        self.grid_btn.setIcon(IconFactory.create_icon("grid", 16))
        self.grid_btn.setCheckable(True)
        self.grid_btn.setChecked(False)
        self.grid_btn.setToolTip("격자 가이드 표시 토글 (Ctrl+')")
        self.grid_btn.toggled.connect(self.grid_toggle_requested.emit)
        layout.addWidget(self.grid_btn)

        # 6. Grid Spacing Editable Combobox
        self.grid_combo = QComboBox(self)
        self.grid_combo.setEditable(True)
        self.grid_combo.addItems(["8", "16", "24", "32", "48", "64", "100", "128"])
        self.grid_combo.setCurrentText("32")
        self.grid_combo.setToolTip("격자 간격 (직접 입력하거나 프리셋 선택)")
        self.grid_combo.setFixedWidth(54)

        line_edit = self.grid_combo.lineEdit()
        if line_edit:
            line_edit.setValidator(QIntValidator(2, 1000, self))
            line_edit.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.grid_combo.currentTextChanged.connect(self._on_grid_text_changed)
        layout.addWidget(self.grid_combo)

        # Separator Line 2
        sep2 = QLabel("|", self)
        sep2.setStyleSheet("color: rgba(100, 116, 139, 0.4); font-weight: normal; margin: 0 1px;")
        layout.addWidget(sep2)

        # 7. Canvas View Mode Indicators & Controls (Rotation, Flip H, Flip V)
        self.rotate_btn = QToolButton(self)
        self.rotate_btn.setIcon(IconFactory.create_icon("rotate", 16))
        self.rotate_btn.setText(" 0°")
        self.rotate_btn.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.rotate_btn.setMinimumWidth(68)
        self.rotate_btn.setToolTip("캔버스 시계방향 90° 회전 (현재: 0°)")
        self.rotate_btn.clicked.connect(self.rotate_requested.emit)
        layout.addWidget(self.rotate_btn)

        self.flip_h_btn = QToolButton(self)
        self.flip_h_btn.setIcon(IconFactory.create_icon("flip_h", 18))
        self.flip_h_btn.setIconSize(QSize(18, 18))
        self.flip_h_btn.setFixedSize(30, 26)
        self.flip_h_btn.setCheckable(True)
        self.flip_h_btn.setToolTip("캔버스 좌우 대칭 반전 (수평) [↔]")
        self.flip_h_btn.clicked.connect(self.flip_h_requested.emit)
        layout.addWidget(self.flip_h_btn)

        self.flip_v_btn = QToolButton(self)
        self.flip_v_btn.setIcon(IconFactory.create_icon("flip_v", 18))
        self.flip_v_btn.setIconSize(QSize(18, 18))
        self.flip_v_btn.setFixedSize(30, 26)
        self.flip_v_btn.setCheckable(True)
        self.flip_v_btn.setToolTip("캔버스 상하 대칭 반전 (수직) [↕]")
        self.flip_v_btn.clicked.connect(self.flip_v_requested.emit)
        layout.addWidget(self.flip_v_btn)

    def apply_theme(self, theme: str):
        self.is_dark = (theme == "dark")
        self._apply_style()
        self.update()

    def _apply_style(self):
        if self.is_dark:
            self.setStyleSheet("""
                QWidget#CanvasHudOverlay {
                    background-color: rgba(30, 38, 56, 0.96);
                    border-radius: 16px;
                    border: 1px solid rgba(52, 68, 96, 0.9);
                }
                QToolButton {
                    background-color: transparent;
                    color: #f1f5f9;
                    border: 1px solid transparent;
                    border-radius: 10px;
                    padding: 2px 5px;
                    font-size: 11px;
                    font-weight: bold;
                }
                QToolButton:hover {
                    background-color: rgba(47, 62, 88, 0.9);
                    border: 1px solid rgba(66, 86, 122, 0.7);
                }
                QToolButton:checked {
                    background-color: #2b4c7e;
                    border: 1px solid #5287d1;
                    color: #ffffff;
                }
                QLabel {
                    color: #f1f5f9;
                    font-size: 11px;
                    font-weight: bold;
                    min-width: 32px;
                }
                QComboBox {
                    background-color: rgba(23, 31, 47, 0.95);
                    color: #f1f5f9;
                    border: 1px solid rgba(52, 68, 96, 0.8);
                    border-radius: 8px;
                    padding: 1px 2px;
                    font-size: 11px;
                    min-height: 18px;
                }
                QComboBox QAbstractItemView {
                    background-color: #171f2f;
                    color: #f1f5f9;
                    selection-background-color: #2b4c7e;
                    selection-color: #ffffff;
                }
            """)
        else:
            self.setStyleSheet("""
                QWidget#CanvasHudOverlay {
                    background-color: rgba(240, 243, 246, 0.95);
                    border-radius: 16px;
                    border: 1px solid rgba(148, 163, 184, 0.65);
                }
                QToolButton {
                    background-color: transparent;
                    color: #1e293b;
                    border: 1px solid transparent;
                    border-radius: 10px;
                    padding: 2px 5px;
                    font-size: 11px;
                    font-weight: bold;
                }
                QToolButton:hover {
                    background-color: rgba(203, 213, 225, 0.8);
                    border: 1px solid rgba(148, 163, 184, 0.5);
                }
                QToolButton:checked {
                    background-color: #2563eb;
                    border: 1px solid #1d4ed8;
                    color: #ffffff;
                }
                QLabel {
                    color: #1e293b;
                    font-size: 11px;
                    font-weight: bold;
                    min-width: 32px;
                }
                QComboBox {
                    background-color: rgba(255, 255, 255, 0.95);
                    color: #0f172a;
                    border: 1px solid rgba(148, 163, 184, 0.6);
                    border-radius: 8px;
                    padding: 1px 2px;
                    font-size: 11px;
                    min-height: 18px;
                }
                QComboBox QAbstractItemView {
                    background-color: #ffffff;
                    color: #1e293b;
                    selection-background-color: #2563eb;
                    selection-color: #ffffff;
                }
            """)

    def retranslate_ui(self):
        from core.i18n import I18N
        self.zoom_out_btn.setToolTip(I18N.tr("hud_zoom_out_tip"))
        self.zoom_label.setToolTip(I18N.tr("status_zoom", zoom=int(round(float(self.zoom_label.text().replace("%", "") or 100)))))
        self.zoom_in_btn.setToolTip(I18N.tr("hud_zoom_in_tip"))
        self.reset_btn.setToolTip(I18N.tr("hud_reset_tip"))
        self.grid_btn.setToolTip(I18N.tr("hud_grid_tip"))
        self.grid_combo.setToolTip(I18N.tr("hud_grid_combo_tip"))
        self.rotate_btn.setToolTip(I18N.tr("hud_rotate_tip", rot=self.current_rotation))
        self.flip_h_btn.setToolTip(I18N.tr("hud_flip_h_tip"))
        self.flip_v_btn.setToolTip(I18N.tr("hud_flip_v_tip"))

    def update_view_mode(self, rotation: int, flip_h: bool, flip_v: bool):
        """Updates canvas view mode indicators."""
        from core.i18n import I18N
        self.current_rotation = rotation % 360
        self.is_flipped_h = flip_h
        self.is_flipped_v = flip_v

        self.rotate_btn.setText(f" {self.current_rotation}°")
        self.rotate_btn.setToolTip(I18N.tr("hud_rotate_tip", rot=self.current_rotation))
        self.flip_h_btn.setChecked(self.is_flipped_h)
        self.flip_v_btn.setChecked(self.is_flipped_v)
        self.adjustSize()
        if self.parent():
            self.reposition(self.parent().size())

    def _on_grid_text_changed(self, text: str):
        # Extract digits
        digits = "".join(ch for ch in text if ch.isdigit())
        if digits:
            val = max(2, min(1000, int(digits)))
            self.grid_spacing_changed.emit(val)

    def update_zoom(self, zoom: float):
        pct_str = f"{int(round(zoom * 100))}%"
        self.zoom_label.setText(pct_str)

    def activate_hud(self, duration_ms: int = 2500):
        """Shows the HUD and sets auto-hide timer for duration_ms."""
        self.show()
        self.raise_()
        self.hide_timer.start(duration_ms)

    def _on_hide_timer_timeout(self):
        if not self.underMouse():
            self.hide()

    def enterEvent(self, event):
        if self.isVisible():
            self.hide_timer.stop()
        super().enterEvent(event)

    def leaveEvent(self, event):
        if self.isVisible():
            self.hide_timer.start(2000)
        super().leaveEvent(event)

    def reposition(self, parent_size):
        pw = parent_size.width()
        ph = parent_size.height()
        hint = self.sizeHint()
        w = max(hint.width(), 355)
        h = max(hint.height(), 34)
        x = max(10, (pw - w) // 2)
        y = max(10, ph - h - 14)
        self.setGeometry(x, y, w, h)
