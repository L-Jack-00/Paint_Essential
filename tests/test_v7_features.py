"""
Paint Essential v1.1.0 Feature Verification Test Suite
Tests for:
1. Arrow Tool (creation, 8-handle bounds, rotation, raster merge)
2. Mosaic / Blur Tool (ImageProcessor, drag execution, undo/redo)
3. Step Numbering Badge Tool (auto-increment, rendering, reset, undo/redo)
4. Shape Commit UX (Enter key merge, Esc deselect, outside click bake, double click)
5. Transparent Clipboard Copy (PNG MIME data preservation)
6. New Canvas Preset Dialog (YouTube, SNS, FHD, clipboard auto-fit)
7. Eyedropper Pixel Loupe (11x11 sampling, hex formatting)
"""
import unittest
import math
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QImage, QColor, QKeyEvent, QMouseEvent
from PyQt6.QtCore import Qt, QRect, QRectF, QPointF, QPoint, QMimeData, QByteArray, QBuffer

from core.layer_manager import LayerManager, LayerType, ShapeItemData
from core.history_manager import HistoryManager
from core.input_safety import InputSafetyTracker, InputMode
from core.image_processor import ImageProcessor
from ui.canvas_view import CanvasView
from ui.shape_items import TransformableShapeItem
from ui.dialogs.new_canvas_dialog import NewCanvasDialog


