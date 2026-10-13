"""
Paint Essential - Photoshop-style Tool Cluster Button
LJack Protocol: Multi-subtool grouping with long-press and right-click popup menus.
"""
from typing import List, Tuple, Callable, Any
from PyQt6.QtWidgets import QToolButton, QMenu
from PyQt6.QtCore import Qt, QTimer, QPoint, QPointF
from PyQt6.QtGui import QPainter, QColor, QPolygonF
from ui.icon_factory import IconFactory


class ToolClusterButton(QToolButton):
    """
    A tool button that can host multiple sub-tools (Photoshop-style tool grouping).
    - Left Click: Activates current active sub-tool.
    - Right Click / Long-press (400ms): Shows popup menu with all sub-tools.
    - Draws a subtle triangle in bottom-right corner when multiple sub-tools exist.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.sub_tools: List[Tuple[Any, str, str, Callable[[], None]]] = []
        self.current_sub_idx: int = 0
        self._press_pos = None
        self._long_pressed = False

        self.setCheckable(True)
        self.long_press_timer = QTimer(self)
        self.long_press_timer.setSingleShot(True)
        self.long_press_timer.setInterval(400)
        self.long_press_timer.timeout.connect(self._show_sub_menu)
        self.clicked.connect(self._on_clicked)

    def _on_clicked(self):
        if not self._long_pressed:
            self.trigger_active_sub_tool()
        self._long_pressed = False

    def add_sub_tool(self, tool_id: Any, icon_key: str, title: str, callback: Callable[[], None]):
        self.sub_tools.append((tool_id, icon_key, title, callback))
        if len(self.sub_tools) == 1:
            self.setIcon(IconFactory.create_icon(icon_key))
            self.setToolTip(title)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._press_pos = event.pos()
            self._long_pressed = False
            self.long_press_timer.start()
        elif event.button() == Qt.MouseButton.RightButton:
            self.long_press_timer.stop()
            self._show_sub_menu()
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._press_pos and (event.pos() - self._press_pos).manhattanLength() > 8:
            self.long_press_timer.stop()
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self.long_press_timer.stop()
        super().mouseReleaseEvent(event)

    def contextMenuEvent(self, event):
        self.long_press_timer.stop()
        self._show_sub_menu()
        event.accept()

    def _show_sub_menu(self):
        if not self.sub_tools:
            return
        self.long_press_timer.stop()
        self._long_pressed = True
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
        """)

        for idx, (t_id, icon_key, title, cb) in enumerate(self.sub_tools):
            act = menu.addAction(IconFactory.create_icon(icon_key), title)
            act.setCheckable(True)
            if idx == self.current_sub_idx:
                act.setChecked(True)

            def _make_trigger(sub_idx, callback):
                def _trigger():
                    self.set_active_sub_tool(sub_idx)
                    callback()
                return _trigger

            act.triggered.connect(_make_trigger(idx, cb))

        menu.exec(self.mapToGlobal(QPoint(self.width(), 0)))

    def set_active_sub_tool(self, idx: int):
        if 0 <= idx < len(self.sub_tools):
            self.current_sub_idx = idx
            t_id, icon_key, title, cb = self.sub_tools[idx]
            self.setIcon(IconFactory.create_icon(icon_key))
            self.setToolTip(title)

    def trigger_active_sub_tool(self):
        if 0 <= self.current_sub_idx < len(self.sub_tools):
            _, _, _, cb = self.sub_tools[self.current_sub_idx]
            cb()

    def paintEvent(self, event):
        super().paintEvent(event)
        if len(self.sub_tools) > 1:
            p = QPainter(self)
            p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(100, 116, 139, 200))
            w, h = float(self.width()), float(self.height())
            triangle = QPolygonF([
                QPointF(w - 7.0, h - 2.5),
                QPointF(w - 2.5, h - 7.0),
                QPointF(w - 2.5, h - 2.5)
            ])
            p.drawPolygon(triangle)
            p.end()
