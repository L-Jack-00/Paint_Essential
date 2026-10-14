"""
Paint Pro - Input Safety & Interlock Rig
LJack Protocol Pillar 6: Physical Input Safety & Stuck Prevention
Ensures mouse/keyboard states never get stuck when mouse leaves window or loses focus.
"""
from enum import Enum
from typing import Optional, Callable


class InputMode(Enum):
    SELECT = "select"
    SELECT_AREA = "select_area"
    SELECT_LASSO = "select_lasso"
    SELECT_WAND = "select_wand"
    BRUSH = "brush"
    PENCIL = "pencil"
    ERASER = "eraser"
    FLOOD_FILL = "flood_fill"
    SHAPE_RECT = "shape_rect"
    SHAPE_ROUNDED_RECT = "shape_rounded_rect"
    SHAPE_ELLIPSE = "shape_ellipse"
    SHAPE_LINE = "shape_line"
    SHAPE_ARROW = "shape_arrow"
    EYEDROPPER = "eyedropper"
    MOSAIC = "mosaic"
    STEP_BADGE = "step_badge"
    TEXT = "text"
    PAN = "pan"


class InputSafetyTracker:
    def __init__(self):
        self.is_mouse_down = False
        self.current_mode: InputMode = InputMode.BRUSH
        self.is_space_pressed = False
        self.on_emergency_release_cb: Optional[Callable[[], None]] = None

    def register_emergency_release_callback(self, cb: Callable[[], None]):
        self.on_emergency_release_cb = cb

    def set_mouse_down(self, down: bool):
        self.is_mouse_down = down

    def set_space_pressed(self, pressed: bool):
        self.is_space_pressed = pressed

    def emergency_release(self):
        """Forces all pressed keys and mouse states to reset cleanly."""
        was_active = self.is_mouse_down or self.is_space_pressed
        self.is_mouse_down = False
        self.is_space_pressed = False
        if was_active and self.on_emergency_release_cb:
            self.on_emergency_release_cb()
