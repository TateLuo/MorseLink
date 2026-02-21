import time
import math
import threading
from collections import deque
import logging
from typing import Deque, Optional, Callable

import numpy as np

try:
    import sounddevice as sd
except Exception:
    sd = None

from .config_manager import ConfigManager


logger = logging.getLogger(__name__)


class _SoundDeviceBuzzer:
    """Low-latency buzzer based on sounddevice callback stream."""

    def __init__(self):
        if sd is None:
            raise RuntimeError("sounddevice is not available")

        configer = ConfigManager()
        self.freq = float(configer.get_buzz_freq())

        self.sample_rate = 48000
        self.block_size = 256
        self.channels = 1
        self.volume = 0.45

        self.attack_ms = 0.35
        self.release_ms = 1.0
        # Sub-ms taps are not physically audible; keep a practical audible floor.
        self.min_click_ms = 12.0
        # For ultra-short clicks, apply a light floor without stretching normal dots.
        self.tap_feedback_min_ms = 28.0
        # Startup guard to avoid first-symbol drop on some backends/devices.
        self.start_guard_ms = 12.0
        self._phase = 0.0
        self._phase_inc = (2.0 * math.pi * self.freq) / self.sample_rate
        self._amp = 0.0

        self._attack_coeff = self._ms_to_coeff(self.attack_ms)
        self._release_coeff = self._ms_to_coeff(self.release_ms)
        self._min_click_samples = self._samples(self.min_click_ms)
        self._tap_feedback_min_samples = self._samples(self.tap_feedback_min_ms)
        self._start_guard_samples = self._samples(self.start_guard_ms)
        self._manual_hold_remaining = 0
        self._manual_started_at = 0.0
        self._manual_emitted_samples = 0

        self._lock = threading.RLock()

        self._loop_on = False

        self._pulse_segments: Deque[tuple[bool, int]] = deque()
        self._pulse_on = False
        self._pulse_remaining = 0

        self._morse_segments: Deque[tuple[bool, int]] = deque()
        self._morse_on = False
        self._morse_remaining = 0
        self._morse_total_samples = 0
        self._morse_done_samples = 0
        self._morse_state = "idle"  # idle | playing | finished
        self._morse_token = 0

        self.playback_callback: Optional[Callable] = None
        self.sound_for_test_listen = None

        stream_kwargs = dict(
            samplerate=self.sample_rate,
            blocksize=self.block_size,
            channels=self.channels,
            dtype="float32",
            latency="high",
            callback=self._audio_callback,
        )
        try:
            self._stream = sd.OutputStream(
                prime_output_buffers_using_stream_callback=True,
                **stream_kwargs,
            )
        except TypeError:
            self._stream = sd.OutputStream(**stream_kwargs)
        self._stream.start()
        logger.info("BuzzerSimulator(sounddevice) initialized: %s Hz", self.sample_rate)

    @property
    def is_playing(self) -> bool:
        with self._lock:
            return (
                self._loop_on
                or self._manual_hold_remaining > 0
                or self._pulse_remaining > 0
                or bool(self._pulse_segments)
                or self._morse_state == "playing"
                or self._morse_remaining > 0
                or bool(self._morse_segments)
            )

    def _ms_to_coeff(self, ms: float) -> float:
        seconds = max(0.0005, float(ms) / 1000.0)
        return float(math.exp(-1.0 / (seconds * self.sample_rate)))

    def _samples(self, ms: float) -> int:
        raw_ms = float(ms)
        if raw_ms <= 0:
            return 0
        samples = int(round(raw_ms * self.sample_rate / 1000.0))
        # Keep any positive duration audible, even if it is shorter than one sample period.
        return max(1, samples)

    def _samples_to_ms(self, samples: int) -> float:
        if samples <= 0:
            return 0.0
        return float(samples) * 1000.0 / float(self.sample_rate)

    def _notify(self, value):
        cb = self.playback_callback
        if cb:
            try:
                cb(value)
            except Exception:
                logger.exception("playback_callback error")

    def _is_scheduler_idle_locked(self) -> bool:
        return (
            not self._loop_on
            and self._manual_hold_remaining <= 0
            and self._pulse_remaining <= 0
            and not self._pulse_segments
            and self._morse_remaining <= 0
            and not self._morse_segments
        )

    def _normalized_tone_samples(self, duration_ms: float) -> int:
        val = self._samples(duration_ms)
        if 0 < val < self._min_click_samples:
            return self._min_click_samples
        return val

    def _iter_morse_tokens(self, morse_code: str):
        i = 0
        s = morse_code or ""
        while i < len(s):
            if s.startswith("///", i):
                yield "///"
                i += 3
            else:
                yield s[i]
                i += 1

    def _ensure_pulse_locked(self):
        while self._pulse_remaining <= 0 and self._pulse_segments:
            self._pulse_on, self._pulse_remaining = self._pulse_segments.popleft()
        if self._pulse_remaining <= 0 and not self._pulse_segments:
            self._pulse_on = False
            self._pulse_remaining = 0

    def _ensure_morse_locked(self):
        while self._morse_remaining <= 0 and self._morse_segments:
            self._morse_on, self._morse_remaining = self._morse_segments.popleft()
        if self._morse_remaining <= 0 and not self._morse_segments:
            self._morse_on = False
            self._morse_remaining = 0

    def _advance_pulse_locked(self, frames: int):
        remain = frames
        while remain > 0:
            self._ensure_pulse_locked()
            if self._pulse_remaining <= 0:
                break
            take = min(remain, self._pulse_remaining)
            self._pulse_remaining -= take
            remain -= take

    def _advance_morse_locked(self, frames: int):
        remain = frames
        while remain > 0:
            self._ensure_morse_locked()
            if self._morse_remaining <= 0:
                break
            take = min(remain, self._morse_remaining)
            self._morse_remaining -= take
            self._morse_done_samples += take
            remain -= take

        if self._morse_state == "playing":
            self._ensure_morse_locked()
            if self._morse_remaining <= 0 and not self._morse_segments:
                self._morse_state = "finished"
                self.sound_for_test_listen = None

    def _advance_manual_hold_locked(self, frames: int):
        if self._manual_hold_remaining <= 0:
            return
        self._manual_hold_remaining = max(0, self._manual_hold_remaining - frames)

    def _consume_scheduler_locked(self, max_frames: int) -> tuple[int, bool]:
        self._ensure_pulse_locked()
        self._ensure_morse_locked()

        manual_tone_on = self._loop_on or self._manual_hold_remaining > 0
        tone_on = manual_tone_on or self._pulse_on or self._morse_on

        step = max_frames
        if self._manual_hold_remaining > 0:
            step = min(step, self._manual_hold_remaining)
        if self._pulse_remaining > 0:
            step = min(step, self._pulse_remaining)
        if self._morse_remaining > 0:
            step = min(step, self._morse_remaining)

        if step <= 0:
            step = max_frames

        if tone_on and manual_tone_on and step > 0:
            self._manual_emitted_samples += int(step)

        self._advance_manual_hold_locked(step)
        self._advance_pulse_locked(step)
        self._advance_morse_locked(step)
        return step, tone_on

    def _render_block(self, frames: int, tone_on: bool) -> np.ndarray:
        target = self.volume if tone_on else 0.0
        coeff = self._attack_coeff if target > self._amp else self._release_coeff

        n = np.arange(1, frames + 1, dtype=np.float32)
        powers = np.power(coeff, n).astype(np.float32, copy=False)
        env = target + (self._amp - target) * powers
        self._amp = float(env[-1])

        phases = self._phase + self._phase_inc * np.arange(frames, dtype=np.float32)
        tone = np.sin(phases).astype(np.float32, copy=False)
        self._phase = float((self._phase + self._phase_inc * frames) % (2.0 * math.pi))

        return tone * env

    def _audio_callback(self, outdata, frames, time_info, status):
        # Keep callback path free of any logging/IO to avoid underruns.
        _ = status

        mono = np.zeros(frames, dtype=np.float32)
        pos = 0

        while pos < frames:
            with self._lock:
                step, tone_on = self._consume_scheduler_locked(frames - pos)
            block = self._render_block(step, tone_on)
            mono[pos : pos + step] = block
            pos += step

        if self.channels == 1:
            outdata[:frames, 0] = mono
        else:
            outdata[:frames, :] = mono[:, None]

    def _start_morse_progress_thread(self, token: int):
        def _worker():
            last_percent = -1
            while True:
                with self._lock:
                    if token != self._morse_token:
                        return
                    state = self._morse_state
                    done = self._morse_done_samples
                    total = max(1, self._morse_total_samples)

                if state != "playing":
                    break

                percent = int((done / total) * 100)
                percent = max(0, min(100, percent))
                if percent != last_percent:
                    last_percent = percent
                    self._notify(percent)

                time.sleep(0.08)

            with self._lock:
                if token != self._morse_token:
                    return
                if self._morse_state == "finished":
                    self._morse_state = "idle"
                    self.sound_for_test_listen = None
                    final = "finished"
                else:
                    return

            self._notify(final)

        threading.Thread(target=_worker, daemon=True).start()

    def start(self, switch):
        if not switch:
            return
        min_hold = 0
        was_idle = False
        with self._lock:
            was_idle = self._is_scheduler_idle_locked()
            if not self._loop_on:
                self._manual_started_at = time.perf_counter()
                self._manual_emitted_samples = 0
            self._loop_on = True
            if self._min_click_samples > 0:
                min_hold = self._min_click_samples
                if was_idle and self._start_guard_samples > 0:
                    # Compensate for possible device/backend wake-up drop on ultra-short manual taps.
                    min_hold += self._start_guard_samples * 2
                self._manual_hold_remaining = max(self._manual_hold_remaining, min_hold)
            manual_hold = int(self._manual_hold_remaining)
        stream_active = bool(getattr(self._stream, "active", False)) if hasattr(self, "_stream") else False
        logger.info(
            "[AUDIO][start] idle=%s min_hold_ms=%.3f manual_hold_ms=%.3f stream_active=%s",
            was_idle,
            self._samples_to_ms(min_hold),
            self._samples_to_ms(manual_hold),
            stream_active,
        )
        self._notify("started")

    def stop(self):
        held_ms = 0.0
        emitted_ms = 0.0
        with self._lock:
            if self._manual_started_at > 0:
                held_ms = max(0.0, (time.perf_counter() - self._manual_started_at) * 1000.0)
            emitted_ms = self._samples_to_ms(int(self._manual_emitted_samples))
            self._loop_on = False
            pulse_pending = len(self._pulse_segments)
            manual_hold = int(self._manual_hold_remaining)
            morse_state = str(self._morse_state)
        stream_active = bool(getattr(self._stream, "active", False)) if hasattr(self, "_stream") else False
        logger.info(
            "[AUDIO][stop] held_ms=%.3f emitted_ms=%.3f residual_hold_ms=%.3f pulse_pending=%d morse_state=%s stream_active=%s",
            held_ms,
            emitted_ms,
            self._samples_to_ms(manual_hold),
            pulse_pending,
            morse_state,
            stream_active,
        )
        self._notify("stopped")

    def play_for_duration(self, duration, switch, interval=35):
        if not switch:
            return
        req_ms = max(0.0, float(duration))
        req_gap_ms = max(0.0, float(interval))
        raw_dur = self._samples(duration)
        short_click = 0 < raw_dur < self._min_click_samples
        dur = self._min_click_samples if short_click else raw_dur
        gap = self._samples(interval)
        tap_floor_applied = False
        if gap <= 0 and short_click and 0 < dur < self._tap_feedback_min_samples:
            dur = self._tap_feedback_min_samples
            tap_floor_applied = True
        idle = False
        tone_dur = dur
        with self._lock:
            if dur > 0:
                idle = self._is_scheduler_idle_locked()
                if idle and self._start_guard_samples > 0:
                    # Keep first click immediate (no leading silence), but extend its audible window.
                    tone_dur += self._start_guard_samples
                    if short_click:
                        # Very short taps need extra protection against backend/device wake-up loss.
                        tone_dur += self._start_guard_samples
                self._pulse_segments.append((True, tone_dur))
            if gap > 0:
                self._pulse_segments.append((False, gap))

        logger.info(
            "[AUDIO][pulse] req_ms=%.3f req_gap_ms=%.3f raw_ms=%.3f out_ms=%.3f "
            "short_click=%s tap_floor=%s tap_floor_ms=%.3f idle=%s guard_ms=%.3f",
            req_ms,
            req_gap_ms,
            self._samples_to_ms(raw_dur),
            self._samples_to_ms(tone_dur),
            short_click,
            tap_floor_applied,
            self._samples_to_ms(self._tap_feedback_min_samples),
            idle,
            self._samples_to_ms(self._start_guard_samples),
        )

    def stop_play_for_duration(self):
        with self._lock:
            self._pulse_segments.clear()
            self._pulse_on = False
            self._pulse_remaining = 0

    def play_morse_code(self, morse_code, dot_duration, dash_duration, char_interval, word_interval):
        self.stop_playing_morse_code()

        dot = self._normalized_tone_samples(dot_duration)
        dah = self._normalized_tone_samples(dash_duration)
        char_gap = self._samples(char_interval)
        word_gap = self._samples(word_interval)

        segments: Deque[tuple[bool, int]] = deque()
        total = 0

        for tok in self._iter_morse_tokens(morse_code):
            if tok == ".":
                if dot > 0:
                    segments.append((True, dot))
                    total += dot
                if dot > 0:
                    segments.append((False, dot))
                    total += dot
            elif tok == "-":
                if dah > 0:
                    segments.append((True, dah))
                    total += dah
                if dot > 0:
                    segments.append((False, dot))
                    total += dot
            elif tok == "/":
                if char_gap > 0:
                    segments.append((False, char_gap))
                    total += char_gap
            elif tok == "///":
                if word_gap > 0:
                    segments.append((False, word_gap))
                    total += word_gap

        if total <= 0:
            self._notify("finished")
            return

        was_idle = False
        first_tone_samples = 0
        tone_count = 0
        gap_count = 0
        with self._lock:
            was_idle = self._is_scheduler_idle_locked()
            if self._start_guard_samples > 0 and was_idle and segments:
                # Apply guard to the first tone segment instead of delaying with leading silence.
                adjusted: Deque[tuple[bool, int]] = deque()
                applied = False
                for is_tone, length in segments:
                    if not applied and is_tone and length > 0:
                        adjusted.append((True, int(length) + int(self._start_guard_samples)))
                        total += self._start_guard_samples
                        applied = True
                    else:
                        adjusted.append((is_tone, length))
                segments = adjusted

            for is_tone, length in segments:
                if is_tone:
                    tone_count += 1
                    if first_tone_samples <= 0 and length > 0:
                        first_tone_samples = int(length)
                else:
                    gap_count += 1

            self._morse_token += 1
            token = self._morse_token
            self._morse_segments = segments
            self._morse_on = False
            self._morse_remaining = 0
            self._morse_total_samples = total
            self._morse_done_samples = 0
            self._morse_state = "playing"
            self.sound_for_test_listen = morse_code

        logger.info(
            "[AUDIO][morse] code=%s dot_ms=%.3f dash_ms=%.3f letter_gap_ms=%.3f word_gap_ms=%.3f "
            "tones=%d gaps=%d first_tone_ms=%.3f total_ms=%.3f idle=%s",
            str(morse_code),
            float(dot_duration),
            float(dash_duration),
            float(char_interval),
            float(word_interval),
            tone_count,
            gap_count,
            self._samples_to_ms(first_tone_samples),
            self._samples_to_ms(total),
            was_idle,
        )

        self._notify("started")
        self._start_morse_progress_thread(token)

    def stop_playing_morse_code(self):
        with self._lock:
            was_playing = self._morse_state == "playing"
            self._morse_token += 1
            self._morse_segments.clear()
            self._morse_on = False
            self._morse_remaining = 0
            self._morse_total_samples = 0
            self._morse_done_samples = 0
            self._morse_state = "idle"
            self.sound_for_test_listen = None

        if was_playing:
            self._notify("stopped")

    def set_playback_callback(self, callback):
        self.playback_callback = callback

    def close(self):
        try:
            if self._stream is not None:
                self._stream.stop()
                self._stream.close()
        except Exception:
            logger.exception("Failed to close sounddevice stream")


