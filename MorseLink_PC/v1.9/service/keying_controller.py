from __future__ import annotations

import time
from dataclasses import dataclass
from enum import Enum
from typing import Callable, Optional

from PySide6.QtCore import QObject, Qt, QTimer


class KeyElement(str, Enum):
    DIT = "."
    DAH = "-"


class KeyerState(str, Enum):
    IDLE = "idle"
    KEYDOWN = "keydown"
    GAP = "gap"


class IambicMode(str, Enum):
    OFF = "off"
    A = "a"
    B = "b"


class KeyerMode(str, Enum):
    STRAIGHT = "straight"
    SINGLE = "single"
    IAMBIC_A = "iambic_a"
    IAMBIC_B = "iambic_b"


@dataclass(frozen=True)
class AutoElementEvent:
    symbol: str
    keydown_ms: int
    gap_ms: int


class MorseKeyingController(QObject):
    """Shared manual/auto key controller based on key_rule.md."""

    def __init__(
        self,
        parent: Optional[QObject] = None,
        dot_ms: int = 100,
        dash_ms: int = 300,
        keyer_mode: KeyerMode = KeyerMode.IAMBIC_A,
        on_manual_down: Optional[Callable[[], None]] = None,
        on_manual_up: Optional[Callable[[float], None]] = None,
        on_auto_element: Optional[Callable[[AutoElementEvent], None]] = None,
        on_auto_stopped: Optional[Callable[[], None]] = None,
    ) -> None:
        super().__init__(parent)
        self._dot_ms = max(1, int(dot_ms))
        self._dash_ms = max(1, int(dash_ms))
        self._keyer_mode = keyer_mode

        self._on_manual_down = on_manual_down
        self._on_manual_up = on_manual_up
        self._on_auto_element = on_auto_element
        self._on_auto_stopped = on_auto_stopped

        self._manual_pressed = False
        self._manual_started_at = 0.0

        self._state = KeyerState.IDLE
        self._current_element: Optional[KeyElement] = None
        self._last_element: Optional[KeyElement] = None

        self._dit_pressed = False
        self._dah_pressed = False
        self._dit_memory = False
        self._dah_memory = False
        self._squeeze_seen = False

        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.setTimerType(Qt.PreciseTimer)
        self._timer.timeout.connect(self._on_timer_timeout)

    @property
    def auto_active(self) -> bool:
        return self._state != KeyerState.IDLE

    @property
    def manual_pressed(self) -> bool:
        return self._manual_pressed

    def set_timing(self, dot_ms: int, dash_ms: int) -> None:
        self._dot_ms = max(1, int(dot_ms))
        self._dash_ms = max(1, int(dash_ms))

    def set_keyer_mode(self, mode: KeyerMode | str) -> None:
        if isinstance(mode, KeyerMode):
            self._keyer_mode = mode
            return
        try:
            self._keyer_mode = KeyerMode(str(mode).lower())
        except ValueError:
            self._keyer_mode = KeyerMode.STRAIGHT

    @property
    def keyer_mode(self) -> KeyerMode:
        return self._keyer_mode

    def set_iambic_mode(self, mode: IambicMode) -> None:
        if mode == IambicMode.A:
            self._keyer_mode = KeyerMode.IAMBIC_A
        elif mode == IambicMode.B:
            self._keyer_mode = KeyerMode.IAMBIC_B
        else:
            self._keyer_mode = KeyerMode.SINGLE

    def manual_press(self) -> None:
        if self._manual_pressed:
            return
        self._manual_pressed = True
        self._manual_started_at = time.perf_counter()
        if self._on_manual_down:
            self._on_manual_down()

    def manual_release(self, emit: bool = True) -> Optional[float]:
        if not self._manual_pressed:
            return None
        duration_ms = (time.perf_counter() - self._manual_started_at) * 1000.0
        self._manual_pressed = False
        if emit and self._on_manual_up:
            self._on_manual_up(duration_ms)
        return duration_ms

    def press_dit(self) -> None:
        if self._keyer_mode == KeyerMode.STRAIGHT:
            return
        self._dit_pressed = True
        if self._state == KeyerState.KEYDOWN:
            self._dit_memory = True
        self._update_squeeze()
        self._start_if_idle()

    def release_dit(self) -> None:
        self._dit_pressed = False

    def press_dah(self) -> None:
        if self._keyer_mode == KeyerMode.STRAIGHT:
            return
        self._dah_pressed = True
        if self._state == KeyerState.KEYDOWN:
            self._dah_memory = True
        self._update_squeeze()
        self._start_if_idle()

    def release_dah(self) -> None:
        self._dah_pressed = False

    def stop_auto(self, notify: bool = True) -> None:
        was_active = self._state != KeyerState.IDLE or self._timer.isActive()
        self._timer.stop()
        self._state = KeyerState.IDLE
        self._current_element = None
        self._dit_pressed = False
        self._dah_pressed = False
        self._dit_memory = False
        self._dah_memory = False
        self._squeeze_seen = False
        if notify and was_active and self._on_auto_stopped:
            self._on_auto_stopped()

    def stop_all(self, notify: bool = True) -> None:
        self.manual_release(emit=False)
        self.stop_auto(notify=notify)

    def _update_squeeze(self) -> None:
        if self._dit_pressed and self._dah_pressed:
            self._squeeze_seen = True

    def _start_if_idle(self) -> None:
        if self._keyer_mode == KeyerMode.STRAIGHT:
            return
        if self._state != KeyerState.IDLE:
            return
        next_element = self._select_next_element()
        if next_element is None:
            return
        self._begin_element(next_element)

    def _on_timer_timeout(self) -> None:
        if self._state == KeyerState.KEYDOWN:
            self._state = KeyerState.GAP
            self._current_element = None
            self._timer.start(self._dot_ms)
            return

        if self._state != KeyerState.GAP:
            return

        next_element = self._select_next_element()
        if next_element is None:
            self._enter_idle()
            return
        self._begin_element(next_element)

    def _begin_element(self, element: KeyElement) -> None:
        self._state = KeyerState.KEYDOWN
        self._current_element = element
        self._last_element = element
        duration = self._dot_ms if element == KeyElement.DIT else self._dash_ms
        # 先启动定时器，避免 UI 回调耗时影响键控节拍。
        self._timer.start(duration)
        if self._on_auto_element:
            self._on_auto_element(
                AutoElementEvent(symbol=element.value, keydown_ms=duration, gap_ms=self._dot_ms)
            )

    def _enter_idle(self) -> None:
        was_active = self._state != KeyerState.IDLE or self._timer.isActive()
        self._timer.stop()
        self._state = KeyerState.IDLE
        self._current_element = None
        self._dit_memory = False
        self._dah_memory = False
        self._squeeze_seen = False
        if was_active and self._on_auto_stopped:
            self._on_auto_stopped()

    def _select_next_element(self) -> Optional[KeyElement]:
        dual_pressed = self._dit_pressed and self._dah_pressed
        dual_memory = self._dit_memory and self._dah_memory
        dual_intent = dual_pressed or dual_memory

        if self._keyer_mode == KeyerMode.STRAIGHT:
            self._squeeze_seen = False
            return None

        if (
            self._keyer_mode == KeyerMode.IAMBIC_B
            and self._squeeze_seen
            and not dual_intent
            and self._last_element is not None
        ):
            self._squeeze_seen = False
            return self._opposite(self._last_element)

        if self._keyer_mode in (KeyerMode.IAMBIC_A, KeyerMode.IAMBIC_B):
            if dual_intent:
                if dual_memory:
                    self._dit_memory = False
                    self._dah_memory = False
                if self._last_element is None:
                    return KeyElement.DIT
                return self._opposite(self._last_element)
        elif dual_intent:
            if dual_memory:
                self._dit_memory = False
                self._dah_memory = False
            return KeyElement.DAH

        if self._dit_pressed and not self._dah_pressed:
            return KeyElement.DIT
        if self._dah_pressed and not self._dit_pressed:
            return KeyElement.DAH

        if self._dit_memory and not self._dah_memory:
            self._dit_memory = False
            return KeyElement.DIT
        if self._dah_memory and not self._dit_memory:
            self._dah_memory = False
            return KeyElement.DAH

        self._squeeze_seen = False
        return None

    @staticmethod
    def _opposite(element: KeyElement) -> KeyElement:
        return KeyElement.DAH if element == KeyElement.DIT else KeyElement.DIT
