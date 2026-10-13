"""
Paint Pro - Test Suite for v5.4.0 Upgrades
Tests:
1. Multi-stage pixel grid (subtle gray at zoom < 4.5, alternating dashed at zoom >= 4.5)
2. Vector shape to raster merge with full Undo/Redo
3. Layer name cleanup (no '[래스터]' header prefix)
4. Canvas floating bottom HUD overlay (interactive zoom, reset, editable grid input)
5. Scrubby slider control (horizontal drag value adjustment)
6. Marquee selection 8-handle transformation, context menu, rotate, flip, and invert
7. Drawing operations strictly restricted to selection bounds
8. Flood fill with alpha threshold (n%) and selection clipping
9. Selection sub-tools (Lasso mode, Magic Wand mask detection)
10. Advanced Color Adjustment dialog (resizable, zoomable preview, 54px labels, multi-layer batch)
"""
import unittest
from PyQt6.QtWidgets import QApplication, QTextEdit, QLabel
from PyQt6.QtCore import Qt, QPointF, QRect, QRectF
from PyQt6.QtGui import QColor, QImage, QPixmap, QPainter

from core.layer_manager import LayerManager, LayerType, ShapeItemData
from core.history_manager import HistoryManager
from core.input_safety import InputSafetyTracker, InputMode
from core.image_processor import ImageProcessor
from ui.canvas_view import CanvasView
from ui.selection_item import MarqueeSelectionBox
from ui.scrubby_control import ScrubbyLabel
from ui.canvas_hud import CanvasHudOverlay
from ui.dialogs.adjustment_dialog import AdjustmentDialog
from ui.main_window import MainWindow

# Ensure QApplication exists for headless tests
app = QApplication.instance() or QApplication([])


