"""
Paint Essential - Unit Test Suite for 3 Core Micro-interactions UX
1. Cursor Dynamic Interaction Guide (Shape hover, Handles, Spacebar Pan)
2. Ghost Indicator (Ghost Preview, Dimming, Capsule Badge, Empty Space Click Merge)
3. Smart Focus Pulse Animation (Property Highlight Trigger Signal)
"""
import unittest
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt, QPointF, QPoint
from PyQt6.QtGui import QColor, QKeyEvent, QMouseEvent, QCursor

from core.layer_manager import LayerManager, LayerType, ShapeItemData
from core.history_manager import HistoryManager
from core.input_safety import InputSafetyTracker, InputMode
from ui.canvas_view import CanvasView
from ui.shape_items import TransformableShapeItem, HandleType
from ui.main_window import MainWindow

app = QApplication.instance() or QApplication([])


class MockHoverEvent:
    def __init__(self, pt: QPointF):
        self._pt = pt

    def pos(self):
        return self._pt


class TestV9MicroInteractions(unittest.TestCase):
    def setUp(self):
        self.lm = LayerManager(canvas_width=400, canvas_height=300)
        self.safety = InputSafetyTracker()
        self.history = HistoryManager()
        self.cv = CanvasView(self.lm, self.safety, self.history)
        self.cv.resize(400, 300)

    def test_01_cursor_dynamic_interactions(self):
        """1. Cursor states for shape hover, handles, and spacebar panning."""
        # Create a rectangle shape at (20, 20, 60, 40)
        self.cv._commit_shape(QPointF(20, 20), QPointF(80, 60), InputMode.SHAPE_RECT)
        shape_layer = self.lm.get_default_shape_layer()
        self.assertEqual(len(shape_layer.shapes), 1)
        shape_id = shape_layer.shapes[0].id
        shape_item = self.cv.shape_items[shape_id]
        shape_item.setSelected(True)

        # Hover shape body (center 0, 0 in local coords) -> SizeAllCursor
        hover_ev = MockHoverEvent(QPointF(0, 0))
        shape_item.hoverMoveEvent(hover_ev)
        self.assertEqual(shape_item.cursor().shape(), Qt.CursorShape.SizeAllCursor)

        # Hover rotate handle -> PointingHandCursor
        rot_handle = shape_item._get_handle_rects()[HandleType.ROTATE]
        hover_rot = MockHoverEvent(rot_handle.center())
        shape_item.hoverMoveEvent(hover_rot)
        self.assertEqual(shape_item.cursor().shape(), Qt.CursorShape.PointingHandCursor)

        # Hover corner handle -> SizeFDiagCursor
        tl_handle = shape_item._get_handle_rects()[HandleType.TOP_LEFT]
        hover_tl = MockHoverEvent(tl_handle.center())
        shape_item.hoverMoveEvent(hover_tl)
        self.assertEqual(shape_item.cursor().shape(), Qt.CursorShape.SizeFDiagCursor)

        # Hover leave -> cursor reset
        leave_ev = MockHoverEvent(QPointF(0, 0))
        shape_item.hoverLeaveEvent(leave_ev)

        # Spacebar Pan Interaction
        # 1. Press Space -> OpenHandCursor
        space_press = QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_Space, Qt.KeyboardModifier.NoModifier)
        self.cv.keyPressEvent(space_press)
        self.assertEqual(self.cv.cursor().shape(), Qt.CursorShape.OpenHandCursor)
        self.assertTrue(self.safety.is_space_pressed)

        # 2. Mouse Press during space -> ClosedHandCursor
        press_pt = QPointF(self.cv.mapFromScene(QPointF(50, 50)))
        mouse_press = QMouseEvent(
            QMouseEvent.Type.MouseButtonPress,
            press_pt,
            Qt.MouseButton.LeftButton,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier
        )
        self.cv.mousePressEvent(mouse_press)
        self.assertEqual(self.cv.cursor().shape(), Qt.CursorShape.ClosedHandCursor)
        self.assertTrue(self.cv.is_middle_panning)

        # 3. Mouse Release -> OpenHandCursor (space still held)
        mouse_release = QMouseEvent(
            QMouseEvent.Type.MouseButtonRelease,
            press_pt,
            Qt.MouseButton.LeftButton,
            Qt.MouseButton.NoButton,
            Qt.KeyboardModifier.NoModifier
        )
        self.cv.mouseReleaseEvent(mouse_release)
        self.assertEqual(self.cv.cursor().shape(), Qt.CursorShape.OpenHandCursor)

        # 4. Release Space -> ArrowCursor
        space_release = QKeyEvent(QKeyEvent.Type.KeyRelease, Qt.Key.Key_Space, Qt.KeyboardModifier.NoModifier)
        self.cv.keyReleaseEvent(space_release)
        self.assertEqual(self.cv.cursor().shape(), Qt.CursorShape.ArrowCursor)
        self.assertFalse(self.safety.is_space_pressed)

    def test_02_ghost_indicator_hover_outside_and_dimming(self):
        """2. Ghost indicator activates on empty space hover with dwell delay and dims shape outline."""
        # Create shape at (20, 20, 80, 60)
        self.cv._commit_shape(QPointF(20, 20), QPointF(80, 60), InputMode.SHAPE_RECT)
        shape_layer = self.lm.get_default_shape_layer()
        shape_id = shape_layer.shapes[0].id
        shape_item = self.cv.shape_items[shape_id]
        shape_item.setSelected(True)

        self.assertFalse(self.cv.is_ghost_preview_active)
        self.assertFalse(shape_item.is_dimmed)

        # Move mouse to empty canvas (250, 200), outside the shape
        outside_vp = QPointF(self.cv.mapFromScene(QPointF(250, 200)))
        move_outside = QMouseEvent(
            QMouseEvent.Type.MouseMove,
            outside_vp,
            Qt.MouseButton.NoButton,
            Qt.MouseButton.NoButton,
            Qt.KeyboardModifier.NoModifier
        )
        self.cv.mouseMoveEvent(move_outside)

        # Dwell timer should be armed
        self.assertTrue(self.cv.ghost_dwell_timer.isActive())
        self.assertIsNotNone(self.cv._ghost_cursor_pos)

        # Simulate dwell timer timeout (180ms passed)
        self.cv.ghost_dwell_timer.timeout.emit()

        # Ghost preview must now be active, and shape outline dimmed to 30%
        self.assertTrue(self.cv.is_ghost_preview_active)
        self.assertTrue(shape_item.is_dimmed)

        # Moving mouse back inside shape (50, 40) deactivates ghost preview immediately
        inside_vp = QPointF(self.cv.mapFromScene(QPointF(50, 40)))
        move_inside = QMouseEvent(
            QMouseEvent.Type.MouseMove,
            inside_vp,
            Qt.MouseButton.NoButton,
            Qt.MouseButton.NoButton,
            Qt.KeyboardModifier.NoModifier
        )
        self.cv.mouseMoveEvent(move_inside)
        self.assertFalse(self.cv.is_ghost_preview_active)
        self.assertFalse(shape_item.is_dimmed)

    def test_03_empty_space_click_merges_shape_to_raster(self):
        """3. Clicking empty space cleanly bakes/merges the selected shape into the raster layer."""
        self.cv._commit_shape(QPointF(20, 20), QPointF(80, 60), InputMode.SHAPE_RECT)
        shape_layer = self.lm.get_default_shape_layer()
        self.assertEqual(len(shape_layer.shapes), 1)

        # Arm ghost preview by moving to empty space
        outside_vp = QPointF(self.cv.mapFromScene(QPointF(250, 200)))
        move_outside = QMouseEvent(
            QMouseEvent.Type.MouseMove,
            outside_vp,
            Qt.MouseButton.NoButton,
            Qt.MouseButton.NoButton,
            Qt.KeyboardModifier.NoModifier
        )
        self.cv.mouseMoveEvent(move_outside)
        self.cv.ghost_dwell_timer.timeout.emit()
        self.assertTrue(self.cv.is_ghost_preview_active)

        # Click at empty space
        click_outside = QMouseEvent(
            QMouseEvent.Type.MouseButtonPress,
            outside_vp,
            Qt.MouseButton.LeftButton,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier
        )
        self.cv.mousePressEvent(click_outside)

        # Shape should be baked into raster layer and removed from shape layer
        self.assertEqual(len(shape_layer.shapes), 0)
        self.assertFalse(self.cv.is_ghost_preview_active)

    def test_04_smart_focus_pulse_trigger_signal(self):
        """4. Switching to tools with dynamic parameter controls triggers property highlight pulse signal."""
        win = MainWindow()
        triggered_modes = []
        win.property_highlight_triggered.connect(lambda m: triggered_modes.append(m))

        self.assertTrue(hasattr(win, "threshold_container"))

        # Switch to Mosaic (J) -> triggers pulse
        win._set_tool(InputMode.MOSAIC)
        self.assertIn(str(InputMode.MOSAIC), triggered_modes)

        # Switch to Step Badge (K) -> triggers pulse
        win._set_tool(InputMode.STEP_BADGE)
        self.assertIn(str(InputMode.STEP_BADGE), triggered_modes)

        # Switch to Rounded Rect (U) -> triggers pulse
        win._set_tool(InputMode.SHAPE_ROUNDED_RECT)
        self.assertIn(str(InputMode.SHAPE_ROUNDED_RECT), triggered_modes)

        # Switch to Flood Fill (G) -> triggers pulse
        win._set_tool(InputMode.FLOOD_FILL)
        self.assertIn(str(InputMode.FLOOD_FILL), triggered_modes)

        # Switch to Magic Wand (W) -> triggers pulse
        win._set_tool(InputMode.SELECT_WAND)
        self.assertIn(str(InputMode.SELECT_WAND), triggered_modes)

        # Switch to Text (T) -> triggers pulse
        win._set_tool(InputMode.TEXT)
        self.assertIn(str(InputMode.TEXT), triggered_modes)

        # Switch to Brush (B) -> no additional pulse for static tools
        count_before = len(triggered_modes)
        win._set_tool(InputMode.BRUSH)
        self.assertEqual(len(triggered_modes), count_before)

        win.close()

    def test_05_ghost_indicator_toggle_disabled(self):
        """5. When ghost indicator is disabled, empty hover does not dim, and outside click clears selection without baking."""
        self.cv.set_ghost_indicator_enabled(False)
        self.assertFalse(self.cv.ghost_indicator_enabled)

        # Create shape at (20, 20, 80, 60)
        self.cv._commit_shape(QPointF(20, 20), QPointF(80, 60), InputMode.SHAPE_RECT)
        shape_layer = self.lm.get_default_shape_layer()
        self.assertEqual(len(shape_layer.shapes), 1)
        shape_id = shape_layer.shapes[0].id
        shape_item = self.cv.shape_items[shape_id]
        shape_item.setSelected(True)

        # Move mouse to empty space
        outside_vp = QPointF(self.cv.mapFromScene(QPointF(250, 200)))
        move_outside = QMouseEvent(
            QMouseEvent.Type.MouseMove,
            outside_vp,
            Qt.MouseButton.NoButton,
            Qt.MouseButton.NoButton,
            Qt.KeyboardModifier.NoModifier
        )
        self.cv.mouseMoveEvent(move_outside)

        # Dwell timer should NOT be running
        self.assertFalse(self.cv.ghost_dwell_timer.isActive())
        self.assertFalse(self.cv.is_ghost_preview_active)
        self.assertFalse(shape_item.is_dimmed)

        # Click at empty space
        click_outside = QMouseEvent(
            QMouseEvent.Type.MouseButtonPress,
            outside_vp,
            Qt.MouseButton.LeftButton,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier
        )
        self.cv.mousePressEvent(click_outside)

        # Shape should NOT be baked into raster layer; remains in shape layer
        self.assertEqual(len(shape_layer.shapes), 1)
        # Selection should be cleared
        self.assertFalse(shape_item.isSelected())

    def test_06_main_window_and_settings_dialog_ghost_checkbox(self):
        """6. Checkbox in MainWindow sidebar and SettingsDialog synchronizes and controls ghost indicator."""
        from ui.dialogs.settings_dialog import SettingsDialog
        win = MainWindow()

        # Check default state
        self.assertTrue(hasattr(win, "ghost_indicator_check"))
        self.assertTrue(win.ghost_indicator_check.isChecked())
        self.assertTrue(win.ghost_indicator_enabled)
        self.assertTrue(win.canvas_view.ghost_indicator_enabled)

        # Uncheck via sidebar checkbox
        win.ghost_indicator_check.setChecked(False)
        self.assertFalse(win.ghost_indicator_enabled)
        self.assertFalse(win.canvas_view.ghost_indicator_enabled)

        # Open SettingsDialog
        dlg = SettingsDialog(
            current_theme=win.current_theme,
            current_language=win.current_language,
            ghost_indicator_enabled=win.ghost_indicator_enabled,
            parent=win
        )
        self.assertTrue(hasattr(dlg, "ghost_indicator_check"))
        self.assertFalse(dlg.ghost_indicator_check.isChecked())

        # Toggle in SettingsDialog
        dlg.ghost_indicator_toggled.connect(win._on_ghost_indicator_toggled)
        dlg.ghost_indicator_check.setChecked(True)
        self.assertTrue(win.ghost_indicator_enabled)
        self.assertTrue(win.ghost_indicator_check.isChecked())
        self.assertTrue(win.canvas_view.ghost_indicator_enabled)

        dlg.close()
        win.close()

    def test_07_selected_shape_modification_in_shape_mode_not_insertion(self):
        """7. In shape drawing mode, dragging a selected shape's body or handles edits it instead of inserting a shape."""
        from PyQt6.QtTest import QTest
        self.safety.current_mode = InputMode.SHAPE_RECT
        self.cv.show()

        # 1. Commit initial shape at (20, 20) to (80, 60) -> w=60, h=40
        self.cv._commit_shape(QPointF(20, 20), QPointF(80, 60), InputMode.SHAPE_RECT)
        shape_layer = self.lm.get_default_shape_layer()
        self.assertEqual(len(shape_layer.shapes), 1)
        self_shape = shape_layer.shapes[0]
        item = self.cv.shape_items[self_shape.id]
        item.setSelected(True)

        # 2. Resize via BOT_RIGHT handle
        handles = item._get_handle_rects()
        br = handles[HandleType.BOT_RIGHT]
        scene_br = item.mapToScene(br.center())
        vp_br = self.cv.mapFromScene(scene_br)

        QTest.mousePress(self.cv.viewport(), Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, vp_br)
        self.assertTrue(self.cv.is_shape_handle_dragging)
        self.assertEqual(item.active_handle, HandleType.BOT_RIGHT)

        # Drag handle by +20, +20
        vp_br_drag = self.cv.mapFromScene(scene_br + QPointF(20, 20))
        QTest.mouseMove(self.cv.viewport(), vp_br_drag)
        QTest.mouseRelease(self.cv.viewport(), Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, vp_br_drag)

        # Verify resized and NO extra shape inserted
        self.assertEqual(len(shape_layer.shapes), 1)
        self.assertGreater(item.width, 60)
        self.assertGreater(item.height, 40)

        # 3. Move via body drag
        vp_body = self.cv.mapFromScene(QPointF(item.pos()))
        QTest.mousePress(self.cv.viewport(), Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, vp_body)
        self.assertTrue(self.cv.is_shape_handle_dragging)
        self.assertFalse(self.cv.input_safety.is_mouse_down)

        vp_body_drag = self.cv.mapFromScene(QPointF(item.pos()) + QPointF(30, 25))
        QTest.mouseMove(self.cv.viewport(), vp_body_drag)
        QTest.mouseRelease(self.cv.viewport(), Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, vp_body_drag)

        # Verify moved and STILL no extra shape
        self.assertEqual(len(shape_layer.shapes), 1)

        # 4. Press ESC to deselect shape
        QTest.keyClick(self.cv, Qt.Key.Key_Escape)
        self.assertEqual(len(self.cv.scene.selectedItems()), 0)

        # 5. In SHAPE_RECT mode, drag a brand new shape in empty space
        p1 = self.cv.mapFromScene(QPointF(150, 100))
        p2 = self.cv.mapFromScene(QPointF(250, 200))
        QTest.mousePress(self.cv.viewport(), Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, p1)
        QTest.mouseMove(self.cv.viewport(), p2)
        QTest.mouseRelease(self.cv.viewport(), Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, p2)

        # New shape should now be inserted!
        self.assertEqual(len(shape_layer.shapes), 2)


if __name__ == "__main__":
    unittest.main()

