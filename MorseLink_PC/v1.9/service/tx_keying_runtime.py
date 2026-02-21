from __future__ import annotations

import logging
import time
from typing import Callable, Optional

from PySide6.QtCore import QObject, QTimer

from service.keying_controller import AutoElementEvent, KeyerMode, MorseKeyingController
from utils.adaptive_morse_decoder import AdaptiveMorseDecoder

logger = logging.getLogger(__name__)


class TxKeyingRuntime(QObject):
    """Shared TX keying runtime used by online and training pages."""

    def __init__(
        self,
        parent: Optional[QObject],
        buzzer,
        get_wpm: Optional[Callable[[], int]],
        on_stop_gap_timers: Callable[[], None],
        on_start_letter_timer: Callable[[], None],
        on_manual_down: Optional[Callable[[], None]] = None,
        on_manual_up_begin: Optional[Callable[[], None]] = None,
        on_manual_symbol: Optional[Callable[[str, float, float, float], None]] = None,
        on_auto_symbol: Optional[Callable[[AutoElementEvent], None]] = None,
        on_auto_stopped: Optional[Callable[[], None]] = None,
        on_send_event: Optional[Callable[[str, int], None]] = None,
        tx_now_ms: Optional[Callable[[], int]] = None,
    ) -> None:
        super().__init__(parent)
        self.buzzer = buzzer
        self.get_wpm = get_wpm
        self.on_stop_gap_timers = on_stop_gap_timers
        self.on_start_letter_timer = on_start_letter_timer
        self.on_manual_down = on_manual_down
        self.on_manual_up_begin = on_manual_up_begin
        self.on_manual_symbol = on_manual_symbol
        self.on_auto_symbol = on_auto_symbol
        self.on_auto_stopped = on_auto_stopped
        self.on_send_event = on_send_event
        self.tx_now_ms = tx_now_ms

        self.dot_duration = 100
        self.dash_duration = 300
        self.letter_interval_duration = 300
        self.word_interval_duration = 700
        self.keyer_mode = "straight"
        self.send_buzz_status = False
        self.saved_key = []

        self.pressed_keys_time_interval = 0.0
        self.last_key_pressed_time = 0.0

        self.key_controller = MorseKeyingController(
            parent=self,
            dot_ms=self.dot_duration,
            dash_ms=self.dash_duration,
            keyer_mode=self.to_keyer_mode(self.keyer_mode),
            on_manual_down=self._on_manual_key_down,
            on_manual_up=self._on_manual_key_up,
            on_auto_element=self._on_auto_element,
            on_auto_stopped=self._on_auto_stopped,
        )

    def refresh_runtime(
        self,
        dot_duration: int,
        dash_duration: int,
        letter_interval_duration: int,
        word_interval_duration: int,
        keyer_mode: str,
        send_buzz_status,
        saved_key,
    ) -> None:
        self.dot_duration = int(dot_duration)
        self.dash_duration = int(dash_duration)
        self.letter_interval_duration = int(letter_interval_duration)
        self.word_interval_duration = int(word_interval_duration)
        self.keyer_mode = str(keyer_mode or "straight").lower()
        self.send_buzz_status = send_buzz_status

        if isinstance(saved_key, str):
            self.saved_key = saved_key.split(",")
        elif isinstance(saved_key, list):
            self.saved_key = saved_key
        else:
            self.saved_key = []

        self.key_controller.set_timing(self.dot_duration, self.dash_duration)
        self.key_controller.set_keyer_mode(self.to_keyer_mode(self.keyer_mode))

    def to_keyer_mode(self, mode_text):
        mode = str(mode_text or "straight").lower()
        mapping = {
            "straight": KeyerMode.STRAIGHT,
            "single": KeyerMode.SINGLE,
            "single_paddle": KeyerMode.SINGLE,
            "iambic_a": KeyerMode.IAMBIC_A,
            "iambic_b": KeyerMode.IAMBIC_B,
        }
        return mapping.get(mode, KeyerMode.STRAIGHT)

    def is_straight_mode(self):
        return self.to_keyer_mode(self.keyer_mode) == KeyerMode.STRAIGHT

    def parse_saved_keys(self):
        try:
            dot_key = int(str(self.saved_key[0]).strip().strip('"').strip("'"))
            dah_key = int(str(self.saved_key[1]).strip().strip('"').strip("'"))
        except (IndexError, ValueError, TypeError):
            return None, None
        return dot_key, dah_key

    def prepare_manual_press(self, max_interval_seconds=10):
        self.on_stop_gap_timers()

        if self.last_key_pressed_time != 0:
            self.pressed_keys_time_interval = time.time() - self.last_key_pressed_time
            if self.pressed_keys_time_interval > max_interval_seconds:
                self.pressed_keys_time_interval = 0
        else:
            self.pressed_keys_time_interval = 0

    def press_manual(self, ready: bool, allow_transmit: bool, max_interval_seconds=10):
        if not ready or not allow_transmit or not self.is_straight_mode():
            return False
        if self.key_controller.manual_pressed:
            return False
        self.prepare_manual_press(max_interval_seconds=max_interval_seconds)
        self.key_controller.manual_press()
        return True

    def release_manual(self):
        if not self.key_controller.manual_pressed:
            return False
        self.key_controller.manual_release()
        return True

    def handle_key_press(
        self,
        key: int,
        is_auto_repeat: bool,
        ready: bool,
        allow_transmit: bool,
        max_interval_seconds=10,
    ):
        if is_auto_repeat:
            return False

        dot_key, dah_key = self.parse_saved_keys()
        if dot_key is None or not ready:
            return False

        if self.is_straight_mode():
            if key == dot_key and allow_transmit and not self.key_controller.manual_pressed:
                self.prepare_manual_press(max_interval_seconds=max_interval_seconds)
                self.key_controller.manual_press()
                return True
            return False

        if not allow_transmit:
            return False
        if key == dot_key:
            self.on_stop_gap_timers()
            self.key_controller.press_dit()
            return True
        if key == dah_key:
            self.on_stop_gap_timers()
            self.key_controller.press_dah()
            return True
        return False

    def handle_key_release(self, key: int, is_auto_repeat: bool):
        if is_auto_repeat:
            return False

        dot_key, dah_key = self.parse_saved_keys()
        if dot_key is None:
            return False

        if self.is_straight_mode():
            if key == dot_key and self.key_controller.manual_pressed:
                self.key_controller.manual_release()
                return True
            return False

        if key == dot_key:
            self.key_controller.release_dit()
            return True
        if key == dah_key:
            self.key_controller.release_dah()
            return True
        return False

    def determine_morse_character(self, duration):
        try:
            wpm = int(self.get_wpm()) if callable(self.get_wpm) else 20
            decoder = AdaptiveMorseDecoder(initial_wpm=wpm, sensitivity=0.4, learning_window=100)
            character, _ = decoder.process_duration(duration)
            if character in (".", "-"):
                return character
        except Exception:
            pass

        if float(duration) < float(self.dot_duration):
            return "."
        return "-"

    def stop_all(self, notify=True):
        self.key_controller.stop_all(notify=notify)

    def _emit_tx_event(self, event_type: str, event_time_ms: int):
        if not self.on_send_event:
            return
        self.on_send_event(event_type, int(event_time_ms))

    def _now_event_ms(self):
        if not callable(self.tx_now_ms):
            return 0
        try:
            return int(self.tx_now_ms())
        except Exception:
            return 0

    def _on_manual_key_down(self):
        logger.debug("[TX][manual_down] send_audio=%s", bool(self.send_buzz_status))
        self.buzzer.start(self.send_buzz_status)
        if self.on_manual_down:
            self.on_manual_down()
        self._emit_tx_event("down", self._now_event_ms())

    def _on_manual_key_up(self, duration_ms: float):
        manual_duration_ms = max(0.0, float(duration_ms))
        if self.on_manual_up_begin:
            self.on_manual_up_begin()

        self.buzzer.stop()
        morse_code = self.determine_morse_character(duration_ms)
        logger.debug(
            "[TX][manual_up] measured_ms=%.3f symbol=%s send_audio=%s",
            manual_duration_ms,
            morse_code,
            bool(self.send_buzz_status),
        )

        gap_ms = float(self.pressed_keys_time_interval * 1000.0)
        if self.on_manual_symbol:
            self.on_manual_symbol(morse_code, float(duration_ms), gap_ms, manual_duration_ms)
        self.on_start_letter_timer()
        self._emit_tx_event("up", self._now_event_ms())
        self.last_key_pressed_time = time.time()

    def _on_auto_element(self, event: AutoElementEvent):
        down_event_time_ms = self._now_event_ms()
        self._emit_tx_event("down", down_event_time_ms)
        QTimer.singleShot(
            max(1, int(event.keydown_ms)),
            lambda t=down_event_time_ms + int(event.keydown_ms): self._emit_tx_event("up", t),
        )

        logger.debug(
            "[TX][auto_element] symbol=%s keydown_ms=%s gap_ms=%s send_audio=%s",
            event.symbol,
            event.keydown_ms,
            event.gap_ms,
            bool(self.send_buzz_status),
        )
        self.buzzer.play_for_duration(event.keydown_ms, self.send_buzz_status, interval=event.gap_ms)
        if self.on_auto_symbol:
            self.on_auto_symbol(event)

    def _on_auto_stopped(self):
        self.buzzer.stop_play_for_duration()
        if self.on_auto_stopped:
            self.on_auto_stopped()
        self.on_start_letter_timer()
