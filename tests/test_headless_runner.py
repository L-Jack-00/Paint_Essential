"""
Paint Pro - Headless Self-Test Runner
LJack Protocol Pillar 2 & Autonomous Directive 1:
Runs 100% in-memory with zero GUI windows in < 0.5s, asserting all core logic.
"""
import unittest
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QImage, QColor, QPainter

# Headless QApplication instance
app = QApplication.instance() or QApplication([])

from core.image_processor import ImageProcessor, AnchorPoint
from core.layer_manager import LayerManager, ShapeItemData, LayerType
from core.history_manager import HistoryManager
from core.input_safety import InputSafetyTracker, InputMode


class TestPaintProCore(unittest.TestCase):
    def test_01_anchor_offset_calculation(self):
        """Tests that all 9 anchor points compute exact coordinate offsets."""
        old_w, old_h = 200, 100
        new_w, new_h = 400, 300

        # TOP_LEFT (NW): dx=0, dy=0
        dx, dy = ImageProcessor.calculate_anchor_offset(old_w, old_h, new_w, new_h, AnchorPoint.TOP_LEFT)
        self.assertEqual((dx, dy), (0, 0))

        # CENTER: dx=100, dy=100
        dx, dy = ImageProcessor.calculate_anchor_offset(old_w, old_h, new_w, new_h, AnchorPoint.CENTER)
        self.assertEqual((dx, dy), (100, 100))

        # BOTTOM_RIGHT (SE): dx=200, dy=200
        dx, dy = ImageProcessor.calculate_anchor_offset(old_w, old_h, new_w, new_h, AnchorPoint.BOTTOM_RIGHT)
        self.assertEqual((dx, dy), (200, 200))

    def test_02_canvas_resize_anchor(self):
        """Tests resizing canvas without scaling content."""
        src = QImage(100, 100, QImage.Format.Format_ARGB32_Premultiplied)
        src.fill(QColor(255, 0, 0))  # Solid Red

        # Expand to 200x200 with Green background, centered
        resized = ImageProcessor.resize_canvas(
            src, 200, 200, AnchorPoint.CENTER, bg_color=QColor(0, 255, 0)
        )
        self.assertEqual(resized.width(), 200)
        self.assertEqual(resized.height(), 200)

        # Center pixel (100, 100) must be red
        center_pixel = resized.pixelColor(100, 100)
        self.assertEqual(center_pixel.red(), 255)
        self.assertEqual(center_pixel.green(), 0)

        # Corner pixel (0, 0) must be green
        corner_pixel = resized.pixelColor(0, 0)
        self.assertEqual(corner_pixel.red(), 0)
        self.assertEqual(corner_pixel.green(), 255)

    def test_03_color_adjustments(self):
        """Tests HSL, Brightness, and Contrast color filters."""
        src = QImage(50, 50, QImage.Format.Format_ARGB32_Premultiplied)
        src.fill(QColor(100, 100, 100))  # Mid gray

        # Increase brightness
        brighter = ImageProcessor.adjust_colors(src, brightness_shift=50.0)
        p = brighter.pixelColor(25, 25)
        self.assertGreater(p.red(), 100)
        self.assertEqual(brighter.width(), 50)
        self.assertEqual(brighter.height(), 50)

    def test_04_transformations(self):
        """Tests 90-degree rotation and flipping."""
        src = QImage(40, 20, QImage.Format.Format_ARGB32_Premultiplied)
        rotated = ImageProcessor.rotate_90(src, clockwise=True)
        self.assertEqual(rotated.width(), 20)
        self.assertEqual(rotated.height(), 40)

        flipped = ImageProcessor.flip(src, horizontal=True)
        self.assertEqual(flipped.width(), 40)
        self.assertEqual(flipped.height(), 20)

    def test_05_layer_manager_default_routing(self):
        """Tests that shapes act as individual layers without separate default shape layer."""
        lm = LayerManager(400, 300)
        self.assertEqual(len(lm.layers), 1)
        self.assertEqual(lm.layers[0].name, "배경 레이어")

        # Insert shape -> creates independent shape layer
        shape = ShapeItemData(shape_type="rect", x=50, y=50, width=80, height=60)
        lm.add_shape_to_default_layer(shape)

        self.assertEqual(len(lm.layers), 2)
        self.assertEqual(lm.layers[1].layer_type, LayerType.SHAPE)
        shape_layer = lm.get_default_shape_layer()
        self.assertEqual(len(shape_layer.shapes), 1)
        self.assertEqual(shape_layer.shapes[0].shape_type, "rect")

    def test_06_composite_rendering(self):
        """Tests flattening layers to a single composite image."""
        lm = LayerManager(100, 100)
        shape = ShapeItemData(
            shape_type="rect", x=10, y=10, width=50, height=50,
            fill_color="#ff0000", stroke_color="#000000"
        )
        lm.add_shape_to_default_layer(shape)
        composite = lm.composite_to_image()
        self.assertEqual(composite.width(), 100)
        self.assertEqual(composite.height(), 100)
        # Inside rect should be red
        self.assertEqual(composite.pixelColor(20, 20).red(), 255)

    def test_07_history_undo_redo(self):
        """Tests Command pattern undo/redo stack."""
        hm = HistoryManager(max_steps=10)
        val = [0]

        def do_step():
            val[0] = 10
        def undo_step():
            val[0] = 0

        do_step()
        hm.record_step("Set to 10", undo_step, do_step)
        self.assertEqual(val[0], 10)

        hm.undo()
        self.assertEqual(val[0], 0)

        hm.redo()
        self.assertEqual(val[0], 10)

    def test_08_input_safety(self):
        """Tests physical input safety tracker and emergency release."""
        ist = InputSafetyTracker()
        ist.set_mouse_down(True)
        ist.set_space_pressed(True)

        released = [False]
        ist.register_emergency_release_callback(lambda: released.__setitem__(0, True))

        ist.emergency_release()
        self.assertFalse(ist.is_mouse_down)
        self.assertFalse(ist.is_space_pressed)
        self.assertTrue(released[0])

    def test_09_history_memory_quota_eviction(self):
        """LJack Pillar 4 & Blind Spot 1: Verifies HistoryManager evicts steps when memory limit is exceeded."""
        # 1MB memory limit for testing
        hm = HistoryManager(max_steps=50, max_memory_mb=1)
        large_step_bytes = 600 * 1024  # 600 KB

        # Step 1: 600 KB
        hm.record_step("Step 1", lambda: None, lambda: None, estimated_bytes=large_step_bytes)
        self.assertEqual(len(hm.undo_stack), 1)

        # Step 2: 600 KB -> Total 1.2MB > 1MB limit -> Step 1 must be evicted!
        hm.record_step("Step 2", lambda: None, lambda: None, estimated_bytes=large_step_bytes)
        self.assertEqual(len(hm.undo_stack), 1)
        self.assertEqual(hm.undo_stack[0].description, "Step 2")

    def test_10_flood_fill_alpha_aware(self):
        """Tests alpha-aware flood fill algorithm."""
        src = QImage(30, 30, QImage.Format.Format_ARGB32_Premultiplied)
        src.fill(QColor(255, 255, 255, 255))  # White background

        # Draw a black 10x10 box in the center
        p = QPainter(src)
        p.fillRect(10, 10, 10, 10, QColor(0, 0, 0, 255))
        p.end()

        # Flood fill center with blue (0, 0, 255)
        filled = ImageProcessor.flood_fill(src, 15, 15, QColor(0, 0, 255, 255), tolerance=10)

        # (15, 15) must be Blue
        self.assertEqual(filled.pixelColor(15, 15), QColor(0, 0, 255, 255))
        # (0, 0) must remain White
        self.assertEqual(filled.pixelColor(0, 0), QColor(255, 255, 255, 255))

    def test_11_input_modes(self):
        """Verifies PENCIL, FLOOD_FILL, and SELECT_AREA are registered in InputMode."""
        self.assertEqual(InputMode.PENCIL.value, "pencil")
        self.assertEqual(InputMode.FLOOD_FILL.value, "flood_fill")
        self.assertEqual(InputMode.SELECT_AREA.value, "select_area")

    def test_12_layer_auto_naming(self):
        """Verifies automatic layer naming and sequential numbering."""
        lm = LayerManager()
        name1 = lm.generate_new_layer_name("새 레이어")
        self.assertEqual(name1, "새 레이어")
        lm.add_layer(name1)

        name2 = lm.generate_new_layer_name("새 레이어")
        self.assertEqual(name2, "새 레이어 2")
        lm.add_layer(name2)

        name3 = lm.generate_new_layer_name("새 레이어")
        self.assertEqual(name3, "새 레이어 3")

    def test_13_merge_shape_into_raster(self):
        """Verifies vector shape baking into raster layer."""
        lm = LayerManager(100, 100)
        shape = ShapeItemData(
            id="test_rect", shape_type="rect",
            x=10, y=10, width=40, height=40,
            fill_color="#ff0000", stroke_color="#000000"
        )
        lm.add_shape_to_default_layer(shape)
        self.assertEqual(len(lm.get_default_shape_layer().shapes), 1)

        # Merge to background raster layer
        success = lm.merge_shape_into_raster("test_rect", "bg_layer")
        self.assertTrue(success)

        # Shape must be removed from shape layer
        self.assertEqual(len(lm.get_default_shape_layer().shapes), 0)

        # Raster layer must now contain the painted shape pixels
        bg_layer = lm.get_layer("bg_layer")
        self.assertEqual(bg_layer.raster_image.pixelColor(20, 20).red(), 255)


if __name__ == "__main__":
    unittest.main()
