"""
Paint Essential - Unit Test Suite for v1.2.0 Features
LJack Protocol Pillar 4: Headless Self-Test Runner & Regression Gate
Testing:
- Dynamic threshold controls (Step Badge, Mosaic, Rounded Rect)
- Step Badge formats (numbers, upper/lower alpha) & canvas click/reset
- Tool cluster buttons (Rectangle & Arrow sub-modes)
- Arrow vector geometry (single, double, curved single, curved double)
- Rounded rectangle geometry & corner radius live link
- Non-blocking ToastOverlay notifications on Copy/Cut
"""
import unittest
import sys
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt, QPoint, QPointF, QRectF
from PyQt6.QtGui import QMouseEvent, QColor

from ui.main_window import MainWindow
from core.input_safety import InputMode
from ui.canvas_view import format_step_badge
from core.shape_geometry import create_arrow_path, create_rounded_rect_path
from ui.toast_overlay import ToastOverlay


app = QApplication.instance()
if not app:
    app = QApplication(sys.argv)


class TestV8Features(unittest.TestCase):
    def setUp(self):
        self.win = MainWindow()
        self.cv = self.win.canvas_view
        self.lm = self.win.layer_manager

    def tearDown(self):
        self.win.close()

    def test_01_step_badge_dynamic_threshold(self):
        """Verifies Step Badge dynamic threshold label, range, and suffix."""
        self.win._set_tool(InputMode.STEP_BADGE)
        self.assertIn("시작 번호", self.win.threshold_label.text())
        self.assertEqual(self.win.threshold_spin.suffix(), " 번")
        self.assertEqual(self.win.threshold_spin.minimum(), 1)
        self.assertEqual(self.win.threshold_spin.maximum(), 99)

        # Changing spinbox value syncs to canvas_view
        self.win.threshold_spin.setValue(7)
        self.assertEqual(self.cv.step_badge_start, 7)
        self.assertEqual(self.cv.step_badge_count, 7)

    def test_02_step_badge_formatting_modes(self):
        """Verifies Step Badge text formatting for numbers, upper alpha, and lower alpha."""
        # 1. Number mode
        self.assertEqual(format_step_badge(1, "number"), "1")
        self.assertEqual(format_step_badge(20, "number"), "20")
        self.assertEqual(format_step_badge(21, "number"), "21")

        # 2. Upper alpha mode
        self.assertEqual(format_step_badge(1, "alpha_upper"), "A")
        self.assertEqual(format_step_badge(26, "alpha_upper"), "Z")
        self.assertEqual(format_step_badge(27, "alpha_upper"), "AA")

        # 3. Lower alpha mode
        self.assertEqual(format_step_badge(1, "alpha_lower"), "a")
        self.assertEqual(format_step_badge(26, "alpha_lower"), "z")
        self.assertEqual(format_step_badge(27, "alpha_lower"), "aa")

    def test_03_step_badge_click_increment_and_right_click_reset(self):
        """Verifies Step Badge increments count on click and resets to start on right-click."""
        self.win._set_tool(InputMode.STEP_BADGE)
        self.win.threshold_spin.setValue(5)
        self.cv.step_badge_mode = "number"

        # Apply badge at (50, 50)
        self.cv._apply_step_badge(QPointF(50, 50))

        # Count should increment to 6
        self.assertEqual(self.cv.step_badge_count, 6)

        # Simulate right click on canvas to reset
        pos = QPointF(50, 50)
        right_press = QMouseEvent(
            QMouseEvent.Type.MouseButtonPress,
            pos, pos,
            Qt.MouseButton.RightButton,
            Qt.MouseButton.RightButton,
            Qt.KeyboardModifier.NoModifier
        )
        self.cv.mousePressEvent(right_press)
        self.assertEqual(self.cv.step_badge_count, 5)

    def test_04_mosaic_dynamic_threshold(self):
        """Verifies Mosaic dynamic threshold label, range, and live connection."""
        self.win._set_tool(InputMode.MOSAIC)
        self.assertIn("블록 크기", self.win.threshold_label.text())
        self.assertEqual(self.win.threshold_spin.suffix(), " px")
        self.assertEqual(self.win.threshold_spin.minimum(), 4)
        self.assertEqual(self.win.threshold_spin.maximum(), 64)

        # Changing spinbox updates canvas_view
        self.win.threshold_spin.setValue(20)
        self.assertEqual(self.cv.mosaic_block_size, 20)
        self.assertEqual(self.win.mosaic_block_size, 20)

    def test_05_rounded_rect_cluster_and_threshold(self):
        """Verifies Rounded Rectangle cluster sub-tool and corner radius threshold."""
        self.assertIsNotNone(self.win.rect_cluster_btn)
        self.assertEqual(len(self.win.rect_cluster_btn.sub_tools), 2)

        # Select rounded rect submode
        self.win._select_rect_mode(InputMode.SHAPE_ROUNDED_RECT, 1)
        self.assertEqual(self.win.input_safety.current_mode, InputMode.SHAPE_ROUNDED_RECT)
        self.assertIn("모서리 곡률", self.win.threshold_label.text())
        self.assertEqual(self.win.threshold_spin.suffix(), " px")
        self.assertEqual(self.win.threshold_spin.minimum(), 2)
        self.assertEqual(self.win.threshold_spin.maximum(), 64)

        # Value change updates rect_corner_radius
        self.win.threshold_spin.setValue(18)
        self.assertEqual(self.cv.rect_corner_radius, 18)
        self.assertEqual(self.win.rect_corner_radius, 18)

    def test_06_arrow_cluster_modes_and_geometry(self):
        """Verifies Arrow cluster 4 sub-modes and shape_geometry path generation."""
        self.assertIsNotNone(self.win.arrow_cluster_btn)
        self.assertEqual(len(self.win.arrow_cluster_btn.sub_tools), 4)

        modes = ["single", "double", "curved_single", "curved_double"]
        for idx, m in enumerate(modes):
            self.win._select_arrow_mode(m, idx)
            self.assertEqual(self.win.arrow_mode, m)
            self.assertEqual(self.cv.arrow_mode, m)
            self.assertEqual(self.win.input_safety.current_mode, InputMode.SHAPE_ARROW)

            # Test path creation for each mode
            path = create_arrow_path(120, 80, arrow_mode=m, meta={"ctrl_offset_ratio": 0.3})
            self.assertFalse(path.isEmpty())

    def test_07_rounded_rect_geometry(self):
        """Verifies rounded rectangle geometry creation."""
        path = create_rounded_rect_path(100, 80, corner_radius=15)
        self.assertFalse(path.isEmpty())
        bounds = path.boundingRect()
        self.assertAlmostEqual(bounds.width(), 100, delta=1.0)
        self.assertAlmostEqual(bounds.height(), 80, delta=1.0)

    def test_08_toast_overlay_headless(self):
        """Verifies ToastOverlay initializes and displays messages cleanly."""
        toast = ToastOverlay(self.cv)
        self.assertIsNotNone(toast)
        toast.show_toast("클립보드에 투명 PNG로 복사되었습니다")
        self.assertFalse(toast.isHidden())
        self.assertIn("투명 PNG", toast.label.text())
        toast.hide_toast()

    def test_09_clipboard_copy_triggers_toast(self):
        """Verifies copy/cut operations display toast messages."""
        # Setup small selection
        self.cv.selection_rect = QRectF(10, 10, 50, 50)
        self.cv.has_active_selection = True

        self.cv.copy_selection()
        self.assertFalse(self.cv.toast.isHidden())
        self.assertIn("복사", self.cv.toast.label.text())

        self.cv.copy_selection_transparent()
        self.assertFalse(self.cv.toast.isHidden())
        self.assertIn("투명 PNG", self.cv.toast.label.text())

        self.cv.cut_selection()
        self.assertFalse(self.cv.toast.isHidden())
        self.assertIn("잘라내어", self.cv.toast.label.text())


if __name__ == "__main__":
    unittest.main()