class BuzzerSimulator:
    """Buzzer facade backed only by sounddevice."""

    def __init__(self):
        self._impl = None
        try:
            self._impl = _SoundDeviceBuzzer()
            self.backend = "sounddevice"
        except Exception as e:
            raise RuntimeError("sounddevice backend unavailable, and pygame fallback was removed") from e

    def __getattr__(self, item):
        return getattr(self._impl, item)

    @property
    def is_playing(self):
        return getattr(self._impl, "is_playing", False)

    @property
    def sound_for_test_listen(self):
        return getattr(self._impl, "sound_for_test_listen", None)

    @sound_for_test_listen.setter
    def sound_for_test_listen(self, value):
        setattr(self._impl, "sound_for_test_listen", value)

    def start(self, switch):
        self._impl.start(switch)

    def stop(self):
        self._impl.stop()

    def play_for_duration(self, duration, switch, interval=35):
        self._impl.play_for_duration(duration, switch, interval)

    def stop_play_for_duration(self):
        self._impl.stop_play_for_duration()

    def play_morse_code(self, morse_code, dot_duration, dash_duration, char_interval, word_interval):
        self._impl.play_morse_code(morse_code, dot_duration, dash_duration, char_interval, word_interval)

    def stop_playing_morse_code(self):
        self._impl.stop_playing_morse_code()

    def set_playback_callback(self, callback):
        self._impl.set_playback_callback(callback)

    def close(self):
        if hasattr(self._impl, "close"):
            self._impl.close()

    def __del__(self):
        try:
            self.close()
        except Exception:
            pass
