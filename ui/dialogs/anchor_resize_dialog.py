"""
Paint Pro - Anchor Resize Dialog
Photoshop-style 9-point anchor canvas resize dialog.
"""
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QSpinBox,
    QPushButton, QGroupBox, QGridLayout, QCheckBox, QDialogButtonBox
)
from core.image_processor import AnchorPoint


class AnchorResizeDialog(QDialog):
    def __init__(self, current_width: int, current_height: int, parent=None):
        super().__init__(parent)
        self.setWindowTitle("캔버스 크기 조정 (축 설정)")
        self.setFixedSize(360, 360)
        self.old_w = current_width
        self.old_h = current_height
        self.selected_anchor = AnchorPoint.CENTER

        self._init_ui()

    def showEvent(self, event):
        super().showEvent(event)
        from ui.theme_utils import apply_window_titlebar
        theme = getattr(self.parent(), "current_theme", "light") if self.parent() else "light"
        apply_window_titlebar(self, theme, deep_navy_hex="#0d1527")

    def _init_ui(self):
        layout = QVBoxLayout(self)

        # 1. Current size label
        info_label = QLabel(f"현재 캔버스 크기: {self.old_w} × {self.old_h} px")
        info_label.setStyleSheet("font-weight: bold; margin-bottom: 8px;")
        layout.addWidget(info_label)

        # 2. Dimensions input
        dim_box = QGroupBox("새 캔버스 크기")
        dim_layout = QGridLayout(dim_box)

        dim_layout.addWidget(QLabel("너비 (W):"), 0, 0)
        self.width_spin = QSpinBox()
        self.width_spin.setRange(10, 8192)
        self.width_spin.setValue(self.old_w)
        self.width_spin.setSuffix(" px")
        dim_layout.addWidget(self.width_spin, 0, 1)

        dim_layout.addWidget(QLabel("높이 (H):"), 1, 0)
        self.height_spin = QSpinBox()
        self.height_spin.setRange(10, 8192)
        self.height_spin.setValue(self.old_h)
        self.height_spin.setSuffix(" px")
        dim_layout.addWidget(self.height_spin, 1, 1)

        self.keep_ratio_cb = QCheckBox("가로세로 비율 유지")
        dim_layout.addWidget(self.keep_ratio_cb, 2, 0, 1, 2)
        self.width_spin.valueChanged.connect(self._on_width_changed)

        layout.addWidget(dim_box)

        # 3. 9-Point Anchor Grid
        anchor_box = QGroupBox("기준 축 설정 (Anchor Pivot)")
        anchor_layout = QGridLayout(anchor_box)
        self.anchor_buttons = {}

        grid_matrix = [
            (AnchorPoint.TOP_LEFT, "↖ NW", 0, 0),
            (AnchorPoint.TOP_CENTER, "↑ N", 0, 1),
            (AnchorPoint.TOP_RIGHT, "↗ NE", 0, 2),
            (AnchorPoint.MIDDLE_LEFT, "← W", 1, 0),
            (AnchorPoint.CENTER, "● C", 1, 1),
            (AnchorPoint.MIDDLE_RIGHT, "→ E", 1, 2),
            (AnchorPoint.BOTTOM_LEFT, "↙ SW", 2, 0),
            (AnchorPoint.BOTTOM_CENTER, "↓ S", 2, 1),
            (AnchorPoint.BOTTOM_RIGHT, "↘ SE", 2, 2),
        ]

        for pt, label, r, c in grid_matrix:
            btn = QPushButton(label)
            btn.setCheckable(True)
            btn.setFixedSize(50, 40)
            btn.clicked.connect(lambda checked, p=pt: self._select_anchor(p))
            anchor_layout.addWidget(btn, r, c)
            self.anchor_buttons[pt] = btn

        self._update_anchor_button_styles()
        layout.addWidget(anchor_box)

        # 4. Buttons
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        button_box.button(QDialogButtonBox.StandardButton.Ok).setText("확인")
        button_box.button(QDialogButtonBox.StandardButton.Cancel).setText("취소")
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def _on_width_changed(self, new_w: int):
        if self.keep_ratio_cb.isChecked() and self.old_w > 0:
            ratio = self.old_h / self.old_w
            self.height_spin.blockSignals(True)
            self.height_spin.setValue(int(new_w * ratio))
            self.height_spin.blockSignals(False)

    def _select_anchor(self, anchor: AnchorPoint):
        self.selected_anchor = anchor
        self._update_anchor_button_styles()

    def _update_anchor_button_styles(self):
        for pt, btn in self.anchor_buttons.items():
            if pt == self.selected_anchor:
                btn.setChecked(True)
                btn.setStyleSheet("background-color: #2563eb; color: white; font-weight: bold;")
            else:
                btn.setChecked(False)
                btn.setStyleSheet("")

    def get_values(self):
        return self.width_spin.value(), self.height_spin.value(), self.selected_anchor
