"""
Paint Essential - Theme & OS Window Bar Integration Utilities
LJack Protocol: Native DWM titlebar caption styling and color synchronization
for QMainWindow and QDialog popup windows.
"""
import sys


def apply_window_titlebar(window, theme: str = "dark", deep_navy_hex: str = "#0d1527"):
    """
    Reflects the theme onto the OS window title bar using Windows DWM API.
    For dark mode, sets a deep navy caption bar (#0d1527) with crisp off-white text (#f1f5f9).
    Works reliably for both QMainWindow and QDialog popup windows.
    """
    if sys.platform != "win32":
        return
    try:
        import ctypes
        from ctypes import wintypes
        hwnd = int(window.winId())
        is_dark = (theme == "dark")

        # 1. Dark Mode (DWMWA_USE_IMMERSIVE_DARK_MODE = 20, fallback 19)
        dark_flag = ctypes.c_int(1 if is_dark else 0)
        for attr in (20, 19):
            res = ctypes.windll.dwmapi.DwmSetWindowAttribute(
                wintypes.HWND(hwnd),
                wintypes.DWORD(attr),
                ctypes.byref(dark_flag),
                ctypes.sizeof(dark_flag)
            )
            if res == 0:
                break

        # 2. Windows 11 Title Bar Custom Color (COLORREF: 0x00BBGGRR)
        if is_dark:
            # Deep Navy Hex: #0d1527 -> R=0x0D, G=0x15, B=0x27
            r = int(deep_navy_hex[1:3], 16)
            g = int(deep_navy_hex[3:5], 16)
            b = int(deep_navy_hex[5:7], 16)
            caption_color = ctypes.c_uint32((b << 16) | (g << 8) | r)
            text_color = ctypes.c_uint32(0x00F9F5F1)  # Soft off-white (#f1f5f9)
        else:
            caption_color = ctypes.c_uint32(0x00FCFAF8)  # Light slate (#f8fafc)
            text_color = ctypes.c_uint32(0x003B291E)     # Slate text (#1e293b)

        # DWMWA_CAPTION_COLOR = 35
        ctypes.windll.dwmapi.DwmSetWindowAttribute(
            wintypes.HWND(hwnd),
            wintypes.DWORD(35),
            ctypes.byref(caption_color),
            ctypes.sizeof(caption_color)
        )
        # DWMWA_TEXT_COLOR = 36
        ctypes.windll.dwmapi.DwmSetWindowAttribute(
            wintypes.HWND(hwnd),
            wintypes.DWORD(36),
            ctypes.byref(text_color),
            ctypes.sizeof(text_color)
        )
    except Exception:
        pass
