"""
Paint Essential - New Canvas Preset Dialog
v1.1.0 High-productivity canvas creation with one-click presets:
- Clipboard Image Auto-fit
- YouTube Thumbnail (1280 x 720)
- Square / SNS (1080 x 1080)
- FHD Standard (1920 x 1080)
"""
from typing import Tuple, Optional
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel,
    QSpinBox, QPushButton, QGroupBox, QRadioButton, QDialogButtonBox,
    QApplication, QMessageBox
)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QIcon, QFont, QImage
from ui.icon_factory import IconFactory


class NewCanvasDialog(QDialog):
    def __init__(self, parent=None, default_width: int = 900, default_height: int = 600):
        super().__init__(parent)
        self.setWindowTitle("새 캔버스 만들기")
        self.setFixedSize(440, 420)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint)

        self._width = default_width
        self._height = default_height
        self._transparent_bg = False

        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(18, 18, 18, 18)

        # 1. Presets Group Box
        preset_group = QGroupBox("⚡ 빠른 프리셋 (클릭 시 자동 적용)")
        preset_layout = QGridLayout(preset_group)
        preset_layout.setSpacing(8)

        # Clipboard preset button
        self.btn_clipboard = QPushButton("📋 클립보드 크기 맞춤")
        self.btn_clipboard.setToolTip("클립보드에 복사된 이미지의 해상도에 맞춥니다")
        self.btn_clipboard.clicked.connect(self._apply_clipboard_preset)
        preset_layout.addWidget(self.btn_clipboard, 0, 0)

        # YouTube thumbnail
        self.btn_youtube = QPushButton("🎬 유튜브 썸네일 (1280×720)")
        self.btn_youtube.setToolTip("1280 × 720 px (16:9 HD)")
        self.btn_youtube.clicked.connect(lambda: self._set_dimensions(1280, 720))
        preset_layout.addWidget(self.btn_youtube, 0, 1)

        # Square / SNS
        self.btn_sns = QPushButton("📱 정사각형 / SNS (1080×1080)")
        self.btn_sns.setToolTip("1080 × 1080 px (1:1 인스타그램/프로필)")
        self.btn_sns.clicked.connect(lambda: self._set_dimensions(1080, 1080))
        preset_layout.addWidget(self.btn_sns, 1, 0)

        # FHD Standard
        self.btn_fhd = QPushButton("🖥️ FHD 표준 (1920×1080)")
        self.btn_fhd.setToolTip("1920 × 1080 px (16:9 Full HD)")
        self.btn_fhd.clicked.connect(lambda: self._set_dimensions(1920, 1080))
        preset_layout.addWidget(self.btn_fhd, 1, 1)

        layout.addWidget(preset_group)

        # 2. Custom Dimensions Group Box
        dim_group = QGroupBox("📐 캔버스 규격")
        dim_layout = QGridLayout(dim_group)
        dim_layout.setSpacing(10)

        dim_layout.addWidget(QLabel("너비 (Width):"), 0, 0)
        self.width_spin = QSpinBox()
        self.width_spin.setRange(1, 16384)
        self.width_spin.setValue(self._width)
        self.width_spin.setSuffix(" px")
        dim_layout.addWidget(self.width_spin, 0, 1)

        dim_layout.addWidget(QLabel("높이 (Height):"), 1, 0)
        self.height_spin = QSpinBox()
        self.height_spin.setRange(1, 16384)
        self.height_spin.setValue(self._height)
        self.height_spin.setSuffix(" px")
        dim_layout.addWidget(self.height_spin, 1, 1)

        layout.addWidget(dim_group)

        # 3. Background Color Options
        bg_group = QGroupBox("🎨 배경 옵션")
        bg_layout = QHBoxLayout(bg_group)
        self.radio_white = QRadioButton("기본 흰색 (불투명)")
        self.radio_white.setChecked(True)
        self.radio_transparent = QRadioButton("투명 배경 (체크보드)")
        bg_layout.addWidget(self.radio_white)
        bg_layout.addWidget(self.radio_transparent)
        layout.addWidget(bg_group)

        # 4. Dialog Buttons
        btn_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        btn_box.button(QDialogButtonBox.StandardButton.Ok).setText("캔버스 생성")
        btn_box.button(QDialogButtonBox.StandardButton.Cancel).setText("취소")
        btn_box.accepted.connect(self.accept)
        btn_box.rejected.connect(self.reject)
        layout.addWidget(btn_box)

    def _set_dimensions(self, width: int, height: int):
        self.width_spin.setValue(width)
        self.height_spin.setValue(height)

    def _apply_clipboard_preset(self):
        cb = QApplication.clipboard()
        img = cb.image()
        if not img.isNull() and img.width() > 0 and img.height() > 0:
            self._set_dimensions(img.width(), img.height())
        else:
            QMessageBox.information(
                self,
                "클립보드 안내",
                "클립보드에 유효한 이미지가 없습니다.\n화면을 캡처(PrintScreen)하거나 이미지를 복사한 후 다시 시도하세요."
            )

    def get_dimensions(self) -> Tuple[int, int, bool]:
        """Returns (width, height, is_transparent)."""
        return self.width_spin.value(), self.height_spin.value(), self.radio_transparent.isChecked()
