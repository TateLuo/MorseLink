import math
import numpy as np

from PySide6.QtCore import QTimer, QRect
from PySide6.QtGui import QPainter, QImage, QColor, QPen
from PySide6.QtWidgets import QWidget


# ==========================================================
# IC-7300 风格瀑布配色（低饱和、工程向）
# 深蓝底 -> 蓝青 -> 绿 -> 黄绿 -> 黄白
# ==========================================================
def intensity_to_rgb_ic7300(x: np.ndarray) -> np.ndarray:
    """
    x: [0,1] float32
    return: uint8 RGB
    """
    x = np.clip(x, 0.0, 1.0).astype(np.float32)

    xp = np.array([0.00, 0.18, 0.38, 0.62, 0.82, 1.00], dtype=np.float32)

    rp = np.array([6, 8, 18, 90, 190, 245], dtype=np.float32)
    gp = np.array([10, 24, 85, 175, 235, 250], dtype=np.float32)
    bp = np.array([26, 70, 95, 70, 35, 210], dtype=np.float32)

    r = np.interp(x, xp, rp)
    g = np.interp(x, xp, gp)
    b = np.interp(x, xp, bp)

    rgb = np.stack([r, g, b], axis=-1)

    # 轻微降低饱和：灰度混合 6%
    gray = (0.2126 * rgb[..., 0] + 0.7152 * rgb[..., 1] + 0.0722 * rgb[..., 2])[..., None]
    rgb = rgb * 0.94 + gray * 0.06

    return np.clip(rgb, 0, 255).astype(np.uint8)


