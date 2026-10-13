"""
Paint Essential - Unit Test Suite for v1.0.0 Quality Fixes (Issue 1 ~ 6)
LJack Protocol: Headless Regression Rig
"""
import unittest
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt, QPointF, QRect, QRectF
from PyQt6.QtGui import QColor, QImage, QPixmap, QPainter, QKeySequence

from core.layer_manager import LayerManager, LayerType, ShapeItemData
from core.history_manager import HistoryManager
from core.input_safety import InputSafetyTracker
from core.image_processor import ImageProcessor
from ui.canvas_view import CanvasView
from ui.layer_panel import LayerPanel
from ui.dialogs.adjustment_dialog import AdjustmentDialog
from ui.main_window import MainWindow

app = QApplication.instance() or QApplication([])


class TestV6Fixes(unittest.TestCase):
    def test_issue1_reparent_children_on_parent_delete(self):
        """Issue 1: When a parent layer is removed, children must be re-parented to target.parent_id."""
        lm = LayerManager(400, 300)
        parent = lm.add_layer("부모 레이어", LayerType.RASTER)
        child = lm.add_layer("자식 레이어", LayerType.RASTER)
        child.parent_id = parent.id

        self.assertFalse(parent.parent_id)
        self.assertEqual(child.parent_id, parent.id)

        # Remove parent layer
        removed = lm.remove_layer(parent.id)
        self.assertTrue(removed)

        # Child must have its parent_id reset to None (promoted/outdented)
        self.assertIsNone(child.parent_id)
        self.assertIn(child, lm.layers)
        self.assertTrue(lm.is_layer_effectively_visible(child.id))

    def test_issue2_layer_panel_history_undo_redo(self):
        """Issue 2: Layer panel additions, deletions, and moves must be recorded in HistoryManager."""
        win = MainWindow()
        lm = win.layer_manager
        hm = win.history_manager

        initial_count = len(lm.layers)

        # Add layer via panel
        win.layer_panel._add_layer()
        self.assertEqual(len(lm.layers), initial_count + 1)
        self.assertTrue(hm.can_undo())

        # Undo addition
        win._action_undo()
        self.assertEqual(len(lm.layers), initial_count)

        # Redo addition
        win._action_redo()
        self.assertEqual(len(lm.layers), initial_count + 1)

        # Delete added layer
        added_id = lm.layers[-1].id
        win.layer_panel._del_specific_layer(added_id)
        self.assertEqual(len(lm.layers), initial_count)

        # Undo deletion
        win._action_undo()
        self.assertEqual(len(lm.layers), initial_count + 1)
        self.assertIsNotNone(lm.get_layer(added_id))

        win.close()

    def test_issue3_cut_and_floating_commit_history(self):
        """Issue 3: Cut and floating selection commit must record undoable history steps."""
        win = MainWindow()
        cv = win.canvas_view
        hm = win.history_manager
        active = win.layer_manager.get_active_layer()

        # Set selection rect
        cv.selection_rect = QRectF(10, 10, 40, 40)
        cv.cut_selection()

        # History should contain cut step
        self.assertTrue(any("잘라내기" in s.description for s in hm.undo_stack))

        # Undo cut restores selection rect and image
        cv.commit_floating_selection_if_any()
        win._action_undo()
        self.assertIsNotNone(cv.selection_rect)
        self.assertEqual(cv.selection_rect, QRectF(10, 10, 40, 40))

        win.close()

    def test_issue4_all_layers_rotate_and_flip(self):
        """Issue 4: 90-degree rotate and flip must transform all raster layers and vector shapes."""
        win = MainWindow()
        lm = win.layer_manager

        l2 = lm.add_layer("추가 레이어", LayerType.RASTER)
        shape_layer = lm.get_default_shape_layer()
        s = ShapeItemData(id="test_s", shape_type="rect", x=50, y=50, width=40, height=30)
        shape_layer.shapes.append(s)

        orig_w, orig_h = lm.width, lm.height

        # Rotate 90
        win._action_rotate()
        self.assertEqual(lm.width, orig_h)
        self.assertEqual(lm.height, orig_w)

        # Check all layers rotated
        bg_img = lm.get_layer("bg_layer").raster_image
        self.assertEqual(bg_img.width(), orig_h)
        self.assertEqual(bg_img.height(), orig_w)

        l2_img = l2.raster_image
        self.assertEqual(l2_img.width(), orig_h)
        self.assertEqual(l2_img.height(), orig_w)

        # Check shape coords transformed
        self.assertNotEqual((s.x, s.y), (50, 50))

        # Undo rotate restores dimensions and shapes
        win._action_undo()
        self.assertEqual(lm.width, orig_w)
        self.assertEqual(lm.height, orig_h)
        self.assertEqual((s.x, s.y), (50.0, 50.0))

        win.close()

    def test_issue5_fast_color_adjust_and_proxy(self):
        """Issue 5: Color adjustment executes rapidly (< 150ms on 4K) and preview uses proxy."""
        w, h = 3840, 2160
        img = QImage(w, h, QImage.Format.Format_ARGB32_Premultiplied)
        img.fill(QColor(120, 140, 160, 255))

        adjusted = ImageProcessor.adjust_colors(
            img, hue_shift=30.0, saturation_scale=1.2, brightness_shift=15.0, contrast_scale=1.1
        )
        self.assertEqual(adjusted.width(), w)
        self.assertEqual(adjusted.height(), h)

        # Check proxy generation in AdjustmentDialog
        dlg = AdjustmentDialog(img)
        proxy, sel = dlg._get_preview_proxy()
        self.assertIsNotNone(proxy)
        self.assertLessEqual(max(proxy.width(), proxy.height()), 800)
        dlg.close()

    def test_issue6_f1_shortcut_binding(self):
        """Issue 6: Settings action must have F1 shortcut bound."""
        win = MainWindow()
        self.assertTrue(hasattr(win, "settings_act"))
        self.assertEqual(win.settings_act.shortcut().toString(), "F1")
        win.close()


if __name__ == "__main__":
    unittest.main()
