"""
Paint Pro - Hierarchical Layer Panel (Tree View)
LJack Protocol Pillar 5: Interaction Invariance & Multi-view Synchronization
Features expandable categorized shape hierarchy, drag-and-drop reordering,
auto-numbering layer creation, and right-click raster merge context menu.
"""
from typing import Optional, Dict
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTreeWidget, QTreeWidgetItem,
    QPushButton, QMessageBox, QMenu, QAbstractItemView, QTabBar
)
from PyQt6.QtCore import pyqtSignal, Qt, QPoint
from PyQt6.QtGui import QColor
from core.layer_manager import LayerManager, LayerType, Layer
from core.i18n import I18N


class LayerTreeWidget(QTreeWidget):
    """QTreeWidget subclass emitting hierarchy_dropped on internal drag-and-drop completion."""
    hierarchy_dropped = pyqtSignal()

    def dropEvent(self, event):
        super().dropEvent(event)
        self.hierarchy_dropped.emit()


class LayerPanel(QWidget):
    layer_changed = pyqtSignal()
    shape_selected = pyqtSignal(str)   # Emits shape_id when user clicks shape in tree
    shape_merge_requested = pyqtSignal(str) # Emits shape_id to merge to raster
    shape_delete_requested = pyqtSignal(str)

    def __init__(self, layer_manager: LayerManager, parent=None, history_manager=None):
        super().__init__(parent)
        self.layer_manager = layer_manager
        self.history_manager = history_manager
        self.layer_items: Dict[str, QTreeWidgetItem] = {}
        self.current_filter = "all"
        self._init_ui()
        self.refresh_list()

    @property
    def current_history_manager(self):
        if getattr(self, "history_manager", None) is not None:
            return self.history_manager
        p = self.parent()
        if p is not None:
            if hasattr(p, "history_manager") and p.history_manager is not None:
                return p.history_manager
            if hasattr(p, "active_doc") and p.active_doc and getattr(p.active_doc, "history_manager", None):
                return p.active_doc.history_manager
        return None

    def _capture_layer_state(self):
        """Captures a snapshot of layers list, active_layer_id, and per-layer properties."""
        return {
            "layers": list(self.layer_manager.layers),
            "active_layer_id": self.layer_manager.active_layer_id,
            "props": {
                l.id: {
                    "parent_id": l.parent_id,
                    "visible": l.visible,
                    "opacity": l.opacity,
                    "name": l.name,
                }
                for l in self.layer_manager.layers
            }
        }

    def _restore_layer_state(self, state):
        """Restores the snapshot state and refreshes tree and canvas."""
        self.layer_manager.layers = list(state["layers"])
        self.layer_manager.active_layer_id = state["active_layer_id"]
        for l in self.layer_manager.layers:
            if l.id in state["props"]:
                p = state["props"][l.id]
                l.parent_id = p["parent_id"]
                l.visible = p["visible"]
                l.opacity = p["opacity"]
                l.name = p["name"]
        self.refresh_list()
        self.layer_changed.emit()

    def _record_layer_history(self, desc: str, before_state, after_state):
        hm = self.current_history_manager
        if hm is not None:
            hm.record_step(
                desc,
                lambda: self._restore_layer_state(before_state),
                lambda: self._restore_layer_state(after_state),
            )

    def _init_ui(self):
        self.setMinimumWidth(130)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        # 3-Tab Filter Bar: ALL / 레이어 / 도형
        self.filter_tabs = QTabBar(self)
        self.filter_tabs.setObjectName("LayerFilterTabs")
        self.filter_tabs.setExpanding(True)
        self.filter_tabs.setDocumentMode(True)
        self.filter_tabs.addTab("ALL")
        self.filter_tabs.addTab("레이어")
        self.filter_tabs.addTab("도형")
        self.filter_tabs.currentChanged.connect(self._on_filter_tab_changed)
        layout.addWidget(self.filter_tabs)

        # LayerTreeWidget with drag-and-drop hierarchy persistence
        self.tree = LayerTreeWidget()
        self.tree.setHeaderHidden(True)
        self.tree.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.tree.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self._on_context_menu)
        self.tree.itemClicked.connect(self._on_item_clicked)
        self.tree.hierarchy_dropped.connect(self._sync_hierarchy_from_tree)
        self.tree.model().rowsMoved.connect(lambda *args: self._sync_hierarchy_from_tree())

        layout.addWidget(self.tree)

        # Compact Toolbar Buttons (Fits snugly in 130px minimum width)
        btn_layout = QHBoxLayout()
        btn_layout.setContentsMargins(0, 2, 0, 0)
        btn_layout.setSpacing(2)

        self.add_btn = QPushButton("+ 추가")
        self.add_btn.setToolTip("새 레이어 추가")
        self.del_btn = QPushButton("- 삭제")
        self.del_btn.setToolTip("선택 레이어/도형 삭제")
        self.up_btn = QPushButton("▲")
        self.up_btn.setToolTip("위로 이동")
        self.down_btn = QPushButton("▼")
        self.down_btn.setToolTip("아래로 이동")

        for btn in (self.add_btn, self.del_btn, self.up_btn, self.down_btn):
            btn.setObjectName("LayerPanelBtn")

        self.add_btn.clicked.connect(self._add_layer)
        self.del_btn.clicked.connect(self._del_layer)
        self.up_btn.clicked.connect(self._move_up)
        self.down_btn.clicked.connect(self._move_down)

        self.retranslate_ui()

    def _on_filter_tab_changed(self, idx: int):
        if idx == 0:
            self.current_filter = "all"
        elif idx == 1:
            self.current_filter = "layer"
        elif idx == 2:
            self.current_filter = "shape"
        self.refresh_list()

    def retranslate_ui(self):
        """Updates layer panel texts according to current active language."""
        if hasattr(self, "filter_tabs"):
            self.filter_tabs.setTabText(0, I18N.tr("layer_tab_all"))
            self.filter_tabs.setTabText(1, I18N.tr("layer_tab_layers"))
            self.filter_tabs.setTabText(2, I18N.tr("layer_tab_shapes"))
            self.filter_tabs.setTabToolTip(0, "모든 레이어 표시")
            self.filter_tabs.setTabToolTip(1, "일반 레이어만 표시")
            self.filter_tabs.setTabToolTip(2, "도형 레이어만 표시")

        self.add_btn.setText(I18N.tr("layer_add"))
        self.add_btn.setToolTip(I18N.tr("layer_add_tip"))
        self.del_btn.setText(I18N.tr("layer_del"))
        self.del_btn.setToolTip(I18N.tr("layer_del_tip"))
        self.up_btn.setToolTip(I18N.tr("layer_up_tip"))
        self.down_btn.setToolTip(I18N.tr("layer_down_tip"))
        self.refresh_list()

    def refresh_list(self):
        self.tree.blockSignals(True)
        self.tree.clear()

        self.layer_items = {}

        filter_mode = getattr(self, "current_filter", "all")
        if filter_mode == "layer":
            target_layers = [l for l in self.layer_manager.layers if l.layer_type == LayerType.RASTER]
        elif filter_mode == "shape":
            target_layers = [l for l in self.layer_manager.layers if l.layer_type == LayerType.SHAPE]
        else:
            target_layers = list(self.layer_manager.layers)

        target_ids = {l.id for l in target_layers}
        root_layers = [l for l in target_layers if not l.parent_id or l.parent_id not in target_ids]

        def create_item(layer: Layer, parent_container) -> QTreeWidgetItem:
            item = QTreeWidgetItem(parent_container)
            item.setData(0, Qt.ItemDataRole.UserRole, {
                "type": "layer",
                "id": layer.id,
                "layer_type": layer.layer_type.value
            })

            # Check parent chain visibility
            parent_visible = True
            if layer.parent_id:
                parent_visible = self.layer_manager.is_layer_effectively_visible(layer.parent_id)

            # Checkbox for visibility
            item.setCheckState(0, Qt.CheckState.Checked if layer.visible else Qt.CheckState.Unchecked)

            if not parent_visible:
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEnabled)
                item.setForeground(0, QColor(140, 145, 155))
            else:
                item.setFlags(item.flags() | Qt.ItemFlag.ItemIsEnabled)

            from ui.icon_factory import IconFactory
            if layer.layer_type == LayerType.SHAPE:
                s_type = layer.shapes[0].shape_type if layer.shapes else "rect"
                item.setIcon(0, IconFactory.create_icon(f"shape_{s_type}", 16))
                badge = "[도형]"
            else:
                badge = "[레이어]" if layer.id != "bg_layer" else ""

            item.setText(0, f"{badge} {layer.name}".strip())

            if layer.id == self.layer_manager.active_layer_id:
                item.setSelected(True)

            self.layer_items[layer.id] = item
            return item

        for layer in reversed(root_layers):
            root_item = create_item(layer, self.tree)
            self.tree.addTopLevelItem(root_item)
            self._add_child_layers(layer.id, root_item, create_item, target_ids)

        self.tree.blockSignals(False)

    def _add_child_layers(self, parent_id: str, parent_item: QTreeWidgetItem, create_item_fn, allowed_ids):
        children = [l for l in self.layer_manager.layers if l.parent_id == parent_id and l.id in allowed_ids]
        for child in reversed(children):
            child_item = create_item_fn(child, parent_item)
            parent_item.addChild(child_item)
            parent_item.setExpanded(True)
            self._add_child_layers(child.id, child_item, create_item_fn, allowed_ids)

    def _on_item_clicked(self, item: QTreeWidgetItem, column: int):
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if not data:
            return

        layer_id = data.get("id")
        if not layer_id:
            return
        layer = self.layer_manager.get_layer(layer_id)
        if not layer:
            return

        is_checked = (item.checkState(0) == Qt.CheckState.Checked)
        if layer.visible != is_checked:
            self.layer_manager.set_visible(layer_id, is_checked)
            self.refresh_list()
            self.layer_changed.emit()
        else:
            self.layer_manager.set_active_layer(layer_id)
            if layer.layer_type == LayerType.SHAPE:
                self.shape_selected.emit(layer.id)
            self.layer_changed.emit()

    def _create_empty_space_menu(self) -> QMenu:
        menu = QMenu(self)
        menu.addAction("➕ 새 레이어 추가")
        return menu

    def _on_context_menu(self, pos: QPoint):
        item = self.tree.itemAt(pos)
        if not item:
            menu = self._create_empty_space_menu()
            chosen = menu.exec(self.tree.mapToGlobal(pos))
            if chosen and chosen.text() == "➕ 새 레이어 추가":
                self._add_layer()
            return

        data = item.data(0, Qt.ItemDataRole.UserRole)
        if not data:
            return

        layer_id = data.get("id")
        if not layer_id:
            return
        layer = self.layer_manager.get_layer(layer_id)
        if not layer:
            return

        menu = QMenu()

        if layer.layer_type == LayerType.SHAPE:
            merge_act = menu.addAction(I18N.tr("menu_merge_raster"))
            front_act = menu.addAction(I18N.tr("menu_bring_front"))
            back_act = menu.addAction(I18N.tr("menu_send_back"))
            menu.addSeparator()
            del_act = menu.addAction(I18N.tr("menu_del_shape"))

            chosen = menu.exec(self.tree.mapToGlobal(pos))
            if chosen == merge_act:
                self.shape_merge_requested.emit(layer_id)
            elif chosen == front_act:
                self.layer_manager.bring_shape_to_front(layer_id)
                self.refresh_list()
                self.layer_changed.emit()
            elif chosen == back_act:
                self.layer_manager.send_shape_to_back(layer_id)
                self.refresh_list()
                self.layer_changed.emit()
            elif chosen == del_act:
                self._del_specific_layer(layer_id)

        elif layer.layer_type == LayerType.RASTER:
            add_act = menu.addAction(I18N.tr("layer_add"))
            indent_act = None
            outdent_act = None
            if layer.parent_id:
                outdent_act = menu.addAction(I18N.tr("layer_outdent"))
            else:
                indent_act = menu.addAction(I18N.tr("layer_indent"))
            menu.addSeparator()
            del_act = menu.addAction(I18N.tr("layer_del"))

            chosen = menu.exec(self.tree.mapToGlobal(pos))
            if chosen == add_act:
                self._add_layer()
            elif chosen == indent_act and indent_act:
                self._indent_layer(layer_id)
            elif chosen == outdent_act and outdent_act:
                self._outdent_layer(layer_id)
            elif chosen == del_act:
                self._del_specific_layer(layer_id)

    def _indent_layer(self, layer_id: str):
        """Sets this layer as a sub-layer of the visually adjacent layer above it."""
        layer = self.layer_manager.get_layer(layer_id)
        if not layer or layer.parent_id:
            return
        root_layers = [l for l in self.layer_manager.layers if not l.parent_id]
        if layer in root_layers:
            idx = root_layers.index(layer)
            if idx + 1 < len(root_layers):
                parent_candidate = root_layers[idx + 1]
            elif idx - 1 >= 0:
                parent_candidate = root_layers[idx - 1]
            else:
                return
            before = self._capture_layer_state()
            layer.parent_id = parent_candidate.id
            self.refresh_list()
            self.layer_changed.emit()
            after = self._capture_layer_state()
            self._record_layer_history("레이어 구조 변경 (하위 계층화)", before, after)

    def _outdent_layer(self, layer_id: str):
        """Promotes this sub-layer to the root level."""
        layer = self.layer_manager.get_layer(layer_id)
        if not layer or not layer.parent_id:
            return
        before = self._capture_layer_state()
        layer.parent_id = None
        self.refresh_list()
        self.layer_changed.emit()
        after = self._capture_layer_state()
        self._record_layer_history("레이어 구조 변경 (상위 승격)", before, after)

    def _sync_hierarchy_from_tree(self):
        """Synchronizes LayerManager hierarchy and ordering after tree drag-and-drop."""
        before = self._capture_layer_state()
        new_layers_order = []

        def walk_item(item: QTreeWidgetItem, p_id: Optional[str]):
            d = item.data(0, Qt.ItemDataRole.UserRole)
            if d and d.get("type") == "layer":
                lay_id = d["id"]
                lay = self.layer_manager.get_layer(lay_id)
                if lay:
                    lay.parent_id = p_id
                    new_layers_order.append(lay)
                    for c_idx in reversed(range(item.childCount())):
                        c_item = item.child(c_idx)
                        walk_item(c_item, lay_id)

        top_count = self.tree.topLevelItemCount()
        for i in reversed(range(top_count)):
            t_item = self.tree.topLevelItem(i)
            walk_item(t_item, None)

        for lay in self.layer_manager.layers:
            if lay not in new_layers_order:
                new_layers_order.append(lay)

        self.layer_manager.layers = new_layers_order
        self.refresh_list()
        self.layer_changed.emit()
        after = self._capture_layer_state()
        if before["layers"] != after["layers"] or before["props"] != after["props"]:
            self._record_layer_history("레이어 구조 변경 (트리 이동)", before, after)

    def _on_rows_moved(self, parent, start, end, destination, row):
        self._sync_hierarchy_from_tree()

    def _add_layer(self):
        # Requirement: Default name is '새 레이어', auto-incremented if duplicate
        before = self._capture_layer_state()
        auto_name = self.layer_manager.generate_new_layer_name("새 레이어")
        self.layer_manager.add_layer(auto_name, LayerType.RASTER)
        self.refresh_list()
        self.layer_changed.emit()
        after = self._capture_layer_state()
        self._record_layer_history("새 레이어 추가", before, after)

    def _del_specific_layer(self, layer_id: str):
        layer = self.layer_manager.get_layer(layer_id)
        if not layer:
            return

        if layer.layer_type == LayerType.SHAPE:
            before = self._capture_layer_state()
            self.layer_manager.remove_layer(layer_id)
            self.shape_delete_requested.emit(layer_id)
            self.refresh_list()
            self.layer_changed.emit()
            after = self._capture_layer_state()
            self._record_layer_history("도형 삭제", before, after)
            return

        raster_layers = [l for l in self.layer_manager.layers if l.layer_type == LayerType.RASTER]
        if len(raster_layers) <= 1 and layer in raster_layers:
            QMessageBox.warning(self, "삭제 불가", I18N.tr("warn_min_one_layer"))
            return

        before = self._capture_layer_state()
        if not self.layer_manager.remove_layer(layer_id):
            QMessageBox.warning(self, "삭제 불가", "최소 1개 이상의 레이어가 유지되어야 합니다.")
            return

        self.refresh_list()
        self.layer_changed.emit()
        after = self._capture_layer_state()
        self._record_layer_history("레이어 삭제", before, after)

    def _del_layer(self):
        cur_item = self.tree.currentItem()
        if cur_item:
            d = cur_item.data(0, Qt.ItemDataRole.UserRole)
            if d and "id" in d:
                self._del_specific_layer(d["id"])
                return
        if self.layer_manager.active_layer_id:
            self._del_specific_layer(self.layer_manager.active_layer_id)

    def _move_up(self):
        cur_item = self.tree.currentItem()
        if not cur_item:
            return
        d = cur_item.data(0, Qt.ItemDataRole.UserRole)
        if not d or "id" not in d:
            return
        layer = self.layer_manager.get_layer(d["id"])
        if not layer or layer not in self.layer_manager.layers:
            return
        idx = self.layer_manager.layers.index(layer)
        if idx < len(self.layer_manager.layers) - 1:
            before = self._capture_layer_state()
            self.layer_manager.move_layer(idx, idx + 1)
            self.refresh_list()
            self.layer_changed.emit()
            after = self._capture_layer_state()
            self._record_layer_history("레이어 순서 변경 (위로)", before, after)

    def _move_down(self):
        cur_item = self.tree.currentItem()
        if not cur_item:
            return
        d = cur_item.data(0, Qt.ItemDataRole.UserRole)
        if not d or "id" not in d:
            return
        layer = self.layer_manager.get_layer(d["id"])
        if not layer or layer not in self.layer_manager.layers:
            return
        idx = self.layer_manager.layers.index(layer)
        if idx > 0:
            before = self._capture_layer_state()
            self.layer_manager.move_layer(idx, idx - 1)
            self.refresh_list()
            self.layer_changed.emit()
            after = self._capture_layer_state()
            self._record_layer_history("레이어 순서 변경 (아래로)", before, after)

    def select_layer(self, layer_id: str):
        if layer_id in self.layer_items:
            item = self.layer_items[layer_id]
            self.tree.blockSignals(True)
            self.tree.setCurrentItem(item)
            item.setSelected(True)
            self.tree.scrollToItem(item)
            self.tree.blockSignals(False)