class MorseCodeVisualizer(QWidget):
    """
    IC-7300 风格 CW 频谱 / 瀑布（自适应发报速度）
    - 频谱：用 _level（AGC）画，观感像电台
    - 瀑布：可选用“按键包络”驱动，短按不会被拉长
    - 自适应：根据发报触发密度调整瀑布记忆 / off 熄灭速度
    - 可选：自适应FPS（快手更高帧率，短按更精细）
    """

    def __init__(self, num_channels=11, waterfall_h=420, parent=None):
        super().__init__(parent)

        self.num_channels = int(num_channels)
        self.waterfall_h = int(waterfall_h)

        # ==================================================
        # 接收机/显示参数
        # ==================================================
        self.noise_floor = 0.03
        self.tx_strength = 1.0
        self.display_gain = 2.0

        # 频谱 AGC
        self.attack = 0.8
        self.decay = 0.90

        # ==================================================
        # 瀑布“基础观感”参数（会被自适应插值覆盖）
        # ==================================================
        self.wf_attack = 0.85

        # “慢手”与“快手”两套时间常数（自适应会在两者之间插值）
        self.wf_decay_slow = 0.94         # 慢手：瀑布记忆更长
        self.wf_decay_fast = 0.85         # 快手：瀑布记忆更短
        self.wf_decay = self.wf_decay_slow

        self.wf_off_fast_decay_slow = 0.85  # 慢手：off 熄灭慢（更好看清点划）
        self.wf_off_fast_decay_fast = 0.60  # 快手：off 熄灭快（不糊成直线）
        self.wf_off_fast_decay = self.wf_off_fast_decay_slow

        # ==================================================
        # 瀑布映射参数（IC-7300味道）
        # ==================================================
        self.wf_floor = 0.10
        self.wf_dyn_range_db = 55.0
        self.wf_gamma = 0.85
        self.wf_contrast = 1.10
        self.wf_dither = 0.010

        # ==================================================
        # FPS / 流速（可自适应）
        # ==================================================
        self.enable_adaptive_fps = True

        # 慢手 FPS（ms/帧）与快手 FPS
        self.fps_ms_slow = 40   # ~25 FPS
        self.fps_ms_fast = 16   # ~60 FPS
        self.fps_ms = self.fps_ms_slow

        # ==================================================
        # 是否用“按键包络”驱动瀑布（强烈建议 True）
        # True：短按短、长按长（更像键控）
        # False：瀑布仍用 _wf_level（更像电台，但短按更可能被拉长）
        # ==================================================
        self.waterfall_use_key_envelope = True

        # 包络平滑（让边缘自然一点，不要锯齿）
        self.env_attack = 0.90  # on 上升速度（0.7~0.95）
        self.env_decay = 0.55   # off 衰减速度（越小越“断”，0.4~0.8）

        # ==================================================
        # 自适应速度估计（按键触发密度）
        # ==================================================
        self._speed_score = 0.0  # 0..1
        self.speed_attack = 0.25  # 新速度进入有多快
        self.speed_decay = 0.95   # 速度掉下来有多慢
        self._prev_on_mask = np.zeros(self.num_channels, dtype=bool)

        # ==================================================
        # 通道状态
        # ==================================================
        self.channel_generating = [False] * self.num_channels
        self.channel_pulses = [[] for _ in range(self.num_channels)]

        self._level = np.zeros(self.num_channels, dtype=np.float32)      # 频谱AGC
        self._wf_level = np.zeros(self.num_channels, dtype=np.float32)   # 瀑布记忆（若不用包络）
        self._env = np.zeros(self.num_channels, dtype=np.float32)        # ✅ 按键包络

        self._noise_state = np.random.rand(self.num_channels).astype(np.float32) * self.noise_floor

        # ==================================================
        # 瀑布缓冲
        # ==================================================
        self._wf_width = 0
        self._wf_height = 0
        self.wf = None

        self._phase = 0.0

        # IF 扩散核（频率方向扩散）
        self._if_kernel = np.array(
            [0.02, 0.04, 0.07, 0.11, 0.18, 0.32, 1.00, 0.32, 0.18, 0.11, 0.07, 0.04, 0.02],
            dtype=np.float32
        )
        self._if_half = len(self._if_kernel) // 2

        self._smooth_kernel = np.array([0.20, 0.60, 0.20], dtype=np.float32)

        # timer
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.tick)
        self.timer.start(self.fps_ms)

    # ==================================================
    # 对外接口
    # ==================================================
    def start_generating(self, channel):
        if 0 <= channel < self.num_channels:
            self.channel_generating[channel] = True

    def stop_generating(self, channel):
        if 0 <= channel < self.num_channels:
            self.channel_generating[channel] = False

    def generate_blocks(self, channel_idx=5, count=1, height=3, radius=0, gap_ms=90):
        """
        channel_idx: 通道
        count: 连续块数
        height: on 段持续“帧数”（如果你想也用ms，可以再封一层）
        gap_ms: 最小间隔（毫秒），✅ 与帧率解耦
        """
        if 0 <= channel_idx < self.num_channels:
            dur = max(1, int(height))
            gap_frames = max(1, int(round(float(gap_ms) / float(self.fps_ms))))

            q = self.channel_pulses[channel_idx]
            for _ in range(count):
                if q and q[-1] > 0:
                    q.append(-gap_frames)
                q.append(dur)
                q.append(-gap_frames)

    # ==================================================
    # 内部：根据 speed_score(0..1) 插值参数
    # ==================================================
    def _apply_adaptive_params(self):
        t = float(np.clip(self._speed_score, 0.0, 1.0))

        # 记忆长度
        self.wf_decay = (1 - t) * self.wf_decay_slow + t * self.wf_decay_fast
        # off 熄灭速度
        self.wf_off_fast_decay = (1 - t) * self.wf_off_fast_decay_slow + t * self.wf_off_fast_decay_fast

        # 自适应FPS（可选）
        if self.enable_adaptive_fps:
            new_ms = int(round((1 - t) * self.fps_ms_slow + t * self.fps_ms_fast))
            new_ms = int(np.clip(new_ms, min(self.fps_ms_slow, self.fps_ms_fast), max(self.fps_ms_slow, self.fps_ms_fast)))
            if new_ms != self.fps_ms:
                self.fps_ms = new_ms
                # 重新启动timer（动态流速）
                self.timer.start(self.fps_ms)

    # ==================================================
    # 核心更新
    # ==================================================
    def tick(self):
        n = self.num_channels

        # 连续底噪
        self._noise_state = 0.96 * self._noise_state + 0.04 * np.random.rand(n).astype(np.float32) * self.noise_floor
        level = self._noise_state.copy()

        # 本帧是否在发（用于包络、瀑布门控）
        on_mask = np.zeros(n, dtype=bool)

        # 更新脉冲队列 + 计算本帧 on/off
        for ch in range(n):
            pulse_on = False

            if self.channel_pulses[ch]:
                seg = self.channel_pulses[ch][0]
                if seg > 0:
                    pulse_on = True
                    seg -= 1
                else:
                    pulse_on = False
                    seg += 1

                if seg == 0:
                    self.channel_pulses[ch].pop(0)
                else:
                    self.channel_pulses[ch][0] = seg

            if self.channel_generating[ch] or pulse_on:
                on_mask[ch] = True
                flutter = 0.04 * math.sin(self._phase + ch * 0.6)
                level[ch] += self.tx_strength + flutter

        self._phase += 0.10

        # ========== 速度估计（触发密度）==========
        rising = np.logical_and(on_mask, np.logical_not(self._prev_on_mask))
        press_count = float(np.sum(rising))

        # 映射成 0..1 的速度指标（经验：每帧 >=2 次“新按下”就很快）
        instant = float(np.clip(press_count / 2.0, 0.0, 1.0))

        # 快上慢下
        if instant > self._speed_score:
            self._speed_score += (instant - self._speed_score) * self.speed_attack
        else:
            self._speed_score *= self.speed_decay

        self._prev_on_mask = on_mask.copy()

        # 应用自适应参数（记忆/熄灭/FPS）
        self._apply_adaptive_params()

        # ========== 频谱AGC（用于上面的频谱图）==========
        for i in range(n):
            if level[i] > self._level[i]:
                self._level[i] += (level[i] - self._level[i]) * self.attack
            else:
                self._level[i] *= self.decay

        # ========== 按键包络（用于瀑布“短按不被拉长”）==========
        # 目标：on_mask -> env 变成平滑的 0..1
        for i in range(n):
            target = 1.0 if on_mask[i] else 0.0
            if target > self._env[i]:
                self._env[i] += (target - self._env[i]) * self.env_attack
            else:
                self._env[i] += (target - self._env[i]) * self.env_decay

        # ========== 瀑布短记忆（当你不用包络时才用）==========
        if not self.waterfall_use_key_envelope:
            for i in range(n):
                if on_mask[i]:
                    if self._level[i] > self._wf_level[i]:
                        self._wf_level[i] += (self._level[i] - self._wf_level[i]) * self.wf_attack
                    else:
                        self._wf_level[i] *= self.wf_decay
                else:
                    # off：强制快速熄灭（避免糊成直线）
                    self._wf_level[i] *= self.wf_off_fast_decay

        self.update()

    # ==================================================
    # IC-7300 风格瀑布强度映射
    # ==================================================
    def _wf_map(self, spectrum: np.ndarray) -> np.ndarray:
        s = np.clip(spectrum, 0.0, None).astype(np.float32)

        # 显示噪声地板
        s = np.maximum(0.0, s - self.wf_floor)

        eps = 1e-6
        s_db = 20.0 * np.log10(s + eps)

        s_db = np.clip(s_db, -self.wf_dyn_range_db, 0.0)
        x = (s_db + self.wf_dyn_range_db) / self.wf_dyn_range_db

        x = np.clip((x - 0.5) * self.wf_contrast + 0.5, 0.0, 1.0)
        x = np.power(x, self.wf_gamma)

        if self.wf_dither > 0:
            x = np.clip(
                x + (np.random.rand(*x.shape).astype(np.float32) - 0.5) * self.wf_dither,
                0.0, 1.0
            )
        return x

    # ==================================================
    # 绘制
    # ==================================================
    def paintEvent(self, event):
        p = QPainter(self)

        w, h = self.width(), self.height()
        margin = 8

        spec_h = int(h * 0.25)
        spec_rect = QRect(margin, margin, w - 2 * margin, spec_h)
        wf_rect = QRect(
            margin,
            spec_rect.bottom() + margin,
            w - 2 * margin,
            h - spec_h - 2 * margin
        )

        # 初始化瀑布缓冲
        target_w = max(1, wf_rect.width())
        target_h = max(1, wf_rect.height())

        if (self._wf_width != target_w) or (self._wf_height != target_h) or (self.wf is None):
            self._wf_width = target_w
            self._wf_height = target_h
            self.wf = np.zeros((self._wf_height, self._wf_width, 3), dtype=np.uint8)

        # 背景
        p.fillRect(spec_rect, QColor(8, 12, 22))

        # ==================================================
        # 频谱图（用 _level）
        # ==================================================
        spec_disp = np.log1p(self._level * self.display_gain * 4.0)
        spec_disp /= np.log1p(4.0 * self.display_gain)
        spec_disp = np.clip(spec_disp, 0.0, 1.0).astype(np.float32)

        spec_w = max(1, spec_rect.width())
        spec_h_px = max(1, spec_rect.height())

        spec_spectrum = np.zeros(spec_w, dtype=np.float32)
        spec_centers = np.linspace(0, spec_w - 1, self.num_channels)

        for i, amp in enumerate(spec_disp):
            if amp < 0.01:
                continue
            cx = int(spec_centers[i])
            for dx, wgt in [(-2, 0.12), (-1, 0.35), (0, 1.00), (1, 0.35), (2, 0.12)]:
                x = cx + dx
                if 0 <= x < spec_w:
                    spec_spectrum[x] += amp * wgt

        spec_spectrum = np.clip(spec_spectrum, 0.0, 1.0)
        if spec_w >= 3:
            spec_spectrum = np.convolve(spec_spectrum, np.array([0.2, 0.6, 0.2], dtype=np.float32), mode="same")

        # 网格
        p.setPen(QPen(QColor(20, 40, 60), 1))
        for k in range(1, 4):
            y = spec_rect.top() + int(spec_h_px * k / 4)
            p.drawLine(spec_rect.left(), y, spec_rect.right(), y)

        # 谱线
        p.setPen(QPen(QColor(120, 220, 160), 2))
        last_x = spec_rect.left()
        last_y = spec_rect.bottom()

        for x in range(spec_w):
            amp = float(spec_spectrum[x])
            y = spec_rect.bottom() - int(amp * (spec_h_px - 2)) - 1
            px = spec_rect.left() + x
            if x > 0:
                p.drawLine(last_x, last_y, px, y)
            last_x, last_y = px, y

        # 通道中心刻度
        p.setPen(QPen(QColor(30, 80, 90), 1))
        for cx in spec_centers:
            px = spec_rect.left() + int(cx)
            p.drawLine(px, spec_rect.bottom() - 8, px, spec_rect.bottom())

        # ==================================================
        # 瀑布（关键：选择用包络 or 用 _wf_level）
        # ==================================================
        if self.waterfall_use_key_envelope:
            # 用“按键包络”驱动瀑布：短按不会被AGC/记忆拉长
            # 同时保留一点 flutter 观感（可选）
            base = self._env.copy()
            # 让亮度略带动态（像电台）
            base = np.clip(base * (0.85 + 0.15 * (np.sin(self._phase + np.arange(self.num_channels) * 0.6) * 0.5 + 0.5)), 0.0, 1.0)
            disp = base.astype(np.float32)
        else:
            # 用 _wf_level（更像电台，但短按更可能拉长）
            disp = np.log1p(self._wf_level * self.display_gain * 4.0)
            disp /= np.log1p(4.0 * self.display_gain)
            disp = np.clip(disp, 0.0, 1.0).astype(np.float32)

        spectrum = np.zeros(self._wf_width, dtype=np.float32)
        centers = np.linspace(0, self._wf_width - 1, self.num_channels)

        for i, amp in enumerate(disp):
            if amp < 0.02:
                continue
            cx = int(centers[i])
            left = cx - self._if_half

            k = self._if_kernel * amp
            for j in range(len(k)):
                x = left + j
                if 0 <= x < self._wf_width:
                    spectrum[x] += k[j]

        if self._wf_width >= 3:
            spectrum = np.convolve(spectrum, self._smooth_kernel, mode="same")

        spectrum = np.clip(spectrum, 0.0, 1.2)

        x = self._wf_map(spectrum)
        row_rgb = intensity_to_rgb_ic7300(x)

        # 瀑布滚动：上旧下新
        self.wf[:-1] = self.wf[1:]
        self.wf[-1] = row_rgb

        img = QImage(self.wf.data, self._wf_width, self._wf_height, self._wf_width * 3, QImage.Format_RGB888)
        p.drawImage(wf_rect, img)

        p.end()
