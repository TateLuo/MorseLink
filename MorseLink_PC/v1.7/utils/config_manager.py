import json
import os
from PyQt5.QtCore import QSettings
from PyQt5.QtWidgets import QMessageBox

class ConfigManager:
    def __init__(self, config_file='config.ini', db_dir='resources/config'):
        self.config_file = os.path.join(db_dir, config_file)
        self.settings = QSettings(self.config_file, QSettings.IniFormat)
        self.initialize_config()

    def initialize_config(self):
        """检查是否存在配置项，并根据需要设置默认值"""
        default_values = {
            "Version/current_version": "1.2.0",
            "Version/first_run_status": True,
            "SelfInfo/my_call": "None",
            "Time/dot_time": 110,
            "Time/dash_time": 300,
            "Time/letter_interval_duration_time": 150,
            "Time/word_interval_duration_time": 320,
            "server/url": "这里请填写你服务器的ip",
            "server/port": 1883,
            "server/channel_name": 7000,
            "server/port": 1883,
            "Setting/language": "any",
            "Setting/buzz_freq": 800,
            "Setting/autokey_status": False,
            "Setting/keyborad_key": "81,87",
            "Setting/send_buzz_status": True,
            "Setting/receive_buzz_status": True,
            "Setting/translation_visibility": True,
            "Setting/visualizer_visibility": True,
            "Setting/sender_font_size": 15,
            "Listen/min_word_length": 4,
            "Listen/max_word_length": 4,
            "Listen/min_groups": 4,
            "Listen/max_groups": 4,
            "Listen/weight": 0.2,
            "Decoder/wpm": 20,  # Initial version
            "Decoder/version": "1.0.0",  # Initial version
            "Decoder/dot_duration": 100.0,  # Default dot duration
            "Decoder/dash_threshold": 200.0,  # Default dash threshold
            "Decoder/speed_profile": json.dumps([]),  # Empty speed profile
            "Decoder/history": json.dumps([]),  # Empty history
        }

        # 遍历字典，确保每个配置项都有默认值
        for key, value in default_values.items():
            if not self.settings.contains(key):
                self.set_value(key, value)

    def get_value(self, key, default=None, value_type=str):
        """获取配置值，并根据类型进行转换"""
        try:
            value = self.settings.value(key, default)
            if value is None:
                return default
            if value_type == bool:
                return str(value).lower() in ['true', '1', 'yes']
            return value_type(value)
        except Exception as e:
            QMessageBox.warning(None, "警告", f"获取配置项失败: {e}")
            return default

    def set_value(self, key, value):
        """设置配置值"""
        print(f"Setting {key} to {value}")
        if value is None:
            value = ""  # 设置为默认值
        self.settings.setValue(key, value)

    # 获取和保存历史数据
    def get_history(self):
        return json.loads(self.get_value("Decoder/history", "[]", value_type=str))

    def set_history(self, history):
        self.set_value("Decoder/history", json.dumps(history))

    # 获取和保存WPM
    def get_wpm(self):
        return self.get_value("Decoder/dot_duration", value_type=int)

    def set_wpm(self, value):
        self.set_value("Decoder/dot_duration", int(value))

    # 获取和保存点时长
    def get_dot_duration(self):
        return self.get_value("Decoder/dot_duration", value_type=float)

    def set_dot_duration(self, value):
        self.set_value("Decoder/dot_duration", float(value))

    # 获取和保存划时长阈值
    def get_dash_threshold(self):
        return self.get_value("Decoder/dash_threshold", value_type=float)

    def set_dash_threshold(self, value):
        self.set_value("Decoder/dash_threshold", float(value))

    # 获取和保存速度配置
    def get_speed_profile(self):
        return json.loads(self.get_value("Decoder/speed_profile", "[]", value_type=str))

    def set_speed_profile(self, profile):
        self.set_value("Decoder/speed_profile", json.dumps(profile))

    # 获取和保存版本号
    def get_version(self):
        return self.get_value("Decoder/version", value_type=str)

    def set_version(self, version):
        self.set_value("Decoder/version", version)

    # 获取和保存呼号
    def get_my_call(self):
        return self.get_value("SelfInfo/my_call", value_type=str)

    def set_my_call(self, value):
        self.set_value("SelfInfo/my_call", value)

    # 获取和保存是否第一次启动状态
    def get_first_run_status(self):
        return self.get_value("Version/first_run_status", value_type=bool)

    def set_first_run_status(self, value):
        self.set_value("Version/first_run_status", value)

    # 获取和保存当前软件版本
    def get_current_version(self):
        return self.get_value("Version/current_version", value_type=str)

    def set_current_version(self, value):
        self.set_value("Version/current_version", value)

    # 获取和保存点的时间
    def get_dot_time(self):
        return self.get_value("Time/dot_time", value_type=int)

    def set_dot_time(self, value):
        self.set_value("Time/dot_time", value)

    # 获取和保存划的时间
    def get_dash_time(self):
        return self.get_value("Time/dash_time", value_type=int)

    def set_dash_time(self, value):
        self.set_value("Time/dash_time", value)

    # 获取和保存点间隔的时间
    def get_letter_interval_duration_time(self):
        return self.get_value("Time/letter_interval_duration_time", value_type=int)

    def set_letter_interval_duration_time(self, value):
        self.set_value("Time/letter_interval_duration_time", value)

    # 获取和保存划间隔的时间
    def get_word_interval_duration_time(self):
        return self.get_value("Time/word_interval_duration_time", value_type=int)

    def set_word_interval_duration_time(self, value):
        self.set_value("Time/word_interval_duration_time", value)

    # 获取和保存服务器 URL
    def get_server_url(self):
        return self.get_value("server/url", value_type=str)

    def set_server_url(self, value):
        self.set_value("server/url", value)

    # 获取和保存服务器端口
    def get_server_port(self):
        return self.get_value("server/port", value_type=int)

    def set_server_port(self, value):
        self.set_value("server/port", value)

    # 获取和保存服务器频道
    def get_server_channel_name(self):
        return self.get_value("server/channel_name", value_type=int)

    def set_server_channel_name(self, value):
        self.set_value("server/channel_name", value)

    # 获取和保存语言配置
    def get_language(self):
        return self.get_value("Setting/language", value_type=str)

    def set_language(self, value):
        self.set_value("Setting/language", value)

    # 获取和保存蜂鸣器频率
    def get_buzz_freq(self):
        return self.get_value("Setting/buzz_freq", value_type=int)

    def set_buzz_freq(self, value):
        self.set_value("Setting/buzz_freq", value)

    # 获取和保存自动键开启状态
    def get_autokey_status(self):
        return self.get_value("Setting/autokey_status", value_type=bool)

    def set_autokey_status(self, value):
        self.set_value("Setting/autokey_status", value)

    # 获取和保存键盘按键配置
    def get_keyborad_key(self):
        return self.get_value("Setting/keyborad_key", value_type=str)

    def set_keyborad_key(self, value):
        self.set_value("Setting/keyborad_key", value)

    # 获取和保存发报蜂鸣器状态
    def get_send_buzz_status(self):
        return self.get_value("Setting/send_buzz_status", value_type=bool)

    def set_send_buzz_status(self, value):
        self.set_value("Setting/send_buzz_status", value)

    # 获取和保存收报蜂鸣器状态
    def get_receive_buzz_status(self):
        return self.get_value("Setting/receive_buzz_status", value_type=bool)

    def set_receive_buzz_status(self, value):
        self.set_value("Setting/receive_buzz_status", value)

    # 获取和保存翻译可见性
    def get_translation_visibility(self):
        return self.get_value("Setting/translation_visibility", value_type=bool)

    def set_translation_visibility(self, value):
        self.set_value("Setting/translation_visibility", value)

    # 获取和保存发报动画可见性
    def get_visualizer_visibility(self):
        return self.get_value("Setting/visualizer_visibility", value_type=bool)

    def set_visualizer_visibility(self, value):
        self.set_value("Setting/visualizer_visibility", value)

    # 获取和保存发报界面电码字体大小
    def get_sender_font_size(self):
        return self.get_value("Setting/sender_font_size", value_type=int)

    def set_sender_font_size(self, value):
        self.set_value("Setting/sender_font_size", value)

    # 获取和保存单词最小长度
    def get_min_word_length(self):
        return self.get_value("Listen/min_word_length", value_type=int)

    def set_min_word_length(self, value):
        self.set_value("Listen/min_word_length", value)

    # 获取和保存单词最大长度
    def get_max_word_length(self):
        return self.get_value("Listen/max_word_length", value_type=int)

    def set_max_word_length(self, value):
        self.set_value("Listen/max_word_length", value)

    # 获取和保存组的最小数量
    def get_min_groups(self):
        return self.get_value("Listen/min_groups", value_type=int)

    def set_min_groups(self, value):
        self.set_value("Listen/min_groups", value)

    # 获取和保存组的最大数量
    def get_max_groups(self):
        return self.get_value("Listen/max_groups", value_type=int)

    def set_max_groups(self, value):
        self.set_value("Listen/max_groups", value)

    # 获取和保存听力主课程权重
    def get_listen_weight(self):
        return self.get_value("Listen/weight", value_type=float)

    def set_listen_weight(self, value):
        self.set_value("Listen/weight", value)

