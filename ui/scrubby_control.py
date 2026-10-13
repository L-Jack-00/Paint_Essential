"""
Paint Pro - Scrubby Slider Control
Photoshop & Blender style scrubby horizontal drag interaction on labels and spinboxes.
"""
from PyQt6.QtWidgets import QLabel
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QCursor, QMouseEvent


class ScrubbyLabel(QLabel):
    """
    A label that acts as a Blender/Photoshop-style scrubby slider.
    Dragging horizontally smoothly increments or decrements the bound value.
    """
    valueChanged = pyqtSignal(int)

    def __init__(self, text: str, initial_value: int = 100, min_val: int = 0, max_val: int = 100, parent=None):
        super().__init__(text, parent)
        self.value = initial_value
        self.min_val = min_val
        self.max_val = max_val
        self.is_dragging = False
        self.drag_start_x = 0.0
        self.drag_start_val = initial_value
        self.sensitivity = 0.5  # 2 pixels per unit

        self.setCursor(QCursor(Qt.CursorShape.SizeHorCursor))
        self.setToolTip(f"{text} 마우스 좌/우 드래그로 수치 조절")

    def set_value(self, val: int):
        self.value = max(self.min_val, min(self.max_val, val))

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self.is_dragging = True
            self.drag_start_x = event.globalPosition().x()
            self.drag_start_val = self.value
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent):
        if self.is_dragging:
            dx = event.globalPosition().x() - self.drag_start_x
            delta = int(dx * self.sensitivity)
            new_val = max(self.min_val, min(self.max_val, self.drag_start_val + delta))
            if new_val != self.value:
                self.value = new_val
                self.valueChanged.emit(new_val)
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton and self.is_dragging:
            self.is_dragging = False
            event.accept()
            return
        super().mouseReleaseEvent(event)