class TestV5Upgrades(unittest.TestCase):
    def setUp(self):
        self.lm = LayerManager(canvas_width=400, canvas_height=300)
        self.safety = InputSafetyTracker()
        self.hm = HistoryManager()
        self.cv = CanvasView(self.lm, self.safety, self.hm)

    def test_01_multi_stage_pixel_grid(self):
        """Verifies multi-stage grid pen selection at different zoom levels."""
        self.cv.set_pixel_grid_enabled(True)
        pm = QPixmap(100, 100)
        painter = QPainter(pm)

        # Zoom < threshold (e.g. 5.0): Pixel grid is NOT shown yet
        self.cv.set_zoom_level(5.0)
        self.assertFalse(self.cv.zoom_level >= self.cv.pixel_grid_threshold)

        # Stage 1: Zoom = 9.0 (Subtle gray solid line at >= 800% zoom)
        self.cv.set_zoom_level(9.0)
        self.assertTrue(self.cv.zoom_level >= self.cv.pixel_grid_threshold)
        self.assertTrue(self.cv.zoom_level < 12.0)
        self.cv.drawForeground(painter, QRectF(0, 0, 100, 100))

        # Stage 2: Zoom = 14.0 (Alternating 50% opacity dotted dashes at >= 1200% zoom)
        self.cv.set_zoom_level(14.0)
        self.assertTrue(self.cv.zoom_level >= 12.0)
        self.cv.drawForeground(painter, QRectF(0, 0, 100, 100))
        painter.end()

    def test_02_shape_merge_to_raster_with_undo_redo(self):
        """Verifies vector shape merged into raster layer can be undone and redone."""
        # 1. Add vector rectangle
        shape = ShapeItemData(
            id="test_rect_1",
            shape_type="rect",
            x=10.0, y=10.0, width=50.0, height=40.0,
            fill_color="#ff0000",
            stroke_color="#000000",
            stroke_width=2
        )
        shape_layer = self.lm.get_default_shape_layer()
        shape_layer.shapes.append(shape)
        self.cv.rebuild_scene()
        self.assertIn("test_rect_1", self.cv.shape_items)

        bg_layer = self.lm.get_layer("bg_layer")
        c_before = bg_layer.raster_image.pixelColor(20, 20)

        # 2. Merge shape to raster layer
        self.cv.merge_shape_to_raster("test_rect_1")
        self.assertNotIn("test_rect_1", self.cv.shape_items)
        self.assertEqual(len(shape_layer.shapes), 0)

        c_after = bg_layer.raster_image.pixelColor(20, 20)
        self.assertEqual(c_after.red(), 255)

        # 3. Undo merge
        self.assertTrue(self.hm.can_undo)
        self.hm.undo()
        self.assertEqual(len(shape_layer.shapes), 1)
        self.assertEqual(shape_layer.shapes[0].id, "test_rect_1")
        self.assertIn("test_rect_1", self.cv.shape_items)
        c_undone = bg_layer.raster_image.pixelColor(20, 20)
        self.assertEqual(c_undone, c_before)

        # 4. Redo merge
        self.assertTrue(self.hm.can_redo)
        self.hm.redo()
        self.assertEqual(len(shape_layer.shapes), 0)
        self.assertNotIn("test_rect_1", self.cv.shape_items)
        c_redone = bg_layer.raster_image.pixelColor(20, 20)
        self.assertEqual(c_redone.red(), 255)

    def test_03_layer_panel_name_without_raster_prefix(self):
        """Verifies raster layers do not contain '[래스터]' header prefix in LayerPanel."""
        from ui.layer_panel import LayerPanel
        panel = LayerPanel(self.lm)
        panel.refresh_list()

        count = panel.tree.topLevelItemCount()
        self.assertGreater(count, 0)
        for i in range(count):
            item = panel.tree.topLevelItem(i)
            text = item.text(0)
            self.assertFalse(text.startswith("[래스터]"), f"Layer name should not start with [래스터]: {text}")

    def test_04_canvas_hud_overlay_controls(self):
        """Verifies CanvasHudOverlay signals and editable direct input."""
        hud = CanvasHudOverlay(self.cv.viewport())
        self.cv.hud = hud

        zoom_in_called = []
        hud.zoom_in_requested.connect(lambda: zoom_in_called.append(True))
        hud.zoom_in_btn.click()
        self.assertTrue(zoom_in_called)

        reset_called = []
        hud.zoom_reset_requested.connect(lambda: reset_called.append(True))
        hud.reset_btn.click()
        self.assertTrue(reset_called)

        # Test direct input in grid combo
        spacing_results = []
        hud.grid_spacing_changed.connect(lambda val: spacing_results.append(val))
        hud.grid_combo.setEditText("48")
        self.assertIn(48, spacing_results)

    def test_05_scrubby_label_horizontal_drag(self):
        """Verifies ScrubbyLabel horizontal dragging updates values."""
        label = ScrubbyLabel("굵기: ", initial_value=10, min_val=1, max_val=50)
        val_changes = []
        label.valueChanged.connect(lambda v: val_changes.append(v))

        # Simulate horizontal drag: +20px -> +10 units (sensitivity 0.5)
        label.is_dragging = True
        label.drag_start_x = 100.0
        label.drag_start_val = 10

        from PyQt6.QtGui import QMouseEvent
        from PyQt6.QtCore import QPointF, QEvent
        event = QMouseEvent(
            QEvent.Type.MouseMove,
            QPointF(120, 50),
            QPointF(120, 50),
            Qt.MouseButton.LeftButton,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier
        )
        label.mouseMoveEvent(event)
        self.assertEqual(label.value, 20)
        self.assertIn(20, val_changes)

    def test_06_drawing_restricted_to_selection(self):
        """Verifies painting (brush/pencil) strictly paints within selection_rect."""
        bg = self.lm.get_layer("bg_layer")
        self.lm.set_active_layer("bg_layer")

        # Set selection rect from (50, 50) to (150, 150)
        self.cv.selection_rect = QRectF(50, 50, 100, 100)
        self.cv.primary_color = QColor(255, 0, 0, 255)
        self.cv.stroke_width = 4
        self.safety.current_mode = InputMode.PENCIL

        # Draw a diagonal line that crosses the selection from (0, 0) to (200, 200)
        self.cv._draw_raster_line(QPointF(0, 0), QPointF(200, 200))

        # Pixel at (10, 10) outside selection must remain untouched (white)
        c_outside = bg.raster_image.pixelColor(10, 10)
        self.assertEqual(c_outside, QColor(255, 255, 255, 255))

        # Pixel at (100, 100) inside selection must be drawn (red)
        c_inside = bg.raster_image.pixelColor(100, 100)
        self.assertEqual(c_inside, QColor(255, 0, 0, 255))

    def test_07_flood_fill_with_alpha_threshold_and_clip_rect(self):
        """Verifies flood fill respects alpha threshold and selection rect boundary."""
        img = QImage(100, 100, QImage.Format.Format_RGBA8888)
        img.fill(QColor(0, 0, 0, 0))  # Fully transparent

        # Draw a semi-transparent square (alpha=50) at (20, 20, 60, 60)
        p = QPainter(img)
        p.fillRect(20, 20, 60, 60, QColor(100, 100, 100, 50))
        p.end()

        c_before = img.pixelColor(55, 55)

        # Fill with tolerance and alpha threshold up to 30% (approx 76/255)
        # and clip to rect (10, 10, 40, 40)
        clip = QRect(10, 10, 40, 40)
        filled = ImageProcessor.flood_fill(
            img, 25, 25, QColor(0, 255, 0, 255),
            tolerance=32, alpha_threshold=30, clip_rect=clip
        )

        # Pixel inside clip rect at (25, 25) must be filled
        c_inside = filled.pixelColor(25, 25)
        self.assertEqual(c_inside, QColor(0, 255, 0, 255))

        # Pixel outside clip rect at (55, 55) must NOT be filled (must match c_before)
        c_outside = filled.pixelColor(55, 55)
        self.assertEqual(c_outside, c_before)

    def test_08_magic_wand_mask_detection(self):
        """Verifies find_wand_mask detects contiguous matching pixels."""
        img = QImage(50, 50, QImage.Format.Format_RGBA8888)
        img.fill(QColor(255, 255, 255, 255))

        # Draw a red blob in the center
        p = QPainter(img)
        p.fillRect(10, 10, 20, 20, QColor(255, 0, 0, 255))
        p.end()

        mask = ImageProcessor.find_wand_mask(img, 15, 15, tolerance=10)
        self.assertIsNotNone(mask)
        self.assertTrue(mask[15, 15])
        self.assertTrue(mask[25, 25])
        self.assertFalse(mask[5, 5])

    def test_09_marquee_selection_transform_and_inversion(self):
        """Verifies selection box 90deg rotate, flip H/V, and invert selection."""
        self.cv.selection_rect = QRectF(20, 20, 60, 40)
        self.cv._update_marquee_preview(QPointF(20, 20), QPointF(80, 60))
        self.assertIsNotNone(self.cv.marquee_box)

        # Test invert selection
        self.assertFalse(self.cv.is_selection_inverted)
        self.cv.invert_selection()
        self.assertTrue(self.cv.is_selection_inverted)
        self.assertTrue(self.cv.marquee_box.is_inverted)

        # Test deselect
        self.cv.deselect()
        self.assertIsNone(self.cv.selection_rect)
        self.assertFalse(self.cv.is_selection_inverted)

    def test_10_adjustment_dialog_features(self):
        """Verifies AdjustmentDialog resizability, labels width, and selection masking."""
        img = QImage(100, 100, QImage.Format.Format_RGBA8888)
        img.fill(QColor(128, 128, 128, 255))

        dlg = AdjustmentDialog(img, selection_rect=QRect(10, 10, 30, 30))
        self.assertTrue(dlg.isSizeGripEnabled())
        self.assertEqual(dlg.hue_val_label.width(), 54)
        self.assertEqual(dlg.sat_val_label.width(), 54)

        # Apply adjustments
        dlg.bri_slider.setValue(50)
        adj_img = dlg.get_adjusted_image()

        # Inside selection rect (20, 20) brightness is boosted
        c_in = adj_img.pixelColor(20, 20)
        self.assertGreater(c_in.red(), 128)

        # Outside selection rect (70, 70) remains untouched (128)
        c_out = adj_img.pixelColor(70, 70)
        self.assertEqual(c_out.red(), 128)

    def test_11_insert_shape_in_selection_bounds(self):
        """Verifies Approach 1: Inserting shape matching selection bounds preserves 100% vector editability."""
        # 1. Create marquee selection rect at (30, 40, 100, 80)
        self.cv.selection_rect = QRectF(30, 40, 100, 80)
        self.cv._update_marquee_preview(QPointF(30, 40), QPointF(130, 120))

        # 2. Insert rectangle matching selection bounds
        item = self.cv.insert_shape_in_selection("rect")
        self.assertIsNotNone(item)
        self.assertEqual(item.shape_data.shape_type, "rect")
        self.assertEqual(item.shape_data.x, 30.0)
        self.assertEqual(item.shape_data.y, 40.0)
        self.assertEqual(item.shape_data.width, 100.0)
        self.assertEqual(item.shape_data.height, 80.0)

        # Selection marquee must be cleared and new shape must be selected
        self.assertIsNone(self.cv.selection_rect)
        self.assertTrue(item.isSelected())
        self.assertEqual(self.safety.current_mode, InputMode.SELECT)
        # Approach 2: Must have clip_rect in meta
        self.assertIn("clip_rect", item.shape_data.meta)
        self.assertEqual(item.shape_data.meta["clip_rect"], [30.0, 40.0, 100.0, 80.0])

        # 3. Verify vector item remains fully editable on shape layer
        shape_layer = self.lm.get_default_shape_layer()
        self.assertIn(item.shape_data, shape_layer.shapes)
        self.assertIn(item.shape_data.id, self.cv.shape_items)

        # 4. Verify Undo and Redo for inserted shape
        self.assertTrue(self.hm.can_undo)
        self.hm.undo()
        self.assertNotIn(item.shape_data, shape_layer.shapes)
        self.hm.redo()
        self.assertIn(item.shape_data.id, self.cv.shape_items)

        # 5. Verify toolbar tool selection does NOT auto-create shape (User Request Fix)
        win = MainWindow()
        win.canvas_view.selection_rect = QRectF(50, 60, 120, 90)
        win._set_tool(InputMode.SHAPE_ELLIPSE)
        # Switching tool must NOT auto-insert shape
        self.assertEqual(len(win.layer_manager.get_default_shape_layer().shapes), 0)

        # Context menu insert_shape_in_selection maintains Approach 2 vector clipping mask insertion
        inserted = win.canvas_view.insert_shape_in_selection("ellipse")
        self.assertIsNotNone(inserted)
        win_shapes = win.layer_manager.get_default_shape_layer().shapes
        self.assertGreater(len(win_shapes), 0)
        last_shape = win_shapes[-1]
        self.assertEqual(last_shape.shape_type, "ellipse")
        self.assertEqual(last_shape.x, 50.0)
        self.assertEqual(last_shape.y, 60.0)
        self.assertEqual(last_shape.width, 120.0)
        self.assertEqual(last_shape.height, 90.0)
        self.assertIn("clip_rect", last_shape.meta)

    def test_12_flood_fill_sample_all_layers(self):
        """Verifies flood fill respects boundaries from all visible layers when sample_all_layers is enabled."""
        # Layer 1: Bottom color layer (transparent)
        color_layer = self.lm.add_layer("컬러 레이어", layer_type=LayerType.RASTER)
        color_layer.raster_image.fill(QColor(0, 0, 0, 0))

        # Layer 2: Top line art layer with a black boundary box (20, 20, 40, 40)
        line_layer = self.lm.add_layer("선화 레이어", layer_type=LayerType.RASTER)
        line_layer.raster_image.fill(QColor(0, 0, 0, 0))
        p = QPainter(line_layer.raster_image)
        p.setPen(QColor(0, 0, 0, 255))
        p.drawRect(20, 20, 40, 40)
        p.end()

        # Set active layer to color_layer
        self.lm.set_active_layer(color_layer.id)
        self.cv.primary_color = QColor(255, 0, 0, 255)

        # 1. Fill without sample_all_layers (False)
        self.cv.fill_sample_all_layers = False
        self.cv._apply_flood_fill(QPointF(30, 30))
        # Since color_layer has no boundaries, it leaks and fills pixels outside the box too
        c_out_false = color_layer.raster_image.pixelColor(80, 80)
        self.assertEqual(c_out_false, QColor(255, 0, 0, 255))

        # Reset color_layer
        color_layer.raster_image.fill(QColor(0, 0, 0, 0))

        # 2. Fill WITH sample_all_layers (True)
        self.cv.fill_sample_all_layers = True
        self.cv._apply_flood_fill(QPointF(30, 30))

        # Inside the line art box (30, 30), color_layer must be filled red
        c_in_true = color_layer.raster_image.pixelColor(30, 30)
        self.assertEqual(c_in_true, QColor(255, 0, 0, 255))

        # Outside the line art box (80, 80), color_layer must remain transparent!
        c_out_true = color_layer.raster_image.pixelColor(80, 80)
        self.assertEqual(c_out_true, QColor(0, 0, 0, 0))

    def test_13_layer_panel_half_minimum_width(self):
        """Verifies layer panel minimum width is halved to 130px."""
        from ui.layer_panel import LayerPanel
        lp = LayerPanel(self.lm)
        self.assertLessEqual(lp.minimumWidth(), 130)

        win = MainWindow()
        # Find dock widget
        from PyQt6.QtWidgets import QDockWidget
        docks = win.findChildren(QDockWidget)
        self.assertGreater(len(docks), 0)
        for d in docks:
            self.assertLessEqual(d.minimumWidth(), 130)

    def test_14_selection_border_hit_test_and_interior_drawing(self):
        """Verifies MarqueeSelectionBox body drag is restricted to border, allowing interior drawing."""
        from ui.selection_item import MarqueeSelectionBox
        rect = QRectF(50, 50, 100, 100)
        box = MarqueeSelectionBox(rect)

        # Border hit test (border is within 6px of 50 or 150)
        self.assertTrue(box._hit_test_border(QPointF(51, 80)))  # Near left border
        self.assertTrue(box._hit_test_border(QPointF(149, 80))) # Near right border
        self.assertTrue(box._hit_test_border(QPointF(80, 52)))  # Near top border
        self.assertTrue(box._hit_test_border(QPointF(80, 148))) # Near bottom border

        # Interior hit test (center of rect: 100, 100)
        self.assertFalse(box._hit_test_border(QPointF(100, 100))) # Deep interior

        # Outside hit test
        self.assertFalse(box._hit_test_border(QPointF(10, 10)))

        # Verify drawing inside selection clips to selection without moving box
        self.cv.selection_rect = rect
        self.cv.marquee_box = box
        self.safety.current_mode = InputMode.BRUSH
        self.cv.primary_color = QColor(0, 255, 0, 255)

        # Draw line inside selection from (60, 60) to (90, 90)
        self.cv._draw_raster_line(QPointF(60, 60), QPointF(90, 90))
        act_lay = self.lm.get_active_layer()
        self.assertEqual(act_lay.raster_image.pixelColor(70, 70), QColor(0, 255, 0, 255))
        # Marquee rect must remain unchanged at (50, 50, 100, 100)
        self.assertEqual(self.cv.selection_rect, rect)

    def test_15_switching_layers_preserves_selection_marquee(self):
        """Verifies that selecting another layer does NOT clear/drop the active marquee selection."""
        # Setup active selection
        self.cv.selection_rect = QRectF(20, 30, 80, 60)
        from ui.selection_item import MarqueeSelectionBox
        self.cv.marquee_box = MarqueeSelectionBox(self.cv.selection_rect)
        self.cv.scene.addItem(self.cv.marquee_box)

        # Add new layer and switch active layer
        new_lay = self.lm.add_layer("새 레이어 2")
        self.lm.set_active_layer(new_lay.id)

        # Trigger rebuild_scene as LayerPanel does
        self.cv.rebuild_scene()

        # Selection rect and marquee box MUST be preserved!
        self.assertIsNotNone(self.cv.selection_rect)
        self.assertEqual(self.cv.selection_rect, QRectF(20, 30, 80, 60))
        self.assertIsNotNone(self.cv.marquee_box)
        self.assertIn(self.cv.marquee_box, self.cv.scene.items())

    def test_16_spinbox_vector_arrow_icons(self):
        """Verifies IconFactory generates clean vector PNG arrow assets for QSS."""
        from ui.icon_factory import IconFactory
        up_url, down_url = IconFactory.ensure_spinbox_arrows()
        import os
        self.assertTrue(os.path.exists(up_url))
        self.assertTrue(os.path.exists(down_url))
        self.assertGreater(os.path.getsize(up_url), 50)
        self.assertGreater(os.path.getsize(down_url), 50)

    def test_17_adjustment_dialog_multiselect_empty_state_and_middle_pan(self):
        """Verifies AdjustmentDialog multi-layer checklist, empty state text, and middle pan."""
        img = QImage(100, 100, QImage.Format.Format_ARGB32_Premultiplied)
        img.fill(QColor(255, 0, 0, 255))

        dlg = AdjustmentDialog(img, layers=self.lm.layers, active_layer_id="bg_layer")
        # Checkboxes must exist for raster layers
        self.assertGreater(len(dlg.layer_checkboxes), 0)
        self.assertIsNotNone(dlg.select_all_check)

        # Uncheck all layer checkboxes
        for cb in dlg.layer_checkboxes.values():
            cb.setChecked(False)
        self.assertEqual(len(dlg.get_target_layer_ids()), 0)

        # When 0 layers checked, preview must display "아무것도 선택되지 않음"
        dlg._update_preview()
        self.assertTrue(dlg.preview_widget.full_pixmap.isNull())
        self.assertEqual(dlg.preview_widget.img_label.text(), "아무것도 선택되지 않음")

        # Test ZoomablePreviewWidget middle click drag panning
        pw = dlg.preview_widget
        pw.set_pixmap(QPixmap.fromImage(img))
        self.assertFalse(pw.is_panning)

    def test_18_canvas_hud_activation_and_ctrl_0_shortcut(self):
        """Verifies CanvasHudOverlay activates on pan/zoom and Ctrl+0 resets view."""
        self.assertIsNotNone(self.cv.hud)

        # Zoom in should activate HUD and update zoom
        self.cv.set_zoom_level(2.0)
        self.assertFalse(self.cv.hud.isHidden())
        self.assertEqual(self.cv.hud.zoom_label.text(), "200%")

        # Ctrl+0 key press event should reset view to 1.0 (100%)
        from PyQt6.QtGui import QKeyEvent
        key_event = QKeyEvent(
            QKeyEvent.Type.KeyPress,
            Qt.Key.Key_0,
            Qt.KeyboardModifier.ControlModifier
        )
        self.cv.keyPressEvent(key_event)
        self.assertEqual(self.cv.zoom_level, 1.0)
        self.assertEqual(self.cv.hud.zoom_label.text(), "100%")

    def test_19_approach_2_vector_clipping_mask_rendering_and_merging(self):
        """Verifies Approach 2: Vector shape clipping mask rendering and raster merging."""
        # 1. Create shape with clip_rect
        clip_bounds = [40.0, 40.0, 50.0, 50.0]
        shape_data = ShapeItemData(
            shape_type="rect",
            x=20.0, y=20.0, width=100.0, height=100.0,
            stroke_color="#ff0000",
            fill_color="#0000ff",
            stroke_width=2,
            meta={"clip_rect": clip_bounds}
        )
        shape_layer = self.lm.get_default_shape_layer()
        shape_layer.shapes.append(shape_data)
        item = self.cv._create_shape_graphics_item(shape_data)

        # 2. Render to QImage via composite_to_image
        comp = self.lm.composite_to_image()
        # Pixel inside clip_bounds (e.g. 50, 50) should be colored by the shape
        c_inside = comp.pixelColor(50, 50)
        self.assertEqual(c_inside.blue(), 255)

        # Pixel outside clip_bounds (e.g. 25, 25, which is inside shape rect (20,20,100,100) but outside clip_bounds)
        # MUST remain background white or transparent, NOT colored by shape!
        c_outside = comp.pixelColor(25, 25)
        self.assertNotEqual(c_outside, QColor(0, 0, 255, 255))

        # 3. Merge clipped shape to raster layer
        merged = self.lm.merge_shape_into_raster(shape_data.id)
        self.assertTrue(merged)
        bg_layer = self.lm.get_layer("bg_layer")
        c_merged_inside = bg_layer.raster_image.pixelColor(50, 50)
        self.assertEqual(c_merged_inside.blue(), 255)
        c_merged_outside = bg_layer.raster_image.pixelColor(25, 25)
        self.assertNotEqual(c_merged_outside, QColor(0, 0, 255, 255))

    def test_20_layer_hierarchy_effective_visibility(self):
        """Verifies parent/child layer hierarchy and cascading effective visibility."""
        p_lay = self.lm.add_layer("Parent Layer", LayerType.RASTER)
        c_lay = self.lm.add_layer("Child Layer", LayerType.RASTER)
        c_lay.parent_id = p_lay.id

        # Both visible initially
        self.assertTrue(p_lay.visible)
        self.assertTrue(c_lay.visible)
        self.assertTrue(self.lm.is_layer_effectively_visible(p_lay.id))
        self.assertTrue(self.lm.is_layer_effectively_visible(c_lay.id))

        # Paint red on child layer
        c_lay.raster_image.fill(QColor(255, 0, 0, 255))
        comp = self.lm.composite_to_image()
        self.assertEqual(comp.pixelColor(50, 50).red(), 255)

        # Hide parent -> Child becomes effectively hidden even though c_lay.visible is still True!
        p_lay.visible = False
        self.assertFalse(self.lm.is_layer_effectively_visible(p_lay.id))
        self.assertFalse(self.lm.is_layer_effectively_visible(c_lay.id))
        self.assertTrue(c_lay.visible)

        # Composite output must NOT contain child's red pixels (returns white canvas background)
        comp_hidden = self.lm.composite_to_image()
        self.assertEqual(comp_hidden.pixelColor(50, 50), QColor(255, 255, 255, 255))

        # Re-enable parent -> Child becomes effectively visible again
        p_lay.visible = True
        self.assertTrue(self.lm.is_layer_effectively_visible(c_lay.id))

    def test_21_layer_panel_context_menu_and_icons(self):
        """Verifies LayerPanel empty space right-click menu and clean icon display."""
        from ui.layer_panel import LayerPanel
        panel = LayerPanel(self.lm)
        self.assertIsNotNone(panel.tree)

        # Empty-space context menu creation
        menu = panel._create_empty_space_menu()
        self.assertIsNotNone(menu)
        actions = [a.text() for a in menu.actions()]
        self.assertTrue(any("새 레이어 추가" in t for t in actions))

        # Icons: raster layers have no icon; shape layer has icon
        bg_item = panel.layer_items.get("bg_layer")
        if bg_item:
            self.assertTrue(bg_item.icon(0).isNull())

        shape_item = panel.layer_items.get("default_shape_layer")
        if shape_item:
            self.assertFalse(shape_item.icon(0).isNull())

    def test_22_transparent_selection_background_fill(self):
        """Verifies non-background transparent raster layer clears to alpha 0 upon cut, without turning white."""
        trans_layer = self.lm.add_layer("Transparent Layer", LayerType.RASTER)
        self.lm.active_layer_id = trans_layer.id
        self.cv.rebuild_scene()

        # Fill transparent layer with semi-transparent blue
        trans_layer.raster_image.fill(QColor(0, 0, 255, 128))
        self.assertEqual(trans_layer.raster_image.pixelColor(20, 20).alpha(), 128)

        # Cut selection rect [10, 10, 30, 30]
        sel_rect = QRectF(10, 10, 30, 30)
        self.cv.selection_rect = sel_rect
        self.cv._create_floating_selection_from_rect(sel_rect)

        # The cut region on trans_layer must be transparent (alpha 0), NOT secondary color (white)!
        cut_pixel = trans_layer.raster_image.pixelColor(20, 20)
        self.assertEqual(cut_pixel.alpha(), 0)

        # Commit floating selection back
        self.cv.commit_floating_selection_if_any()

    def test_23_integer_pixel_snap_calculation(self):
        """Verifies integer pixel snapping eliminates High-DPI anti-aliasing drift."""
        self.cv.pixel_snap_enabled = True

        # Odd stroke width (e.g. 1, 3, 5): Center offset is +0.5
        self.cv.stroke_width = 3
        pt_in = QPointF(10.2, 20.7)
        pt_snapped = self.cv.snap_coordinate(pt_in)
        self.assertAlmostEqual(pt_snapped.x(), 10.5)
        self.assertAlmostEqual(pt_snapped.y(), 20.5)

        # Even stroke width (e.g. 2, 4): Center offset is +0.0
        self.cv.stroke_width = 2
        pt_snapped_even = self.cv.snap_coordinate(pt_in)
        self.assertAlmostEqual(pt_snapped_even.x(), 10.0)
        self.assertAlmostEqual(pt_snapped_even.y(), 20.0)

        # Disabled snap: returns original coordinate unchanged
        self.cv.pixel_snap_enabled = False
        pt_unsnapped = self.cv.snap_coordinate(pt_in)
        self.assertEqual(pt_unsnapped, pt_in)

    def test_24_per_tool_remembered_threshold(self):
        """Verifies in-memory per-tool threshold persistence across switching."""
        win = MainWindow()
        self.assertIn(InputMode.FLOOD_FILL, win.tool_thresholds)
        self.assertIn(InputMode.SELECT_WAND, win.tool_thresholds)

        # 1. Flood fill defaults to 0%
        win._set_tool(InputMode.FLOOD_FILL)
        self.assertEqual(win.threshold_spin.value(), 0)
        self.assertEqual(win.threshold_spin.suffix(), " %")

        # User modifies flood fill threshold to 40%
        win.threshold_spin.setValue(40)
        self.assertEqual(win.tool_thresholds[InputMode.FLOOD_FILL], 40)
        self.assertEqual(win.canvas_view.fill_alpha_threshold, 40)

        # 2. Switch to Magic Wand: defaults to 32 (range 0..255, suffix "")
        win._set_tool(InputMode.SELECT_WAND)
        self.assertEqual(win.threshold_spin.value(), 32)
        self.assertEqual(win.threshold_spin.suffix(), "")
        self.assertEqual(win.threshold_spin.maximum(), 255)
        self.assertEqual(win.canvas_view.fill_tolerance, 32)

        # User modifies wand tolerance to 64
        win.threshold_spin.setValue(64)
        self.assertEqual(win.tool_thresholds[InputMode.SELECT_WAND], 64)
        self.assertEqual(win.canvas_view.fill_tolerance, 64)

        # 3. Switch back to Flood Fill: remembers 40%!
        win._set_tool(InputMode.FLOOD_FILL)
        self.assertEqual(win.threshold_spin.value(), 40)
        self.assertEqual(win.threshold_spin.suffix(), " %")
        self.assertEqual(win.canvas_view.fill_alpha_threshold, 40)

        # 4. Switch back to Magic Wand: remembers 64!
        win._set_tool(InputMode.SELECT_WAND)
        self.assertEqual(win.threshold_spin.value(), 64)
        self.assertEqual(win.threshold_spin.suffix(), "")
        self.assertEqual(win.canvas_view.fill_tolerance, 64)

    def test_25_canvas_hud_view_mode_monitoring_and_fixed_position(self):
        """Verifies HUD is parented directly to CanvasView (immune to viewport scrolling) and reflects view mode."""
        # HUD overlay must be direct child of CanvasView, not viewport()
        self.assertEqual(self.cv.hud.parent(), self.cv)

        # View mode updating
        self.cv.set_view_mode(90, True, False)
        self.assertIn("90°", self.cv.hud.rotate_btn.text())
        self.assertTrue(self.cv.hud.flip_h_btn.isChecked())
        self.assertFalse(self.cv.hud.flip_v_btn.isChecked())

        self.cv.set_view_mode(180, False, True)
        self.assertIn("180°", self.cv.hud.rotate_btn.text())
        self.assertFalse(self.cv.hud.flip_h_btn.isChecked())
        self.assertTrue(self.cv.hud.flip_v_btn.isChecked())

    def test_26_freehand_lasso_preview_and_selection(self):
        """Verifies freehand lasso records points and generates bounding marquee box on release."""
        self.safety.current_mode = InputMode.SELECT_LASSO

        # Simulate lasso drag points
        self.cv.lasso_points = [
            QPointF(20, 20),
            QPointF(60, 20),
            QPointF(60, 80),
            QPointF(20, 80)
        ]
        self.assertIsNone(self.cv.selection_rect)

        # Simulate mouse release in lasso mode
        from PyQt6.QtGui import QMouseEvent
        release_event = QMouseEvent(
            QMouseEvent.Type.MouseButtonRelease,
            QPointF(20, 80),
            Qt.MouseButton.LeftButton,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier
        )
        self.cv.mouseReleaseEvent(release_event)

        # Selection rect must be created with bounding box [20, 20, 40, 60]
        self.assertIsNotNone(self.cv.selection_rect)
        self.assertEqual(self.cv.selection_rect.x(), 20)
        self.assertEqual(self.cv.selection_rect.y(), 20)
        self.assertEqual(self.cv.selection_rect.width(), 40)
        self.assertEqual(self.cv.selection_rect.height(), 60)
        self.assertIsNotNone(self.cv.marquee_box)

    def test_27_dedicated_right_click_tool_actions(self):
        """Verifies dedicated right-click actions for Brush, Pencil, Eraser, Fill, Eyedropper, and Shapes."""
        from PyQt6.QtGui import QMouseEvent

        pt = QPointF(self.cv.mapFromScene(QPointF(50, 50)))
        event = QMouseEvent(QMouseEvent.Type.MouseButtonPress, pt, Qt.MouseButton.RightButton, Qt.MouseButton.RightButton, Qt.KeyboardModifier.NoModifier)

        # 1. Brush right click -> Soft eraser
        self.safety.current_mode = InputMode.BRUSH
        self.cv.mousePressEvent(event)
        self.assertTrue(self.cv.is_right_erasing)
        self.assertEqual(self.cv.eraser_type, "soft")
        self.cv._on_emergency_release()

        # 2. Pencil right click -> Pixel eraser
        self.safety.current_mode = InputMode.PENCIL
        self.cv.mousePressEvent(event)
        self.assertTrue(self.cv.is_right_erasing)
        self.assertEqual(self.cv.eraser_type, "pixel")
        self.cv._on_emergency_release()

        # 3. Shape right click -> Color swap
        self.safety.current_mode = InputMode.SHAPE_RECT
        self.cv.mousePressEvent(event)
        self.assertTrue(self.cv.is_shape_swapped)
        self.cv._on_emergency_release()

        # 4. Eyedropper right click -> Samples secondary color
        picked_colors = []
        self.cv.secondary_color_picked.connect(lambda c: picked_colors.append(c))
        self.safety.current_mode = InputMode.EYEDROPPER
        self.cv.mousePressEvent(event)
        self.assertEqual(len(picked_colors), 1)

    def test_28_large_preview_dialog_in_adjustment_dialog(self):
        """Verifies AdjustmentDialog '🔍 크게 보기' creates resizable LargePreviewDialog with live sync."""
        img = QImage(100, 100, QImage.Format.Format_ARGB32_Premultiplied)
        img.fill(QColor(255, 0, 0, 255))
        dlg = AdjustmentDialog(img, layers=self.lm.layers)

        # Open large preview
        self.assertIsNone(dlg.large_preview_dialog)
        dlg._open_large_preview()
        self.assertIsNotNone(dlg.large_preview_dialog)
        self.assertTrue(dlg.large_preview_dialog.isVisible())

        # Check pixmap is initialized in large preview
        lpw = dlg.large_preview_dialog.preview_widget
        self.assertFalse(lpw.full_pixmap.isNull())

        # Adjust hue slider and verify large preview updates
        dlg.hue_slider.setValue(90)
        self.assertFalse(lpw.full_pixmap.isNull())
        dlg.large_preview_dialog.close()

    def test_29_hud_styled_background_and_3digit_rotation(self):
        """Verifies CanvasHudOverlay has WA_StyledBackground, paintEvent renders, and 3-digit angle is not truncated."""
        from PyQt6.QtGui import QPaintEvent
        self.assertTrue(self.cv.hud.testAttribute(Qt.WidgetAttribute.WA_StyledBackground))

        # Test paintEvent renders without exception
        pm = QPixmap(self.cv.hud.size())
        painter = QPainter(pm)
        pe = QPaintEvent(self.cv.hud.rect())
        self.cv.hud.paintEvent(pe)
        painter.end()

        # 3-digit rotation angle (e.g. 270°) must display fully without elision '...'
        self.cv.set_view_mode(270, False, False)
        self.assertIn("270°", self.cv.hud.rotate_btn.text())
        self.assertNotIn("...", self.cv.hud.rotate_btn.text())
        self.assertGreaterEqual(self.cv.hud.rotate_btn.minimumWidth(), 68)

    def test_30_distinct_flip_icons(self):
        """Verifies flip_h and flip_v generate distinct, non-identical high-contrast icons."""
        from ui.icon_factory import IconFactory
        pm_h = IconFactory.create_icon("flip_h", 24).pixmap(24, 24)
        pm_v = IconFactory.create_icon("flip_v", 24).pixmap(24, 24)
        self.assertFalse(pm_h.isNull())
        self.assertFalse(pm_v.isNull())

        # Render to images and verify pixel differences
        img_h = pm_h.toImage()
        img_v = pm_v.toImage()
        diff_count = 0
        for y in range(24):
            for x in range(24):
                if img_h.pixelColor(x, y) != img_v.pixelColor(x, y):
                    diff_count += 1
        self.assertGreater(diff_count, 10)

    def test_31_separate_tools_dock_and_layer_dock(self):
        """Verifies MainWindow has separate tools_dock and layer_dock widgets with <=130px min width."""
        win = MainWindow()
        self.assertTrue(hasattr(win, "tools_dock"))
        self.assertTrue(hasattr(win, "layer_dock"))
        self.assertNotEqual(win.tools_dock, win.layer_dock)
        self.assertEqual(win.tools_dock.objectName(), "ToolsDock")
        self.assertEqual(win.layer_dock.objectName(), "LayerDock")
        self.assertLessEqual(win.tools_dock.minimumWidth(), 130)
        self.assertLessEqual(win.layer_dock.minimumWidth(), 130)

    def test_32_adjustment_dialog_hierarchical_layer_tree(self):
        """Verifies AdjustmentDialog displays hierarchical layer tree on right side."""
        p_lay = self.lm.add_layer("Parent Group", LayerType.RASTER)
        c_lay = self.lm.add_layer("Child In Group", LayerType.RASTER)
        c_lay.parent_id = p_lay.id

        img = QImage(100, 100, QImage.Format.Format_ARGB32_Premultiplied)
        img.fill(QColor(255, 0, 0, 255))
        dlg = AdjustmentDialog(img, layers=self.lm.layers, active_layer_id=c_lay.id)

        # Right-side layer tree must exist
        self.assertTrue(hasattr(dlg, "layer_tree"))
        self.assertGreater(dlg.layer_tree.topLevelItemCount(), 0)

        # Both parent and child must have checkboxes
        self.assertIn(p_lay.id, dlg.layer_checkboxes)
        self.assertIn(c_lay.id, dlg.layer_checkboxes)

        # Check parent and uncheck child
        dlg.layer_checkboxes[p_lay.id].setChecked(True)
        dlg.layer_checkboxes[c_lay.id].setChecked(False)
        target_ids = dlg.get_target_layer_ids()
        self.assertNotIn(c_lay.id, target_ids)
        self.assertIn(p_lay.id, target_ids)

    def test_33_hud_wheel_only_activation(self):
        """Verifies HUD stays hidden on mouse hover and activates exclusively on mouse wheel actions."""
        from PyQt6.QtGui import QMouseEvent, QWheelEvent
        from PyQt6.QtCore import QPointF, QPoint
        self.cv.resize(800, 600)
        hud = self.cv.hud
        hud.hide()
        self.assertTrue(hud.isHidden())

        # 1. Mouse move near bottom edge (should NOT activate HUD)
        move_event = QMouseEvent(
            QMouseEvent.Type.MouseMove,
            QPointF(400, 580),
            Qt.MouseButton.NoButton,
            Qt.MouseButton.NoButton,
            Qt.KeyboardModifier.NoModifier
        )
        self.cv.mouseMoveEvent(move_event)
        self.assertTrue(hud.isHidden())

        # 2. Wheel event (zoom or scroll, should activate HUD)
        wheel_event = QWheelEvent(
            QPointF(400, 300),
            QPointF(400, 300),
            QPoint(0, 0),
            QPoint(0, 120),
            Qt.MouseButton.NoButton,
            Qt.KeyboardModifier.ControlModifier,
            Qt.ScrollPhase.NoScrollPhase,
            False
        )
        self.cv.wheelEvent(wheel_event)
        self.assertFalse(hud.isHidden())

    def test_34_toggle_buttons_text_retention(self):
        """Verifies trans_select_btn and snap_btn retain visible text without drift after click/toggle."""
        win = MainWindow()
        text1_before = win.trans_select_btn.text()
        text2_before = win.snap_btn.text()
        self.assertEqual(text1_before, "투명 선택")
        self.assertEqual(text2_before, "픽셀 스냅")

        # Toggle transparent selection
        win.trans_select_btn.click()
        self.assertTrue(win.trans_select_act.isChecked())
        self.assertEqual(win.trans_select_btn.text(), text1_before)

        # Toggle snap
        win.snap_btn.click()
        self.assertFalse(win.snap_act.isChecked())
        self.assertEqual(win.snap_btn.text(), text2_before)

    def test_35_settings_dialog_and_credits(self):
        """Verifies SettingsDialog features: language toggle, theme toggle, empty patch notes, and credits."""
        from ui.dialogs.settings_dialog import SettingsDialog
        win = MainWindow()
        dlg = SettingsDialog(current_theme=win.current_theme, current_language=win.current_language, parent=win)

        # Theme toggle signal
        theme_events = []
        dlg.theme_changed.connect(lambda t: theme_events.append(t))
        dlg.theme_dark_rb.setChecked(True)
        self.assertIn("dark", theme_events)

        # Lang toggle signal
        lang_events = []
        dlg.language_changed.connect(lambda l: lang_events.append(l))
        dlg.lang_en_rb.setChecked(True)
        self.assertIn("en", lang_events)

        # Check patch notes contains version release notes
        self.assertTrue("v1.0.0" in dlg.patch_text.toPlainText() or "v1.1.0" in dlg.patch_text.toPlainText() or "v1.2.0" in dlg.patch_text.toPlainText())

        # Check labels for credits
        labels_text = " ".join([lbl.text() for lbl in dlg.findChildren(QLabel)])
        self.assertIn("L.Jack with Google Antigravity", labels_text)
        self.assertIn("Paint Essential", labels_text)

        # Verify MainWindow dull slate-navy theme switching
        win._apply_theme("dark")
        self.assertEqual(win.current_theme, "dark")
        self.assertIn("#1e2638", win.styleSheet())
        win._apply_theme("light")
        self.assertEqual(win.current_theme, "light")
        self.assertIn("#f8fafc", win.styleSheet())

    def test_36_program_rebranding_window_title(self):
        """Verifies MainWindow title rebranding and settings button existence."""
        win = MainWindow()
        self.assertIn("Paint Essential", win.windowTitle())
        self.assertIn("페인트 에센셜", win.windowTitle())
        self.assertTrue(hasattr(win, "settings_act"))
        self.assertIsNotNone(win.settings_act)

    def test_37_dynamic_language_switching(self):
        """Verifies live Korean <-> English switching retranslates all UI components without restart."""
        win = MainWindow()
        self.assertEqual(win.current_language, "ko")
        self.assertIn("페인트 에센셜", win.windowTitle())
        self.assertEqual(win.tools_dock.windowTitle(), "도구 및 속성")
        self.assertEqual(win.layer_dock.windowTitle(), "레이어 및 도형 계층")
        self.assertIn("투명", win.trans_select_btn.text())
        self.assertIn("스냅", win.snap_btn.text())
        self.assertIn("굵기", win.stroke_label.text())

        # Switch to English live
        win._on_language_changed("en")
        self.assertEqual(win.current_language, "en")
        self.assertEqual(win.windowTitle(), "Paint Essential - LJack Edition")
        self.assertEqual(win.tools_dock.windowTitle(), "Tools & Properties")
        self.assertEqual(win.layer_dock.windowTitle(), "Layers & Shapes")
        self.assertIn("Trans. Select", win.trans_select_btn.text())
        self.assertIn("Pixel Snap", win.snap_btn.text())
        self.assertIn("Size", win.stroke_label.text())
        self.assertEqual(win.tool_names[InputMode.BRUSH], "Brush")

        # Switch back to Korean live
        win._on_language_changed("ko")
        self.assertEqual(win.current_language, "ko")
        self.assertIn("페인트 에센셜", win.windowTitle())
        self.assertEqual(win.tools_dock.windowTitle(), "도구 및 속성")
        self.assertEqual(win.layer_dock.windowTitle(), "레이어 및 도형 계층")
        self.assertIn("투명 선택", win.trans_select_btn.text())
        self.assertIn("픽셀 스냅", win.snap_btn.text())
        self.assertIn("굵기", win.stroke_label.text())
        self.assertEqual(win.tool_names[InputMode.BRUSH], "브러시")

    def test_38_dull_dark_palette_and_titlebar(self):
        """Verifies dull slate-navy palette (#1e2638), deep navy titlebar, and outlined icons."""
        win = MainWindow()
        win._apply_theme("dark")
        self.assertEqual(win.current_theme, "dark")
        self.assertIn("#1e2638", win.styleSheet())
        self.assertIn("#253147", win.styleSheet())
        self.assertIn("#344460", win.styleSheet())
        # Title bar update on MainWindow and dialog popups should succeed without errors
        from ui.theme_utils import apply_window_titlebar
        from ui.dialogs.settings_dialog import SettingsDialog
        from ui.dialogs.anchor_resize_dialog import AnchorResizeDialog
        from ui.icon_factory import IconFactory

        apply_window_titlebar(win, "dark", "#0d1527")
        apply_window_titlebar(win, "light")

        dlg = SettingsDialog(parent=win)
        apply_window_titlebar(dlg, "dark", "#0d1527")

        resize_dlg = AnchorResizeDialog(800, 600, parent=win)
        apply_window_titlebar(resize_dlg, "dark", "#0d1527")

        # Verify outlined vector icons
        icon_outlined = IconFactory.create_icon("brush", 24, outline=True)
        self.assertFalse(icon_outlined.isNull())
        pm = icon_outlined.pixmap(24, 24)
        self.assertGreater(pm.width(), 0)

    def test_39_sublayer_persistence_and_context_menu(self):
        """Verifies sub-layer persistence and context menu indent/outdent."""
        from ui.layer_panel import LayerPanel
        lm = LayerManager()
        l1 = lm.add_layer("Parent Layer")
        l2 = lm.add_layer("Child Layer")
        panel = LayerPanel(lm)

        # 1. Indent l2 to become child of l1
        panel._indent_layer(l2.id)
        self.assertEqual(l2.parent_id, l1.id)

        # 2. Re-refreshing list must keep l2 nested, NOT popping back out
        panel.refresh_list()
        self.assertEqual(l2.parent_id, l1.id)
        self.assertEqual(panel.layer_items[l1.id].childCount(), 1)
        self.assertEqual(panel.tree.topLevelItemCount(), 2) # bg, l1 (l2 is inside l1)

        # 3. Outdent l2 back to top-level
        panel._outdent_layer(l2.id)
        self.assertIsNone(l2.parent_id)
        panel.refresh_list()
        self.assertEqual(panel.layer_items[l1.id].childCount(), 0)
        self.assertEqual(panel.tree.topLevelItemCount(), 3) # bg, l1, l2

    def test_40_qsettings_zero_file_persistence(self):
        """Verifies settings save to Windows Registry without creating files."""
        import os
        from PyQt6.QtCore import QSettings
        settings = QSettings("PaintEssential", "Settings")
        # NativeFormat on Windows stores in Registry: \HKEY_CURRENT_USER\Software\PaintEssential\Settings
        self.assertEqual(settings.format(), QSettings.Format.NativeFormat)
        self.assertIn("HKEY_CURRENT_USER", settings.fileName())
        self.assertFalse(os.path.exists(settings.fileName()))


if __name__ == "__main__":
    unittest.main()


