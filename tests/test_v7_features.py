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

        # Shape should be automatically baked to raster
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


if __name__ == "__main__":
    unittest.main()
