import logging
import string
from PyQt5.QtCore import QObject, QTimer

# 配置日志
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


class ChannelProcessor(QObject):
    def __init__(self, channel_id, buzzer, morsecode_visualizer, signal_light=None):
        super().__init__()
        self.channel_id = channel_id
        self.buzz = buzzer
        self.morsecode_visualizer = morsecode_visualizer
        self.signal_light = signal_light

        # 定义消息列表
        self.message_list = []
        # 当前处理的消息索引
        self.index = 0

        # 间隔定时器状态
        self.isRunningTimerInterval = False
        # 播放定时器状态
        self.isRunningTimerPlay = False

        # 发送消息参数及接收消息和播放逻辑
        self.timer_play_interval = QTimer()
        self.timer_stop_play_audio = QTimer()

        # 连接槽函数
        self.timer_play_interval.timeout.connect(self.start_play)
        self.timer_stop_play_audio.timeout.connect(self.stop)

    def receive_message(self, message):
        """
        接收消息并添加到消息列表。
        如果没有音频正在播放，则开始处理消息。
        """
        self.message_list.append(message)
        logging.info(f"Channel {self.channel_id} received message: {message}")

        # 如果没有音频正在播放，则开始处理消息
        if not self.isRunningTimerInterval and not self.isRunningTimerPlay:
            self.received_audio_process(self.index)

    def received_audio_process(self, index):
        """
        处理接收到的音频消息。
        根据消息列表中的时间间隔启动计时器，准备播放音频。

        参数：
            - index: 消息列表中的索引。
        """
        try:
            message = self.message_list[index]
            raw_wait_time = message[1]
            wait_time = int(float(self.remove_symbols_and_spaces(raw_wait_time)))

            # 计时器只能计算大于 1 毫秒的整数
            if wait_time <= 0:
                wait_time = 10  # 默认最小等待时间
                logging.warning(f"Invalid wait_time: {raw_wait_time}, using default value: {wait_time}")

            if wait_time == 0:
                self.start_play()  # 如果等待时间为 0，直接开始播放
            else:
                # 更新计时器运行状态
                self.isRunningTimerInterval = True
                # 启动计时器
                self.timer_play_interval.start(wait_time)
                logging.info(f"Channel {self.channel_id} waiting for {wait_time} ms before playing.")
        except (ValueError, IndexError) as e:
            logging.error(f"Failed to process wait_time: {e}")

    def start_play(self):
        """
        开始播放音频信号。
        启动蜂鸣器、动画和信号灯，并根据播放时间启动停止计时器。
        """
        if self.index >= len(self.message_list):
            logging.error(f"Index {self.index} out of range for message list.")
            return

        message = self.message_list[self.index]
        try:
            raw_play_time = message[0]
            play_time = int(float(self.remove_symbols_and_spaces(raw_play_time)))

            # 确保播放时间有效
            if play_time <= 0:
                play_time = 10  # 默认最小播放时间
                logging.warning(f"Invalid play_time: {raw_play_time}, using default value: {play_time}")

            # 启动蜂鸣器、动画和信号灯
            if self.buzz:
                self.buzz.start(1)
            if self.morsecode_visualizer:
                self.morsecode_visualizer.start_generating(self.channel_id)
            if self.signal_light:
                self.signal_light.set_state(1)

            # 停止间隔计时器并更新状态
            self.timer_play_interval.stop()
            self.isRunningTimerInterval = False

            # 启动停止播放计时器
            self.isRunningTimerPlay = True
            self.timer_stop_play_audio.start(play_time)
            logging.info(f"Channel {self.channel_id} started playing for {play_time} ms")
        except (ValueError, IndexError) as e:
            logging.error(f"Failed to process play_time: {e}")

    def stop(self):
        """
        停止播放音频信号。
        关闭蜂鸣器、停止动画和信号灯，并处理下一条消息。
        """
        # 停止播放信号
        if self.buzz:
            self.buzz.stop()
        if self.morsecode_visualizer:
            self.morsecode_visualizer.stop_generating(self.channel_id)
        if self.signal_light:
            self.signal_light.set_state(0)

        # 停止播放计时器
        self.timer_stop_play_audio.stop()
        self.isRunningTimerPlay = False

        # 处理下一条消息
        self.index += 1
        if self.index < len(self.message_list):
            self.received_audio_process(self.index)
        else:
            # 重置状态
            self.index = 0
            self.message_list.clear()
            logging.info(f"Channel {self.channel_id} finished processing all messages.")

    def remove_symbols_and_spaces(self, s):
        """
        去除字符串首尾的所有符号和空格。

        参数：
            - s: 输入的字符串或数字。

        返回值：
            - 去除符号和空格后的字符串。如果输入不是字符串，则直接返回。
        """
        if not isinstance(s, str):
            return str(s)  # 将非字符串转换为字符串
        symbols = string.punctuation + string.whitespace
        stripped = s.strip(symbols)
        return stripped if stripped else "0"  # 如果为空，返回默认值 "0"


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

    def receive_message(self, channel_id, message):
        """
        接收指定通道的消息。
        """
        if channel_id in self.channels:
            self.channels[channel_id].receive_message(message)
            logging.info(f"Message routed to channel {channel_id}: {message}")
        else:
            logging.error(f"Channel {channel_id} does not exist.")

    def get_channel(self, channel_id):
        """
        获取指定通道的处理器实例。
        """
        return self.channels.get(channel_id, None)