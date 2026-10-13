"""
Paint Pro - Advanced Color & Tone Adjustment Dialog
LJack Protocol: Resizable interactive dialog, zoomable live preview with middle-click pan,
multi-layer checklist selection, empty-state text ("아무것도 선택되지 않음"),
fixed-width slider labels (no layout jumping at 100%), and selection-confined masking.
"""
from typing import Optional, List, Dict
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QSlider,
    QPushButton, QGroupBox, QGridLayout, QCheckBox, QDialogButtonBox,
    QScrollArea, QToolButton, QTreeWidget, QTreeWidgetItem
)
from PyQt6.QtCore import Qt, QRect, QPoint, QEvent
from PyQt6.QtGui import QImage, QPixmap, QPainter, QColor
from core.image_processor import ImageProcessor


class ZoomablePreviewWidget(QScrollArea):
    """
    Zoomable preview widget allowing user to inspect color adjustment details.
    Supports Ctrl+Wheel zooming, Middle-click drag panning, and renders centered
    white text '아무것도 선택되지 않음' when no graphics or layers are selected.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.zoom_level = 1.0
        self.full_pixmap = QPixmap()

        self.img_label = QLabel()
        self.img_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setWidget(self.img_label)
        self.setWidgetResizable(True)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setStyleSheet("background-color: #1e293b; border-radius: 4px;")

        # Middle-click drag panning support
        self.is_panning = False
        self.pan_start_pos = QPoint()
        self.pan_start_h = 0
        self.pan_start_v = 0
        self.viewport().installEventFilter(self)

    def set_pixmap(self, pix: Optional[QPixmap]):
        if pix is None or pix.isNull():
            self.full_pixmap = QPixmap()
            self.img_label.setPixmap(QPixmap())
            self.img_label.setText("아무것도 선택되지 않음")
            self.img_label.setStyleSheet("color: #ffffff; font-size: 14px; font-weight: bold; background-color: #1e293b;")
        else:
            self.full_pixmap = pix
            self.img_label.setText("")
            self.img_label.setStyleSheet("background-color: #1e293b;")
            self._refresh()

    def set_zoom(self, zoom: float):
        self.zoom_level = max(0.2, min(8.0, zoom))
        self._refresh()

    def zoom_in(self):
        self.set_zoom(self.zoom_level * 1.25)

    def zoom_out(self):
        self.set_zoom(self.zoom_level / 1.25)

    def reset_zoom(self):
        self.set_zoom(1.0)

    def eventFilter(self, obj, event):
        if obj == self.viewport():
            if event.type() == QEvent.Type.MouseButtonPress and event.button() == Qt.MouseButton.MiddleButton:
                self.is_panning = True
                self.pan_start_pos = event.pos()
                self.pan_start_h = self.horizontalScrollBar().value()
                self.pan_start_v = self.verticalScrollBar().value()
                self.setCursor(Qt.CursorShape.ClosedHandCursor)
                return True
            elif event.type() == QEvent.Type.MouseMove and self.is_panning:
                delta = event.pos() - self.pan_start_pos
                self.horizontalScrollBar().setValue(self.pan_start_h - delta.x())
                self.verticalScrollBar().setValue(self.pan_start_v - delta.y())
                return True
            elif event.type() == QEvent.Type.MouseButtonRelease and event.button() == Qt.MouseButton.MiddleButton:
                if self.is_panning:
                    self.is_panning = False
                    self.setCursor(Qt.CursorShape.ArrowCursor)
                    return True
        return super().eventFilter(obj, event)

    def wheelEvent(self, event):
        if event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            delta = event.angleDelta().y()
            if delta > 0:
                self.zoom_in()
            else:
                self.zoom_out()
            event.accept()
            return
        super().wheelEvent(event)

    def _refresh(self):
        if self.full_pixmap.isNull():
            self.img_label.setPixmap(QPixmap())
            self.img_label.setText("아무것도 선택되지 않음")
            self.img_label.setStyleSheet("color: #ffffff; font-size: 14px; font-weight: bold; background-color: #1e293b;")
            return

        target_w = max(10, int(self.full_pixmap.width() * self.zoom_level))
        target_h = max(10, int(self.full_pixmap.height() * self.zoom_level))
        scaled = self.full_pixmap.scaled(
            target_w, target_h,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation if self.zoom_level < 2.0 else Qt.TransformationMode.FastTransformation
        )
        self.img_label.setPixmap(scaled)


class LargePreviewDialog(QDialog):
    """
    Standalone resizable dialog displaying a large live preview of color/tone adjustments.
    Synchronized in real-time with the main AdjustmentDialog controls.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("색상/톤 보정 실시간 미리보기 (대형 창)")
        self.resize(880, 640)
        self.setMinimumSize(480, 360)
        self.setSizeGripEnabled(True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        tb = QHBoxLayout()
        self.zoom_out_btn = QToolButton(self)
        self.zoom_out_btn.setText("－")
        self.zoom_out_btn.setToolTip("미리보기 축소")
        self.zoom_out_btn.clicked.connect(self._zoom_out)

        self.zoom_in_btn = QToolButton(self)
        self.zoom_in_btn.setText("＋")
        self.zoom_in_btn.setToolTip("미리보기 확대")
        self.zoom_in_btn.clicked.connect(self._zoom_in)

        self.zoom_reset_btn = QToolButton(self)
        self.zoom_reset_btn.setText("1:1")
        self.zoom_reset_btn.setToolTip("1:1 원본 크기")
        self.zoom_reset_btn.clicked.connect(self._zoom_reset)

        self.zoom_label = QLabel("100%", self)
        self.zoom_label.setStyleSheet("font-size: 11px; min-width: 36px;")

        tb.addWidget(self.zoom_out_btn)
        tb.addWidget(self.zoom_label)
        tb.addWidget(self.zoom_in_btn)
        tb.addWidget(self.zoom_reset_btn)
        tb.addStretch()

        close_btn = QPushButton("닫기", self)
        close_btn.clicked.connect(self.close)
        tb.addWidget(close_btn)

        layout.addLayout(tb)

        self.preview_widget = ZoomablePreviewWidget(self)
        layout.addWidget(self.preview_widget)

    def set_pixmap(self, pix: Optional[QPixmap]):
        self.preview_widget.set_pixmap(pix)

    def _zoom_in(self):
        self.preview_widget.zoom_in()
        self.zoom_label.setText(f"{int(round(self.preview_widget.zoom_level * 100))}%")

    def _zoom_out(self):
        self.preview_widget.zoom_out()
        self.zoom_label.setText(f"{int(round(self.preview_widget.zoom_level * 100))}%")

    def _zoom_reset(self):
        self.preview_widget.reset_zoom()
        self.zoom_label.setText("100%")

    def showEvent(self, event):
        super().showEvent(event)
        from ui.theme_utils import apply_window_titlebar
        theme = getattr(self.parent(), "current_theme", "light") if self.parent() else "light"
        apply_window_titlebar(self, theme, deep_navy_hex="#0d1527")


class AdjustmentDialog(QDialog):
    def __init__(
        self,
        source_image: QImage,
        parent=None,
        layers=None,
        active_layer_id: Optional[str] = None,
        selection_rect: Optional[QRect] = None
    ):
        super().__init__(parent)
        self.setWindowTitle("색상 및 톤 보정 (색조/채도/명도/대비)")
        self.resize(920, 560)
        self.setMinimumSize(820, 480)
        self.setSizeGripEnabled(True)

        self.source_image = source_image
        self.layers = layers or []
        self.active_layer_id = active_layer_id
        self.selection_rect = selection_rect
        self.large_preview_dialog: Optional[LargePreviewDialog] = None

        # Map raster layers
        self.raster_layers: Dict[str, any] = {}
        if self.layers:
            for l in self.layers:
                if getattr(l, "layer_type", None) and getattr(l.layer_type, "value", "") == "raster" and l.raster_image:
                    self.raster_layers[l.id] = l

        self._init_ui()
        self._update_preview()

    def showEvent(self, event):
        super().showEvent(event)
        from ui.theme_utils import apply_window_titlebar
        theme = getattr(self.parent(), "current_theme", "light") if self.parent() else "light"
        apply_window_titlebar(self, theme, deep_navy_hex="#0d1527")

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(8)

        # 3-Column Middle Layout: [1. Sliders] [2. Real-time Preview] [3. Hierarchical Layer Tree]
        mid_layout = QHBoxLayout()
        mid_layout.setSpacing(10)

        # 1. Left side: Sliders with fixed-width value labels (No Jumping!)
        controls_group = QGroupBox("색상 및 톤 슬라이더")
        grid = QGridLayout(controls_group)
        grid.setSpacing(10)

        # 1. Hue (-180 ~ +180)
        grid.addWidget(QLabel("색조 (Hue):"), 0, 0)
        self.hue_slider = QSlider(Qt.Orientation.Horizontal)
        self.hue_slider.setRange(-180, 180)
        self.hue_slider.setValue(0)
        self.hue_val_label = QLabel("0°")
        self.hue_val_label.setFixedWidth(54)
        self.hue_val_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        grid.addWidget(self.hue_slider, 0, 1)
        grid.addWidget(self.hue_val_label, 0, 2)

        # 2. Saturation (-100 ~ +100 %)
        grid.addWidget(QLabel("채도 (Saturation):"), 1, 0)
        self.sat_slider = QSlider(Qt.Orientation.Horizontal)
        self.sat_slider.setRange(-100, 100)
        self.sat_slider.setValue(0)
        self.sat_val_label = QLabel("0%")
        self.sat_val_label.setFixedWidth(54)
        self.sat_val_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        grid.addWidget(self.sat_slider, 1, 1)
        grid.addWidget(self.sat_val_label, 1, 2)

        # 3. Brightness (-100 ~ +100)
        grid.addWidget(QLabel("명도 (Brightness):"), 2, 0)
        self.bri_slider = QSlider(Qt.Orientation.Horizontal)
        self.bri_slider.setRange(-100, 100)
        self.bri_slider.setValue(0)
        self.bri_val_label = QLabel("0")
        self.bri_val_label.setFixedWidth(54)
        self.bri_val_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        grid.addWidget(self.bri_slider, 2, 1)
        grid.addWidget(self.bri_val_label, 2, 2)

        # 4. Contrast (-100 ~ +100 %)
        grid.addWidget(QLabel("대비 (Contrast):"), 3, 0)
        self.con_slider = QSlider(Qt.Orientation.Horizontal)
        self.con_slider.setRange(-100, 100)
        self.con_slider.setValue(0)
        self.con_val_label = QLabel("0%")
        self.con_val_label.setFixedWidth(54)
        self.con_val_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        grid.addWidget(self.con_slider, 3, 1)
        grid.addWidget(self.con_val_label, 3, 2)

        # Connect signals
        for s in (self.hue_slider, self.sat_slider, self.bri_slider, self.con_slider):
            s.valueChanged.connect(self._on_slider_changed)

        # Reset button
        reset_btn = QPushButton("값 초기화 (Reset)")
        reset_btn.setStyleSheet("padding: 4px 10px; margin-top: 6px;")
        reset_btn.clicked.connect(self._reset_values)
        grid.addWidget(reset_btn, 4, 0, 1, 3)

        mid_layout.addWidget(controls_group, stretch=4)

        # 2. Center: Zoomable Preview
        preview_group = QGroupBox("실시간 미리보기")
        prev_vbox = QVBoxLayout(preview_group)

        # Preview toolbar: Zoom In, Zoom Out, Reset 1:1, Zoom level, Large Preview
        prev_toolbar = QHBoxLayout()
        self.zoom_out_btn = QToolButton()
        self.zoom_out_btn.setText("－")
        self.zoom_out_btn.setToolTip("미리보기 축소")
        self.zoom_out_btn.clicked.connect(self._preview_zoom_out)

        self.zoom_in_btn = QToolButton()
        self.zoom_in_btn.setText("＋")
        self.zoom_in_btn.setToolTip("미리보기 확대")
        self.zoom_in_btn.clicked.connect(self._preview_zoom_in)

        self.zoom_reset_btn = QToolButton()
        self.zoom_reset_btn.setText("1:1")
        self.zoom_reset_btn.setToolTip("미리보기 1:1 원본 크기")
        self.zoom_reset_btn.clicked.connect(self._preview_zoom_reset)

        self.preview_zoom_label = QLabel("100%")
        self.preview_zoom_label.setStyleSheet("font-size: 11px; min-width: 36px;")

        self.large_preview_btn = QToolButton()
        self.large_preview_btn.setText("🔍 크게 보기")
        self.large_preview_btn.setToolTip("실시간 미리보기를 별도의 대형 팝업창에서 확인합니다.")
        self.large_preview_btn.clicked.connect(self._open_large_preview)

        prev_toolbar.addWidget(self.zoom_out_btn)
        prev_toolbar.addWidget(self.preview_zoom_label)
        prev_toolbar.addWidget(self.zoom_in_btn)
        prev_toolbar.addWidget(self.zoom_reset_btn)
        prev_toolbar.addWidget(self.large_preview_btn)
        prev_toolbar.addStretch()
        prev_vbox.addLayout(prev_toolbar)

        # Zoomable Preview Display
        self.preview_widget = ZoomablePreviewWidget(self)
        prev_vbox.addWidget(self.preview_widget)

        mid_layout.addWidget(preview_group, stretch=5)

        # 3. Right side: Hierarchical Layer Tree Panel (User requirement: 원래 레이어 표시 방법처럼 우측에 계층구조로 표시)
        layers_group = QGroupBox("대상 레이어 계층")
        layers_vbox = QVBoxLayout(layers_group)
        layers_vbox.setContentsMargins(8, 8, 8, 8)
        layers_vbox.setSpacing(6)

        # Header row: Master select all & selection info
        header_row = QHBoxLayout()
        self.select_all_check = QCheckBox("모든 래스터 레이어 선택")
        self.select_all_check.setToolTip("모든 래스터 레이어를 일괄 선택하거나 해제합니다.")
        self.select_all_check.toggled.connect(self._on_select_all_toggled)
        header_row.addWidget(self.select_all_check)
        layers_vbox.addLayout(header_row)

        if self.selection_rect:
            rw = int(self.selection_rect.width())
            rh = int(self.selection_rect.height())
            sel_info = QLabel(f"✂️ [선택 영역 전용: {rw}×{rh} px]")
            sel_info.setStyleSheet("color: #2563eb; font-weight: bold; font-size: 11px;")
            layers_vbox.addWidget(sel_info)

        # Hierarchical Layer Tree
        self.layer_tree = QTreeWidget()
        self.layer_tree.setHeaderHidden(True)
        self.layer_tree.setIndentation(16)
        self.layer_tree.setStyleSheet("""
            QTreeWidget {
                background-color: #ffffff;
                border: 1px solid #cbd5e1;
                border-radius: 6px;
                padding: 4px;
            }
            QTreeWidget::item {
                padding: 2px;
            }
        """)

        self.layer_checkboxes: Dict[str, QCheckBox] = {}
        if self.layers:
            root_layers = [l for l in self.layers if not getattr(l, "parent_id", None)]

            def add_layer_tree_item(layer, parent_widget):
                item = QTreeWidgetItem(parent_widget)
                is_raster = getattr(layer, "layer_type", None) and getattr(layer.layer_type, "value", "") == "raster" and layer.raster_image is not None

                cb = QCheckBox(layer.name)
                cb.setStyleSheet("font-size: 12px;")
                if is_raster:
                    is_chk = (layer.id == self.active_layer_id) if self.active_layer_id else True
                    cb.setChecked(is_chk)
                    cb.toggled.connect(self._on_layer_checkbox_toggled)
                    self.layer_checkboxes[layer.id] = cb
                else:
                    cb.setText(f"[도형] {layer.name}")
                    cb.setEnabled(False)
                    cb.setToolTip("색상 보정은 래스터 레이어에만 적용됩니다.")

                self.layer_tree.setItemWidget(item, 0, cb)
                item.setExpanded(True)

                children = [l for l in self.layers if getattr(l, "parent_id", None) == layer.id]
                for child in reversed(children):
                    add_layer_tree_item(child, item)

                return item

            for root in reversed(root_layers):
                add_layer_tree_item(root, self.layer_tree)
        else:
            dummy_item = QTreeWidgetItem(self.layer_tree)
            dummy_cb = QCheckBox("현재 레이어")
            dummy_cb.setChecked(True)
            dummy_cb.toggled.connect(self._update_preview)
            self.layer_checkboxes["active"] = dummy_cb
            self.layer_tree.setItemWidget(dummy_item, 0, dummy_cb)

        layers_vbox.addWidget(self.layer_tree)
        mid_layout.addWidget(layers_group, stretch=4)

        main_layout.addLayout(mid_layout)

        # Bottom Dialog Buttons
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        button_box.button(QDialogButtonBox.StandardButton.Ok).setText("적용")
        button_box.button(QDialogButtonBox.StandardButton.Cancel).setText("취소")
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        main_layout.addWidget(button_box)

    def _preview_zoom_in(self):
        self.preview_widget.zoom_in()
        self.preview_zoom_label.setText(f"{int(round(self.preview_widget.zoom_level * 100))}%")

    def _preview_zoom_out(self):
        self.preview_widget.zoom_out()
        self.preview_zoom_label.setText(f"{int(round(self.preview_widget.zoom_level * 100))}%")

    def _preview_zoom_reset(self):
        self.preview_widget.reset_zoom()
        self.preview_zoom_label.setText("100%")

    def _on_select_all_toggled(self, checked: bool):
        for cb in self.layer_checkboxes.values():
            cb.blockSignals(True)
            cb.setChecked(checked)
            cb.blockSignals(False)
        self._update_preview()

    def _on_layer_checkbox_toggled(self):
        # Update master select all check state without triggering loop
        all_checked = all(cb.isChecked() for cb in self.layer_checkboxes.values()) if self.layer_checkboxes else False
        self.select_all_check.blockSignals(True)
        self.select_all_check.setChecked(all_checked)
        self.select_all_check.blockSignals(False)
        self._update_preview()

    def _reset_values(self):
        for s in (self.hue_slider, self.sat_slider, self.bri_slider, self.con_slider):
            s.blockSignals(True)
            s.setValue(0)
            s.blockSignals(False)
        self._on_slider_changed()

    def _on_slider_changed(self):
        h = self.hue_slider.value()
        s = self.sat_slider.value()
        b = self.bri_slider.value()
        c = self.con_slider.value()

        # Fixed width strings formatting
        self.hue_val_label.setText(f"{h}°")
        self.sat_val_label.setText(f"{s}%")
        self.bri_val_label.setText(f"{b}")
        self.con_val_label.setText(f"{c}%")

        self._update_preview()

    def get_target_layer_ids(self) -> List[str]:
        """Returns the list of layer IDs currently selected via checkboxes."""
        return [l_id for l_id, cb in self.layer_checkboxes.items() if cb.isChecked() and l_id != "active"]

    def _get_composite_for_checked_layers(self) -> Optional[QImage]:
        target_ids = self.get_target_layer_ids()
        if not target_ids and "active" not in self.layer_checkboxes:
            return None
        if not target_ids and "active" in self.layer_checkboxes and self.layer_checkboxes["active"].isChecked():
            return self.source_image

        if not target_ids:
            return None

        if len(target_ids) == 1 and target_ids[0] in self.raster_layers:
            return self.raster_layers[target_ids[0]].raster_image

        # Composite selected raster layers in stack order (bottom to top)
        comp = QImage(self.source_image.width(), self.source_image.height(), QImage.Format.Format_ARGB32_Premultiplied)
        comp.fill(QColor(0, 0, 0, 0))
        p = QPainter(comp)
        has_any = False
        for l in self.layers:
            if l.id in target_ids and l.raster_image is not None:
                p.drawImage(0, 0, l.raster_image)
                has_any = True
        p.end()
        return comp if has_any else None

    def _open_large_preview(self):
        if not self.large_preview_dialog:
            self.large_preview_dialog = LargePreviewDialog(self)
        self.large_preview_dialog.show()
        self.large_preview_dialog.raise_()
        self.large_preview_dialog.activateWindow()
        self._update_preview()

    PROXY_MAX_DIM = 800

    def _get_preview_proxy(self):
        """
        Issue 5: Returns (proxy_image, scaled_selection_rect) for the currently checked layers.
        The full-resolution composite is downscaled ONCE to <= PROXY_MAX_DIM and cached per
        layer-selection key, so slider drags never touch the 4K original.
        """
        key = (tuple(sorted(self.get_target_layer_ids())),
               bool(self.layer_checkboxes.get("active").isChecked()) if "active" in self.layer_checkboxes else False)
        cache = getattr(self, "_proxy_cache", None)
        if cache is not None and cache[0] == key:
            return cache[1], cache[2]

        src = self._get_composite_for_checked_layers()
        if src is None:
            self._proxy_cache = (key, None, None)
            return None, None

        w, h = src.width(), src.height()
        scale = min(1.0, float(self.PROXY_MAX_DIM) / float(max(w, h, 1)))
        if scale < 1.0:
            proxy = src.scaled(
                max(1, int(round(w * scale))), max(1, int(round(h * scale))),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        else:
            proxy = src

        sel = None
        if self.selection_rect is not None and not self.selection_rect.isEmpty():
            sx = proxy.width() / float(w)
            sy = proxy.height() / float(h)
            r = self.selection_rect
            sel = QRect(int(r.x() * sx), int(r.y() * sy),
                        max(1, int(round(r.width() * sx))), max(1, int(round(r.height() * sy))))

        self._proxy_cache = (key, proxy, sel)
        return proxy, sel

    def _update_preview(self):
        src, sel = self._get_preview_proxy()
        if src is None:
            # User requirement: Empty state with centered white text "아무것도 선택되지 않음"
            self.preview_widget.set_pixmap(None)
            if self.large_preview_dialog and self.large_preview_dialog.isVisible():
                self.large_preview_dialog.set_pixmap(None)
            return

        h, s_scale, b_shift, c_scale = self.get_adjustment_params()

        # Adjust colors on the lightweight proxy only (full-res is applied once on OK)
        adjusted = self._apply_adjustment_to_image(src, h, s_scale, b_shift, c_scale, sel)

        pix = QPixmap.fromImage(adjusted)
        self.preview_widget.set_pixmap(pix)
        if self.large_preview_dialog and self.large_preview_dialog.isVisible():
            self.large_preview_dialog.set_pixmap(pix)

    @staticmethod
    def _apply_adjustment_to_image(
        img: QImage,
        h: float,
        s_scale: float,
        b_shift: float,
        c_scale: float,
        selection_rect: Optional[QRect] = None
    ) -> QImage:
        if selection_rect is None or selection_rect.isEmpty():
            return ImageProcessor.adjust_colors(
                img,
                hue_shift=h,
                saturation_scale=s_scale,
                brightness_shift=b_shift,
                contrast_scale=c_scale,
            )

        # Adjust only the cropped selection region and blend onto copy
        result = img.copy()
        bounded_rect = selection_rect.intersected(QRect(0, 0, img.width(), img.height()))
        if bounded_rect.isEmpty():
            return result

        sub_img = img.copy(bounded_rect)
        adjusted_sub = ImageProcessor.adjust_colors(
            sub_img,
            hue_shift=h,
            saturation_scale=s_scale,
            brightness_shift=b_shift,
            contrast_scale=c_scale,
        )

        p = QPainter(result)
        p.drawImage(bounded_rect.topLeft(), adjusted_sub)
        p.end()
        return result

    def get_adjusted_image(self) -> QImage:
        """Returns adjusted image for single target layer."""
        src = self._get_composite_for_checked_layers() or self.source_image
        h, s_scale, b_shift, c_scale = self.get_adjustment_params()
        return self._apply_adjustment_to_image(src, h, s_scale, b_shift, c_scale, self.selection_rect)

    def get_target_layer_id(self) -> Optional[str]:
        ids = self.get_target_layer_ids()
        return ids[0] if ids else None

    def is_all_layers(self) -> bool:
        return self.select_all_check.isChecked()

    def get_adjustment_params(self):
        h = float(self.hue_slider.value())
        s_scale = 1.0 + (float(self.sat_slider.value()) / 100.0)
        b_shift = float(self.bri_slider.value()) * 1.28
        c_scale = 1.0 + (float(self.con_slider.value()) / 100.0)
        return h, s_scale, b_shift, c_scale
