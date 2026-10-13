"""
Paint Essential - Floating Toast Overlay Notification
LJack Protocol: Non-blocking visual feedback for clipboard operations.
"""
from PyQt6.QtWidgets import QWidget, QLabel, QHBoxLayout, QGraphicsOpacityEffect
from PyQt6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, QPoint
from PyQt6.QtGui import QFont


class ToastOverlay(QWidget):
    """
    Floating semi-transparent pill/banner positioned at the top-center of CanvasView.
    Non-blocking (WA_TransparentForMouseEvents) and auto-fading after duration_ms.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(18, 8, 18, 8)

        self.label = QLabel("", self)
        self.label.setFont(QFont("Malgun Gothic", 10, QFont.Weight.DemiBold))
        self.label.setStyleSheet("color: #ffffff; background: transparent;")
        layout.addWidget(self.label)

        self.setStyleSheet("""
            ToastOverlay {
                background-color: rgba(15, 23, 42, 0.88);
                border: 1px solid rgba(255, 255, 255, 0.18);
                border-radius: 18px;
            }
        """)

        self.opacity_effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self.opacity_effect)
        self.opacity_effect.setOpacity(0.0)

        self.hide_timer = QTimer(self)
        self.hide_timer.setSingleShot(True)
        self.hide_timer.timeout.connect(self._fade_out)

        self.anim = None
        self.hide()

    def show_toast(self, message: str, duration_ms: int = 1200):
        self.label.setText(message)
        self.adjustSize()
        self._reposition()

        self.show()
        self.raise_()

        # Stop existing timer/anim
        self.hide_timer.stop()
        if self.anim:
            self.anim.stop()

        # Fade in
        self.anim = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.anim.setDuration(120)
        self.anim.setStartValue(self.opacity_effect.opacity())
        self.anim.setEndValue(1.0)
        self.anim.start()

        # Schedule fade out
        self.hide_timer.start(duration_ms)

    def hide_toast(self):
        if self.anim:
            self.anim.stop()
        self.hide_timer.stop()
        self.hide()

    def _fade_out(self):
        if self.anim:
            self.anim.stop()
        self.anim = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.anim.setDuration(350)
        self.anim.setStartValue(1.0)
        self.anim.setEndValue(0.0)
        self.anim.finished.connect(self.hide)
        self.anim.start()

    def _reposition(self):
        p = self.parentWidget()
        if p and p.width() > 0:
            x = max(10, (p.width() - self.width()) // 2)
            y = 20
            self.move(x, y)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._reposition()
