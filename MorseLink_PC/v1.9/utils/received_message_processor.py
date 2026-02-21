import logging
import math
import time
from collections import deque
from PySide6.QtCore import QObject, QTimer

logger = logging.getLogger(__name__)


class ChannelProcessor(QObject):
    def __init__(self, channel_id, buzzer, morsecode_visualizer, signal_light=None):
        super().__init__()
        self.channel_id = channel_id
        self.buzz = buzzer
        self.morsecode_visualizer = morsecode_visualizer
        self.signal_light = signal_light

        # 待回放队列：元素为 (play_ms, gap_before_ms)
        self._pending = deque()
        # 当前正在排程/回放的元素：(play_ms, gap_before_ms, target_start_ms)
        self._current = None
        # 上一次“理论抬键时刻”（毫秒, perf_counter 基准）
        self._last_release_ms = None
        # fallback：当设备不支持按时长回放时，用 start/stop 兜底
        self._manual_buzz_hold = False

        self._start_timer = QTimer(self)
        self._start_timer.setSingleShot(True)
        self._start_timer.timeout.connect(self._start_current)

        self._finish_timer = QTimer(self)
        self._finish_timer.setSingleShot(True)
        self._finish_timer.timeout.connect(self._finish_current)

    def receive_message(self, message, *, play_audio=True):
        """
        接收消息并加入回放队列。
        message = [pressed_time_ms, pressed_interval_ms]
        """
        play_ms, gap_before_ms = self._parse_message(message)
        self._pending.append((play_ms, gap_before_ms, bool(play_audio)))
        logger.debug("Channel %s received message: play=%s gap=%s", self.channel_id, play_ms, gap_before_ms)
        self._schedule_next()

    def _now_ms(self):
        return time.perf_counter() * 1000.0

    def _to_ms(self, value, default, minimum):
        try:
            raw = float(value)
        except (TypeError, ValueError):
            return default
        if raw < 0:
            return default
        ms = int(math.ceil(raw))
        if ms >= minimum:
            return ms
        if raw > 0:
            return minimum
        return default

    def _parse_message(self, message):
        if not isinstance(message, (list, tuple)):
            logger.warning("Channel %s got non-list message: %r", self.channel_id, message)
            return 10, 0

        raw_play = message[0] if len(message) > 0 else 0
        raw_gap = message[1] if len(message) > 1 else 0

        play_ms = self._to_ms(raw_play, default=10, minimum=1)
        gap_before_ms = self._to_ms(raw_gap, default=0, minimum=0)
        return play_ms, gap_before_ms

    def _schedule_next(self):
        if self._current is not None or not self._pending:
            return

        play_ms, gap_before_ms, play_audio = self._pending.popleft()
        now_ms = self._now_ms()

        if self._last_release_ms is None:
            target_start_ms = now_ms + gap_before_ms
        else:
            # gap 是“上一键抬起”到“当前键按下”的间隔；
            # 若网络延迟导致已过目标时刻，则立即播放，避免间隔被二次叠加。
            target_start_ms = max(now_ms, self._last_release_ms + gap_before_ms)

        self._current = (play_ms, gap_before_ms, target_start_ms, play_audio)

        delay_ms = max(0, int(round(target_start_ms - now_ms)))
        if delay_ms <= 0:
            self._start_current()
            return

        self._start_timer.start(delay_ms)
        logger.debug("Channel %s scheduled in %s ms", self.channel_id, delay_ms)

    def _start_current(self):
        if self._current is None:
            return

        play_ms, _, _, play_audio = self._current

        if play_audio:
            self._play_audio(play_ms)
        self._play_visual(play_ms)
        self._play_signal_light(play_ms)

        self._finish_timer.start(max(1, play_ms))
        logger.debug("Channel %s started playing for %s ms", self.channel_id, play_ms)

    def _finish_current(self):
        if self._current is None:
            return

        play_ms, _, target_start_ms, _ = self._current
        self._last_release_ms = target_start_ms + play_ms

        if self._manual_buzz_hold and self.buzz:
            try:
                self.buzz.stop()
            except Exception:
                pass
            self._manual_buzz_hold = False

        self._current = None
        self._schedule_next()

    def _play_audio(self, play_ms):
        if not self.buzz:
            return

        try:
            self.buzz.play_for_duration(play_ms, True, interval=0)
            self._manual_buzz_hold = False
        except Exception:
            self.buzz.start(1)
            self._manual_buzz_hold = True

    def _play_visual(self, play_ms):
        if not self.morsecode_visualizer:
            return

        fps_ms = int(getattr(self.morsecode_visualizer, "fps_ms", 40) or 40)
        fps_ms = max(1, fps_ms)
        height_frames = max(1, int(math.ceil(float(play_ms) / float(fps_ms))))

        try:
            self.morsecode_visualizer.generate_blocks(
                channel_idx=self.channel_id,
                count=1,
                height=height_frames,
                gap_ms=0,
            )
        except Exception:
            self.morsecode_visualizer.start_generating(self.channel_id)
            QTimer.singleShot(
                max(1, play_ms),
                lambda ch=self.channel_id: self.morsecode_visualizer.stop_generating(ch),
            )

    def _play_signal_light(self, play_ms):
        if not self.signal_light:
            return

        if hasattr(self.signal_light, "switch_to_red_for_duration"):
            self.signal_light.switch_to_red_for_duration(play_ms)
            return

        self.signal_light.set_state(1)
        QTimer.singleShot(max(1, play_ms), lambda: self.signal_light.set_state(0))


class MultiChannelProcessor(QObject):
    def __init__(self, main_channel_buzzer, main_channel_morsecode_visualizer, main_channel_signal_light):
        super().__init__()
        self.channels = {}

        # 初始化主通道（第 5 个通道，channel_id = 4）
        self.channels[5] = ChannelProcessor(5, main_channel_buzzer, main_channel_morsecode_visualizer, main_channel_signal_light)

        # 初始化其他通道
        for i in range(11):
            if i != 5:  # 跳过主通道
                self.channels[i] = ChannelProcessor(i, main_channel_buzzer, main_channel_morsecode_visualizer, main_channel_signal_light)

    def receive_message(self, channel_id, message, *, play_audio=True):
        """
        接收指定通道的消息。
        """
        if channel_id in self.channels:
            self.channels[channel_id].receive_message(message, play_audio=play_audio)
            logger.debug("Message routed to channel %s: %s", channel_id, message)
        else:
            logger.error("Channel %s does not exist.", channel_id)

    def get_channel(self, channel_id):
        """
        获取指定通道的处理器实例。
        """
        return self.channels.get(channel_id, None)
