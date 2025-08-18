# -*- coding: utf-8 -*-
"""
模块名称：通用设置对话框
功能说明：实现应用程序的通用设置界面，包含呼号设置、字体大小调整、快捷键配置等功能
"""

from PyQt5.QtWidgets import QDialog, QVBoxLayout, QLabel, QHBoxLayout, QSpacerItem, QSizePolicy
from PyQt5.QtGui import QKeySequence
from PyQt5.QtCore import Qt
from qfluentwidgets import LineEdit, PushButton, Slider, SpinBox
from utils.config_manager import ConfigManager


class GeneralSettingDialog(QDialog):
    """通用设置对话框类"""

    def __init__(self, parent=None):
        """
        初始化设置对话框
        :param parent: 父窗口对象
        """
        super().__init__(parent)
        # 窗口基本设置
        self.setWindowTitle(self.tr("设置"))
        self.setGeometry(100, 100, 400, 200)
        
        # 配置管理器初始化
        self.config_manager = ConfigManager()

        # 从配置文件加载初始值
        self._initialize_config_values()

        # UI初始化
        self.initUI()

        # 界面状态初始化
        self.initSetting()

    def _initialize_config_values(self):
        """从配置文件加载所有配置值"""
        self.dot_time = self.config_manager.get_dot_time()
        self.my_call = self.config_manager.get_my_call()
        self.autokey_status = self.config_manager.get_autokey_status()
        self.keyborad_key = self.config_manager.get_keyborad_key()
        self.send_buzz_status = self.config_manager.get_send_buzz_status()
        self.receive_buzz_status = self.config_manager.get_receive_buzz_status()
        self.translation_visibility = self.config_manager.get_translation_visibility()
        self.visualizer_visibility = self.config_manager.get_visualizer_visibility()
        self.buzz_freq = self.config_manager.get_buzz_freq()
        self.sender_font_size = self.config_manager.get_sender_font_size()

        # 键盘监听状态相关
        self.listening_keyborad = False      # 键盘监听标志
        self.listening_keyborad_record = 0   # 按键记录次数（需要记录两次）

    def initUI(self):
        """初始化用户界面组件"""
        # 主垂直布局
        self.main_vbox = QVBoxLayout()

        # 呼号设置布局
        #self._setup_call_sign_layout()

        # 字体大小设置布局
        self._setup_font_size_layout()

        # 自动键设置布局
        self._setup_autokey_layout()

        # 键盘发送设置布局
        self._setup_keyboard_send_layout()

        # 声音相关设置布局
        self._setup_audio_settings_layout()

        # 功能开关布局
        self._setup_feature_switches_layout()

        # 底部按钮布局
        self._setup_bottom_buttons_layout()

        self.setLayout(self.main_vbox)

    def _setup_call_sign_layout(self):
        """呼号设置区域布局"""
        self.my_call_hbox = QHBoxLayout()
        current_call_sign = self.my_call if self.my_call != '' else '未设置'
        self.label_my_call = QLabel(self.tr("当前呼号: ") + current_call_sign)
        self.edit_my_call = LineEdit(self)
        self.edit_my_call.setPlaceholderText(self.tr("输入呼号"))
        self.my_call_hbox.addWidget(self.label_my_call)
        self.my_call_hbox.addWidget(self.edit_my_call)
        self.main_vbox.addLayout(self.my_call_hbox)

    def _setup_font_size_layout(self):
        """字体大小设置区域布局"""
        self.sender_font_size_hbox = QHBoxLayout()
        self.label_sender_font_size = QLabel(self.tr("字体大小: "))
        self.spinBox_sender_font_size = SpinBox(self)
        self.spinBox_sender_font_size.setAccelerated(True)
        self.sender_font_size_hbox.addWidget(self.label_sender_font_size)
        self.sender_font_size_hbox.addWidget(self.spinBox_sender_font_size)
        self.main_vbox.addLayout(self.sender_font_size_hbox)

    def _setup_autokey_layout(self):
        """自动键设置区域布局"""
        self.autokey_set_hbox = QHBoxLayout()
        self.label_autokey_status = QLabel(self.tr('自动键: '))
        self.btn_change_status_autokey = PushButton(self.tr("启用"))
        self.autokey_set_hbox.addWidget(self.label_autokey_status)
        self.autokey_set_hbox.addWidget(self.btn_change_status_autokey)
        self.btn_change_status_autokey.clicked.connect(self.set_autokey_status)
        self.main_vbox.addLayout(self.autokey_set_hbox)

    def _setup_keyboard_send_layout(self):
        """键盘发送设置区域布局"""
        self.keybora_set_hbox = QHBoxLayout()
        keyboard_text = self.tr("键盘发送: ")
        key_sequence = QKeySequence(self.keyborad_key).toString()
        self.label_current_keyborad = QLabel(f"{keyboard_text}{key_sequence}")
        self.btn_change_keyborad = PushButton(self.tr("更改"))
        self.keybora_set_hbox.addWidget(self.label_current_keyborad)
        self.keybora_set_hbox.addWidget(self.btn_change_keyborad)
        self.btn_change_keyborad.clicked.connect(self.change_keyborad)
        self.main_vbox.addLayout(self.keybora_set_hbox)

    def _setup_audio_settings_layout(self):
        """声音相关设置布局（发送/接收蜂鸣声）"""
        # 发送蜂鸣声设置
        self.send_buzz_status_hbox = QHBoxLayout()
        self.label_audio_status = QLabel(self.tr('发送蜂鸣声'))
        self.btn_audio_status = PushButton(self.tr("启用"))
        self.send_buzz_status_hbox.addWidget(self.label_audio_status)
        self.send_buzz_status_hbox.addWidget(self.btn_audio_status)
        self.btn_audio_status.clicked.connect(self.change_send_buzz_status)
        self.main_vbox.addLayout(self.send_buzz_status_hbox)

        # 接收蜂鸣声设置
        self.receive_buzz_status_hbox = QHBoxLayout()
        self.label_receive_buzz_status = QLabel(self.tr('接收蜂鸣声'))
        self.btn_receive_buzz_status = PushButton(self.tr("启用"))
        self.receive_buzz_status_hbox.addWidget(self.label_receive_buzz_status)
        self.receive_buzz_status_hbox.addWidget(self.btn_receive_buzz_status)
        self.btn_receive_buzz_status.clicked.connect(self.change_receive_buzz_status)
        self.main_vbox.addLayout(self.receive_buzz_status_hbox)

        # 蜂鸣器频率设置
        self.set_buzz_freq_hbox = QHBoxLayout()
        self.label_set_buzz_freq = QLabel(self.tr('蜂鸣器频率'))
        self.slider_set_buzz_freq = Slider(Qt.Horizontal, self)
        self.slider_set_buzz_freq.setFixedWidth(200)
        self.slider_set_buzz_freq.setRange(300, 1000)
        self.set_buzz_freq_hbox.addWidget(self.label_set_buzz_freq)
        self.set_buzz_freq_hbox.addWidget(self.slider_set_buzz_freq)
        self.slider_set_buzz_freq.valueChanged.connect(self.set_buzz_freq)
        self.main_vbox.addLayout(self.set_buzz_freq_hbox)

    def _setup_feature_switches_layout(self):
        """功能开关布局（解码/动画）"""
        # 解码显示开关
        self.translation_switch_hbox = QHBoxLayout()
        self.label_translation_switch = QLabel(self.tr('消息显示与翻译'))
        self.btn_translation_switch = PushButton(self.tr("启用"))
        self.translation_switch_hbox.addWidget(self.label_translation_switch)
        self.translation_switch_hbox.addWidget(self.btn_translation_switch)
        self.btn_translation_switch.clicked.connect(self.change_translation_visibility)
        self.main_vbox.addLayout(self.translation_switch_hbox)

        # 动画显示开关
        self.visualizer_switch_hbox = QHBoxLayout()
        self.label_visualizer_switch = QLabel(self.tr('摩尔斯电码动画'))
        self.btn_visualizer_switch = PushButton(self.tr("启用"))
        self.visualizer_switch_hbox.addWidget(self.label_visualizer_switch)
        self.visualizer_switch_hbox.addWidget(self.btn_visualizer_switch)
        self.btn_visualizer_switch.clicked.connect(self.change_visualizer_visibility)
        self.main_vbox.addLayout(self.visualizer_switch_hbox)

    def _setup_bottom_buttons_layout(self):
        """底部按钮布局（保存/取消）"""
        self.final_hbox = QHBoxLayout()
        self.btn_cancel = PushButton(self.tr("放弃设置"))
        self.btn_save = PushButton(self.tr("保存设置"))
        self.btn_save.clicked.connect(self.save)
        self.btn_cancel.clicked.connect(self.cancel)

        spacer = QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)
        self.final_hbox.addItem(spacer)
        self.final_hbox.addWidget(self.btn_cancel)
        self.final_hbox.addWidget(self.btn_save)
        self.main_vbox.addLayout(self.final_hbox)

    def initSetting(self):
        """初始化界面状态"""
        # 字体大小设置
        self.spinBox_sender_font_size.setValue(self.sender_font_size)
        
        # 蜂鸣器频率设置
        self.slider_set_buzz_freq.setValue(self.buzz_freq)
        self.label_set_buzz_freq.setText(
            self.tr("蜂鸣器频率: ") + str(self.buzz_freq) + self.tr("Hz"))

        # 键盘快捷键显示处理
        saved_key = self.keyborad_key.split(',')
        self._process_key_display(saved_key)

        # 各功能开关状态初始化
        self._update_switch_states()

    def _process_key_display(self, saved_key):
        """处理键盘快捷键显示"""
        self.key_one = '空格' if QKeySequence(int(saved_key[0])).toString() == " " else QKeySequence(int(saved_key[0])).toString()
        self.key_two = '空格' if QKeySequence(int(saved_key[1])).toString() == " " else QKeySequence(int(saved_key[1])).toString()
        self.label_current_keyborad.setText(
            self.tr('键盘发送:') + self.key_one + ',' + self.key_two)

    def _update_switch_states(self):
        """更新所有开关按钮状态"""
        # 自动键状态
        self._update_switch(self.autokey_status, 
                          self.btn_change_status_autokey,
                          self.label_autokey_status,
                          '自动键')

        # 发送蜂鸣声状态
        self._update_switch(self.send_buzz_status,
                          self.btn_audio_status,
                          self.label_audio_status,
                          '发送蜂鸣声')

        # 接收蜂鸣声状态
        self._update_switch(self.receive_buzz_status,
                          self.btn_receive_buzz_status,
                          self.label_receive_buzz_status,
                          '接收蜂鸣声')

        # 解码显示状态
        self._update_switch(self.translation_visibility,
                          self.btn_translation_switch,
                          self.label_translation_switch,
                          '解码')

        # 动画显示状态
        self._update_switch(self.visualizer_visibility,
                          self.btn_visualizer_switch,
                          self.label_visualizer_switch,
                          '摩尔斯电码动画')

    def _update_switch(self, status, button, label, feature_name):
        """
        更新开关状态显示
        :param status: 当前状态（True/False）
        :param button: 操作的按钮对象
        :param label: 状态标签对象
        :param feature_name: 功能名称（用于显示）
        """
        if status:
            button.setText(self.tr("禁用"))
            label.setText(self.tr(f'{feature_name}: 已启用'))
        else:
            button.setText(self.tr("启用"))
            label.setText(self.tr(f'{feature_name}: 已禁用'))

    # -------------------- 事件处理函数 --------------------
    def set_autokey_status(self):
        """切换自动键状态"""
        self.autokey_status = not self.autokey_status
        self._update_switch(self.autokey_status,
                          self.btn_change_status_autokey,
                          self.label_autokey_status,
                          '自动键')

    def change_keyborad(self):
        """启动键盘快捷键修改流程"""
        self.listening_keyborad = True
        self.label_current_keyborad.setText(self.tr("请按下任意键作为 'Dah'"))

    def change_send_buzz_status(self):
        """切换发送蜂鸣声状态"""
        self.send_buzz_status = not self.send_buzz_status
        self._update_switch(self.send_buzz_status,
                          self.btn_audio_status,
                          self.label_audio_status,
                          '发送蜂鸣声')

    def change_receive_buzz_status(self):
        """切换接收蜂鸣声状态"""
        self.receive_buzz_status = not self.receive_buzz_status
        self._update_switch(self.receive_buzz_status,
                          self.btn_receive_buzz_status,
                          self.label_receive_buzz_status,
                          '接收蜂鸣声')

    def set_buzz_freq(self, value):
        """设置蜂鸣器频率"""
        self.buzz_freq = value
        self.label_set_buzz_freq.setText(
            self.tr('蜂鸣器频率: ') + str(self.buzz_freq) + 'Hz')

    def change_translation_visibility(self):
        """切换解码显示状态"""
        self.translation_visibility = not self.translation_visibility
        self._update_switch(self.translation_visibility,
                          self.btn_translation_switch,
                          self.label_translation_switch,
                          '解码')

    def change_visualizer_visibility(self):
        """切换动画显示状态"""
        self.visualizer_visibility = not self.visualizer_visibility
        self._update_switch(self.visualizer_visibility,
                          self.btn_visualizer_switch,
                          self.label_visualizer_switch,
                          '摩尔斯电码动画')

    def keyPressEvent(self, event):
        """处理键盘按键事件"""
        if not self.listening_keyborad:
            return

        if self.listening_keyborad_record == 0:
            # 记录第一个按键（Dah）
            self._handle_first_key(event)
        elif self.listening_keyborad_record == 1:
            # 记录第二个按键（Dit）
            self._handle_second_key(event)

    def _handle_first_key(self, event):
        """处理第一个按键记录"""
        key = event.key()
        self.keyborad_key = str(key)
        self.listening_keyborad_record += 1
        self.label_current_keyborad.setText(self.tr('请再次按下任意键作为 "Dit"'))

    def _handle_second_key(self, event):
        """处理第二个按键记录"""
        key = event.key()
        self.keyborad_key += "," + str(key)
        self.listening_keyborad_record = 0
        self.listening_keyborad = False
        self._update_key_display()

    def _update_key_display(self):
        """更新键盘快捷键显示"""
        saved_key = self.keyborad_key.split(',')
        self.key_one = '空格' if QKeySequence(int(saved_key[0])).toString() == " " else QKeySequence(int(saved_key[0])).toString()
        self.key_two = '空格' if QKeySequence(int(saved_key[1])).toString() == " " else QKeySequence(int(saved_key[1])).toString()
        self.label_current_keyborad.setText(
            self.tr('键盘发送:') + self.key_one + ',' + self.key_two)

    def save(self):
        """保存所有设置到配置文件"""
        # 保存呼号
        if self.edit_my_call.text():
            self.my_call = self.edit_my_call.text()
            self.config_manager.set_my_call(self.my_call)

        # 保存各配置项
        self.config_manager.set_sender_font_size(self.spinBox_sender_font_size.value())
        self.config_manager.set_autokey_status(self.autokey_status)
        self.config_manager.set_keyborad_key(self.keyborad_key)
        self.config_manager.set_send_buzz_status(self.send_buzz_status)
        self.config_manager.set_receive_buzz_status(self.receive_buzz_status)
        self.config_manager.set_translation_visibility(self.translation_visibility)
        self.config_manager.set_visualizer_visibility(self.visualizer_visibility)
        self.config_manager.set_buzz_freq(self.buzz_freq)

        self.accept()

    def cancel(self):
        """关闭对话框（不保存设置）"""
        self.accept()