class TestV7Features(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.lm = LayerManager(canvas_width=200, canvas_height=150)
        self.safety = InputSafetyTracker()
        self.history = HistoryManager()
        self.cv = CanvasView(self.lm, self.safety, self.history)

    # 1. Mosaic & Blur
    def test_mosaic_effect(self):
        img = QImage(100, 100, QImage.Format.Format_ARGB32_Premultiplied)
        img.fill(QColor(255, 0, 0, 255))
        # Add some variation
        for y in range(20, 40):
            for x in range(20, 40):
                img.setPixelColor(x, y, QColor(0, 255, 0, 255))

        target_rect = QRect(10, 10, 40, 40)
        mosaic_img = ImageProcessor.apply_mosaic(img, target_rect, block_size=8)
        self.assertEqual(mosaic_img.width(), 100)
        self.assertEqual(mosaic_img.height(), 100)
        # Check that pixels within the block share identical color (pixelated)
        c1 = mosaic_img.pixelColor(20, 20)
        c2 = mosaic_img.pixelColor(22, 22)
        self.assertEqual(c1, c2)

    def test_canvas_view_mosaic_tool_undo_redo(self):
        self.safety.current_mode = InputMode.MOSAIC
        active_layer = self.lm.get_active_layer()
        active_layer.raster_image.fill(QColor(255, 255, 255, 255))
        active_layer.raster_image.setPixelColor(50, 50, QColor(0, 0, 0, 255))

        # Apply mosaic over 40x40 area
        p1 = QPointF(30, 30)
        p2 = QPointF(70, 70)
        self.cv.drag_start_pt = p1
        self.cv._finalize_mosaic(p1, p2)

        # Check step recorded in history
        self.assertEqual(self.history.can_undo(), True)
        self.assertEqual(self.history.step_count, 1)

        # Undo should restore original image
        self.history.undo()
        self.assertEqual(active_layer.raster_image.pixelColor(50, 50), QColor(0, 0, 0, 255))

        # Redo should reapply mosaic
        self.history.redo()
        self.assertNotEqual(active_layer.raster_image.pixelColor(50, 50), QColor(0, 0, 0, 255))

    # 2. Dedicated Arrow Tool
    def test_arrow_shape_creation_and_raster_merge(self):
        self.safety.current_mode = InputMode.SHAPE_ARROW
        p1 = QPointF(20, 30)
        p2 = QPointF(100, 30)  # Horizontal arrow pointing right
        self.cv._commit_shape(p1, p2, InputMode.SHAPE_ARROW)

        shape_layer = self.lm.get_default_shape_layer()
        self.assertEqual(len(shape_layer.shapes), 1)
        arrow = shape_layer.shapes[0]
        self.assertEqual(arrow.shape_type, "arrow")
        self.assertAlmostEqual(arrow.meta.get("rotation", 0.0), 0.0, places=1)
        self.assertGreater(arrow.width, 50)

        # Merge to raster
        merged = self.lm.merge_shape_into_raster(arrow.id)
        self.assertTrue(merged)
        self.assertEqual(len(shape_layer.shapes), 0)

        # Active raster image should now contain non-transparent pixels from the baked arrow
        active_layer = self.lm.get_active_layer()
        # Arrow body crosses roughly around y=30
        has_colored_pixel = False
        for x in range(30, 90):
            if active_layer.raster_image.pixelColor(x, 30).alpha() > 100:
                has_colored_pixel = True
                break
        self.assertTrue(has_colored_pixel)

    def test_arrow_shape_rotate_and_flip(self):
        shape_data = ShapeItemData(
            shape_type="arrow",
            x=20.0, y=20.0, width=60.0, height=20.0,
            meta={"rotation": 45.0}
        )
        shape_0 = ShapeItemData(
            shape_type="arrow",
            x=20.0, y=100.0, width=60.0, height=20.0,
            meta={"rotation": 0.0}
        )
        self.lm.add_shape_to_default_layer(shape_data)
        self.lm.add_shape_to_default_layer(shape_0)
        self.lm.rotate_all_90(clockwise=True)

        # Width and height should be swapped, and rotation should be updated
        self.assertEqual(shape_data.width, 20.0)
        self.assertEqual(shape_data.height, 60.0)
        self.assertAlmostEqual(shape_data.meta["rotation"], 135.0, places=1)
        self.assertAlmostEqual(shape_0.meta["rotation"], 90.0, places=1)

        # Rotate back CCW
        self.lm.rotate_all_90(clockwise=False)
        self.assertEqual(shape_data.width, 60.0)
        self.assertEqual(shape_data.height, 20.0)
        self.assertAlmostEqual(shape_data.meta["rotation"], 45.0, places=1)
        self.assertAlmostEqual(shape_0.meta["rotation"], 0.0, places=1)

        # Horizontal flip
        self.lm.flip_all(horizontal=True)
        self.assertAlmostEqual(shape_data.meta["rotation"], 135.0, places=1)
        self.assertAlmostEqual(shape_0.meta["rotation"], 180.0, places=1)

    # 3. Step Numbering Badge Tool
    def test_step_badge_auto_increment_and_reset(self):
        self.safety.current_mode = InputMode.STEP_BADGE
        self.assertEqual(self.cv.current_step_badge, 1)

        # Place badge #1
        self.cv._apply_step_badge(QPointF(40, 40))
        self.assertEqual(self.cv.current_step_badge, 2)
        self.assertEqual(self.history.step_count, 1)

        # Place badge #2
        self.cv._apply_step_badge(QPointF(80, 40))
        self.assertEqual(self.cv.current_step_badge, 3)
        self.assertEqual(self.history.step_count, 2)

        # Undo should decrement / restore raster and restore current_step_badge counter
        self.history.undo()
        self.assertEqual(self.cv.current_step_badge, 2)
        self.assertEqual(self.history.step_count, 1)  # 1 step remaining in undo stack
        self.assertTrue(self.history.can_redo())

        # Second undo restores to 1
        self.history.undo()
        self.assertEqual(self.cv.current_step_badge, 1)
        self.assertEqual(self.history.step_count, 0)

        # Redo advances to 2
        self.history.redo()
        self.assertEqual(self.cv.current_step_badge, 2)

        # Right click simulated: reset to 1
        event = QMouseEvent(
            QMouseEvent.Type.MouseButtonPress,
            QPointF(10, 10),
            Qt.MouseButton.RightButton,
            Qt.MouseButton.RightButton,
            Qt.KeyboardModifier.NoModifier
        )
        self.cv.mousePressEvent(event)
        self.assertEqual(self.cv.current_step_badge, 1)

    # 4. Shape Commit UX (Enter, Esc, Outside Click, Double Click)
    def test_shape_commit_ux_enter_key(self):
        # Create a rectangle shape
        self.cv._commit_shape(QPointF(10, 10), QPointF(50, 50), InputMode.SHAPE_RECT)
        shape_layer = self.lm.get_default_shape_layer()
        self.assertEqual(len(shape_layer.shapes), 1)

        # Press Enter key to merge
        key_event = QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_Return, Qt.KeyboardModifier.NoModifier)
        self.cv.keyPressEvent(key_event)

        # Shape should be permanently baked into raster and removed from shape layer
        self.assertEqual(len(shape_layer.shapes), 0)

    def test_shape_commit_ux_esc_key(self):
        self.cv._commit_shape(QPointF(10, 10), QPointF(50, 50), InputMode.SHAPE_RECT)
        self.assertGreater(len(self.cv.scene.selectedItems()), 0)

        # Press Esc key
        key_event = QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_Escape, Qt.KeyboardModifier.NoModifier)
        self.cv.keyPressEvent(key_event)

        # Selection should be cleared
        self.assertEqual(len(self.cv.scene.selectedItems()), 0)

    def test_shape_commit_ux_click_outside(self):
        self.cv._commit_shape(QPointF(10, 10), QPointF(50, 50), InputMode.SHAPE_RECT)
        shape_layer = self.lm.get_default_shape_layer()
        self.assertEqual(len(shape_layer.shapes), 1)

        # Click at (180, 140), clearly outside the shape at (10~50, 10~50)
        click_outside = QMouseEvent(
            QMouseEvent.Type.MouseButtonPress,
            QPointF(180, 140),
            Qt.MouseButton.LeftButton,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier
        )
        self.cv.mousePressEvent(click_outside)

        # Shape is automatically baked into raster upon clicking outside
        self.assertEqual(len(shape_layer.shapes), 0)

    def test_shape_double_click_merge(self):
        self.cv._commit_shape(QPointF(10, 10), QPointF(50, 50), InputMode.SHAPE_RECT)
        shape_layer = self.lm.get_default_shape_layer()
        self.assertEqual(len(shape_layer.shapes), 1)
        shape_id = shape_layer.shapes[0].id
        shape_item = self.cv.shape_items[shape_id]

        # Trigger double click on shape
        dbl_event = QMouseEvent(
            QMouseEvent.Type.MouseButtonDblClick,
            QPointF(0, 0),
            Qt.MouseButton.LeftButton,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier
        )
        shape_item.mouseDoubleClickEvent(dbl_event)
        self.assertEqual(len(shape_layer.shapes), 0)

    # 5. Transparent Clipboard Copy
    def test_transparent_clipboard_png_mime(self):
        img = QImage(32, 32, QImage.Format.Format_ARGB32_Premultiplied)
        img.fill(QColor(0, 0, 0, 0))  # Fully transparent
        # Paint red dot in center
        img.setPixelColor(16, 16, QColor(255, 0, 0, 255))

        byte_array = QByteArray()
        buffer = QBuffer(byte_array)
        buffer.open(QBuffer.OpenModeFlag.WriteOnly)
        success = img.save(buffer, "PNG")
        buffer.close()
        self.assertTrue(success)
        self.assertGreater(byte_array.size(), 0)

        # Check PNG magic bytes
        self.assertEqual(bytes(byte_array[:8]), b'\x89PNG\r\n\x1a\n')

        # Test safe clipboard mime setter
        res = CanvasView._safe_clipboard_set_png_mime(img)
        self.assertTrue(res)

    # 6. New Canvas Preset Dialog
    def test_new_canvas_preset_dialog(self):
        dlg = NewCanvasDialog(default_width=900, default_height=600)
        w, h, trans = dlg.get_dimensions()
        self.assertEqual((w, h), (900, 600))
        self.assertFalse(trans)

        # Click YouTube thumbnail preset
        dlg.btn_youtube.click()
        w, h, trans = dlg.get_dimensions()
        self.assertEqual((w, h), (1280, 720))

        # Click SNS square preset
        dlg.btn_sns.click()
        w, h, trans = dlg.get_dimensions()
        self.assertEqual((w, h), (1080, 1080))

        # Click FHD preset
        dlg.btn_fhd.click()
        w, h, trans = dlg.get_dimensions()
        self.assertEqual((w, h), (1920, 1080))

    # 7. Eyedropper Pixel Loupe State
    def test_eyedropper_pixel_loupe_state(self):
        self.safety.current_mode = InputMode.EYEDROPPER
        self.lm.get_active_layer().raster_image.fill(QColor(10, 20, 30, 255))

        # Simulate mouse move over canvas
        move_event = QMouseEvent(
            QMouseEvent.Type.MouseMove,
            QPointF(50, 50),
            Qt.MouseButton.NoButton,
            Qt.MouseButton.NoButton,
            Qt.KeyboardModifier.NoModifier
        )
        self.cv.mouseMoveEvent(move_event)
        self.assertIsNotNone(self.cv._loupe_cursor_pos)
        self.assertIsNotNone(self.cv._loupe_scene_pt)

        # Switch to Brush tool: loupe tracking should disappear
        self.safety.current_mode = InputMode.BRUSH
        self.cv.mouseMoveEvent(move_event)
        self.assertIsNone(self.cv._loupe_cursor_pos)

    # 8. Merge into Raster Layer Directly Below (Skipping Shapes)
    def test_shape_merge_into_raster_layer_below_skipping_shapes(self):
        """Verifies shape merges into the raster layer directly below it, skipping other shapes."""
        # Setup stack: bg_layer (white) -> layer1 (transparent) -> shape1 (blue rect) -> shape2 (red rect)
        bg = self.lm.get_layer("bg_layer")
        bg.raster_image.fill(QColor(255, 255, 255, 255))

        layer1 = self.lm.add_layer("레이어 1")
        # layer1 is transparent initially

        # Add shape1
        s1 = ShapeItemData(id="s1_blue", shape_type="rect", x=10, y=10, width=30, height=30, fill_color="#0000ff")
        self.lm.add_shape_layer(s1)

        # Add shape2
        s2 = ShapeItemData(id="s2_red", shape_type="rect", x=50, y=50, width=30, height=30, fill_color="#ff0000")
        self.lm.add_shape_layer(s2)

        self.cv.rebuild_scene()

        # Find target raster layer below shape2 (s2_red)
        target = self.lm.find_raster_layer_below("s2_red")
        self.assertIsNotNone(target)
        self.assertEqual(target.id, layer1.id, "Target raster layer below shape 2 must be layer1, skipping shape 1!")

        # Merge s2_red
        self.cv.merge_shape_to_raster("s2_red")

        # Verify s2_red pixels baked into layer1
        c_layer1 = layer1.raster_image.pixelColor(60, 60)
        self.assertEqual(c_layer1.red(), 255)
        self.assertEqual(c_layer1.blue(), 0)

        # Verify bg_layer did NOT get painted with s2_red (remains white)
        c_bg = bg.raster_image.pixelColor(60, 60)
        self.assertEqual(c_bg, QColor(255, 255, 255, 255))

        # Test Undo
        self.assertTrue(self.history.can_undo)
        self.history.undo()
        self.assertIn("s2_red", self.cv.shape_items)
        # layer1 pixel should be reverted (alpha 0)
        self.assertEqual(layer1.raster_image.pixelColor(60, 60).alpha(), 0)

    def test_raster_layer_merge_down_skipping_shapes(self):
        """Verifies raster layer merges down into the nearest raster layer below, skipping shapes."""
        # Setup stack: bg_layer -> layer1 (green) -> shape1 (blue) -> layer2 (yellow)
        bg = self.lm.get_layer("bg_layer")
        layer1 = self.lm.add_layer("레이어 1")
        layer1.raster_image.fill(QColor(0, 255, 0, 255))

        s1 = ShapeItemData(id="s1_shape", shape_type="rect", x=10, y=10, width=20, height=20, fill_color="#0000ff")
        self.lm.add_shape_layer(s1)

        layer2 = self.lm.add_layer("레이어 2")
        layer2.raster_image.fill(QColor(255, 255, 0, 255))

        self.cv.rebuild_scene()

        # Target below layer2 should be layer1 (skipping s1_shape)
        target = self.lm.find_raster_layer_below(layer2.id)
        self.assertIsNotNone(target)
        self.assertEqual(target.id, layer1.id)

        # Merge layer2 down
        self.cv.merge_layer_down(layer2.id)

        # layer2 should no longer exist in layer_manager.layers
        self.assertIsNone(self.lm.get_layer(layer2.id))

        # layer1 should now contain pixels from layer2 (yellow)
        c_merged = layer1.raster_image.pixelColor(50, 50)
        self.assertEqual(c_merged.red(), 255)
        self.assertEqual(c_merged.green(), 255)

        # Undo merge down
        self.assertTrue(self.history.can_undo)
        self.history.undo()
        self.assertIsNotNone(self.lm.get_layer(layer2.id))
        self.assertEqual(layer1.raster_image.pixelColor(50, 50), QColor(0, 255, 0, 255))

    # 8. Text Tool Tests
    def test_text_shape_layer_creation_and_rendering(self):
        """Verifies text shape layer creation, layer naming, and rasterization."""
        name = self.lm.generate_new_shape_layer_name("text")
        self.assertEqual(name, "텍스트 1")

        text_item = ShapeItemData(
            id="text_1",
            shape_type="text",
            x=20,
            y=30,
            width=100,
            height=40,
            stroke_color="#ff0000",
            meta={
                "text": "Hello World",
                "font_size": 20,
                "font_bold": True,
                "font_family": "Arial",
            }
        )
        layer = self.lm.add_shape_layer(text_item)
        self.assertEqual(layer.name, "텍스트 1")
        self.assertEqual(layer.layer_type, LayerType.SHAPE)
        self.assertEqual(layer.shapes[0].meta["text"], "Hello World")
        self.assertTrue(layer.shapes[0].meta["font_bold"])

        # Test rendering to painter
        rendered_img = QImage(200, 150, QImage.Format.Format_ARGB32_Premultiplied)
        rendered_img.fill(0)
        from PyQt6.QtGui import QPainter
        p = QPainter(rendered_img)
        self.lm._render_shape_to_painter(p, text_item)
        p.end()

        # Check that some pixels were rendered (non-zero alpha)
        has_colored_pixel = False
        for y in range(25, 75):
            for x in range(20, 120):
                if rendered_img.pixelColor(x, y).alpha() > 0:
                    has_colored_pixel = True
                    break
            if has_colored_pixel:
                break
        self.assertTrue(has_colored_pixel, "Rendered text should produce visible pixels")

    def test_text_update_font_size(self):
        """Verifies dynamically updating selected text font size in CanvasView."""
        text_item = ShapeItemData(
            id="text_dyn",
            shape_type="text",
            x=10,
            y=10,
            width=80,
            height=30,
            stroke_color="#0000ff",
            meta={
                "text": "Test Font Size",
                "font_size": 16,
            }
        )
        self.lm.add_shape_layer(text_item)
        self.cv.rebuild_scene()

        # Select the text item
        graphics_item = self.cv.shape_items.get("text_dyn")
        self.assertIsNotNone(graphics_item)
        self.cv.scene.clearSelection()
        graphics_item.setSelected(True)

        # Update font size to 36
        old_w = graphics_item.width
        old_h = graphics_item.height
        self.cv.update_selected_text_font_size(36)

        # ShapeItemData and TransformableShapeItem should have new font size and larger bounds
        self.assertEqual(text_item.meta["font_size"], 36)
        self.assertEqual(graphics_item.shape_data.meta["font_size"], 36)
        self.assertGreater(graphics_item.width, old_w)
        self.assertGreater(graphics_item.height, old_h)

    def test_text_bake_into_raster_layer_with_undo(self):
        """Verifies text layer merges into the raster layer directly below, with full undo."""
        bg = self.lm.get_layer("bg_layer")
        bg.raster_image.fill(QColor(255, 255, 255, 255))

        text_item = ShapeItemData(
            id="text_bake",
            shape_type="text",
            x=10,
            y=10,
            width=80,
            height=30,
            stroke_color="#ff0000",
            meta={
                "text": "BakeMe",
                "font_size": 20,
            }
        )
        self.lm.add_shape_layer(text_item)
        self.cv.rebuild_scene()

        # Merge down text shape
        self.cv.merge_shape_to_raster("text_bake")

        # Text shape item should be removed from scene and layer manager
        self.assertNotIn("text_bake", self.cv.shape_items)
        self.assertIsNone(self.lm.get_layer("text_bake"))

        # Raster layer should have rendered text (red-tinted pixels)
        has_red = False
        for y in range(10, 40):
            for x in range(10, 90):
                c = bg.raster_image.pixelColor(x, y)
                if c.red() > 200 and c.green() < 100 and c.blue() < 100:
                    has_red = True
                    break
            if has_red:
                break
        self.assertTrue(has_red, "Raster layer should contain baked text pixels")

        # Undo should restore the text shape layer
        self.assertTrue(self.history.can_undo)
        self.history.undo()
        self.assertIn("text_bake", self.cv.shape_items)
        self.assertIsNotNone(self.lm.get_layer("text_bake"))

    def test_main_window_text_tool_integration(self):
        """Verifies MainWindow tool palette, action, and threshold controls for Text Tool."""
        from ui.main_window import MainWindow
        win = MainWindow()
        try:
            self.assertIn(InputMode.TEXT, win.tool_actions)
            self.assertIn(InputMode.TEXT, win.tool_buttons)

            # Trigger text tool
            win.tool_actions[InputMode.TEXT].trigger()
            self.assertEqual(win.input_safety.current_mode, InputMode.TEXT)
            self.assertIn("글꼴 크기", win.threshold_label.text())
            self.assertEqual(win.threshold_spin.minimum(), 8)
            self.assertEqual(win.threshold_spin.maximum(), 144)
            self.assertEqual(win.threshold_spin.suffix(), " pt")

            # Changing font size via threshold_spin
            win.threshold_spin.setValue(32)
            self.assertEqual(win.current_font_size, 32)
            if win.canvas_view:
                self.assertEqual(win.canvas_view.current_font_size, 32)
        finally:
            win.close()

    def test_text_paste_and_paint_without_crash(self):
        """Verifies creating and painting a text item (including multiline pasted text) renders without crash."""
        from PyQt6.QtWidgets import QStyleOptionGraphicsItem
        from PyQt6.QtGui import QPainter
        from unittest.mock import patch
        from ui.dialogs.text_edit_dialog import TextEditDialog

        # 1. Direct paint test (verifies QFont import in ui/shape_items.py)
        s_data = ShapeItemData(
            id="text_paint_test",
            shape_type="text",
            x=10,
            y=10,
            width=120,
            height=60,
            stroke_color="#123456",
            meta={
                "text": "Multi-line\npasted text\ntest!",
                "font_size": 20,
                "font_family": "Malgun Gothic",
                "font_bold": True,
                "font_italic": False
            }
        )
        item = TransformableShapeItem(s_data)
        test_img = QImage(200, 200, QImage.Format.Format_ARGB32_Premultiplied)
        p = QPainter(test_img)
        opt = QStyleOptionGraphicsItem()
        # Must not raise NameError or any exception!
        item.paint(p, opt)
        p.end()

        # 2. Simulated paste in TextEditDialog and confirm via _create_text_at
        pasted_content = "Line 1\n  Indented Line 2\nLine 3: 100% stable!"
        with patch.object(TextEditDialog, 'exec', return_value=1):
            with patch.object(TextEditDialog, 'get_properties', return_value={
                "text": pasted_content,
                "font_family": "Malgun Gothic",
                "font_size": 24,
                "font_bold": False,
                "font_italic": False,
                "color": QColor(0, 0, 0)
            }):
                self.cv._create_text_at(QPointF(30, 30))

        # Check item added to scene and can be painted
        self.assertTrue(any(isinstance(it, TransformableShapeItem) and it.shape_type == "text" for it in self.cv.scene.items()))

    def test_context_menu_dismiss_does_not_open_text_editor(self):
        """Verifies dismissing a shape context menu does NOT trigger text editor dialog callback."""
        from unittest.mock import MagicMock, patch
        from PyQt6.QtWidgets import QMenu
        from PyQt6.QtGui import QContextMenuEvent
        from PyQt6.QtCore import QPoint

        s_data = ShapeItemData(
            id="rect_shape",
            shape_type="rect",
            x=10,
            y=10,
            width=50,
            height=50
        )
        item = TransformableShapeItem(s_data)
        edit_text_mock = MagicMock()
        item.on_edit_text_cb = edit_text_mock

        ev = QContextMenuEvent(QContextMenuEvent.Reason.Mouse, QPoint(20, 20), QPoint(20, 20))
        with patch.object(QMenu, 'exec', return_value=None):
            item.contextMenuEvent(ev)

        edit_text_mock.assert_not_called()

    def test_drawing_shape_suppresses_context_menu(self):
        """Verifies drawing shape with right-click suppresses context menu."""
        from unittest.mock import MagicMock
        from PyQt6.QtGui import QContextMenuEvent
        from PyQt6.QtCore import QPoint

        self.safety.current_mode = InputMode.SHAPE_RECT
        self.cv.drag_start_pt = QPointF(10, 10)
        release_ev = QMouseEvent(
            QMouseEvent.Type.MouseButtonRelease,
            QPointF(50, 50),
            Qt.MouseButton.RightButton,
            Qt.MouseButton.RightButton,
            Qt.KeyboardModifier.NoModifier
        )
        self.cv.mouseReleaseEvent(release_ev)

        self.assertTrue(self.cv._suppress_context_menu)

        ctx_ev = MagicMock(spec=QContextMenuEvent)
        self.cv.contextMenuEvent(ctx_ev)
        ctx_ev.accept.assert_called_once()
        self.assertFalse(self.cv._suppress_context_menu)

    def test_delete_selection_with_and_without_transparent_selection(self):
        """Verifies deleting selection fills with secondary_color when transparent selection is off, and transparent when on, while preserving the selection marquee."""
        active_layer = self.lm.get_active_layer()
        active_layer.raster_image.fill(QColor(255, 0, 0, 255))  # Red canvas

        # Secondary color = Green
        self.cv.secondary_color = QColor(0, 255, 0, 255)

        # 1. Transparent selection = False: Delete must fill with secondary_color (not delete sub-color)
        self.cv.transparent_selection_enabled = False
        self.cv.selection_rect = QRectF(10, 10, 20, 20)
        self.cv.delete_selection()

        # Selection rect MUST remain active (not cleared)
        self.assertIsNotNone(self.cv.selection_rect)

        pixel = active_layer.raster_image.pixelColor(15, 15)
        self.assertEqual(pixel.red(), 0)
        self.assertEqual(pixel.green(), 255)
        self.assertEqual(pixel.blue(), 0)
        self.assertEqual(pixel.alpha(), 255)

        # 2. Transparent selection = True: Delete must clear to transparent (0, 0, 0, 0)
        self.cv.transparent_selection_enabled = True
        self.cv.delete_selection()

        # Selection rect still remains
        self.assertIsNotNone(self.cv.selection_rect)

        pixel_trans = active_layer.raster_image.pixelColor(15, 15)
        self.assertEqual(pixel_trans.alpha(), 0)

    def test_delete_selected_content_shapes_and_shortcuts(self):
        """Verifies delete_selected_content deletes image inside selection rect while keeping selection rect active."""
        from ui.main_window import MainWindow

        win = MainWindow()
        try:
            cv = win.canvas_view
            active_layer = win.layer_manager.get_active_layer()
            active_layer.raster_image.fill(QColor(255, 0, 0, 255))
            cv.secondary_color = QColor(0, 0, 255, 255)
            cv.transparent_selection_enabled = False
            cv.selection_rect = QRectF(5, 5, 15, 15)

            # Trigger global delete action
            win._action_delete()

            # Selection rect remains active (not deleted)
            self.assertIsNotNone(cv.selection_rect)
            # Image inside selection was deleted and filled with secondary color
            px = active_layer.raster_image.pixelColor(10, 10)
            self.assertEqual(px.blue(), 255)
        finally:
            win.close()

    def test_delete_selection_with_shapes_and_shape_layer_active(self):
        """Verifies deleting selection rect when shape layer is active correctly deletes both raster underneath and shapes inside."""
        # 1. Background layer (red)
        bg = self.lm.get_active_layer()
        bg.raster_image.fill(QColor(255, 0, 0, 255))

        # 2. Add shape and make shape layer active
        s_data = ShapeItemData(id="test_del_rect", shape_type="rect", x=10, y=10, width=20, height=20)
        shape_layer = self.lm.add_shape_to_default_layer(s_data)
        item = self.cv._create_shape_graphics_item(s_data)
        self.cv.shape_items[s_data.id] = item
        self.assertEqual(self.lm.get_active_layer().id, shape_layer.id)

        # 3. Select area containing the shape
        self.cv.selection_rect = QRectF(5, 5, 30, 30)
        self.cv.secondary_color = QColor(255, 255, 255, 255)
        self.cv.transparent_selection_enabled = False

        self.cv.delete_selection()

        # Selection rect remains
        self.assertIsNotNone(self.cv.selection_rect)
        # Shape inside must be deleted
        self.assertNotIn(s_data.id, self.cv.shape_items)
        self.assertNotIn(item, self.cv.scene.items())
        # Raster underneath must be filled with secondary color
        px = bg.raster_image.pixelColor(15, 15)
        self.assertEqual(px.red(), 255)
        self.assertEqual(px.green(), 255)
        self.assertEqual(px.blue(), 255)


if __name__ == "__main__":
    unittest.main()

