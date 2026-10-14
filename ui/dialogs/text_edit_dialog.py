"""
Paint Pro - Text Input & Edit Dialog
Allows entering and styling vector text with font family, size, bold, italic, and color.
"""
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QSpinBox,
    QPushButton, QFontComboBox, QTextEdit, QToolButton, QColorDialog
)
from PyQt6.QtGui import QFont, QColor, QKeySequence, QShortcut, QIcon, QPixmap, QPainter
from PyQt6.QtCore import Qt
from core.i18n import I18N


class TextEditDialog(QDialog):
    def __init__(
        self,
        initial_text: str = "",
        initial_font_family: str = "Malgun Gothic",
        initial_font_size: int = 24,
        initial_bold: bool = False,
        initial_italic: bool = False,
        initial_color: QColor = QColor(0, 0, 0),
        parent=None
    ):
        super().__init__(parent)
        self.setWindowTitle(I18N.tr("dlg_text_title"))
        self.setMinimumSize(440, 320)
        self.resize(480, 340)

        self.font_family = initial_font_family
        self.font_size = max(8, min(144, initial_font_size))
        self.font_bold = initial_bold
        self.font_italic = initial_italic
        self.text_color = initial_color

        self._init_ui(initial_text)
        self._update_preview()

    def showEvent(self, event):
        super().showEvent(event)
        from ui.theme_utils import apply_window_titlebar
        theme = getattr(self.parent(), "current_theme", "light") if self.parent() else "light"
        apply_window_titlebar(self, theme, deep_navy_hex="#0d1527")
        self.text_edit.setFocus()

    def _init_ui(self, initial_text: str):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(16, 16, 16, 16)

        # 1. Formatting Toolbar Row
        fmt_row = QHBoxLayout()
        fmt_row.setSpacing(6)

        # Font Family
        self.font_combo = QFontComboBox()
        self.font_combo.setCurrentFont(QFont(self.font_family))
        self.font_combo.currentFontChanged.connect(self._on_font_family_changed)
        fmt_row.addWidget(self.font_combo, 3)

        # Font Size
        self.size_spin = QSpinBox()
        self.size_spin.setRange(8, 144)
        self.size_spin.setValue(self.font_size)
        self.size_spin.setSuffix(" pt")
        self.size_spin.setToolTip("글꼴 크기 (pt)")
        self.size_spin.valueChanged.connect(self._on_font_size_changed)
        fmt_row.addWidget(self.size_spin, 1)

        # Bold Button
        self.bold_btn = QToolButton()
        self.bold_btn.setText("B")
        self.bold_btn.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        self.bold_btn.setCheckable(True)
        self.bold_btn.setChecked(self.font_bold)
        self.bold_btn.setToolTip("굵게 (Bold)")
        self.bold_btn.toggled.connect(self._on_bold_toggled)
        fmt_row.addWidget(self.bold_btn)

        # Italic Button
        self.italic_btn = QToolButton()
        self.italic_btn.setText("I")
        self.italic_btn.setFont(QFont("Arial", 10, italic=True))
        self.italic_btn.setCheckable(True)
        self.italic_btn.setChecked(self.font_italic)
        self.italic_btn.setToolTip("기울임꼴 (Italic)")
        self.italic_btn.toggled.connect(self._on_italic_toggled)
        fmt_row.addWidget(self.italic_btn)

        # Color Button
        self.color_btn = QPushButton(" 색상")
        self.color_btn.setToolTip("글꼴 색상 선택")
        self.color_btn.clicked.connect(self._pick_color)
        self._update_color_btn_icon()
        fmt_row.addWidget(self.color_btn)

        layout.addLayout(fmt_row)

        # 2. Text Input Area
        self.prompt_label = QLabel(I18N.tr("dlg_text_prompt"))
        self.prompt_label.setStyleSheet("color: #64748b; font-size: 11px;")
        layout.addWidget(self.prompt_label)

        self.text_edit = QTextEdit()
        self.text_edit.setPlainText(initial_text)
        self.text_edit.setAcceptRichText(False)
        self.text_edit.setPlaceholderText("여기에 텍스트를 입력하세요...")
        layout.addWidget(self.text_edit, 1)

        # Shortcut: Ctrl+Enter to Accept
        ctrl_enter_sc = QShortcut(QKeySequence("Ctrl+Return"), self)
        ctrl_enter_sc.activated.connect(self.accept)
        ctrl_enter_kp = QShortcut(QKeySequence("Ctrl+Enter"), self)
        ctrl_enter_kp.activated.connect(self.accept)

        # 3. Bottom Button Row
        btn_row = QHBoxLayout()
        hint_label = QLabel("단축키: Ctrl+Enter (입력 완료), Esc (취소)")
        hint_label.setStyleSheet("color: #94a3b8; font-size: 11px;")
        btn_row.addWidget(hint_label)
        btn_row.addStretch()

        self.cancel_btn = QPushButton(I18N.tr("btn_cancel"))
        self.cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(self.cancel_btn)

        self.ok_btn = QPushButton(I18N.tr("btn_ok"))
        self.ok_btn.setDefault(True)
        self.ok_btn.clicked.connect(self.accept)
        self.ok_btn.setStyleSheet("""
            QPushButton {
                background-color: #2563eb;
                color: white;
                font-weight: bold;
                padding: 6px 16px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #1d4ed8;
            }
        """)
        btn_row.addWidget(self.ok_btn)

        layout.addLayout(btn_row)

    def _update_color_btn_icon(self):
        pix = QPixmap(16, 16)
        pix.fill(self.text_color)
        p = QPainter(pix)
        p.setPen(QColor(100, 116, 139))
        p.drawRect(0, 0, 15, 15)
        p.end()
        self.color_btn.setIcon(QIcon(pix))

    def _pick_color(self):
        chosen = QColorDialog.getColor(self.text_color, self, "글꼴 색상 선택")
        if chosen.isValid():
            self.text_color = chosen
            self._update_color_btn_icon()
            self._update_preview()

    def _on_font_family_changed(self, font: QFont):
        self.font_family = font.family()
        self._update_preview()

    def _on_font_size_changed(self, size: int):
        self.font_size = size
        self._update_preview()

    def _on_bold_toggled(self, checked: bool):
        self.font_bold = checked
        self._update_preview()

    def _on_italic_toggled(self, checked: bool):
        self.font_italic = checked
        self._update_preview()

    def _update_preview(self):
        font = QFont(self.font_family, min(36, self.font_size))
        font.setBold(self.font_bold)
        font.setItalic(self.font_italic)
        self.text_edit.setFont(font)
        # Apply color
        self.text_edit.setStyleSheet(f"QTextEdit {{ color: {self.text_color.name()}; }}")

    def get_properties(self) -> dict:
        return {
            "text": self.text_edit.toPlainText().rstrip("\r\n"),
            "font_family": self.font_family,
            "font_size": self.font_size,
            "font_bold": self.font_bold,
            "font_italic": self.font_italic,
            "color": getattr(self, "text_color", QColor(0, 0, 0))
        }
