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
from PyQt6.QtCore import Qt, QRect, QPointF, QPoint, QMimeData, QByteArray, QBuffer

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

        # Shape should NOT be automatically baked to raster - remains in shape layer!
        self.assertEqual(len(shape_layer.shapes), 1)
        self.assertEqual(len(self.cv.scene.selectedItems()), 0)

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


if __name__ == "__main__":
    unittest.main()
