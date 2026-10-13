"""
Paint Pro - History Manager (Core Harness)
LJack Protocol Pillar 1 & 4: Invariant State & Memory Safeguard
Provides robust Undo/Redo history stack with memory limits and auto-eviction.
"""
from typing import List, Callable
from dataclasses import dataclass
import gc


@dataclass
class HistoryStep:
    description: str
    undo_fn: Callable[[], None]
    redo_fn: Callable[[], None]
    estimated_bytes: int = 0


class HistoryManager:
    def __init__(self, max_steps: int = 40, max_memory_mb: int = 256):
        self.max_steps = max_steps
        self.max_memory_bytes = max_memory_mb * 1024 * 1024
        self.undo_stack: List[HistoryStep] = []
        self.redo_stack: List[HistoryStep] = []
        self.current_memory_bytes = 0

    def record_step(
        self,
        description: str,
        undo_fn: Callable[[], None],
        redo_fn: Callable[[], None],
        estimated_bytes: int = 0
    ):
        """Records a new reversible action with memory tracking and auto-eviction."""
        step = HistoryStep(
            description=description,
            undo_fn=undo_fn,
            redo_fn=redo_fn,
            estimated_bytes=estimated_bytes
        )
        self.undo_stack.append(step)
        self.current_memory_bytes += estimated_bytes

        # Clear redo stack and reclaim its memory
        self._reclaim_redo_memory()

        # Evict oldest steps if step count or memory limit exceeded
        self._enforce_limits()

    def _enforce_limits(self):
        evicted_any = False
        while len(self.undo_stack) > self.max_steps or (
            self.current_memory_bytes > self.max_memory_bytes and len(self.undo_stack) > 1
        ):
            evicted = self.undo_stack.pop(0)
            self.current_memory_bytes = max(0, self.current_memory_bytes - evicted.estimated_bytes)
            evicted_any = True

        if evicted_any:
            gc.collect()

    def _reclaim_redo_memory(self):
        self.redo_stack.clear()

    @property
    def step_count(self) -> int:
        return len(self.undo_stack)

    def can_undo(self) -> bool:
        return len(self.undo_stack) > 0

    def can_redo(self) -> bool:
        return len(self.redo_stack) > 0

    def undo(self) -> bool:
        if not self.can_undo():
            return False
        step = self.undo_stack.pop()
        try:
            step.undo_fn()
            self.redo_stack.append(step)
            return True
        except Exception as e:
            print(f"[HistoryManager] Undo error: {e}")
            return False

    def redo(self) -> bool:
        if not self.can_redo():
            return False
        step = self.redo_stack.pop()
        try:
            step.redo_fn()
            self.undo_stack.append(step)
            return True
        except Exception as e:
            print(f"[HistoryManager] Redo error: {e}")
            return False

    def clear(self):
        self.undo_stack.clear()
        self.redo_stack.clear()
        self.current_memory_bytes = 0
        gc.collect()
