"""
Paint Essential - Settings Dialog
LJack Protocol: Multi-language (Korean/English), Light/Dark Mode switching,
empty patch notes (testing build), and credits (L.Jack with Google Antigravity).
"""
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QRadioButton,
    QButtonGroup, QGroupBox, QTextEdit, QPushButton, QTabWidget,
    QWidget, QFrame
)
from PyQt6.QtCore import pyqtSignal
from core.i18n import I18N


class SettingsDialog(QDialog):
    theme_changed = pyqtSignal(str)     # "light" or "dark"
    language_changed = pyqtSignal(str)  # "ko" or "en"

    def __init__(
        self,
        current_theme: str = "light",
        current_language: str = "ko",
        parent=None
    ):
        super().__init__(parent)
        self.current_theme = current_theme
        self.current_language = current_language
        I18N.set_language(current_language)

        self.resize(520, 460)
        self.setMinimumSize(460, 380)

        self._init_ui()
        self.retranslate_ui()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(14, 14, 14, 14)
        main_layout.setSpacing(12)

        # Tab Widget for Settings categories
        self.tabs = QTabWidget(self)

        # Tab 1: General (Language & Theme)
        general_tab = QWidget()
        gen_layout = QVBoxLayout(general_tab)
        gen_layout.setContentsMargins(12, 12, 12, 12)
        gen_layout.setSpacing(14)

        # Language Group
        self.lang_group = QGroupBox()
        lang_layout = QHBoxLayout(self.lang_group)
        lang_layout.setContentsMargins(12, 14, 12, 14)
        self.lang_ko_rb = QRadioButton()
        self.lang_en_rb = QRadioButton()
        if self.current_language == "en":
            self.lang_en_rb.setChecked(True)
        else:
            self.lang_ko_rb.setChecked(True)

        self.lang_btn_group = QButtonGroup(self)
        self.lang_btn_group.addButton(self.lang_ko_rb, 0)
        self.lang_btn_group.addButton(self.lang_en_rb, 1)
        self.lang_btn_group.idToggled.connect(self._on_lang_toggled)

        lang_layout.addWidget(self.lang_ko_rb)
        lang_layout.addWidget(self.lang_en_rb)
        lang_layout.addStretch()
        gen_layout.addWidget(self.lang_group)

        # Theme Group
        self.theme_group = QGroupBox()
        theme_layout = QHBoxLayout(self.theme_group)
        theme_layout.setContentsMargins(12, 14, 12, 14)
        self.theme_light_rb = QRadioButton()
        self.theme_dark_rb = QRadioButton()
        if self.current_theme == "dark":
            self.theme_dark_rb.setChecked(True)
        else:
            self.theme_light_rb.setChecked(True)

        self.theme_btn_group = QButtonGroup(self)
        self.theme_btn_group.addButton(self.theme_light_rb, 0)
        self.theme_btn_group.addButton(self.theme_dark_rb, 1)
        self.theme_btn_group.idToggled.connect(self._on_theme_toggled)

        theme_layout.addWidget(self.theme_light_rb)
        theme_layout.addWidget(self.theme_dark_rb)
        theme_layout.addStretch()
        gen_layout.addWidget(self.theme_group)

        gen_layout.addStretch()
        self.tabs.addTab(general_tab, "")

        # Tab 2: Patch Notes (Empty as requested for test build)
        patch_tab = QWidget()
        patch_layout = QVBoxLayout(patch_tab)
        patch_layout.setContentsMargins(10, 10, 10, 10)

        self.patch_text = QTextEdit()
        self.patch_text.setReadOnly(True)
        self.patch_text.setPlainText("")
        patch_layout.addWidget(self.patch_text)
        self.tabs.addTab(patch_tab, "")

        # Tab 3: Credits (크레딧)
        credits_tab = QWidget()
        credits_layout = QVBoxLayout(credits_tab)
        credits_layout.setContentsMargins(16, 16, 16, 16)
        credits_layout.setSpacing(12)

        self.credits_card = QFrame()
        card_layout = QVBoxLayout(self.credits_card)
        card_layout.setContentsMargins(14, 14, 14, 14)
        card_layout.setSpacing(8)

        self.title_lbl = QLabel()
        self.title_lbl.setStyleSheet("font-size: 15px; font-weight: bold;")
        card_layout.addWidget(self.title_lbl)

        self.sub_lbl = QLabel(I18N.tr("credits_sub_label"))
        self.sub_lbl.setStyleSheet("font-size: 11px;")
        card_layout.addWidget(self.sub_lbl)

        card_layout.addSpacing(8)

        self.author_lbl = QLabel()
        card_layout.addWidget(self.author_lbl)

        self.engine_lbl = QLabel()
        card_layout.addWidget(self.engine_lbl)

        self.version_lbl = QLabel()
        card_layout.addWidget(self.version_lbl)

        credits_layout.addWidget(self.credits_card)
        credits_layout.addStretch()
        self.tabs.addTab(credits_tab, "")

        main_layout.addWidget(self.tabs)

        # Bottom OK button
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        self.ok_btn = QPushButton()
        self.ok_btn.setStyleSheet("padding: 6px 22px; font-weight: bold;")
        self.ok_btn.clicked.connect(self.accept)
        btn_layout.addWidget(self.ok_btn)
        main_layout.addLayout(btn_layout)

    def retranslate_ui(self):
        """Dynamically retranslates all widgets in the settings dialog."""
        lang = self.current_language
        self.setWindowTitle(f"{I18N.tr('settings_title', lang)} - Paint Essential")
        self.tabs.setTabText(0, I18N.tr("tab_general", lang))
        self.tabs.setTabText(1, I18N.tr("tab_patch", lang))
        self.tabs.setTabText(2, I18N.tr("tab_credits", lang))

        self.lang_group.setTitle(I18N.tr("group_language", lang))
        self.lang_ko_rb.setText("🇰🇷 " + I18N.tr("lang_ko", lang))
        self.lang_en_rb.setText("🇺🇸 " + I18N.tr("lang_en", lang))

        self.theme_group.setTitle(I18N.tr("group_theme", lang))
        self.theme_light_rb.setText("☀️ " + I18N.tr("theme_light", lang))
        self.theme_dark_rb.setText("🌙 " + I18N.tr("theme_dark", lang))

        self.title_lbl.setText("🎨 Paint Essential (페인트 에센셜)")
        self.sub_lbl.setText(I18N.tr("credits_sub_label", lang))
        author_label = I18N.tr("credits_author_label", lang)
        engine_label = I18N.tr("credits_engine_label", lang)
        version_label = I18N.tr("credits_version_label", lang)

        self.author_lbl.setText(f"✨ <b>{author_label}</b>: L.Jack with Google Antigravity")
        self.engine_lbl.setText(f"⚡ <b>{engine_label}</b>: Paint Essential Core Engine v1.2.2")
        self.version_lbl.setText(f"📦 <b>{version_label}</b>: Paint Essential v1.2.2")

        self.patch_text.setPlainText(I18N.tr("patch_notes_content", lang))

        self.ok_btn.setText(I18N.tr("btn_ok", lang))

    def _on_lang_toggled(self, btn_id: int, checked: bool):
        if checked:
            lang = "ko" if btn_id == 0 else "en"
            self.current_language = lang
            I18N.set_language(lang)
            self.retranslate_ui()
            self.language_changed.emit(lang)

    def showEvent(self, event):
        super().showEvent(event)
        from ui.theme_utils import apply_window_titlebar
        apply_window_titlebar(self, getattr(self, "current_theme", "light"), deep_navy_hex="#0d1527")

    def _on_theme_toggled(self, btn_id: int, checked: bool):
        if checked:
            theme = "light" if btn_id == 0 else "dark"
            self.current_theme = theme
            self.theme_changed.emit(theme)
            from ui.theme_utils import apply_window_titlebar
            apply_window_titlebar(self, theme, deep_navy_hex="#0d1527")
