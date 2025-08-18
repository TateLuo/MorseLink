import re, string
import traceback
from datetime import datetime
import time, json
from PyQt5.QtGui import  QFont
from PyQt5.QtWidgets import (
    QWidget,
    QLabel,
    QVBoxLayout,
    QWidget,
    QHBoxLayout,
    QLineEdit,
    QDialog,
    QDesktopWidget,
    QMessageBox,
)
from PyQt5.QtCore import Qt, QTimer

from utils.mqtt_query_tool import MQTTOnlineCounter
from utils.translator import MorseCodeTranslator
from utils.sound import BuzzerSimulator
from utils.config_manager import ConfigManager
from utils.database_tool import DatabaseTool
from utils.multi_tablet_tool import MultiTableTool
from utils.check_update import VersionChecker
from utils.adaptive_morse_decoder import AdaptiveMorseDecoder
from utils.received_message_processor import MultiChannelProcessor

from gui.widget.morsecode_visualizer import MorseCodeVisualizer
from gui.widget.signal_light import SignalLightWidget
from gui.dialog.general_setting_dialog import GeneralSettingDialog
from gui.dialog.about_dialog import AboutDialog
from gui.dialog.qso_record_dialog import QsoRecordDialog
from gui.dialog.key_modifier_dialog import KeyModifierDialog
from gui.dialog.transmitter_setting_dialog import TransmitterSettingDialog

from service.signal.pyqt_signal import MySignal
from service.mqtt_client import MQTTClient


from qfluentwidgets import PushButton, TransparentPushButton, Slider
from qfluentwidgets import FluentIcon as FIF






