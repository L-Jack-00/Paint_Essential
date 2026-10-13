"""
Paint Essential - Layer Architecture Reorganization & 3-Tab Filter Test Suite
Tests:
1. Individual shape layers created dynamically without pre-baked default shape layer folder.
2. LayerPanel 3-tab filter bar (ALL / 레이어 / 도형).
3. Filtering behaviour: 'ALL' shows all, '레이어' shows only raster, '도형' shows only shape layers.
4. Individual shape layer visibility, deletion, and reordering.
"""
import unittest
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QPointF
from PyQt6.QtGui import QColor

app = QApplication.instance() or QApplication([])

from core.layer_manager import LayerManager, LayerType, ShapeItemData
from core.input_safety import InputMode
from ui.main_window import MainWindow
from ui.layer_panel import LayerPanel


class TestLayerReorganization(unittest.TestCase):
    def setUp(self):
        self.window = MainWindow()
        self.lm = self.window.layer_manager
        self.panel = self.window.layer_panel
        self.cv = self.window.canvas_view

    def tearDown(self):
        self.window.close()

    def test_01_initial_state_clean_raster_only(self):
        """Initial state starts with only background raster layer, no pre-baked empty shape folder."""
        self.assertEqual(len(self.lm.layers), 1)
        self.assertEqual(self.lm.layers[0].layer_type, LayerType.RASTER)
        self.assertEqual(self.lm.layers[0].name, "배경 레이어")
        self.assertEqual(self.panel.filter_tabs.count(), 3)
        self.assertEqual(self.panel.filter_tabs.tabText(0), "ALL")
        self.assertEqual(self.panel.filter_tabs.tabText(1), "레이어")
        self.assertEqual(self.panel.filter_tabs.tabText(2), "도형")

    def test_02_individual_shape_layer_creation_and_naming(self):
        """Creating shapes spawns independent first-class shape layers with sequential names."""
        # Insert rectangle
        self.cv._commit_shape(QPointF(10, 10), QPointF(50, 50), InputMode.SHAPE_RECT)
        self.assertEqual(len(self.lm.layers), 2)
        shape_l1 = self.lm.layers[1]
        self.assertEqual(shape_l1.layer_type, LayerType.SHAPE)
        self.assertEqual(shape_l1.name, "직사각형 1")
        self.assertEqual(len(shape_l1.shapes), 1)

        # Insert arrow
        self.cv._commit_shape(QPointF(20, 20), QPointF(80, 80), InputMode.SHAPE_ARROW)
        self.assertEqual(len(self.lm.layers), 3)
        shape_l2 = self.lm.layers[2]
        self.assertEqual(shape_l2.layer_type, LayerType.SHAPE)
        self.assertEqual(shape_l2.name, "화살표 1")

        # Insert another rectangle
        self.cv._commit_shape(QPointF(30, 30), QPointF(90, 90), InputMode.SHAPE_RECT)
        self.assertEqual(len(self.lm.layers), 4)
        shape_l3 = self.lm.layers[3]
        self.assertEqual(shape_l3.name, "직사각형 2")

    def test_03_layer_panel_three_tab_filtering(self):
        """Tests that ALL / 레이어 / 도형 tabs accurately filter the displayed tree items."""
        # Add 1 additional raster layer
        self.lm.add_layer("래스터 1", LayerType.RASTER)
        # Add 2 shapes
        self.cv._commit_shape(QPointF(10, 10), QPointF(50, 50), InputMode.SHAPE_RECT)
        self.cv._commit_shape(QPointF(20, 20), QPointF(60, 60), InputMode.SHAPE_ELLIPSE)

        # Total layers: bg_layer (raster), 래스터 1 (raster), 직사각형 1 (shape), 타원 1 (shape) -> 4 layers
        self.assertEqual(len(self.lm.layers), 4)

        # Tab 0: ALL -> all 4 layers
        self.panel.filter_tabs.setCurrentIndex(0)
        self.assertEqual(self.panel.current_filter, "all")
        self.assertEqual(self.panel.tree.topLevelItemCount(), 4)

        # Tab 1: 레이어 -> only 2 raster layers
        self.panel.filter_tabs.setCurrentIndex(1)
        self.assertEqual(self.panel.current_filter, "layer")
        self.assertEqual(self.panel.tree.topLevelItemCount(), 2)
        for i in range(self.panel.tree.topLevelItemCount()):
            item = self.panel.tree.topLevelItem(i)
            data = item.data(0, 0x0100)
            layer_id = data["id"] if isinstance(data, dict) else data
            self.assertEqual(self.lm.get_layer(layer_id).layer_type, LayerType.RASTER)

        # Tab 2: 도형 -> only 2 shape layers
        self.panel.filter_tabs.setCurrentIndex(2)
        self.assertEqual(self.panel.current_filter, "shape")
        self.assertEqual(self.panel.tree.topLevelItemCount(), 2)
        for i in range(self.panel.tree.topLevelItemCount()):
            item = self.panel.tree.topLevelItem(i)
            data = item.data(0, 0x0100)
            layer_id = data["id"] if isinstance(data, dict) else data
            self.assertEqual(self.lm.get_layer(layer_id).layer_type, LayerType.SHAPE)

    def test_04_individual_shape_layer_visibility_toggle(self):
        """Toggling an individual shape layer's eye visibility toggles only its graphics item."""
        self.cv._commit_shape(QPointF(10, 10), QPointF(50, 50), InputMode.SHAPE_RECT)
        shape_layer = self.lm.layers[1]
        shape_id = shape_layer.shapes[0].id
        self.assertTrue(self.cv.shape_items[shape_id].isVisible())

        # Toggle layer visibility off
        shape_layer.visible = False
        self.cv.rebuild_scene()
        self.assertFalse(self.cv.shape_items[shape_id].isVisible())

        # Toggle layer visibility on
        shape_layer.visible = True
        self.cv.rebuild_scene()
        self.assertTrue(self.cv.shape_items[shape_id].isVisible())

    def test_05_individual_shape_layer_reordering_and_deletion(self):
        """Moving and deleting independent shape layers works cleanly through LayerPanel."""
        self.cv._commit_shape(QPointF(10, 10), QPointF(50, 50), InputMode.SHAPE_RECT)
        self.cv._commit_shape(QPointF(20, 20), QPointF(60, 60), InputMode.SHAPE_ELLIPSE)
        rect_layer = self.lm.layers[1]
        ellipse_layer = self.lm.layers[2]

        # Initial order: bg (0), rect (1), ellipse (2)
        self.assertEqual(self.lm.layers[1].id, rect_layer.id)
        self.assertEqual(self.lm.layers[2].id, ellipse_layer.id)

        # Move ellipse down (index 2 -> index 1)
        self.panel.tree.setCurrentItem(self.panel.layer_items[ellipse_layer.id])
        self.panel._move_down() # Move down in panel moves lower in stack (earlier index)
        self.assertEqual(self.lm.layers[1].id, ellipse_layer.id)
        self.assertEqual(self.lm.layers[2].id, rect_layer.id)

        # Delete ellipse shape layer
        self.panel._del_specific_layer(ellipse_layer.id)
        self.assertEqual(len(self.lm.layers), 2)
        self.assertIsNone(self.lm.get_layer(ellipse_layer.id))
        self.assertNotIn(ellipse_layer.shapes[0].id, self.cv.shape_items)


if __name__ == "__main__":
    unittest.main()
