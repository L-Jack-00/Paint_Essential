"""
Paint Pro - UI Integration & Comprehensive Audit Test
LJack Protocol Pillar 4: Autonomous Self-Healing Verification
Verifies MainWindow, CanvasView, LayerPanel, and Dialog workflows headlessly.
"""
import unittest
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QColor
from PyQt6.QtCore import Qt, QPointF

app = QApplication.instance() or QApplication([])

from ui.main_window import MainWindow
from ui.dialogs.anchor_resize_dialog import AnchorResizeDialog
from ui.dialogs.adjustment_dialog import AdjustmentDialog
from core.image_processor import AnchorPoint
from core.input_safety import InputMode


class TestUIIntegration(unittest.TestCase):
    def setUp(self):
        self.window = MainWindow()

    def tearDown(self):
        self.window.close()

    def test_01_main_window_init(self):
        """Verifies MainWindow, CanvasView, and LayerPanel initialize properly."""
        self.assertIsNotNone(self.window.canvas_view)
        self.assertIsNotNone(self.window.layer_panel)
        self.assertEqual(len(self.window.layer_manager.layers), 1)
        self.assertEqual(self.window.layer_manager.layers[0].name, "배경 레이어")

    def test_02_tool_switching(self):
        """Verifies tool switching updates input safety mode and UI state."""
        self.window._set_tool(InputMode.SHAPE_RECT)
        self.assertEqual(self.window.input_safety.current_mode, InputMode.SHAPE_RECT)
        self.assertTrue(self.window.tool_actions[InputMode.SHAPE_RECT].isChecked())

    def test_03_vector_shape_insertion_and_selection(self):
        """Verifies vector shapes are appended to the Default Shape Layer and selectable."""
        cv = self.window.canvas_view
        cv.input_safety.current_mode = InputMode.SHAPE_RECT

        # Simulate dragging to create a rectangle
        p1 = QPointF(50, 50)
        p2 = QPointF(150, 150)
        cv._commit_shape(p1, p2, InputMode.SHAPE_RECT)

        shape_layer = self.window.layer_manager.get_default_shape_layer()
        self.assertEqual(len(shape_layer.shapes), 1)
        self.assertEqual(shape_layer.shapes[0].shape_type, "rect")
        self.assertEqual(shape_layer.shapes[0].width, 100)
        self.assertEqual(shape_layer.shapes[0].height, 100)

        # Switch to select tool
        self.window._set_tool(InputMode.SELECT)
        self.assertEqual(self.window.input_safety.current_mode, InputMode.SELECT)

    def test_04_anchor_resize_headless(self):
        """Verifies AnchorResizeDialog logic."""
        dlg = AnchorResizeDialog(900, 600)
        dlg.width_spin.setValue(1200)
        dlg.height_spin.setValue(800)
        dlg._select_anchor(AnchorPoint.TOP_LEFT)
        w, h, anchor = dlg.get_values()
        self.assertEqual(w, 1200)
        self.assertEqual(h, 800)
        self.assertEqual(anchor, AnchorPoint.TOP_LEFT)
        dlg.close()

    def test_05_color_adjustment_headless(self):
        """Verifies AdjustmentDialog calculations."""
        composite = self.window.layer_manager.composite_to_image()
        dlg = AdjustmentDialog(composite)
        dlg.hue_slider.setValue(45)
        dlg.sat_slider.setValue(20)
        dlg.bri_slider.setValue(10)
        dlg.con_slider.setValue(15)

        adjusted = dlg.get_adjusted_image()
        self.assertEqual(adjusted.width(), composite.width())
        self.assertEqual(adjusted.height(), composite.height())
        dlg.close()

    def test_06_undo_redo_integration(self):
        """Verifies undo and redo actions update canvas state."""
        cv = self.window.canvas_view
        initial_shapes = len(self.window.layer_manager.get_default_shape_layer().shapes)

        # Add shape
        cv._commit_shape(QPointF(10, 10), QPointF(50, 50), InputMode.SHAPE_ELLIPSE)
        self.assertEqual(len(self.window.layer_manager.get_default_shape_layer().shapes), initial_shapes + 1)

        # Undo
        self.window._action_undo()
        self.assertEqual(len(self.window.layer_manager.get_default_shape_layer().shapes), initial_shapes)

        # Redo
        self.window._action_redo()
        self.assertEqual(len(self.window.layer_manager.get_default_shape_layer().shapes), initial_shapes + 1)

    def test_07_high_dpi_pixel_snap(self):
        """LJack Pillar 8 & Blind Spot 2: Verifies subpixel snapping eliminates fractional mouse drift."""
        cv = self.window.canvas_view
        cv.stroke_width = 3  # Odd stroke width -> 0.5px offset for center alignment
        cv.pixel_snap_enabled = True

        # Fractional coordinates from high-DPI scaling (e.g. 150%)
        fractional_pt = QPointF(102.333, 45.888)
        snapped = cv.snap_coordinate(fractional_pt)

        # Floor(102.333) = 102 -> + 0.5 = 102.5
        self.assertEqual(snapped.x(), 102.5)
        # Floor(45.888) = 45 -> + 0.5 = 45.5
        self.assertEqual(snapped.y(), 45.5)

        # Even stroke width -> 0.0px offset
        cv.stroke_width = 4
        snapped_even = cv.snap_coordinate(fractional_pt)
        self.assertEqual(snapped_even.x(), 102.0)
        self.assertEqual(snapped_even.y(), 45.0)

    def test_08_shape_layer_invisibility_hides_items(self):
        """Verifies that turning off a shape layer's visibility hides its vector shape items."""
        cv = self.window.canvas_view
        cv._commit_shape(QPointF(20, 20), QPointF(80, 80), InputMode.SHAPE_RECT)

        shape_layer = self.window.layer_manager.get_default_shape_layer()
        self.assertTrue(shape_layer.visible)

        # Retrieve shape item in scene
        shape_data = shape_layer.shapes[0]
        shape_item = cv.shape_items[shape_data.id]
        self.assertTrue(shape_item.isVisible())

        # Toggle layer visibility to False
        self.window.layer_manager.set_visible(shape_layer.id, False)
        cv.rebuild_scene()

        # Shape item must now be hidden!
        self.assertFalse(cv.shape_items[shape_data.id].isVisible())

    def test_09_shift_ctrl_shape_modifiers(self):
        """Verifies Shift (1:1 square/circle) and Ctrl (center-out) shape creation constraints."""
        cv = self.window.canvas_view
        p1 = QPointF(100, 100)
        p2 = QPointF(200, 150)  # dx=100, dy=50

        # Normal Rect
        x, y, w, h = cv._calc_shape_bounds(p1, p2, InputMode.SHAPE_RECT, Qt.KeyboardModifier.NoModifier)
        self.assertEqual((w, h), (100, 50))

        # Shift: Square (aspect ratio 1:1 -> max(100, 50) = 100)
        x_s, y_s, w_s, h_s = cv._calc_shape_bounds(p1, p2, InputMode.SHAPE_RECT, Qt.KeyboardModifier.ShiftModifier)
        self.assertEqual(w_s, 100)
        self.assertEqual(h_s, 100)

        # Ctrl: Center-out expansion (width = 2*dx = 200, height = 2*dy = 100)
        x_c, y_c, w_c, h_c = cv._calc_shape_bounds(p1, p2, InputMode.SHAPE_RECT, Qt.KeyboardModifier.ControlModifier)
        self.assertEqual(w_c, 200)
        self.assertEqual(h_c, 100)
        self.assertEqual(x_c, 0)
        self.assertEqual(y_c, 50)

    def test_10_transformable_shape_handles(self):
        """Verifies PowerPoint-style TransformableShapeItem handles exist and support rotation."""
        from ui.shape_items import TransformableShapeItem, HandleType
        from core.layer_manager import ShapeItemData

        s_data = ShapeItemData(shape_type="rect", x=50, y=50, width=100, height=80)
        item = TransformableShapeItem(s_data)
        item.setSelected(True)

        handles = item._get_handle_rects()
        # 8 resize handles + 1 rotation handle = 9 handles
        self.assertEqual(len(handles), 9)
        self.assertIn(HandleType.ROTATE, handles)
        self.assertIn(HandleType.TOP_LEFT, handles)
        self.assertIn(HandleType.BOT_RIGHT, handles)

    def test_11_marquee_area_selection(self):
        """Verifies MS Paint style marquee selection creation and clearing."""
        cv = self.window.canvas_view
        cv._update_marquee_preview(QPointF(10, 10), QPointF(100, 80))
        self.assertIsNotNone(cv.marquee_box)

        cv._finalize_marquee(QPointF(10, 10), QPointF(100, 80))
        self.assertIsNotNone(cv.selection_rect)
        self.assertEqual(cv.selection_rect.width(), 90)
        self.assertEqual(cv.selection_rect.height(), 70)

        cv.clear_selection_marquee()
        self.assertIsNone(cv.selection_rect)
        self.assertIsNone(cv.marquee_box)

    def test_12_line_direction_vector(self):
        """Verifies straight line endpoints are faithfully preserved across directions."""
        cv = self.window.canvas_view
        # Line going upward-right: from (50, 100) to (150, 20) -> dx=100, dy=-80
        p1 = QPointF(50, 100)
        p2 = QPointF(150, 20)
        x, y, dx, dy = cv._calc_shape_bounds(p1, p2, InputMode.SHAPE_LINE, Qt.KeyboardModifier.NoModifier)
        self.assertEqual(x, 50)
        self.assertEqual(y, 100)
        self.assertEqual(dx, 100)
        self.assertEqual(dy, -80)

    def test_13_marquee_drag_geometry_change_safe(self):
        """Verifies repeatedly updating marquee selection during drag does not raise AttributeError."""
        cv = self.window.canvas_view
        cv._update_marquee_preview(QPointF(10, 10), QPointF(20, 20))
        self.assertIsNotNone(cv.marquee_box)
        # Second and third calls must safely call marquee_box.set_rect without CanvasView.prepareGeometryChange error!
        cv._update_marquee_preview(QPointF(10, 10), QPointF(50, 60))
        cv._update_marquee_preview(QPointF(10, 10), QPointF(100, 120))
        self.assertEqual(cv.marquee_box.rect.width(), 90)
        self.assertEqual(cv.marquee_box.rect.height(), 110)
        cv.clear_selection_marquee()

    def test_14_powerpoint_opposite_anchor_pinning(self):
        """Verifies PowerPoint-style handle resizing: opposite anchor stationary without Ctrl, symmetric with Ctrl."""
        from ui.shape_items import TransformableShapeItem, HandleType
        from core.layer_manager import ShapeItemData

        # 100x100 rectangle with center at (150, 150) -> x=100..200, y=100..200
        s_data = ShapeItemData(shape_type="rect", x=100, y=100, width=100, height=100)
        item = TransformableShapeItem(s_data)
        item.setSelected(True)

        # 1. Normal resize of MID_RIGHT without Ctrl: left edge (x=100) must stay fixed
        item.active_handle = HandleType.MID_RIGHT
        item.drag_start_scene_pos = QPointF(200, 150)
        item.orig_width = 100.0
        item.orig_height = 100.0
        item.orig_pos = QPointF(150, 150)
        item.orig_rotation = 0.0

        class DummyEvent:
            def scenePos(self):
                return QPointF(240, 150)
            def modifiers(self):
                return Qt.KeyboardModifier.NoModifier
            def accept(self):
                pass

        item.mouseMoveEvent(DummyEvent())
        # Width should now be 140
        self.assertEqual(item.width, 140.0)
        # Center should move to 170 (150 + 40/2)
        self.assertEqual(item.pos().x(), 170.0)
        # Left edge = center - width/2 = 170 - 70 = 100 (Stationary!)
        left_edge = item.pos().x() - item.width / 2.0
        self.assertEqual(left_edge, 100.0)

        # 2. Ctrl resize of MID_RIGHT: center must remain fixed at 150, width expands symmetrically (+80px)
        class DummyCtrlEvent:
            def scenePos(self):
                return QPointF(240, 150)
            def modifiers(self):
                return Qt.KeyboardModifier.ControlModifier
            def accept(self):
                pass

        item.mouseMoveEvent(DummyCtrlEvent())
        self.assertEqual(item.width, 180.0)
        self.assertEqual(item.pos().x(), 150.0)  # Center stationary!

        # 3. Corner resize BOT_RIGHT without Ctrl: top-left corner (100, 100) must stay fixed
        item.active_handle = HandleType.BOT_RIGHT
        item.drag_start_scene_pos = QPointF(200, 200)
        item.orig_width = 100.0
        item.orig_height = 100.0
        item.orig_pos = QPointF(150, 150)

        class DummyCornerEvent:
            def scenePos(self):
                return QPointF(250, 260)  # dx=+50, dy=+60
            def modifiers(self):
                return Qt.KeyboardModifier.NoModifier
            def accept(self):
                pass

        item.mouseMoveEvent(DummyCornerEvent())
        self.assertEqual(item.width, 150.0)
        self.assertEqual(item.height, 160.0)
        tl_x = item.pos().x() - item.width / 2.0
        tl_y = item.pos().y() - item.height / 2.0
        self.assertEqual(tl_x, 100.0)
        self.assertEqual(tl_y, 100.0)

    def test_15_line_flip_rotation_handle_tracking(self):
        """Verifies rotation handle and UI follow line midpoint and top dynamically on flip."""
        from ui.shape_items import TransformableShapeItem, HandleType
        from core.layer_manager import ShapeItemData

        s_data = ShapeItemData(
            shape_type="line", x=100, y=100, width=80, height=80,
            meta={"p1_x": -40.0, "p1_y": -40.0, "p2_x": 40.0, "p2_y": 40.0}
        )
        item = TransformableShapeItem(s_data)
        item.setSelected(True)

        handles_before = item._get_handle_rects()
        rot_before = handles_before[HandleType.ROTATE]
        # Midpoint of (-40, 40) is 0
        self.assertAlmostEqual(rot_before.center().x(), 0.0)

        # Invert line horizontally: move p1 to (60, 40) while p2 is at (-40, -40)
        item.p1_local = QPointF(60.0, 40.0)
        item.p2_local = QPointF(-40.0, -40.0)
        handles_after = item._get_handle_rects()
        rot_after = handles_after[HandleType.ROTATE]
        # New midpoint x = (60 + -40) / 2 = 10.0!
        self.assertAlmostEqual(rot_after.center().x(), 10.0)

    def test_16_proportional_resize_small_aspect_ratio_preserved(self):
        """Verifies shrinking shape to microscopic size strictly preserves aspect ratio."""
        from ui.shape_items import TransformableShapeItem, HandleType
        from core.layer_manager import ShapeItemData

        # 100x50 -> 2:1 aspect ratio
        s_data = ShapeItemData(shape_type="rect", x=100, y=100, width=100, height=50)
        item = TransformableShapeItem(s_data)
        item.setSelected(True)

        item.active_handle = HandleType.BOT_RIGHT
        item.drag_start_scene_pos = QPointF(200, 150)
        item.orig_width = 100.0
        item.orig_height = 50.0
        item.orig_pos = QPointF(150, 125)

        # Extreme shrink with Shift (dx=-98, dy=-49) -> target raw (2, 1)
        class ShrinkEvent:
            def scenePos(self):
                return QPointF(102, 101)
            def modifiers(self):
                return Qt.KeyboardModifier.ShiftModifier
            def accept(self):
                pass

        item.mouseMoveEvent(ShrinkEvent())
        # Ratio must strictly remain 2.0! (e.g. 12x6)
        ratio = item.width / item.height
        self.assertAlmostEqual(ratio, 2.0, places=2)
        self.assertGreaterEqual(item.width, 6.0)
        self.assertGreaterEqual(item.height, 6.0)

    def test_17_shape_handle_interaction_with_any_tool(self):
        """Verifies clicking on a selected shape handle allows dragging regardless of current active tool."""
        cv = self.window.canvas_view
        cv._commit_shape(QPointF(50, 50), QPointF(150, 150), InputMode.SHAPE_RECT)
        shape_layer = self.window.layer_manager.get_default_shape_layer()
        shape_item = cv.shape_items[shape_layer.shapes[0].id]
        cv.scene.clearSelection()
        shape_item.setSelected(True)

        # Switch to Brush tool
        self.window._set_tool(InputMode.BRUSH)
        self.assertEqual(self.window.input_safety.current_mode, InputMode.BRUSH)

        # Retrieve scene position of BOT_RIGHT handle
        from ui.shape_items import HandleType
        handles = shape_item._get_handle_rects()
        bot_right_rect = handles[HandleType.BOT_RIGHT]
        scene_pt = shape_item.mapToScene(bot_right_rect.center())

        # Simulate left-click on the handle
        from PyQt6.QtGui import QMouseEvent
        from PyQt6.QtCore import QEvent
        local_pt = QPointF(cv.mapFromScene(scene_pt))
        press_ev = QMouseEvent(
            QEvent.Type.MouseButtonPress,
            local_pt,
            Qt.MouseButton.LeftButton,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier
        )
        cv.mousePressEvent(press_ev)

        # Must have initiated shape handle drag without raster painting!
        self.assertTrue(cv.is_shape_handle_dragging)

        # Release
        rel_ev = QMouseEvent(
            QEvent.Type.MouseButtonRelease,
            local_pt,
            Qt.MouseButton.LeftButton,
            Qt.MouseButton.NoButton,
            Qt.KeyboardModifier.NoModifier
        )
        cv.mouseReleaseEvent(rel_ev)
        self.assertFalse(cv.is_shape_handle_dragging)

    def test_18_transparent_selection_preserves_content(self):
        """Verifies transparent selection keys out secondary color while preserving drawn opaque pixels."""
        cv = self.window.canvas_view
        cv.transparent_selection_enabled = True
        cv.secondary_color = QColor(255, 255, 255, 255)  # White background
        active_layer = self.window.layer_manager.get_active_layer()

        # Draw a solid black square (10x10) at (20, 20) on white canvas
        from PyQt6.QtGui import QPainter
        p = QPainter(active_layer.raster_image)
        p.fillRect(20, 20, 10, 10, QColor(0, 0, 0, 255))
        p.end()

        # Select a 30x30 region encompassing the black square (x=10..40, y=10..40)
        from PyQt6.QtCore import QRectF
        sel_rect = QRectF(10, 10, 30, 30)
        cv._create_floating_selection_from_rect(sel_rect)

        self.assertIsNotNone(cv.floating_selection)
        float_img = cv.floating_selection.pixmap.toImage()

        # The black pixel at relative (15, 15) must remain opaque black!
        black_px = float_img.pixelColor(15, 15)
        self.assertEqual(black_px.alpha(), 255)
        self.assertEqual(black_px.red(), 0)
        self.assertEqual(black_px.green(), 0)
        self.assertEqual(black_px.blue(), 0)

        # The white background pixel at relative (2, 2) must be transparent (keyed out)!
        white_bg_px = float_img.pixelColor(2, 2)
        self.assertEqual(white_bg_px.alpha(), 0)

        # Canvas under the cut area on bg_layer must be filled with secondary_color (white)
        canvas_px = active_layer.raster_image.pixelColor(15, 15)
        self.assertEqual(canvas_px.red(), 255)
        self.assertEqual(canvas_px.green(), 255)
        self.assertEqual(canvas_px.blue(), 255)

        cv.commit_floating_selection_if_any()

    def test_19_zero_tofu_toolbar_icons(self):
        """Verifies that all toolbar actions use valid non-null vector QIcons with zero tofu."""
        from PyQt6.QtGui import QAction
        for mode, act in self.window.tool_actions.items():
            self.assertFalse(act.icon().isNull(), f"Action for {mode} must have a non-null icon")

        # Check file, undo/redo, toggle and zoom actions on toolbar
        for act in self.window.findChildren(QAction):
            if act.toolTip() and not act.text():  # Icon-only ribbon action
                self.assertFalse(act.icon().isNull(), f"Ribbon action '{act.toolTip()}' must have a valid QIcon")

    def test_20_multi_document_tab_management(self):
        """Verifies multi-document tabs lifecycle, creation, and active switching."""
        self.assertEqual(self.window.tab_widget.count(), 1)
        doc1 = self.window.active_doc
        self.assertEqual(doc1.base_title, "제목 없음 1")

        # Create new tab
        self.window._action_new()
        self.assertEqual(self.window.tab_widget.count(), 2)
        doc2 = self.window.active_doc
        self.assertEqual(doc2.base_title, "제목 없음 2")
        self.assertNotEqual(doc1, doc2)
        self.assertEqual(self.window.canvas_view, doc2.canvas_view)

        # Switch back to first tab
        self.window.tab_widget.setCurrentIndex(0)
        self.assertEqual(self.window.active_doc, doc1)
        self.assertEqual(self.window.canvas_view, doc1.canvas_view)

    def test_21_tab_dirty_asterisk_and_save_clearing(self):
        """Verifies asterisk prefix on tab title when modified, and removal upon save."""
        doc = self.window.active_doc
        self.assertFalse(doc.is_modified)
        self.assertEqual(self.window.tab_widget.tabText(0), "제목 없음 1")

        # Simulate user drawing stroke
        self.window.canvas_view._commit_shape(QPointF(10, 10), QPointF(50, 50), InputMode.SHAPE_RECT)
        self.assertTrue(doc.is_modified)
        self.assertEqual(self.window.tab_widget.tabText(0), "*제목 없음 1")

        # Simulate save completion
        doc.is_modified = False
        idx = self.window.tab_widget.indexOf(doc)
        self.window.tab_widget.setTabText(idx, doc.display_title)
        self.assertEqual(self.window.tab_widget.tabText(0), "제목 없음 1")

    def test_22_tab_close_save_prompt_and_auto_recreate(self):
        """Verifies tab close prompts when modified, and auto-recreates empty document when all tabs close."""
        from unittest.mock import patch
        from PyQt6.QtWidgets import QMessageBox

        # Create a second tab and mark it modified
        self.window._action_new()
        self.assertEqual(self.window.tab_widget.count(), 2)
        doc2 = self.window.active_doc
        doc2.is_modified = True

        # When user clicks Cancel, tab should NOT close
        with patch.object(QMessageBox, "question", return_value=QMessageBox.StandardButton.Cancel):
            self.window._on_tab_close_requested(1)
            self.assertEqual(self.window.tab_widget.count(), 2)

        # When user clicks No (Discard), tab should close
        with patch.object(QMessageBox, "question", return_value=QMessageBox.StandardButton.No):
            self.window._on_tab_close_requested(1)
            self.assertEqual(self.window.tab_widget.count(), 1)

        # Close the last tab (unmodified) -> must auto-generate a fresh tab!
        self.window._on_tab_close_requested(0)
        self.assertEqual(self.window.tab_widget.count(), 1)
        self.assertTrue(self.window.active_doc.base_title.startswith("제목 없음"))

    def test_23_zoom_controls_and_view_reset(self):
        """Verifies zoom in/out, view reset (1:1), and UI label synchronization."""
        cv = self.window.canvas_view
        self.assertEqual(cv.zoom_level, 1.0)
        self.assertEqual(self.window.zoom_toolbar_label.text().strip(), "100%")

        # Zoom in
        cv.zoom_in()
        self.assertAlmostEqual(cv.zoom_level, 1.25, places=2)
        self.assertEqual(self.window.zoom_toolbar_label.text().strip(), "125%")
        self.assertIn("125%", self.window.zoom_status_label.text())

        # Reset view
        cv.reset_view()
        self.assertEqual(cv.zoom_level, 1.0)
        self.assertEqual(self.window.zoom_toolbar_label.text().strip(), "100%")
        self.assertIn("100%", self.window.zoom_status_label.text())

    def test_24_pixel_grid_rendering_at_high_zoom(self):
        """Verifies pixel grid is enabled and drawForeground renders cleanly without exceptions."""
        from PyQt6.QtGui import QPixmap, QPainter
        from PyQt6.QtCore import QRectF

        cv = self.window.canvas_view
        self.assertTrue(cv.pixel_grid_enabled)

        # Create pixmap and painter to test drawForeground
        pm = QPixmap(200, 200)
        p = QPainter(pm)

        # 1. At 100% zoom (1.0 < 4.0), pixel grid should not trigger errors
        cv.zoom_level = 1.0
        cv.drawForeground(p, QRectF(0, 0, 200, 200))

        # 2. At 500% zoom (5.0 >= 4.0), pixel grid is active
        cv.zoom_level = 5.0
        cv.drawForeground(p, QRectF(0, 0, 100, 100))
        p.end()

    def test_25_configurable_layout_grid(self):
        """Verifies configurable layout grid toggle, interval changes, and rendering."""
        from PyQt6.QtGui import QPixmap, QPainter
        from PyQt6.QtCore import QRectF

        cv = self.window.canvas_view
        self.assertFalse(cv.grid_visible)

        # Toggle grid on
        self.window.grid_toggle_act.setChecked(True)
        self.assertTrue(cv.grid_visible)

        # Change grid spacing to 16px
        self.window.grid_combo.setCurrentIndex(1)  # 16 px
        self.assertEqual(cv.grid_spacing, 16)

        # Verify rendering passes cleanly
        pm = QPixmap(300, 300)
        p = QPainter(pm)
        cv.drawForeground(p, QRectF(0, 0, 300, 300))
        p.end()

        # Toggle grid off
        self.window.grid_toggle_act.setChecked(False)
        self.assertFalse(cv.grid_visible)

    def test_33_app_icon_integration(self):
        """Verifies high-DPI app icon initializes and binds to MainWindow and IconFactory."""
        from ui.icon_factory import IconFactory
        app_icon = IconFactory.get_app_icon()
        self.assertFalse(app_icon.isNull())
        self.assertFalse(self.window.windowIcon().isNull())

        # Test standalone vector / scaled generation
        icon_24 = IconFactory.create_icon("app_icon", size=24)
        self.assertFalse(icon_24.isNull())


if __name__ == "__main__":
    unittest.main()