class QSOOline(QWidget):

    def __init__(self, stackedWidget):
        super().__init__()

        # 初始化窗口和布局
        self.stackedWidget = stackedWidget
        self.setWindowTitle(self.tr("MorseLink"))
        self.resize(1080, 1920)
        self.center()

        # 必须在主线程中创建帮助页面的两个窗口
        self.table_tool_morse_code = MultiTableTool("morse_code")
        self.table_tool_communication_words = MultiTableTool("communication_words")

        # 初始化常量
        # 定义文本常量
        self.RECEIVED_CODE = "<h3>收到电码:</h3>"
        self.RECEIVED_TRANLATION = self.tr("<h3>收到电码翻译:</h3>")
        self.SEND_TRANSLATION = self.tr("<h3>发送电码翻译:</h3>")
        self.SENT_CODE = self.tr("<h3>发送电码:</h3>")
        self.SENT_CODE_BANNED = self.tr("<h3>发送电码：发射禁止，请稍后再试！</h3>")
        self.NUMBER_CHANNEL = self.tr("<h3>当前频道人数:</h3>")

        # 初始化配置文件管理器
        self.config_manager = ConfigManager()

        # 发送相关参数
        self.start_time = None
        self.morse_code = ""
        self.morse_code_received = ""
        self.morse_code_translation = ""  # 翻译后的摩斯电码字符串（带空格）
        self.received_translation = ""  # 翻译后的摩斯电码字符串（带空格）
        self.dot_duration = int(self.config_manager.get_dot_time())
        self.dash_duration = int(self.config_manager.get_dash_time())
        self.dot = "."
        self.dash = "-"
        self.pressed_keys_autokey = set()
        self.timer_autokey = QTimer(self)
        self.timer_autokey.timeout.connect(self.handle_timer_autokey_timeout)
        self.current_char_autokey = None
        self.is_sending_autokey = False  # 标志是否正在发送字符
        self.is_key_pressed = False
        self.letter_interval_duration = int(self.config_manager.get_letter_interval_duration_time())  # 字母间隔
        self.word_interval_duration = int(self.config_manager.get_word_interval_duration_time())  # 单词间隔
        self.autokey_status = self.config_manager.get_autokey_status()  # 是否启用自动键模式 TRUE, FALSE
        self.send_buzz_status = self.config_manager.get_send_buzz_status()
        self.receive_buzz_status = self.config_manager.get_receive_buzz_status()

        # 设置频道名称
        self.channel_name = self.config_manager.get_server_channel_name()

        # 定时器
        self.gap_time = None

        # 字母间隔定时器
        self.letter_timer = QTimer(self)
        self.letter_timer.setSingleShot(True)
        self.letter_timer.timeout.connect(self.handle_letter_timeout)

        # 单词间隔定时器
        self.word_timer = QTimer(self)
        self.word_timer.setSingleShot(True)
        self.word_timer.timeout.connect(self.handle_word_timeout)

        # 保存通信记录的定时器及相关变量
        self.timer_link_record = QTimer(self)
        self.timer_link_record.setInterval(3000)  # 停止传输后3秒记录
        self.timer_link_record.timeout.connect(self.handle_link_record_timeout)  # 处理定时器超时
        self.is_receiving = False
        self.is_sending = False
        self.current_message_to_record = ""  # 记录待记录的字符
        self.start_record_time = None  # 记录通信开始时间

        # 禁止传输定时器
        self.status_transmit_banned = False  # 默认False表示允许传输
        self.transmit_banned_timer = QTimer(self)
        self.transmit_banned_timer.setSingleShot(True)
        self.transmit_banned_timer.timeout.connect(self.handle_transmit_banned_timeout)

        # 服务器相关参数
        self.is_connected = False

        #初始化服务器客户端数查询定时器
        self.initQueryClientsTimer()

        # 初始化处理接收数据的信号
        self.mysignal = MySignal()
        self.mysignal.process_received_signal.connect(self.process_messages)  # 绑定槽函数

        # 初始化解码器
        self.translator = MorseCodeTranslator()

        # 调用UI初始化函数
        self.initUI()

        # 初始化蜂鸣器
        self.buzz = BuzzerSimulator()

        # 播放间隔
        self.last_sound_play_time = 0  # 记录上次播放时间

        # 初始化一些设置
        self.initSetting()

        # 上次按键状态
        self.last_key_pressed_status = False
        # 上次按键时间
        self.last_key_pressed_time = 0

    def center(self):
        """将窗口居中显示"""
        # 获取屏幕尺寸
        screen = QDesktopWidget().screenGeometry()
        # 获取窗口尺寸
        size = self.geometry()
        # 计算窗口居中的坐标
        self.center_point_x = int((screen.width() - size.width()) / 2)
        self.center_point_y = int((screen.height() - size.height()) / 2)
        # 移动窗口到居中位置
        self.move(self.center_point_x, self.center_point_y)

    def focusOutEvent(self, event):
        """窗口失去焦点事件处理"""
        print("窗口失去焦点")
        # 停止蜂鸣器
        self.buzz.stop()
        # 停止摩斯电码可视化生成
        self.morsecode_visualizer.stop_generating(5)
        # 设置信号灯状态为关闭
        self.signal_light.set_state(0)

        # 如果自动键定时器正在运行，则停止
        if self.timer_autokey.isActive():
            self.timer_autokey.stop()

        # 调用父类的焦点失去事件处理
        super().focusOutEvent(event)


    def initUI(self):
        """
        初始化用户界面。
        创建并布局主界面中的所有控件，包括摩斯电码可视化器、发送和接收区域等。
        """
        # 主布局
        self.hbox_main = QHBoxLayout()

        # 定义消息布局和摩斯电码可视化器的垂直布局
        self.vhox_message_and_morsecode_visualizer = QHBoxLayout()

        # 消息布局（垂直）
        self.vbox_message = QVBoxLayout()

        # 将消息布局添加到布局中
        self.vhox_message_and_morsecode_visualizer.addLayout(self.vbox_message)

        # 发送区域布局（垂直）
        self.vbox_send_message = QVBoxLayout()

        # 添加当前人数
        self.label_number_clients = QLabel(f'当前人数: 未连接服务器')  # 显示当前频率
        self.label_number_clients.setFixedHeight(30)  # 设置固定高度
        font = QFont('SimHei', 13)  # 创建字体对象，样式为 SimHei，大小为 13
        self.label_number_clients.setFont(font)  # 设置字体
        self.label_number_clients.setAlignment(Qt.AlignHCenter)  # 居中对齐
        self.vbox_send_message.addWidget(self.label_number_clients)  # 添加到发送区域布局

        # 添加频率显示和滑动条
        self.label_frequency = QLabel(f'当前中心频率: {self.channel_name} kHz')  # 显示当前频率
        self.label_frequency.setFixedHeight(30)  # 设置固定高度
        font = QFont('SimHei', 13)  # 创建字体对象，样式为 SimHei，大小为 13
        self.label_frequency.setFont(font)  # 设置字体
        self.label_frequency.setAlignment(Qt.AlignHCenter)  # 居中对齐
        self.vbox_send_message.addWidget(self.label_frequency)  # 添加到发送区域布局

        # 创建滑动条
        self.slider_frequency = Slider(Qt.Horizontal, self)  # 水平滑动条
        self.slider_frequency.setMinimum(7000)  # 设置最小值
        self.slider_frequency.setMaximum(7300)  # 设置最大值
        self.slider_frequency.setValue(self.channel_name)  # 设置初始值
        self.slider_frequency.valueChanged.connect(self.update_frequency_label)  # 连接值变化信号
        self.vbox_send_message.addWidget(self.slider_frequency)  # 添加到发送区域布局

        # 显示自己的呼号
        self.label_my_call = QLabel("")
        self.label_my_call.setFixedHeight(30)  # 设置固定高度
        font = QFont('SimHei', 13)  # 创建字体对象，样式为 SimHei，大小为 13
        self.label_my_call.setFont(font)  # 设置字体
        self.label_my_call.setAlignment(Qt.AlignHCenter)  # 居中对齐
        self.vbox_send_message.addWidget(self.label_my_call)

        # 创建水平布局用于显示两个文本（点间隔、键盘发送）
        self.hbox_label = QHBoxLayout()
        self.hbox_label.setContentsMargins(0, 0, 0, 0)  # 设置边距
        self.vbox_send_message.addLayout(self.hbox_label)  # 将布局添加到发送界面

        # 清理屏幕按钮
        self.btn_clean_screen = TransparentPushButton("清理屏幕")
        self.btn_clean_screen.setIcon(FIF.BROOM)
        self.btn_clean_screen.clicked.connect(self.clean_screen)
        self.vbox_send_message.addWidget(self.btn_clean_screen)  # 添加到发送界面

        # 连接服务器按钮
        self.btn_connect_and_disconnect = PushButton(FIF.CONNECT, "连接至服务器", self)
        self.btn_connect_and_disconnect.clicked.connect(self.connectService)
        self.vbox_send_message.addWidget(self.btn_connect_and_disconnect)  # 添加到发送界面

        # 创建发送按钮
        self.btn_send_message = PushButton(FIF.SEND, self.tr("点击发报"), self)
        self.btn_send_message.pressed.connect(self.on_btn_send_message_pressed)  # 按下事件
        self.btn_send_message.released.connect(self.on_btn_send_message_released)  # 释放事件
        self.vbox_send_message.addWidget(self.btn_send_message)  # 添加到发送界面
        self.btn_send_message.setMinimumHeight(100)  # 设置最小高度

        # 创建信号灯控件
        self.signal_light = SignalLightWidget()
        self.signal_light.set_state(0)  # 设置初始状态
        self.signal_light.set_diameter(25)  # 设置直径

        # 创建接收消息相关的控件
        self.label_morse_received = QLabel("收到电码")
        font = QFont()
        font.setBold(True)  # 设置粗体
        font.setPointSize(13)  # 设置字体大小
        self.label_morse_received.setFont(font)

        # 创建发送界面的第一行布局，包含标签和信号灯
        self.hbox_send_message_first_line = QHBoxLayout()
        self.hbox_send_message_first_line.addWidget(self.label_morse_received)
        self.hbox_send_message_first_line.addWidget(self.signal_light)
        self.vbox_message.addLayout(self.hbox_send_message_first_line)  # 添加到消息布局

        # 接收电码输入框
        self.edit_morse_received = QLineEdit()
        self.edit_morse_received.setReadOnly(True)  # 设置为只读
        self.edit_morse_received.setStyleSheet("background: transparent;")  # 设置透明背景
        self.vbox_message.addWidget(self.edit_morse_received)  # 添加到消息布局

        # 接收翻译标签
        self.label_received_translation = QLabel("收到翻译")
        font = QFont()
        font.setBold(True)
        font.setPointSize(13)
        self.label_received_translation.setFont(font)
        self.vbox_message.addWidget(self.label_received_translation)  # 添加到消息布局

        # 接收翻译输入框
        self.edit_received_translation = QLineEdit()
        self.edit_received_translation.setReadOnly(True)
        self.edit_received_translation.setStyleSheet("background: transparent;")
        self.vbox_message.addWidget(self.edit_received_translation)  # 添加到消息布局

        # 发送翻译标签
        self.label_send_translation = QLabel("发送翻译")
        font = QFont()
        font.setBold(True)
        font.setPointSize(13)
        self.label_send_translation.setFont(font)
        self.vbox_message.addWidget(self.label_send_translation)  # 添加到消息布局

        # 发送翻译输入框
        self.edit_send_translation = QLineEdit()
        self.edit_send_translation.setReadOnly(True)
        self.edit_send_translation.setStyleSheet("background: transparent;")
        self.vbox_message.addWidget(self.edit_send_translation)  # 添加到消息布局

        # 发送电码标签
        self.label_morse_sent = QLabel("发送电码")
        font = QFont()
        font.setBold(True)
        font.setPointSize(13)
        self.label_morse_sent.setFont(font)
        self.vbox_message.addWidget(self.label_morse_sent)  # 添加到消息布局

        # 发送电码输入框
        self.edit_morse_code = QLineEdit()
        self.edit_morse_code.setReadOnly(True)
        self.edit_morse_code.setStyleSheet("background: transparent;")
        self.vbox_message.addWidget(self.edit_morse_code)  # 添加到消息布局

        # 创建摩斯电码可视化器控件
        self.morsecode_visualizer = MorseCodeVisualizer()
        # 在消息布局中为摩斯电码可视化器设置更高的拉伸因子
        self.vbox_message.addWidget(self.morsecode_visualizer, stretch=3)  # 垂直方向占3份

        # 在主布局中为消息布局设置更高的拉伸因子
        self.hbox_main.addLayout(self.vhox_message_and_morsecode_visualizer, stretch=3)  # 水平方向占2份
        self.hbox_main.addLayout(self.vbox_send_message, stretch=1)  # 水平方向占1份
        # 设置主布局
        self.setLayout(self.hbox_main)

    def update_frequency_label(self):
        """
        更新频率标签的显示。
        当滑动条的值变化时，更新频率标签的文本。
        """
        frequency = self.slider_frequency.value()  # 获取滑动条的当前值
        self.label_frequency.setText(f"当前中心频率: {frequency} kHz")  # 更新标签文本

        #频道保存到配置文件
        self.channel_name = frequency
        self.config_manager.set_server_channel_name(frequency) 

    def initSetting(self):
        # 初始化数据库工具类
        self.database_tool = DatabaseTool()

        # 检查是否显示翻译
        self.is_translation_visible()

        # 设置字体大小
        self.set_font_size()

        # 从配置文件中获取两个键值，格式示例为 "23,12"
        self.saved_key = self.config_manager.get_keyborad_key().split(',')

        # 设置呼号
        self.set_my_call()

        # 检查动画是否可见
        self.set_visualizer_visibility()

        # 初始化更新检查器，传入当前版本和服务器URL
        update_checker = VersionChecker(self.config_manager.get_current_version(), self.config_manager.get_server_url())

        # 检查更新，返回消息和版本信息
        update_checker.check_update()

        # 初始化通信发送记录键的按下时间
        self.current_message_play_time = None
        self.current_message_play_time_invertal = None

        #定义一个消息处理工具
        self.receive_message_processor = MultiChannelProcessor(self.buzz, self.morsecode_visualizer, self.signal_light)

    def connectService(self):
        """
        处理连接或断开服务的逻辑。
        如果已连接则断开，未连接则尝试连接，并更新 UI 状态。
        
        依赖：
            - self.is_service_connected: 当前连接状态。
            - self.client: 客户端连接对象。
            - self.initChat(): 初始化连接的方法。
        """
        try:
            if self.is_connected:
                # 如果已经连接，则断开连接
                self.client.close()  # 关闭连接
                self.btn_connect_and_disconnect.setText("连接到服务器")  # 更新按钮文本
                self.signal_light.set_state(0)  # 将信号灯设置为灰色（断开连接状态）
            else:
                #先检查是否设置呼号
                if self.check_myCall():
                    # 如果未连接，则尝试连接
                    self.initChat()  # 初始化聊天连接
                    if self.is_connected:
                        self.btn_connect_and_disconnect.setText(self.tr("断开连接"))  # 更新按钮文本
                        self.signal_light.set_state(1)  # 将信号灯设置为绿色（连接状态）
                        QMessageBox.information(self, self.tr("成功"), self.tr("成功连接到服务器！"))  # 通知用户连接成功
                    else:
                        print(self.is_connected)
                else:
                    QMessageBox.information(self, self.tr("提示"), self.tr("线上通联，请先设置呼号（无限制）！"))
                    
        except Exception as e:
            print(e)  # 打印错误信息到控制台（用于调试）
            QMessageBox.information(self, self.tr("错误"), f"{self.tr('错误信息：')} {str(e)}")  # 向用户显示错误信息

    def initChat(self):
        """
        初始化聊天模块，配置 MQTT 客户端并连接到服务器。
        
        依赖：
            - self.config_manager: 配置管理对象，用于获取服务器地址和端口。
            - self.my_call: 客户端标识符的一部分。
            - self.client: MQTT 客户端对象。
        """
        url = self.config_manager.get_server_url()  # 获取服务器地址
        port = int(self.config_manager.get_server_port())  # 获取服务器端口
        user=self.config_manager.get_my_call()  # 获取保存的用户名
        pwd=self.config_manager.get_password()  # 获取保存的用户名
        print(f'{user}{pwd}')
        if user and pwd :
            self.client = MQTTClient(
                broker=url,  # MQTT Broker 地址
                port=port,  # MQTT Broker 端口
                username=str(user),  # 获取保存的用户名
                password=str(pwd),  # 获取保存的用户名
                client_id=self.my_call + str(time.time())  # 客户端 ID，由 my_call 和时间戳组成
            )

            self.client.on_message_received = self.on_message_received  # 设置消息接收回调函数
            self.client.on_connection_status_change = self.on_connection_status_change  # 设置连接状态变更回调函数
            self.client.connect("123")  # 连接到 MQTT 服务器

    def on_message_received(self, message):
        """
        客户端接收服务器消息的回调函数。
        当客户端接收到服务器发送的消息时，触发此函数。

        参数：
            - message: 从服务器接收到的消息内容。

        行为：
            - 通过信号机制将接收到的消息发送到主线程处理。
        """
        self.mysignal.process_received_signal.emit(message)  # 通过信号发送消息

    def process_messages(self, message):
        """
        处理接收到的消息的槽函数。
        解析消息内容并根据消息类型执行相应操作，如显示摩斯电码、更新 UI 状态等。

        参数：
            - message: 接收到的消息内容（JSON 格式字符串）。

        行为：
            - 解析消息内容。
            - 根据消息类型（摩斯电码、呼号、按键时间等）更新 UI 或触发其他操作。
            - 处理异常情况并显示错误信息。
        """
        data = json.loads(message)  # 解析 JSON 格式的消息

        print(f"测试收到data的数据为{message}")

        # 解析接收的数据
        morse_code = data["morseCode"]  # 摩斯电码
        my_call = data["myCall"]  # 发送方呼号
        pressed_time = data["pressedTime"]  # 按键时间
        pressed_interval_time = data["pressedIntervalTime"]  # 按键间隔时间
        my_channel = data["myChannel"]  # 频道名称
        try:
            # 如果呼号不同且频道相同，则进行处理
            if my_call != self.my_call:
                if str(my_channel) == str(self.channel_name):
                    # 如果禁止发送计时器正在运行，则停止
                    if self.transmit_banned_timer.isActive():
                        self.transmit_banned_timer.stop()

                    # 更新 UI 状态
                    self.label_morse_sent.setText(self.SENT_CODE_BANNED)
                    self.status_transmit_banned = True
                    self.transmit_banned_timer.start(1000)  # 启动 1 秒计时器

                    # 处理摩斯电码
                    if morse_code == "/":
                        # 翻译摩斯电码并插入到接收翻译框中
                        morse_code_translated = self.translator.letter_to_morse(self.morse_code_received)
                        self.edit_received_translation.insert(morse_code_translated)
                        self.morse_code_received = ""  # 清空接收的摩斯电码

                        # 在接收框中显示摩斯电码
                        self.edit_morse_received.insert(morse_code)
                    elif morse_code == "//":
                        # 在接收框中显示摩斯电码
                        self.edit_morse_received.insert(morse_code)
                        self.edit_received_translation.insert(" ")  # 插入空格
                        self.morse_code_received = ""  # 清空接收的摩斯电码
                    else:
                        # 显示对方呼号
                        self.call_of_sender = my_call
                        self.label_morse_received.setText(f'{self.RECEIVED_CODE} {self.call_of_sender} {"正在发射"}')

                        # 记录接收的摩斯电码
                        self.morse_code_received += morse_code
                        self.start_record_receive(morse_code)

                        # 在接收框中显示摩斯电码
                        self.edit_morse_received.insert(morse_code)

                        # 获取按键时间和间隔时间
                        play_time = pressed_time
                        play_time_inreval = pressed_interval_time  # 兼容性检查，旧版本可能没有此参数

                    
                        # 创建消息队列
                        message = [play_time, play_time_inreval]
                        self.receive_message_processor.receive_message(5,message)
                        #self.message_list.append(message)  # 添加消息到队列中

                        # 如果没有音频正在播放，则开始处理消息
                        #if not self.isRunningTimerInterval and not self.isRunningTimerPlay:
                            #pass
                            #self.received_audio_process(self.index)
                elif morse_code != "/" and morse_code != "//":
                    #通过频道计算ID
                    result = self.process_side_channel(self.channel_name, my_channel)
                    
                    is_within_range = result['is_within_range']
                    channel_id = result['channel_id']

                    #只接受中心频率的前五和后五个频点
                    if is_within_range:
                        # 获取按键时间和间隔时间
                        play_time = pressed_time
                        play_time_inreval = pressed_interval_time  # 兼容性检查，旧版本可能没有此参数

                
                        # 创建消息队列
                        message = [play_time, play_time_inreval]
                        print(f'将{message}添加至侧音频消息列表')
                        self.receive_message_processor.receive_message(channel_id,message)
        except Exception as e:
            # 捕获异常并显示错误信息
            error_info = traceback.format_exc()  # 获取完整的错误信息，包括行号
            print(error_info)
            #QMessageBox.information(self, self.tr("Error"), f"{self.tr('Error message:')}\n{error_info}")

    def process_side_channel(self, current_channel, side_channel, range_limit=5):
        """
        处理侧音频道，判断是否在当前频道的前后范围内，并返回所属频道ID。

        参数:
            current_channel (int): 当前频道。
            side_channel (int): 侧音频道（接收到的频道）。
            range_limit (int): 前后范围限制，默认为5。

        返回:
            dict: 包含是否在范围内和所属频道ID的结果。
        """
        # 计算可接受的最小和最大频道
        min_channel = current_channel - range_limit
        max_channel = current_channel + range_limit

        # 判断侧音频道是否在范围内
        if min_channel <= side_channel <= max_channel:
            # 计算频道ID
            channel_id = side_channel - min_channel
            return {
                "side_channel": side_channel,
                "is_within_range": True,
                "channel_id": channel_id
            }
        else:
            return {
                "side_channel": side_channel,
                "is_within_range": False,
                "channel_id": None
            }
        
    def on_connection_status_change(self, is_connected):
        """
        监听连接状态变化的回调函数。
        当连接状态发生变化时，更新 UI 和内部状态。

        参数：
            - is_connected: 当前连接状态（True 表示已连接，False 表示未连接）。

        行为：
            - 更新连接状态（self.is_connected）。
            - 更新连接按钮的文本。
            - 更新信号灯状态。
        """
        if is_connected:
            # 如果已连接，更新状态和 UI
            #查询服务器在线客户端数量
            self.startQuery()
            #定时每五分钟查一次

            self.is_connected = is_connected
            self.btn_connect_and_disconnect.setText(self.tr("断开连接"))  # 更新按钮文本
            self.signal_light.set_state(2)  # 将信号灯设置为绿色（连接状态）
        else:
            # 如果未连接，更新状态和 UI
            self.is_connected = is_connected
            #关闭查询人数定时器
            self.timer_query_clients.stop()

            self.btn_connect_and_disconnect.setText(self.tr("连接到服务器"))  # 更新按钮文本
            self.signal_light.set_state(0)  # 将信号灯设置为灰色（断开状态）

    def on_btn_send_message_pressed(self):
        """
        处理发送按钮按下事件。
        当发送按钮被按下时，执行以下操作：
            - 检查是否允许发送。
            - 更新 UI 状态（按钮图标、信号灯、动画等）。
            - 启动蜂鸣器和摩斯电码生成动画。
            - 记录按键时间并计算按键间隔。

        行为：
            - 如果允许发送且按键未被按下，则执行发送逻辑。
            - 更新 UI 和内部状态，启动相关功能。
        """
        # 首先检查是否允许发送
        if not self.status_transmit_banned:
            if not self.is_key_pressed:
                # 设置页面为强聚焦模式，防止用户按下按钮后切换到其他页面导致蜂鸣器无法停止
                self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
                # 更改按钮图标
                self.btn_send_message.setIcon(FIF.SEND_FILL)
                # 启动蜂鸣器
                self.buzz.start(self.send_buzz_status)
                # 启动摩斯电码生成动画
                self.morsecode_visualizer.start_generating(5)
                # 更新信号灯状态
                self.signal_light.set_state(1)

                # 记录按键按下时间
                self.start_time = time.time()
                self.is_key_pressed = True

                # 当鼠标持续点击时，关闭之前的计时器
                self.word_timer.stop()
                self.letter_timer.stop()

                # 计算两次按键之间的间隔
                if self.last_key_pressed_time != 0:
                    # 计算两次按键的时间间隔
                    self.pressed_keys_time_interval = time.time() - self.last_key_pressed_time
                    # 如果间隔过长，则视为 0（非连续操作）
                    if self.pressed_keys_time_interval > 50:
                        self.pressed_keys_time_interval = 0
                else:
                    self.pressed_keys_time_interval = 0


    def on_btn_send_message_released(self):
        """
        处理发送按钮释放事件。
        当发送按钮被释放时，执行以下操作：
            - 更新 UI 状态（按钮图标、信号灯、动画等）。
            - 停止蜂鸣器和摩斯电码生成动画。
            - 记录按键持续时间并发送消息到服务器。
            - 启动字母计时器。

        行为：
            - 如果按键已被按下，则执行释放逻辑。
            - 更新 UI 和内部状态，停止相关功能。
        """
        if self.is_key_pressed:
            # 设置页面为点击聚焦模式，防止按钮释放后切换到其他页面导致蜂鸣器无法停止
            self.setFocusPolicy(Qt.FocusPolicy.ClickFocus)
            # 更改按钮图标
            self.btn_send_message.setIcon(FIF.SEND)
            # 停止摩斯电码生成动画
            self.morsecode_visualizer.stop_generating(5)
            # 更新信号灯状态
            self.signal_light.set_state(2)

            # 停止蜂鸣器
            self.buzz.stop()
            # 计算按键持续时间（毫秒）
            self.pressed_keys_time = (time.time() - self.start_time) * 1000
            print(f'{self.tr("按键持续时间：")} {self.pressed_keys_time}')

            # 根据按键持续时间确定摩斯电码字符
            morse_code = self.determine_morse_character(self.pressed_keys_time)

            # 发送消息到服务器
            self.update_sent_label(morse_code, self.pressed_keys_time, self.pressed_keys_time_interval * 1000)

            # 更新按键状态
            self.is_key_pressed = False

            # 启动字母计时器
            self.start_letter_timer()

            # 记录按键按下时间和状态
            self.last_key_pressed_status = True
            self.last_key_pressed_time = time.time()

    def keyPressEvent(self, event):
        """
        监听键盘按键按下事件。
        根据按键类型（手动键或自动键）执行相应操作，如启动蜂鸣器、动画、计时器等。

        参数：
            - event: 键盘事件对象，包含按键信息。

        行为：
            - 如果是手动键且允许发送，则启动蜂鸣器和动画，记录按键时间。
            - 如果是自动键，则根据按键类型（点或划）启动自动发送逻辑。
        """
        if not event.isAutoRepeat():  # 忽略按键自动重复事件
            # 设置页面为强聚焦模式，防止按钮释放后切换到其他页面导致蜂鸣器无法停止
            self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

            # 判断是手动键还是自动键
            if not self.autokey_status:
                # 手动键
                if event.key() == int(self.saved_key[0]):  # 检查是否按下指定键
                    # 检查是否允许发送
                    if not self.status_transmit_banned:
                        # 允许发送
                        if not self.is_key_pressed:
                            # 启动摩斯电码生成动画
                            self.morsecode_visualizer.start_generating(5)
                            # 更新信号灯状态
                            self.signal_light.set_state(1)
                            # 启动蜂鸣器
                            self.buzz.start(self.send_buzz_status)
                            # 记录按键按下时间
                            self.start_time = time.time()
                            self.is_key_pressed = True
                            # 停止之前的计时器
                            self.word_timer.stop()
                            self.letter_timer.stop()

                            # 计算两次按键之间的间隔
                            if self.last_key_pressed_time != 0:
                                self.pressed_keys_time_interval = time.time() - self.last_key_pressed_time
                                # 如果间隔过长，则视为 0
                                if self.pressed_keys_time_interval > 10:
                                    self.pressed_keys_time_interval = 0
                            else:
                                self.pressed_keys_time_interval = 0
            else:
                # 自动键
                # 第一个键是点（dot），第二个键是划（dash）
                if event.key() == int(self.saved_key[0]):  # 按下点键
                    self.pressed_keys_autokey.add(int(self.saved_key[0]))
                    if not self.is_sending_autokey:  # 如果当前未发送
                        self.current_char_autokey = self.dot
                        # 处理自动键超时
                        if not self.timer_autokey.isActive():
                            self.handle_timer_autokey_timeout()
                            self.timer_autokey.start(self.dot_duration)
                        self.is_sending_autokey = True

                elif event.key() == int(self.saved_key[1]):  # 按下划键
                    self.pressed_keys_autokey.add(int(self.saved_key[1]))
                    if not self.is_sending_autokey:  # 如果当前未发送
                        self.current_char_autokey = self.dash
                        # 处理自动键超时
                        if not self.timer_autokey.isActive():
                            self.handle_timer_autokey_timeout()
                            self.timer_autokey.start(self.dash_duration)
                        self.is_sending_autokey = True

                # 停止之前的计时器
                self.word_timer.stop()
                self.letter_timer.stop()

    def keyReleaseEvent(self, event):
        """
        监听键盘按键释放事件。
        当按键释放时，执行以下操作：
            - 更新 UI 状态（信号灯、动画等）。
            - 停止蜂鸣器和摩斯电码生成动画。
            - 记录按键持续时间并发送消息到服务器。
            - 启动字母计时器。

        参数：
            - event: 键盘事件对象，包含按键信息。

        行为：
            - 如果是手动键，则执行释放逻辑。
            - 如果是自动键，则停止相关功能并重置状态。
        """
        # 设置页面为点击聚焦模式，防止按钮释放后切换到其他页面导致蜂鸣器无法停止
        self.setFocusPolicy(Qt.FocusPolicy.ClickFocus)

        if not event.isAutoRepeat():  # 忽略按键自动重复事件
            # 判断是手动键还是自动键
            if not self.autokey_status:
                # 手动键
                if self.is_key_pressed:
                    # 停止摩斯电码生成动画
                    self.morsecode_visualizer.stop_generating(5)
                    # 更新信号灯状态
                    self.signal_light.set_state(2)
                    # 停止蜂鸣器
                    self.buzz.stop()

                    # 计算按键持续时间（毫秒）
                    self.pressed_keys_time = (time.time() - self.start_time) * 1000
                    print(f'{self.tr("按键持续时间：")} {self.pressed_keys_time}')

                    # 根据按键持续时间确定摩斯电码字符
                    morse_code = self.determine_morse_character(self.pressed_keys_time)

                    # 发送消息到服务器
                    self.update_sent_label(morse_code, self.pressed_keys_time, self.pressed_keys_time_interval * 1000)

                    # 更新按键状态
                    self.is_key_pressed = False
                    # 启动字母计时器
                    self.start_letter_timer()

                    # 记录按键按下时间和状态
                    self.last_key_pressed_status = True
                    self.last_key_pressed_time = time.time()
            else:
                # 自动键
                if event.key() in self.pressed_keys_autokey:
                    self.pressed_keys_autokey.remove(event.key())

                    if event.key() == int(self.saved_key[0]) or event.key() == int(self.saved_key[1]):
                        if not self.pressed_keys_autokey:  # 如果没有其他按键被按下
                            # 停止自动键计时器
                            self.timer_autokey.stop()
                            # 停止蜂鸣器
                            self.buzz.stop_play_for_duration()
                            # 重置当前字符状态
                            self.current_char_autokey = None
                            # 重置发送标志
                            self.is_sending_autokey = False
                            # 启动字母计时器
                            self.start_letter_timer()

    def handle_timer_autokey_timeout(self):
        """
        处理自动键超时事件。
        根据当前字符状态（点或划）执行相应操作，如启动动画、蜂鸣器、信号灯等。
        同时根据按键状态切换当前字符（点或划），并发送消息到服务器。

        行为：
            - 如果当前字符是点（dot），则启动点相关的动画、蜂鸣器和信号灯。
            - 如果当前字符是划（dash），则启动划相关的动画、蜂鸣器和信号灯。
            - 根据按键状态切换当前字符，并发送消息到服务器。
        """
        
        if self.current_char_autokey:
            # 如果当前字符是点
            if self.current_char_autokey == self.dot:
                # 启动蜂鸣器
                self.buzz.play_for_duration(50, self.send_buzz_status)
                # 更新信号灯状态
                self.signal_light.switch_to_red_for_duration(50)
                # 启动下一个计时器
                self.timer_autokey.start(self.dot_duration)

                # 如果划键仍然被按下，则切换到划
                if int(self.saved_key[1]) in self.pressed_keys_autokey:
                    self.current_char_autokey = self.dash
                    # 启动动画
                    self.show_visualizer(self.dash)
                else:
                    self.current_char_autokey = self.dot  # 否则保持为点
                    # 启动动画
                    self.show_visualizer(self.dot)
            else:
                # 如果当前字符是划
                self.timer_autokey.start(self.dash_duration)
                # 启动蜂鸣器
                self.buzz.play_for_duration(90, self.send_buzz_status)
                # 更新信号灯状态
                self.signal_light.switch_to_red_for_duration(80)

                # 如果点键仍然被按下，则切换到点
                if int(self.saved_key[0]) in self.pressed_keys_autokey:
                    self.current_char_autokey = self.dot
                    # 启动动画
                    self.show_visualizer(self.dot)
                else:
                    self.current_char_autokey = self.dash  # 否则保持为划
                    # 启动动画
                    self.show_visualizer(self.dash)

            # 根据当前字符类型发送消息到服务器
            if self.current_char_autokey == self.dot:
                self.update_sent_label(self.current_char_autokey, self.dot_duration, 50)
            elif self.current_char_autokey == self.dash:
                self.update_sent_label(self.current_char_autokey, self.dash_duration, 50)

    def determine_morse_character(self, duration):
        """
        根据按键持续时间确定摩斯电码字符（点或划）。

        参数：
            - duration: 按键持续时间（毫秒）。

        返回值：
            - ".": 如果持续时间小于点的时间阈值。
            - "-": 如果持续时间大于或等于点的时间阈值。
        """
        decoder = AdaptiveMorseDecoder(
                initial_wpm=self.config_manager.get_wpm(),
                sensitivity=0.4,
                learning_window=100
            )
        
        # 获取解码结果和置信度
        character, confidence = decoder.process_duration(duration)
            # 手动触发持久化
        #decoder.persist_state()
        return character


    def update_sent_label(self, morse_code, play_time, play_interval):
        """
        发送数据到服务器并更新 UI。
        将摩斯电码、按键时间和间隔时间发送到服务器，并在 UI 上显示发送的内容。

        参数：
            - morse_code: 摩斯电码字符（点或划）。
            - play_time: 按键持续时间（毫秒），默认值为 100。
            - play_interval: 按键间隔时间（毫秒），默认值为 200。

        行为：
            - 开始通联记录。
            - 如果已连接到服务器，则发送消息到服务器。
            - 在 UI 上显示发送的摩斯电码。
        """
        # 开始通联记录
        self.start_record_send(morse_code, play_time, play_interval)

        # 如果已连接到服务器，则发送消息
        if self.is_connected:
            self.send_morse_code_to_server(morse_code, play_time, play_interval)

        # 在 UI 上显示发送的摩斯电码
        self.edit_morse_code.setText(self.morse_code)
        self.morse_code += morse_code
        print(f'发时的morsecode: {self.morse_code}')

    def send_morse_code_to_server(self, morse_code, play_time=100, play_interval=200):
        """
        将摩斯电码数据发送到服务器。

        参数：
            - morse_code: 摩斯电码字符（点或划）。
            - play_time: 按键持续时间（毫秒），默认值为 100。
            - play_interval: 按键间隔时间（毫秒），默认值为 200。
        """
        # 构造 JSON 数据
        json_data = {
            "morseCode": morse_code,
            "myCall": self.my_call,
            "pressedTime": int(play_time),
            "pressedIntervalTime": int(play_interval),
            "myChannel": self.channel_name
        }

        # 将字典转换为字符串，并将单引号替换为双引号
        message = str(json_data).replace("'", '"')
        print(f'本次将发送的消息为: {message}')

        # 发送消息到服务器
        self.client.send_message(message)
    
    def start_letter_timer(self):
        """
        启动字母间隔计时器。
        用于在发送摩斯电码时，控制字母之间的间隔时间。
        """
        self.letter_timer.start(self.letter_interval_duration)

    def start_word_timer(self):
        """
        启动单词间隔计时器。
        用于在发送摩斯电码时，控制单词之间的间隔时间。
        """
        self.word_timer.start(self.word_interval_duration)

    def handle_letter_timeout(self):
        """
        处理字母间隔计时器超时事件。
        当字母间隔计时器超时时，添加字母分隔符并更新 UI，同时启动单词间隔计时器。

        行为：
            - 在摩斯电码中添加字母分隔符 `/`。
            - 更新 UI 上的摩斯电码显示。
            - 如果已连接到服务器，则发送分隔符到服务器。
            - 在记录的消息中添加分隔符。
            - 启动单词间隔计时器。
            - 翻译摩斯电码并更新翻译结果。
        """
        print(f'字母计时器运行')
        # 添加字母分隔符
        self.morse_code += "/"
        self.edit_morse_code.setText(self.morse_code)

        # 如果已连接到服务器，则发送分隔符到服务器
        if self.is_connected:
            self.send_morse_code_to_server("/", self.dash_duration, 50)

        # 在记录的消息中添加分隔符
        self.current_message_to_record += "/"

        # 启动单词间隔计时器
        self.start_word_timer()

        # 翻译摩斯电码并更新翻译结果
        extracted_mores_code = self.extract_cleaned_parts(self.morse_code)
        self.morse_code_translation_temp = self.translator.letter_to_morse(extracted_mores_code)
        self.morse_code_translation += self.morse_code_translation_temp
        self.edit_send_translation.setText(self.morse_code_translation)

    def handle_word_timeout(self):
        """
        处理单词间隔计时器超时事件。
        当单词间隔计时器超时时，添加单词分隔符并更新 UI。

        行为：
            - 在摩斯电码中添加单词分隔符 `//`。
            - 更新 UI 上的摩斯电码显示。
            - 如果已连接到服务器，则发送分隔符到服务器。
            - 在记录的消息中添加分隔符。
            - 在翻译结果中添加空格并更新 UI。
        """
        print(f'单词计时器运行')
        # 添加单词分隔符
        self.morse_code += "//"
        self.edit_morse_code.setText(self.morse_code)

        # 如果已连接到服务器，则发送分隔符到服务器
        if self.is_connected:
            self.send_morse_code_to_server("//", self.dash_duration, 50)

        # 在记录的消息中添加分隔符
        self.current_message_to_record += "//"

        # 在翻译结果中添加空格并更新 UI
        self.morse_code_translation += " "
        self.edit_send_translation.setText(self.morse_code_translation + " ")
    
    def handle_transmit_banned_timeout(self):
        """
        处理发送禁止计时器超时事件。
        当发送禁止计时器超时时，恢复发送状态并更新 UI 提示。

        行为：
            - 恢复发送状态（`self.status_transmit_banned = False`）。
            - 更新发送提示为默认状态（`self.SENT_CODE`）。
            - 更新接收提示为默认状态（`self.RECEIVED_CODE`）。
        """
        # 恢复发送状态
        self.status_transmit_banned = False

        # 更新发送提示为默认状态
        self.label_morse_sent.setText(self.SENT_CODE)

        # 更新接收提示为默认状态
        self.label_morse_received.setText(f'{self.RECEIVED_CODE}')

    def handle_link_record_timeout(self):
        """
        处理通信记录计时器超时事件。
        当通信记录计时器超时时，记录未记录的通信记录并重置状态。

        行为：
            - 如果正在发送或接收，则获取通信持续时间并记录通信记录。
            - 重置当前消息、播放时间和间隔时间。
            - 停止通信记录计时器。
        """
        if self.is_sending or self.is_receiving:
            # 获取通信持续时间
            duration = self.get_connection_duration()
            # 确定通信方向（发送或接收）
            direction = 'Send' if self.is_sending else 'Receive'

            # 记录通信记录
            self.handle_link_record(
                self.current_message_to_record,
                direction,
                duration,
                self.current_message_play_time,
                self.current_message_play_time_invertal
            )

            # 重置当前消息、播放时间和间隔时间
            self.current_message_to_record = ""
            self.current_message_play_time = ""
            self.current_message_play_time_invertal = ""

            # 重置发送和接收状态
            self.is_sending = False
            self.is_receiving = False

            # 停止通信记录计时器
            self.timer_link_record.stop()

    def handle_link_record(self, message, direction, duration, play_time=0, play_time_interval=0):
        """
        处理每条摩斯电码的接收或发送记录。
        根据通信方向（发送或接收）构造记录，并将其保存到数据库中。

        参数：
            - message: 通信消息内容。
            - direction: 通信方向（"Send" 或 "Receive"）。
            - duration: 通信持续时间。
            - play_time: 播放时间（可选，默认为 0）。
            - play_time_interval: 播放间隔时间（可选，默认为 0）。

        行为：
            - 根据通信方向构造记录。
            - 将记录保存到数据库中。
        """
        if direction == "Send":
            # 构造发送记录
            record = {
                'time': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),  # 当前时间
                'message': message,  # 消息内容
                'direction': direction,  # 通信方向
                'duration': duration,  # 通信持续时间
                'play_time': play_time,  # 播放时间
                'play_time_interval': play_time_interval  # 播放间隔时间
            }
        else:
            # 构造接收记录
            record = {
                'time': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),  # 当前时间
                'message': message,  # 消息内容
                'direction': direction,  # 通信方向
                'duration': duration,  # 通信持续时间
                'sender': self.call_of_sender  # 发送方呼号
            }

        # 将记录保存到数据库中
        self.database_tool.write_qso_record(record)

    def get_connection_duration(self):
        """
        获取通信连接的持续时间。
        如果开始记录时间存在，则计算从开始时间到当前时间的持续时间（秒）。

        返回值：
            - 通信连接的持续时间（秒）。如果未开始记录，则返回 0。
        """
        if self.start_record_time:
            # 计算从开始时间到当前时间的持续时间（秒）
            return (datetime.now() - self.start_record_time).total_seconds()
        return 0  # 如果未开始记录，则返回 0

    def start_record_receive(self, char):
        """
        开始记录接收到的摩斯电码。
        如果当前未处于接收或发送状态，则记录通信开始时间。
        如果正在发送，则立即记录发送的消息。

        参数：
            - char: 接收到的摩斯电码字符。

        行为：
            - 记录通信开始时间（如果未开始记录）。
            - 如果正在发送，则立即记录发送的消息。
            - 将接收到的字符添加到当前消息中。
            - 启动通信记录计时器。
        """
        # 如果当前未处于接收或发送状态，则记录通信开始时间
        if not self.is_receiving and not self.is_sending:
            self.start_record_time = datetime.now()

        # 如果正在发送，则立即记录发送的消息
        if self.is_sending:
            duration = self.get_connection_duration()  # 获取通信持续时间
            direction = 'Receive'
            self.handle_link_record(char, direction, duration)

        # 将接收到的字符添加到当前消息中
        self.current_message_to_record += char

        # 标记为正在接收
        self.is_receiving = True

        # 启动通信记录计时器
        self.timer_link_record.start()

    def start_record_send(self, char, play_time, play_time_interval):
        """
        开始记录发送的摩斯电码。
        如果当前未处于发送或接收状态，则记录通信开始时间。
        如果正在接收，则立即记录接收的消息。

        参数：
            - char: 发送的摩斯电码字符。
            - play_time: 按键持续时间。
            - play_time_interval: 按键间隔时间。

        行为：
            - 记录通信开始时间（如果未开始记录）。
            - 如果正在接收，则立即记录接收的消息。
            - 将发送的字符添加到当前消息中。
            - 记录按键持续时间和间隔时间。
            - 启动通信记录计时器。
        """
        # 如果当前未处于发送或接收状态，则记录通信开始时间
        if not self.is_sending and not self.is_receiving:
            self.start_record_time = datetime.now()

        # 如果正在接收，则立即记录接收的消息
        if self.is_receiving:
            duration = self.get_connection_duration()  # 获取通信持续时间
            direction = 'Send'
            self.handle_link_record(char, direction, duration)

        # 将发送的字符添加到当前消息中
        self.current_message_to_record += char

        # 记录按键持续时间和间隔时间
        if self.current_message_play_time:
            self.current_message_play_time += "," + str(play_time)
            self.current_message_play_time_invertal += "," + str(play_time_interval)
        else:
            self.current_message_play_time = str(play_time)
            self.current_message_play_time_invertal = str(play_time_interval)

        # 标记为正在发送
        self.is_sending = True

        # 启动通信记录计时器
        self.timer_link_record.start()

    def extract_cleaned_parts(self, input_data):
        """
        从输入数据中提取并清理部分内容，支持多维数组。
        使用 '///' 区分组，使用 '/' 分隔组内元素。

        参数：
            - input_data: 输入字符串或多维数组。

        返回值：
            - 清理后的结果，按组分组为列表。
        """
        if isinstance(input_data, str):
            # 如果是字符串，处理并返回清理后的组
            if input_data.endswith("/"):
                input_data = input_data[:-1]  # 移除末尾的 '/'
            # 使用正则表达式过滤出有效的摩斯电码字符
            cleaned_str = re.sub(r"[^.\-/]", "", input_data)
            # 按 '///' 分组，并按 '/' 分隔组内元素
            groups = cleaned_str.split("///")
            cleaned_groups = []
            for group in groups:
                parts = group.split("/")
                cleaned_parts = [part.strip() for part in parts if part.strip()]
                if cleaned_parts:
                    cleaned_groups.append(cleaned_parts)
            return cleaned_groups[-1][-1]  # 返回清理后的结果组
        elif isinstance(input_data, list):
            # 如果是列表，递归处理每个元素
            cleaned_results = []
            for item in input_data:
                cleaned_result = self.extract_cleaned_parts(item)  # 递归调用
                if cleaned_result:  # 只保留非空结果
                    cleaned_results.append(cleaned_result)
            return cleaned_results  # 返回清理后的结果列表
        return []  # 如果输入既不是字符串也不是列表，则返回空列表

    def clean_screen(self):
        """
        清空屏幕内容。
        清除摩斯电码输入框、接收框、翻译框等内容。
        """
        # 清空屏幕内容
        self.edit_morse_code.setText("")  # 清空摩斯电码输入框
        self.edit_morse_received.setText("")  # 清空接收框
        self.edit_send_translation.setText("")  # 清空发送翻译框
        self.edit_received_translation.setText("")  # 清空接收翻译框
        self.morse_code_translation = ""  # 重置摩斯电码翻译
        self.morse_code = ""  # 重置摩斯电码

    def about(self):
        """
        打开关于页面。
        创建并显示关于对话框，居中显示。
        """
        dialog = AboutDialog(self)  # 创建关于对话框
        dialog.move(self.center_point_x, self.center_point_y)  # 居中显示
        dialog.exec_()  # 显示对话框

    def check_qso(self):
        """
        检查 QSO 记录。
        创建并显示 QSO 记录对话框，居中显示。
        """
        qso = QsoRecordDialog()  # 创建 QSO 记录对话框
        qso.move(self.center_point_x, self.center_point_y)  # 居中显示
        qso.exec()  # 显示对话框

    def general_setting(self):
        """
        打开通用设置页面。
        创建并显示通用设置对话框，居中显示。
        如果用户接受设置，则更新相关配置和 UI 状态。
        """
        dialog = GeneralSettingDialog(self)  # 创建通用设置对话框
        dialog.move(self.center_point_x, self.center_point_y)  # 居中显示

        if dialog.exec_() == QDialog.Accepted:  # 如果用户接受设置
            # 更新点持续时间
            self.dot_duration = int(self.config_manager.get_dot_time())

            # 更新 UI 相关设置
            self.is_translation_visible()  # 更新翻译可见性
            self.autokey_status = self.config_manager.get_autokey_status()  # 更新自动键状态
            self.send_buzz_status = self.config_manager.get_send_buzz_status()  # 更新发送蜂鸣器状态
            self.receive_buzz_status = self.config_manager.get_receive_buzz_status()  # 更新接收蜂鸣器状态

            # 更新键盘按键
            self.saved_key = self.config_manager.get_keyborad_key().split(',')
            self.label_keybord_hint.setText(f'Keyboard sending: Dot {dialog.key_one} Dash {dialog.key_two}')

            # 更新呼号
            self.set_my_call()

            # 更新可视化器可见性
            self.set_visualizer_visibility()

            # 重新初始化蜂鸣器
            self.buzz = BuzzerSimulator()

    def transmitter_setting(self):
        """
        打开发射器设置页面。
        创建并显示发射器设置对话框，居中显示。
        如果用户接受设置，则更新相关配置和 UI 状态。
        """
        dialog = TransmitterSettingDialog(self)  # 创建发射器设置对话框
        dialog.move(self.center_point_x, self.center_point_y)  # 居中显示

        if dialog.exec_() == QDialog.Accepted:  # 如果用户接受设置
            # 更新点持续时间
            self.dot_duration = int(self.config_manager.get_dot_time())

            # 更新 UI 相关设置
            self.label_dot_duration.setText(f'Dot interval: {self.config_manager.get_dot_time()}ms')
            self.dash_duration = self.config_manager.get_dash_time()  # 更新划持续时间
            self.letter_interval_duration = self.config_manager.get_letter_interval_duration_time()  # 更新字母间隔时间
            self.word_interval_duration = self.config_manager.get_word_interval_duration_time()  # 更新单词间隔时间

    def morse_key_modifty_setting(self):
        """
        打开摩斯电码键修改设置页面。
        创建并显示摩斯电码键修改对话框，居中显示。
        """
        dialog = KeyModifierDialog(self)  # 创建摩斯电码键修改对话框
        dialog.move(self.center_point_x, self.center_point_y)  # 居中显示
        dialog.exec_()  # 显示对话框
        # Show common phrases action in help options

    def show_common_phrases_action(self):
        """
        显示常用短语表。
        打开常用短语表工具窗口。
        """
        self.table_tool_communication_words.show()

    def show_reference_table_action(self):
        """
        显示摩斯电码参考表。
        打开摩斯电码参考表工具窗口。
        """
        self.table_tool_morse_code.show()

    def is_translation_visible(self):
        """
        检查翻译是否可见。
        根据配置管理器的设置，设置文本框的回显模式（密码模式或普通模式）。
        """
        if not self.config_manager.get_translation_visibility():
            # 如果翻译不可见，设置为密码模式
            self.edit_morse_code.setEchoMode(QLineEdit.Password)
            self.edit_morse_received.setEchoMode(QLineEdit.Password)
            self.edit_received_translation.setEchoMode(QLineEdit.Password)
            self.edit_send_translation.setEchoMode(QLineEdit.Password)
        else:
            # 如果翻译可见，设置为普通模式
            self.edit_morse_code.setEchoMode(QLineEdit.Normal)
            self.edit_morse_received.setEchoMode(QLineEdit.Normal)
            self.edit_received_translation.setEchoMode(QLineEdit.Normal)
            self.edit_send_translation.setEchoMode(QLineEdit.Normal)

    def set_my_call(self):
        """
        设置呼号。
        从配置管理器中获取呼号并更新 UI 显示。
        """
        self.my_call = self.config_manager.get_my_call()
        if not self.my_call == "":
            self.label_my_call.setText(f'{self.my_call.upper()}')  # 更新呼号显示

    def set_visualizer_visibility(self):
        """
        设置可视化器的可见性。
        根据配置管理器的设置，显示或隐藏可视化器。
        """
        if self.config_manager.get_visualizer_visibility():
            self.morsecode_visualizer.show()  # 显示可视化器
        else:
            self.morsecode_visualizer.hide()  # 隐藏可视化器

    def show_visualizer(self, Morsechar):
        # Show animation based on dots and dashes
        if Morsechar == self.dot:
            self.morsecode_visualizer.generate_blocks(height=15)
        else:
            self.morsecode_visualizer.generate_blocks(height=45)
    
    def set_font_size(self):
        """
        设置字体大小。
        从配置管理器中获取字体大小，并应用到相关文本框。
        """
        font_size = self.config_manager.get_sender_font_size()  # 获取字体大小
        font = QFont()
        font.setFamily("Arial")  # 设置字体为 Arial
        font.setPointSize(font_size)  # 设置字体大小
        self.edit_morse_code.setFont(font)  # 应用到摩斯电码输入框
        self.edit_morse_received.setFont(font)  # 应用到接收框
        self.edit_send_translation.setFont(font)  # 应用到发送翻译框
        self.edit_received_translation.setFont(font)  # 应用到接收翻译框

    def initQueryClientsTimer(self):
        """初始化定时器，每隔5分钟触发一次查询"""
        self.timer_query_clients = QTimer(self)
        self.timer_query_clients.timeout.connect(self.startQuery)
        self.timer_query_clients.start(60000)  #40秒查询一次人数

    
    def startQuery(self):
        """启动异步查询，服务器在线人数查询"""

        counter = MQTTOnlineCounter()
        count = counter.get_online_count()
        if count > 0:
            self.label_number_clients.setText(f'服务器在线人数：{count}')
        elif count == 0:
            self.label_number_clients.setText(f'服务器在线人数：{count}')
        else:
            self.label_number_clients.setText(f'查询在线人数时出现错误')



    def check_myCall(self):
        """
        检查用户是否设置了呼号
        """
        my_call = self.config_manager.get_my_call()
        if my_call == "None":
            return False
        else:
            return True