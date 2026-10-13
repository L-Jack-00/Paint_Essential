"""
Paint Essential (페인트 에센셜) - Application Entry Point
Enhanced with Windows High-DPI PassThrough Scaling Policy for Pixel Precision.
"""
import sys
import os

# Ensure local packages are in path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from ui.main_window import MainWindow


def main():
    # LJack Pillar 8: Proactive Windows 11 High-DPI Subpixel Precision Policy
    # Prevents 125%/150%/175% fractional scaling blur and mouse coordinate jitter
    if hasattr(Qt.HighDpiScaleFactorRoundingPolicy, "PassThrough"):
        QApplication.setHighDpiScaleFactorRoundingPolicy(
            Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
        )

    app = QApplication(sys.argv)
    app.setApplicationName("Paint Essential")
    app.setOrganizationName("L-Jack")

    # Set Application Icon
    from ui.icon_factory import IconFactory
    app_icon = IconFactory.get_app_icon()
    if not app_icon.isNull():
        app.setWindowIcon(app_icon)

    # Set modern Windows desktop styling & native Unicode emoji font
    app.setStyle("Fusion")
    from PyQt6.QtGui import QFont
    app_font = QFont()
    app_font.setFamilies(["Segoe UI Emoji", "Segoe UI Symbol", "Malgun Gothic", "Segoe UI", "sans-serif"])
    app_font.setPointSize(10)
    app.setFont(app_font)

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
