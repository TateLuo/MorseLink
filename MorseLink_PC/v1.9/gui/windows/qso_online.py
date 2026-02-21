import re, string
from datetime import datetime
import math
import time, json
from collections import deque
from PySide6.QtGui import  QFont
from PySide6.QtWidgets import (
    QApplication,
    QWidget,
    QLabel,
    QVBoxLayout,
    QWidget,
    QHBoxLayout,
    QLineEdit,
    QDialog,
    QMessageBox,
    QPlainTextEdit,
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QPushButton, QToolButton
from PySide6.QtWidgets import QProgressBar


from PySide6.QtWidgets import QFrame, QSizePolicy
from PySide6.QtGui import QFontDatabase

from utils.translator import MorseCodeTranslator
from utils.sound import BuzzerSimulator
from utils.config_manager import ConfigManager
from utils.database_tool import DatabaseTool
from utils.multi_tablet_tool import MultiTableTool
from utils.check_update import VersionChecker
from utils.received_message_processor import MultiChannelProcessor

from gui.widget.morsecode_visualizer import MorseCodeVisualizer
from gui.widget.signal_light import SignalLightWidget
from gui.dialog.general_setting_dialog import GeneralSettingDialog
from gui.dialog.about_dialog import AboutDialog
from gui.dialog.qso_record_dialog import QsoRecordDialog
from gui.dialog.key_modifier_dialog import KeyModifierDialog
from gui.dialog.transmitter_setting_dialog import TransmitterSettingDialog

from service.signal.qt_signal import MySignal
from service.mqtt_client import MQTTClient
from service.keying_controller import AutoElementEvent
from service.tx_keying_runtime import TxKeyingRuntime
from service.auth.credential_store import PlainConfigCredentialStore


from ui_widgets import PushButton, TransparentPushButton, Slider
from ui_widgets import FluentIcon as FIF






class QSOOline(QWidget):
    """在线通联主界面。"""

    def __init__(self, stackedWidget, context=None):
        super().__init__()
        self.context = context


        self.stackedWidget = stackedWidget
        self.setWindowTitle(self.tr("MorseLink"))

        self.setMinimumSize(0, 0)
        self.center()


        self.table_tool_morse_code = MultiTableTool("morse_code")
        self.table_tool_communication_words = MultiTableTool("communication_words")



        self.RECEIVED_CODE = self.tr("<h3>收到电码:</h3>")
        self.RECEIVED_TRANLATION = self.tr("<h3>收到电码翻译:</h3>")
        self.SEND_TRANSLATION = self.tr("<h3>发送电码翻译:</h3>")
        self.SENT_CODE = self.tr("<h3>发送电码:</h3>")
        self.SENT_CODE_BANNED = self.tr("<h3>发送电码：发射禁用，请稍后再试</h3>")
        self.NUMBER_CHANNEL = self.tr("<h3>当前频道人数:</h3>")


        self.config_manager = self.context.config_manager if self.context else ConfigManager()


        self.morse_code = ""
        self.morse_code_received = ""
        self.morse_code_translation = ""
        self.received_translation = ""
        self.dot_duration = int(self.config_manager.get_dot_time())
        self.dash_duration = int(self.config_manager.get_dash_time())
        self.dot = "."
        self.dash = "-"
        self.letter_interval_duration = int(self.config_manager.get_letter_interval_duration_time())
        self.word_interval_duration = int(self.config_manager.get_word_interval_duration_time())
        self.keyer_mode = str(self.config_manager.get_keyer_mode() or "straight").lower()
        self.rx_tx_lock_tail_ms = int(self.config_manager.get_rx_tx_lock_tail_ms())
        self.send_buzz_status = self.config_manager.get_send_buzz_status()
        self.receive_buzz_status = self.config_manager.get_receive_buzz_status()


        self.channel_name = self.config_manager.get_server_channel_name()


        self.gap_time = None


        self.letter_timer = QTimer(self)
        self.letter_timer.setSingleShot(True)
        self.letter_timer.timeout.connect(self.handle_letter_timeout)


        self.word_timer = QTimer(self)
        self.word_timer.setSingleShot(True)
        self.word_timer.timeout.connect(self.handle_word_timeout)


        self.timer_link_record = QTimer(self)
        self.timer_link_record.setInterval(3000)
        self.timer_link_record.timeout.connect(self.handle_link_record_timeout)
        self.is_receiving = False
        self.is_sending = False
        self.current_message_to_record = ""
        self.start_record_time = None


        self.status_transmit_banned = False
        self.transmit_banned_timer = QTimer(self)
        self.transmit_banned_timer.setSingleShot(True)
        self.transmit_banned_timer.timeout.connect(self.handle_transmit_banned_timeout)


        self.is_connected = False
        self.is_connecting = False
        self._disconnect_requested = False
        self._last_connect_error = ""
        self.client = None
        self._pending_send_msgs = deque()
        self._send_flush_timer = QTimer(self)
        self._send_flush_timer.setInterval(10)
        self._send_flush_timer.timeout.connect(self._flush_send_queue)
        self._connect_spinner_frames = ("|", "/", "-", "\\")
        self._connect_spinner_index = 0
        self._connect_anim_timer = QTimer(self)
        self._connect_anim_timer.setInterval(120)
        self._connect_anim_timer.timeout.connect(self._tick_connecting_indicator)
        self._connect_timeout_timer = QTimer(self)
        self._connect_timeout_timer.setSingleShot(True)
        self._connect_timeout_timer.setInterval(10000)
        self._connect_timeout_timer.timeout.connect(self._handle_connect_timeout)
        self._topic_switch_timer = QTimer(self)
        self._topic_switch_timer.setSingleShot(True)
        self._topic_switch_timer.setInterval(250)
        self._topic_switch_timer.timeout.connect(self._apply_topic_window_update)


        self._protocol_name = "morselink.keyevent"
        self._protocol_version = 2
        self._topic_prefix = "morselink/v2/keyevent"
        self._side_channel_range = 5
        self._desired_sub_topics = set()
        self._tx_clock_origin_ms = int(time.monotonic() * 1000)
        self._tx_session_id = f"{str(self.config_manager.get_my_call() or 'UNKNOWN').upper()}-{int(time.time() * 1000)}"
        self._tx_event_seq = 0
        self._tx_last_event_time_ms = -1


        self._rx_event_states = {}
        self.call_of_sender = self.tr("未知台站")
        self._rx_active_same_key = None

        self._rx_debounce_window_ms = 60
        self._rx_word_tail_delay_ms = 0
        self._rx_letter_timer = QTimer(self)
        self._rx_letter_timer.setSingleShot(True)
        self._rx_letter_timer.timeout.connect(self._finalize_receive_letter_from_timer)
        self._rx_word_timer = QTimer(self)
        self._rx_word_timer.setSingleShot(True)
        self._rx_word_timer.timeout.connect(self._finalize_receive_word_from_timer)
        self._rx_force_up_timer = QTimer(self)
        self._rx_force_up_timer.setSingleShot(True)
        self._rx_force_up_timer.timeout.connect(self._force_finalize_stuck_keydown)



        self.mysignal = MySignal()
        self.mysignal.process_received_signal.connect(self.process_messages)


        self.translator = MorseCodeTranslator()

        self._ui_scale = 1.0
        self._scale_metrics_ready = False
        self._last_decision_tail = []
        self._last_decision_active_index = -2
        self._last_raw_tail = None
        self._last_decode_text = None
        self._max_morse_buffer = 4096
        self._max_translation_buffer = 2048


        self.initUI()


        self.buzz = self.create_buzzer()


        self.last_sound_play_time = 0


        self.initSetting()
        self._capture_scale_metrics()

        self.tx_runtime = TxKeyingRuntime(
            parent=self,
            buzzer=self.buzz,
            get_wpm=self.config_manager.get_wpm,
            on_stop_gap_timers=self._stop_send_gap_timers,
            on_start_letter_timer=self.start_letter_timer,
            on_manual_down=self._tx_runtime_on_manual_down,
            on_manual_up_begin=self._tx_runtime_on_manual_up_begin,
            on_manual_symbol=self._tx_runtime_on_manual_symbol,
            on_auto_symbol=self._tx_runtime_on_auto_symbol,
            on_auto_stopped=self._tx_runtime_on_auto_stopped,
            on_send_event=self._tx_runtime_send_event,
            tx_now_ms=self._tx_now_ms,
        )
        self.key_controller = self.tx_runtime.key_controller
        self._refresh_send_runtime()

    def create_buzzer(self):
        if self.context and hasattr(self.context, "create_buzzer"):
            return self.context.create_buzzer()
        return BuzzerSimulator()

    def create_database_tool(self):
        if self.context and hasattr(self.context, "create_database_tool"):
            return self.context.create_database_tool()
        return DatabaseTool()

    def center(self):


        screen = QApplication.primaryScreen().availableGeometry()

        size = self.geometry()

        self.center_point_x = int((screen.width() - size.width()) / 2)
        self.center_point_y = int((screen.height() - size.height()) / 2)

        self.move(self.center_point_x, self.center_point_y)

    def focusOutEvent(self, event):
        self.buzz.stop()

        self.morsecode_visualizer.stop_generating(5)

        self.signal_light.set_state(0)


        self.key_controller.stop_all(notify=False)


        super().focusOutEvent(event)


    def initUI(self):
        """初始化在线通联页面控件和布局。"""


        self.hbox_main = QHBoxLayout()


        self.vhox_message_and_morsecode_visualizer = QHBoxLayout()


        self.vbox_message = QVBoxLayout()


        self.vhox_message_and_morsecode_visualizer.addLayout(self.vbox_message)


        self.vbox_send_message = QVBoxLayout()


        self.label_number_clients = QLabel(self.tr("当前人数: 未连接服务器"))
        self.label_number_clients.setFixedHeight(30)
        font = QFont('SimHei', 13)
        self.label_number_clients.setFont(font)
        self.label_number_clients.setAlignment(Qt.AlignHCenter)
        self.label_number_clients.hide()



        self.label_frequency = QLabel(self.tr("当前中心频率: {0} kHz").format(self.channel_name))
        self.label_frequency.setFixedHeight(30)
        font = QFont('SimHei', 13)
        self.label_frequency.setFont(font)
        self.label_frequency.setAlignment(Qt.AlignHCenter)



        self.slider_frequency = Slider(Qt.Horizontal, self)
        self.slider_frequency.setMinimum(7000)
        self.slider_frequency.setMaximum(7300)
        self.slider_frequency.setValue(self.channel_name)
        self.slider_frequency.valueChanged.connect(self.update_frequency_label)



        self.label_my_call = QLabel("")
        self.label_my_call.setFixedHeight(30)
        font = QFont('SimHei', 13)
        self.label_my_call.setFont(font)
        self.label_my_call.setAlignment(Qt.AlignHCenter)



        self.hbox_label = QHBoxLayout()
        self.hbox_label.setContentsMargins(0, 0, 0, 0)
        self.vbox_send_message.addLayout(self.hbox_label)


        self.btn_clean_screen = TransparentPushButton(self.tr("清理屏幕"))
        self.btn_clean_screen.setIcon(FIF.BROOM)
        self.btn_clean_screen.clicked.connect(self.clean_screen)



        self.btn_connect_and_disconnect = PushButton(FIF.CONNECT, self.tr("连接服务器"), self)
        self.btn_connect_and_disconnect.clicked.connect(self.connectService)



        self.btn_send_message = PushButton(FIF.SEND, self.tr("点击发报"), self)
        self.btn_send_message.pressed.connect(self.on_btn_send_message_pressed)
        self.btn_send_message.released.connect(self.on_btn_send_message_released)

        self.btn_send_message.setMinimumHeight(100)


        self.signal_light = SignalLightWidget()
        self.signal_light.set_state(0)
        self.signal_light.set_diameter(25)


        self.label_morse_received = QLabel(self.tr("收到电码"))
        self.label_morse_received.hide()
        font = QFont()
        font.setBold(True)
        font.setPointSize(13)
        self.label_morse_received.setFont(font)


        self.hbox_send_message_first_line = QHBoxLayout()
        self.hbox_send_message_first_line.addWidget(self.label_morse_received)

        self.vbox_message.addLayout(self.hbox_send_message_first_line)


        self.edit_morse_received = QLineEdit()
        self.edit_morse_received.hide()
        self.edit_morse_received.setReadOnly(True)
        self.edit_morse_received.setStyleSheet("background: transparent;")
        self.vbox_message.addWidget(self.edit_morse_received)



        self.decoder_panel = self._build_decoder_panel()
        self.vbox_message.addWidget(self.decoder_panel)



        self.label_received_translation = QLabel(self.tr("收到翻译"))
        self.label_received_translation.hide()
        font = QFont()
        font.setBold(True)
        font.setPointSize(13)
        self.label_received_translation.setFont(font)
        self.vbox_message.addWidget(self.label_received_translation)


        self.edit_received_translation = QLineEdit()
        self.edit_received_translation.hide()
        self.edit_received_translation.setReadOnly(True)
        self.edit_received_translation.setStyleSheet("background: transparent;")
        self.vbox_message.addWidget(self.edit_received_translation)


        self.label_send_translation = QLabel(self.tr("发送翻译"))
        self.label_send_translation.hide()
        font = QFont()
        font.setBold(True)
        font.setPointSize(13)
        self.label_send_translation.setFont(font)
        self.vbox_message.addWidget(self.label_send_translation)


        self.edit_send_translation = QLineEdit()
        self.edit_send_translation.hide()
        self.edit_send_translation.setReadOnly(True)
        self.edit_send_translation.setStyleSheet("background: transparent;")
        self.vbox_message.addWidget(self.edit_send_translation)


        self.label_morse_sent = QLabel(self.tr("发送电码"))
        self.label_morse_sent.hide()
        font = QFont()
        font.setBold(True)
        font.setPointSize(13)
        self.label_morse_sent.setFont(font)
        self.vbox_message.addWidget(self.label_morse_sent)


        self.edit_morse_code = QLineEdit()
        self.edit_morse_code.hide()
        self.edit_morse_code.setReadOnly(True)
        self.edit_morse_code.setStyleSheet("background: transparent;")
        self.vbox_message.addWidget(self.edit_morse_code)


        self.morsecode_visualizer = MorseCodeVisualizer()
        self.morsecode_visualizer.enable_adaptive_fps = False
        self.morsecode_visualizer.fps_ms = 16
        self.morsecode_visualizer.timer.start(16)

        self.vbox_message.addWidget(self.morsecode_visualizer, stretch=3)

        self.hbox_main.addLayout(self.vhox_message_and_morsecode_visualizer, stretch=3)


        self.right_panel = self._build_right_panel()
        self.right_panel.setMinimumWidth(320)
        self.right_panel.setMaximumWidth(420)
        self.hbox_main.addWidget(self.right_panel, stretch=1)

        self._apply_right_panel_style(1.0)
        self._apply_decoder_panel_style(1.0)




        self._decoder_refresh_timer = QTimer(self)
        self._decoder_refresh_timer.setSingleShot(True)
        self._decoder_refresh_timer.setInterval(40)
        self._decoder_refresh_timer.timeout.connect(self._refresh_decoder_panel)

        self.edit_received_translation.textChanged.connect(self._schedule_decoder_refresh)
        self.edit_send_translation.textChanged.connect(self._schedule_decoder_refresh)
        self.edit_morse_received.textChanged.connect(self._schedule_decoder_refresh)
        self.edit_morse_code.textChanged.connect(self._schedule_decoder_refresh)


        self._refresh_decoder_panel()



        self.setLayout(self.hbox_main)

    def _schedule_decoder_refresh(self):
        if not self._decoder_refresh_timer.isActive():
            self._decoder_refresh_timer.start()

    def _append_morse_out(self, text: str):
        if not text:
            return
        self.morse_code += text
        if len(self.morse_code) > self._max_morse_buffer:
            self.morse_code = self.morse_code[-self._max_morse_buffer:]
            self.edit_morse_code.setText(self.morse_code)
            return
        self.edit_morse_code.insert(text)

    def _append_send_translation_out(self, text: str):
        if not text:
            return
        self.morse_code_translation += text
        if len(self.morse_code_translation) > self._max_translation_buffer:
            self.morse_code_translation = self.morse_code_translation[-self._max_translation_buffer:]
            self.edit_send_translation.setText(self.morse_code_translation)
            return
        self.edit_send_translation.insert(text)

    def _capture_scale_metrics(self):
        if self._scale_metrics_ready:
            return
        self._scale_metrics_ready = True
        self._base_right_min_width = self.right_panel.minimumWidth()
        self._base_right_max_width = self.right_panel.maximumWidth()
        self._base_top_label_height = self.label_number_clients.height()
        self._base_send_btn_height = self.btn_send_message.minimumHeight()
        self._base_decode_result_height = self.lbl_decode_result.minimumHeight()
        self._base_raw_morse_height = self.lbl_raw_morse.minimumHeight()
        self._base_decision_block_size = self._decision_blocks[0].width() if self._decision_blocks else 42
        self._base_signal_light_diameter = getattr(self.signal_light, "diameter", 25)
        self._capture_base_font_metrics()

    def _capture_base_font_metrics(self):
        for w in [self, *self.findChildren(QWidget)]:
            if w.property("_base_font_size") is not None:
                continue
            f = w.font()
            size = f.pointSizeF()
            if size > 0:
                w.setProperty("_base_font_size", size)

    def _apply_font_scale(self, scale: float):
        for w in [self, *self.findChildren(QWidget)]:
            base = w.property("_base_font_size")
            if base is None:
                continue
            font = w.font()
            font.setPointSizeF(max(8.0, float(base) * scale))
            w.setFont(font)

    def apply_ui_scale(self, scale: float):
        self._capture_scale_metrics()
        scale = max(0.75, min(1.65, float(scale)))
        if abs(scale - self._ui_scale) < 0.02:
            return
        self._ui_scale = scale
        self._apply_font_scale(scale)

        top_h = max(22, int(round(self._base_top_label_height * scale)))
        self.label_number_clients.setFixedHeight(top_h)
        self.label_frequency.setFixedHeight(top_h)
        self.label_my_call.setFixedHeight(top_h)

        right_min = max(260, int(round(self._base_right_min_width * scale)))
        right_max = max(right_min + 40, int(round(self._base_right_max_width * scale)))
        self.right_panel.setMinimumWidth(right_min)
        self.right_panel.setMaximumWidth(right_max)

        self.btn_send_message.setMinimumHeight(max(90, int(round(self._base_send_btn_height * scale))))

        decode_h = max(56, int(round(self._base_decode_result_height * scale)))
        self.lbl_decode_result.setMinimumHeight(decode_h)
        self.lbl_decode_result.setMaximumHeight(decode_h)

        raw_h = max(72, int(round(self._base_raw_morse_height * scale)))
        self.lbl_raw_morse.setMinimumHeight(raw_h)
        self.lbl_raw_morse.setMaximumHeight(raw_h)

        block_size = max(28, int(round(self._base_decision_block_size * scale)))
        for b in self._decision_blocks:
            b.setFixedSize(block_size, block_size)

        if hasattr(self.signal_light, "set_diameter"):
            self.signal_light.set_diameter(max(16, int(round(self._base_signal_light_diameter * scale))))

        self._apply_right_panel_style(scale)
        self._apply_decoder_panel_style(scale)

    def _apply_right_panel_style(self, scale=1.0):
        scale = float(scale)
        title_px = max(11, int(round(14 * scale)))
        meta_px = max(10, int(round(12 * scale)))
        send_px = max(14, int(round(18 * scale)))
        card_caption_px = max(9, int(round(11 * scale)))
        tx_title_px = max(12, int(round(16 * scale)))
        tx_hint_px = max(9, int(round(11 * scale)))
        tx_badge_px = max(9, int(round(12 * scale)))
        mini_v = max(4, int(round(6 * scale)))
        mini_h = max(6, int(round(10 * scale)))
        btn_v = max(6, int(round(8 * scale)))
        btn_h = max(8, int(round(10 * scale)))
        send_pad = max(10, int(round(16 * scale)))
        self.setStyleSheet(f"""
            #rightPanel {{
                background: transparent;
            }}
            #card {{
                background: qlineargradient(
                    x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgba(40,45,52,0.92),
                    stop:1 rgba(28,32,38,0.92)
                );
                border: 1px solid rgba(255,255,255,0.08);
                border-radius: 14px;
            }}
            #cardStrong {{
                background: qlineargradient(
                    x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgba(37,42,48,0.94),
                    stop:1 rgba(27,31,36,0.94)
                );
                border: 1px solid rgba(255,255,255,0.08);
                border-radius: 16px;
            }}
            #cardCaption {{
                color: rgba(232,225,169,0.70);
                font-size: {card_caption_px}px;
                font-weight: 700;
                letter-spacing: 1px;
            }}
            #titleText {{
                color: rgba(255,255,255,0.86);
                font-size: {title_px}px;
                font-weight: 700;
            }}
            #metaText {{
                color: rgba(255,255,255,0.64);
                font-size: {meta_px}px;
            }}
            #freqSlider::groove:horizontal {{
                height: 8px;
                border-radius: 4px;
                background: rgba(0,0,0,0.24);
                border: 1px solid rgba(255,255,255,0.10);
            }}
            #freqSlider::sub-page:horizontal {{
                border-radius: 4px;
                background: rgba(232,225,169,0.60);
            }}
            #freqSlider::add-page:horizontal {{
                border-radius: 4px;
                background: rgba(255,255,255,0.12);
            }}
            #freqSlider::handle:horizontal {{
                width: 16px;
                margin: -5px 0;
                border-radius: 8px;
                background: #e8e1a9;
                border: 1px solid rgba(20,22,26,0.70);
            }}
            #miniBtn {{
                color: rgba(255,255,255,0.82);
                background: rgba(0,0,0,0.16);
                border: 1px solid rgba(255,255,255,0.14);
                border-radius: 8px;
                padding: {mini_v}px {mini_h}px;
            }}
            #miniBtn:hover {{
                background: rgba(255,255,255,0.10);
                border: 1px solid rgba(255,255,255,0.24);
            }}
            #secondaryBtn {{
                color: rgba(255,255,255,0.82);
                background: rgba(0,0,0,0.14);
                border: 1px solid rgba(255,255,255,0.16);
                border-radius: 10px;
                padding: {btn_v}px {btn_h}px;
            }}
            #secondaryBtn:hover {{
                background: rgba(255,255,255,0.10);
                border: 1px solid rgba(255,255,255,0.26);
            }}
            #primaryBtn {{
                color: #e8e1a9;
                background: qlineargradient(
                    x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgba(54,61,69,0.95),
                    stop:1 rgba(33,38,44,0.95)
                );
                border: 1px solid rgba(232,225,169,0.34);
                border-radius: 10px;
                padding: {btn_v}px {btn_h}px;
            }}
            #primaryBtn:hover {{
                background: qlineargradient(
                    x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgba(66,74,83,0.96),
                    stop:1 rgba(40,46,53,0.96)
                );
                border: 1px solid rgba(232,225,169,0.56);
            }}
            #primaryBtn:disabled {{
                color: rgba(232,225,169,0.45);
                background: rgba(45,50,55,0.50);
                border: 1px solid rgba(232,225,169,0.18);
            }}
            #txTitle {{
                color: rgba(255,255,255,0.86);
                font-size: {tx_title_px}px;
                font-weight: 700;
                letter-spacing: 1px;
            }}
            #txHint {{
                color: rgba(255,255,255,0.62);
                font-size: {tx_hint_px}px;
                font-weight: 500;
            }}
            #txBadge {{
                color: #e8e1a9;
                font-size: {tx_badge_px}px;
                font-weight: 700;
                border: 1px solid rgba(232,225,169,0.30);
                border-radius: 10px;
                background: rgba(0,0,0,0.18);
                padding: 2px 8px;
            }}
            #sendBtn {{
                color: #e8e1a9;
                font-size: {send_px}px;
                font-weight: 800;
                letter-spacing: 2px;
                background: qlineargradient(
                    x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgba(44,50,57,0.95),
                    stop:1 rgba(26,30,35,0.95)
                );
                border: 1px solid rgba(232,225,169,0.32);
                border-radius: 12px;
                padding: {send_pad}px;
            }}
            #sendBtn:hover {{
                background: qlineargradient(
                    x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgba(58,66,74,0.96),
                    stop:1 rgba(34,39,45,0.96)
                );
                border: 1px solid rgba(232,225,169,0.55);
            }}
            #sendBtn:pressed {{
                background: rgba(22,26,30,0.96);
                border: 1px solid rgba(232,225,169,0.68);
                padding-top: {max(6, send_pad - 1)}px;
                padding-bottom: {send_pad + 1}px;
            }}
            #sendBtn:disabled {{
                color: rgba(232,225,169,0.45);
                background: rgba(45,50,55,0.55);
                border: 1px solid rgba(232,225,169,0.16);
            }}
        """)

    def _apply_decoder_panel_style(self, scale=1.0):
        scale = float(scale)
        title_px = max(10, int(round(13 * scale)))
        result_px = max(18, int(round(30 * scale)))
        block_px = max(12, int(round(18 * scale)))
        raw_px = max(10, int(round(12 * scale)))
        self.decoder_panel.setStyleSheet(f"""
            #decoderPanel {{
                background: #1b1f24;
                border: 1px solid rgba(255,255,255,0.08);
                border-radius: 12px;
            }}
            #decoderTitle {{
                color: rgba(255,255,255,0.78);
                font-size: {title_px}px;
                font-weight: 600;
            }}
            #decodeResult {{
                color: #e8e1a9;
                font-size: {result_px}px;
                font-weight: 700;
                letter-spacing: 2px;
                border: 1px solid rgba(255,255,255,0.08);
                border-radius: 10px;
                background: rgba(0,0,0,0.18);
                padding: 4px 8px;
            }}
            #decisionStrip {{
                background: rgba(0,0,0,0.18);
                border: 1px solid rgba(255,255,255,0.08);
                border-radius: 10px;
            }}
            #decisionBlock {{
                color: rgba(255,255,255,0.78);
                font-size: {block_px}px;
                font-weight: 700;
                border-radius: 8px;
                background: rgba(255,255,255,0.06);
            }}
            #decisionBlock[active="true"] {{
                color: #1b1f24;
                background: #e8e1a9;
            }}
            #rawMorse {{
                color: rgba(255,255,255,0.60);
                font-size: {raw_px}px;
                background: rgba(0,0,0,0.18);
                border: 1px solid rgba(255,255,255,0.08);
                border-radius: 10px;
                padding: 8px;
            }}
        """)


    def _build_right_panel(self):


        right = QFrame()
        right.setObjectName("rightPanel")
        right.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)

        v = QVBoxLayout(right)
        v.setContentsMargins(12, 12, 12, 12)
        v.setSpacing(12)


        card_status = QFrame()
        card_status.setObjectName("card")
        vs = QVBoxLayout(card_status)
        vs.setContentsMargins(12, 12, 12, 12)
        vs.setSpacing(6)

        status_caption = QLabel(self.tr("站点状态"))
        status_caption.setObjectName("cardCaption")
        status_caption.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)


        self.label_number_clients.setObjectName("metaText")
        self.label_my_call.setObjectName("titleText")

        self.label_conn_state = QLabel(self.tr("状态：未连接"))
        self.label_conn_state.setObjectName("metaText")
        self.label_conn_state.setAlignment(Qt.AlignHCenter)

        vs.addWidget(status_caption)
        vs.addWidget(self.label_number_clients)
        vs.addWidget(self.label_my_call)
        vs.addWidget(self.label_conn_state)

        v.addWidget(card_status)


        card_freq = QFrame()
        card_freq.setObjectName("card")
        vf = QVBoxLayout(card_freq)
        vf.setContentsMargins(12, 12, 12, 12)
        vf.setSpacing(8)

        freq_caption = QLabel(self.tr("频率控制"))
        freq_caption.setObjectName("cardCaption")
        freq_caption.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)

        self.label_frequency.setObjectName("titleText")
        self.slider_frequency.setObjectName("freqSlider")


        row_step = QHBoxLayout()
        row_step.setSpacing(8)

        btn_minus = TransparentPushButton(" - ")
        btn_minus.setObjectName("miniBtn")
        btn_minus.clicked.connect(lambda: self.slider_frequency.setValue(self.slider_frequency.value() - 1))

        btn_plus = TransparentPushButton(" + ")
        btn_plus.setObjectName("miniBtn")
        btn_plus.clicked.connect(lambda: self.slider_frequency.setValue(self.slider_frequency.value() + 1))

        row_step.addWidget(btn_minus)
        row_step.addWidget(btn_plus)
        row_step.addStretch(1)

        vf.addWidget(freq_caption)
        vf.addWidget(self.label_frequency)
        vf.addWidget(self.slider_frequency)
        vf.addLayout(row_step)

        v.addWidget(card_freq)


        card_actions = QFrame()
        card_actions.setObjectName("card")
        va = QVBoxLayout(card_actions)
        va.setContentsMargins(12, 12, 12, 12)
        va.setSpacing(10)

        actions_caption = QLabel(self.tr("通道操作"))
        actions_caption.setObjectName("cardCaption")
        actions_caption.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)

        row_btn = QHBoxLayout()
        row_btn.setSpacing(10)

        self.btn_clean_screen.setObjectName("secondaryBtn")
        self.btn_clean_screen.setText(self.tr("清屏"))
        self.btn_clean_screen.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.btn_connect_and_disconnect.setObjectName("primaryBtn")
        self.btn_connect_and_disconnect.setMinimumWidth(120)
        self.btn_connect_and_disconnect.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.label_connect_spinner = QLabel("")
        self.label_connect_spinner.setObjectName("metaText")
        self.label_connect_spinner.setAlignment(Qt.AlignHCenter | Qt.AlignVCenter)
        self.label_connect_spinner.setFixedWidth(18)

        row_btn.addWidget(self.btn_clean_screen, 0)
        row_btn.addWidget(self.btn_connect_and_disconnect, 1)
        row_btn.addWidget(self.label_connect_spinner)

        va.addWidget(actions_caption)
        va.addLayout(row_btn)
        v.addWidget(card_actions)


        card_tx = QFrame()
        card_tx.setObjectName("cardStrong")
        vt = QVBoxLayout(card_tx)
        vt.setContentsMargins(12, 12, 12, 12)
        vt.setSpacing(8)

        tx_head = QHBoxLayout()
        tx_head.setSpacing(8)

        tx_title = QLabel(self.tr("CW 发报"))
        tx_title.setObjectName("txTitle")
        tx_title.setAlignment(Qt.AlignVCenter | Qt.AlignLeft)

        self.label_tx_badge = QLabel("TX")
        self.label_tx_badge.setObjectName("txBadge")
        self.label_tx_badge.setAlignment(Qt.AlignCenter)

        tx_head.addWidget(tx_title)
        tx_head.addStretch(1)
        tx_head.addWidget(self.label_tx_badge)

        self.label_tx_hint = QLabel(self.tr("按住按钮发报 · 与可视化区域同步反馈"))
        self.label_tx_hint.setObjectName("txHint")
        self.label_tx_hint.setAlignment(Qt.AlignHCenter)

        self.btn_send_message.setObjectName("sendBtn")
        self.btn_send_message.setMinimumHeight(120)

        vt.addLayout(tx_head)
        vt.addWidget(self.label_tx_hint)
        vt.addWidget(self.btn_send_message)

        v.addWidget(card_tx)

        v.addStretch(1)
        return right


    def _build_decoder_panel(self):


        panel = QFrame()
        panel.setObjectName("decoderPanel")
        panel.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)

        v = QVBoxLayout(panel)
        v.setContentsMargins(14, 12, 14, 12)
        v.setSpacing(10)


        self.lbl_decode_title = QLabel(self.tr("解码结果"))
        self.lbl_decode_title.setObjectName("decoderTitle")

        self.lbl_decode_result = QLineEdit("")
        self.lbl_decode_result.setObjectName("decodeResult")
        self.lbl_decode_result.setAlignment(Qt.AlignHCenter | Qt.AlignVCenter)
        self.lbl_decode_result.setReadOnly(True)
        self.lbl_decode_result.setMinimumHeight(74)
        self.lbl_decode_result.setMaximumHeight(74)

        v.addWidget(self.lbl_decode_title)
        v.addWidget(self.lbl_decode_result)


        self.lbl_decision_title = QLabel(self.tr("符号判决"))
        self.lbl_decision_title.setObjectName("decoderTitle")
        v.addWidget(self.lbl_decision_title)

        strip = QFrame()
        strip.setObjectName("decisionStrip")
        strip_layout = QHBoxLayout(strip)
        strip_layout.setContentsMargins(10, 8, 10, 8)
        strip_layout.setSpacing(6)


        self._decision_block_count = 12
        self._decision_blocks = []
        for _ in range(self._decision_block_count):
            b = QLabel("")
            b.setObjectName("decisionBlock")
            b.setAlignment(Qt.AlignCenter)
            b.setFixedSize(42, 42)
            self._decision_blocks.append(b)
            strip_layout.addWidget(b)

        strip_layout.addStretch(1)
        v.addWidget(strip)


        self.lbl_raw_title = QLabel(self.tr("原始点划"))
        self.lbl_raw_title.setObjectName("decoderTitle")

        self.lbl_raw_morse = QPlainTextEdit("")
        self.lbl_raw_morse.setObjectName("rawMorse")
        self.lbl_raw_morse.setReadOnly(True)
        self.lbl_raw_morse.setLineWrapMode(QPlainTextEdit.WidgetWidth)
        self.lbl_raw_morse.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.lbl_raw_morse.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.lbl_raw_morse.setMinimumHeight(92)
        self.lbl_raw_morse.setMaximumHeight(92)

        v.addWidget(self.lbl_raw_title)
        v.addWidget(self.lbl_raw_morse)

        return panel


    def _set_decision_blocks(self, text: str, active_index: int = -1):


        chars = [c for c in text if c.strip() != ""]
        tail = chars[-self._decision_block_count:] if chars else []

        tail = ([""] * (self._decision_block_count - len(tail))) + tail

        if tail == self._last_decision_tail and active_index == self._last_decision_active_index:
            return

        for i, b in enumerate(self._decision_blocks):
            if i >= len(self._last_decision_tail) or tail[i] != self._last_decision_tail[i]:
                b.setText(tail[i])

        changed_indexes = []
        if (
            0 <= self._last_decision_active_index < self._decision_block_count
            and self._last_decision_active_index != active_index
        ):
            prev = self._decision_blocks[self._last_decision_active_index]
            prev.setProperty("active", "false")
            changed_indexes.append(self._last_decision_active_index)

        if 0 <= active_index < self._decision_block_count:
            cur = self._decision_blocks[active_index]
            cur.setProperty("active", "true")
            changed_indexes.append(active_index)

        for idx in set(changed_indexes):
            b = self._decision_blocks[idx]
            b.style().unpolish(b)
            b.style().polish(b)
            b.update()

        self._last_decision_tail = tail
        self._last_decision_active_index = active_index


    def _refresh_decoder_panel(self):

        recv_text = (self.edit_received_translation.text() or "").strip()
        send_text = (self.edit_send_translation.text() or "").strip()


        result = recv_text if recv_text else send_text
        decode_text = result.upper()[-64:] if result else ""
        if decode_text != self._last_decode_text:
            self.lbl_decode_result.setText(decode_text)
            self._last_decode_text = decode_text


        result_for_decision = result[-64:] if result else ""
        if result_for_decision:


            self._set_decision_blocks(result_for_decision.upper(), active_index=self._decision_block_count - 1)
        else:
            self._set_decision_blocks("", active_index=-1)


        raw_recv = (self.edit_morse_received.text() or "")
        raw_send = (self.edit_morse_code.text() or "")
        raw = raw_recv if raw_recv else raw_send


        raw_tail = raw[-600:] if len(raw) > 600 else raw
        if raw_tail != self._last_raw_tail:
            self.lbl_raw_morse.setPlainText(raw_tail)
            self._last_raw_tail = raw_tail
            sb = self.lbl_raw_morse.verticalScrollBar()
            sb.setValue(sb.maximum())


    def _topic_for_channel(self, channel):
        return f"{self._topic_prefix}/{int(channel)}"

    def _build_subscribe_topics(self, center_channel):
        try:
            center = int(center_channel)
        except (TypeError, ValueError):
            center = int(self.channel_name)

        min_channel = int(self.slider_frequency.minimum())
        max_channel = int(self.slider_frequency.maximum())
        lower = max(min_channel, center - int(self._side_channel_range))
        upper = min(max_channel, center + int(self._side_channel_range))
        return {self._topic_for_channel(ch) for ch in range(lower, upper + 1)}

    def _sync_topic_targets(self, apply_now=False):
        publish_topic = self._topic_for_channel(self.channel_name)
        subscribe_topics = self._build_subscribe_topics(self.channel_name)
        self._desired_sub_topics = set(subscribe_topics)

        if not self.client:
            return

        self.client.set_publish_topic(publish_topic)

        # Disconnected/connecting phase: update desired subscriptions only.
        if not self.is_connected:
            self.client.replace_subscriptions(subscribe_topics)
            return

        if apply_now:
            self._topic_switch_timer.stop()
            self._apply_topic_window_update()
            return

        self._topic_switch_timer.stop()
        self._topic_switch_timer.start()

    def _apply_topic_window_update(self):
        if not self.client or not self.is_connected:
            return
        self.client.set_publish_topic(self._topic_for_channel(self.channel_name))
        self.client.replace_subscriptions(self._desired_sub_topics)

    def update_frequency_label(self):

        frequency = self.slider_frequency.value()
        self.label_frequency.setText(self.tr("当前中心频率: {0} kHz").format(frequency))


        self.channel_name = frequency
        self.config_manager.set_server_channel_name(frequency)
        self._sync_topic_targets(apply_now=False)

    def initSetting(self):

        self.database_tool = self.create_database_tool()


        self.is_translation_visible()


        self.set_font_size()


        self.saved_key = self.config_manager.get_keyborad_key().split(',')


        self.set_my_call()


        self.set_visualizer_visibility()


        update_checker = VersionChecker(self.config_manager.get_current_version())


        update_checker.check_update()


        self.current_message_play_time = None
        self.current_message_play_time_invertal = None


        self.receive_message_processor = MultiChannelProcessor(
            self.buzz,
            self.morsecode_visualizer,
            self.signal_light,
        )
        self._sync_topic_targets(apply_now=False)

    def _tick_connecting_indicator(self):
        if not self.is_connecting:
            return
        frame = self._connect_spinner_frames[self._connect_spinner_index % len(self._connect_spinner_frames)]
        self._connect_spinner_index += 1
        self.btn_connect_and_disconnect.setText(self.tr("连接中"))
        if hasattr(self, "label_connect_spinner"):
            self.label_connect_spinner.setText(frame)

    def _set_connecting_state(self, connecting: bool):
        if connecting:
            self.is_connecting = True
            self._connect_spinner_index = 0
            self.btn_connect_and_disconnect.setEnabled(False)
            self.label_conn_state.setText(self.tr("状态：连接中"))
            self._tick_connecting_indicator()
            if not self._connect_anim_timer.isActive():
                self._connect_anim_timer.start()
            self._connect_timeout_timer.start()
            return

        self.is_connecting = False
        self._connect_anim_timer.stop()
        self._connect_timeout_timer.stop()
        self.btn_connect_and_disconnect.setEnabled(True)
        if hasattr(self, "label_connect_spinner"):
            self.label_connect_spinner.setText("")

    def _is_empty_credential(self, value):
        text = str(value).strip()
        return text == "" or text.lower() == "none"

    def _handle_connect_timeout(self):
        if not self.is_connecting:
            return
        self._set_connecting_state(False)
        self.is_connected = False
        self._topic_switch_timer.stop()
        self._disconnect_requested = True
        self.label_conn_state.setText(self.tr("状态：连接超时"))
        self.btn_connect_and_disconnect.setText(self.tr("连接服务器"))
        if self.client:
            try:
                self.client.close()
            except Exception:
                pass
        QMessageBox.warning(self, self.tr("错误"), self.tr("连接超时，请检查网络或服务器配置"))

    def connectService(self):
        """连接或断开 MQTT 服务。"""

        try:
            if self.is_connecting:
                self.label_conn_state.setText(self.tr("状态：连接中"))
                return
            if self.is_connected:

                self._disconnect_requested = True
                self._topic_switch_timer.stop()
                if self.client:
                    self.client.close()
                self._pending_send_msgs.clear()
                self._send_flush_timer.stop()
                self.btn_connect_and_disconnect.setText(self.tr("连接服务器"))
                self.label_conn_state.setText(self.tr("状态：未连接"))
                self.signal_light.set_state(0)
            else:
                if self.check_myCall():

                    self._disconnect_requested = False
                    self._last_connect_error = ""
                    self._set_connecting_state(True)
                    if not self.initChat():
                        self._set_connecting_state(False)
                        self.label_conn_state.setText(self.tr("状态：连接失败"))
                        self.btn_connect_and_disconnect.setText(self.tr("连接服务器"))
                        detail = self._last_connect_error or self.tr("连接初始化失败，请检查服务器设置")
                        QMessageBox.warning(self, self.tr("错误"), str(detail))
                else:
                    QMessageBox.information(self, self.tr("提示"), self.tr("在线通联前请先设置呼号（无限制）"))

        except Exception as e:
            self._set_connecting_state(False)
            QMessageBox.information(self, self.tr("错误"), f"{self.tr('错误信息：')} {str(e)}")
    def initChat(self):
        """根据当前配置初始化 MQTT 客户端。"""

        host = str(self.config_manager.get_server_host() or "").strip()
        port = int(self.config_manager.get_server_active_port())
        scheme = str(self.config_manager.get_server_scheme() or "mqtt").strip().lower()
        use_tls = scheme == "mqtts"
        tls_ca_certs = str(self.config_manager.get_server_tls_ca_certs() or "").strip()
        tls_use_cert = bool(self.config_manager.get_server_tls_use_cert())
        tls_insecure = use_tls and (not tls_use_cert)
        auth_profile = PlainConfigCredentialStore(self.config_manager).get_auth_profile()

        if auth_profile.auth_type == "jwt":
            self._last_connect_error = self.tr("JWT 认证暂未启用，请先使用呼号和密码登录")
            return False
        if auth_profile.auth_type != "plain":
            self._last_connect_error = self.tr("不支持的认证类型")
            return False

        user = auth_profile.username
        pwd = auth_profile.password
        if not host:
            self._last_connect_error = self.tr("服务器主机不能为空")
            return False
        if self._is_empty_credential(user) or self._is_empty_credential(pwd):
            self._last_connect_error = self.tr("在线通联前请先设置呼号和密码")
            return False

        self._tx_clock_origin_ms = int(time.monotonic() * 1000)
        self._tx_event_seq = 0
        self._tx_session_id = f"{str(user).upper()}-{int(time.time() * 1000)}"
        self._tx_last_event_time_ms = -1
        publish_topic = self._topic_for_channel(self.channel_name)
        subscribe_topics = self._build_subscribe_topics(self.channel_name)
        self._desired_sub_topics = set(subscribe_topics)

        self.client = MQTTClient(
            broker=host,
            port=port,
            username=str(user),
            password=str(pwd),
            client_id=self.my_call + str(time.time()),
            use_tls=use_tls,
            tls_ca_certs=(tls_ca_certs if use_tls and tls_use_cert else ""),
            tls_insecure=(tls_insecure if use_tls else False),
        )

        self.client.on_message_received = self.on_message_received
        self.client.on_connection_status_change = self.on_connection_status_change
        ok = self.client.connect(publish_topic, subscribe_topics=subscribe_topics)
        if not ok:
            self._last_connect_error = getattr(self.client, "last_error", "") or self.tr("无法启动连接，请检查服务器地址/端口")
        return ok

    def on_message_received(self, message):

        self.mysignal.process_received_signal.emit(message)
    def _first_non_empty(self, data, keys, default=None):
        if not isinstance(data, dict):
            return default
        for key in keys:
            if key in data:
                value = data.get(key)
                if value is not None and str(value).strip() != "":
                    return value
        return default

    def _safe_int(self, value, default):
        try:
            return int(float(value))
        except (TypeError, ValueError):
            return default

    def _extract_key_event_payload(self, data):
        if not isinstance(data, dict):
            return None

        required_keys = (
            "protocol",
            "version",
            "session_id",
            "seq",
            "myCall",
            "myChannel",
            "event",
            "event_time_ms",
        )
        if any(k not in data for k in required_keys):
            return None

        protocol = str(data.get("protocol", "")).strip()
        if protocol != self._protocol_name:
            return None

        version = self._safe_int(data.get("version"), -1)
        if version != self._protocol_version:
            return None

        event = str(data.get("event", "")).strip().lower()
        if event not in ("down", "up"):
            return None

        payload = {
            "protocol": protocol,
            "version": version,
            "session_id": str(data.get("session_id", "")).strip(),
            "seq": self._safe_int(data.get("seq"), -1),
            "myCall": str(data.get("myCall", "")).strip(),
            "myChannel": self._safe_int(data.get("myChannel"), self.channel_name),
            "event": event,
            "event_time_ms": self._safe_int(data.get("event_time_ms"), -1),
            "keyer_mode": str(data.get("keyer_mode", "straight")).strip().lower(),
            "dot_ms_hint": self._safe_int(data.get("dot_ms_hint"), self.dot_duration),
            "dash_ms_hint": self._safe_int(data.get("dash_ms_hint"), self.dash_duration),
            "letter_gap_ms_hint": self._safe_int(data.get("letter_gap_ms_hint"), self.letter_interval_duration),
            "word_gap_ms_hint": self._safe_int(data.get("word_gap_ms_hint"), self.word_interval_duration),
        }
        if payload["seq"] < 0 or payload["event_time_ms"] < 0:
            return None
        if not payload["session_id"] or not payload["myCall"]:
            return None

        payload["dot_ms_hint"] = max(20, payload["dot_ms_hint"])
        payload["dash_ms_hint"] = max(payload["dot_ms_hint"] * 2, payload["dash_ms_hint"])
        payload["letter_gap_ms_hint"] = max(payload["dot_ms_hint"] * 2, payload["letter_gap_ms_hint"])
        payload["word_gap_ms_hint"] = max(payload["letter_gap_ms_hint"] + payload["dot_ms_hint"], payload["word_gap_ms_hint"])
        return payload

    def _rx_state_key(self, payload):
        return (payload["myCall"].upper(), payload["session_id"], int(payload["myChannel"]))

    def _drop_stale_session_states(self, payload):
        sender = str(payload.get("myCall", "")).upper()
        channel = int(payload.get("myChannel", self.channel_name))
        session_id = str(payload.get("session_id", ""))
        stale_keys = [
            key for key in list(self._rx_event_states.keys())
            if key[0] == sender and key[2] == channel and key[1] != session_id
        ]
        if not stale_keys:
            return
        if self._rx_active_same_key in stale_keys:
            self._cancel_rx_finalize_timers()
            self._rx_active_same_key = None
        for key in stale_keys:
            self._rx_event_states.pop(key, None)

    def _new_rx_state(self, payload):
        return {
            "sender_call": payload["myCall"],
            "session_id": payload["session_id"],
            "channel": int(payload["myChannel"]),
            "last_seq": -1,
            "is_down": False,
            "down_time_ms": None,
            "last_up_time_ms": None,
            "symbol_buffer": "",
            "dot_ms_hint": payload["dot_ms_hint"],
            "dash_ms_hint": payload["dash_ms_hint"],
            "letter_gap_ms_hint": payload["letter_gap_ms_hint"],
            "word_gap_ms_hint": payload["word_gap_ms_hint"],
            "last_rx_wallclock_ms": int(time.monotonic() * 1000),
            "max_hold_timeout_ms": max(1200, payload["dash_ms_hint"] * 4),
            "last_event_time_ms": -1,
            "last_event_type": "",
        }

    def _cancel_rx_finalize_timers(self):
        self._rx_letter_timer.stop()
        self._rx_word_timer.stop()
        self._rx_force_up_timer.stop()
        self._rx_word_tail_delay_ms = 0

    def _arm_rx_finalize_timers(self, state_key, state):
        self._rx_active_same_key = state_key
        letter_gap = max(50, int(state["letter_gap_ms_hint"]))
        word_gap = max(letter_gap + 50, int(state["word_gap_ms_hint"]))
        self._rx_word_tail_delay_ms = max(50, word_gap - letter_gap)
        self._rx_word_timer.stop()
        self._rx_letter_timer.start(letter_gap)

    def _arm_rx_force_up_timer(self, state_key, state):
        self._rx_active_same_key = state_key
        self._rx_force_up_timer.start(max(200, int(state["max_hold_timeout_ms"])))

    def _append_received_morse(self, text):
        if not text:
            return
        self.edit_morse_received.insert(text)

    def _append_received_translation(self, text):
        if not text:
            return
        self.edit_received_translation.insert(text)

    def _duration_to_symbol(self, duration_ms, state):
        duration_ms = max(1, int(duration_ms))
        dot_ms = max(20, int(state.get("dot_ms_hint", self.dot_duration)))
        dash_ms = max(dot_ms * 2, int(state.get("dash_ms_hint", self.dash_duration)))
        threshold = int((dot_ms + dash_ms) / 2)
        return "." if duration_ms < threshold else "-"

    def _flush_receive_symbol_buffer(self, state_key, append_word_space=False):
        state = self._rx_event_states.get(state_key)
        if not state:
            return

        symbol_buffer = str(state.get("symbol_buffer", ""))
        if not symbol_buffer and not append_word_space:
            return

        if symbol_buffer:
            translated = self.translator.letter_to_morse(symbol_buffer)
            self._append_received_translation(translated)
            state["symbol_buffer"] = ""
            self.morse_code_received = ""

        if append_word_space:
            self._append_received_morse("//")
            self._append_received_translation(" ")
        elif symbol_buffer:
            self._append_received_morse("/")

    def _apply_receive_gap(self, state_key, state, gap_ms):
        if gap_ms is None:
            return

        letter_gap = int(state.get("letter_gap_ms_hint", self.letter_interval_duration))
        word_gap = int(state.get("word_gap_ms_hint", self.word_interval_duration))
        if gap_ms >= word_gap:
            self._flush_receive_symbol_buffer(state_key, append_word_space=True)
        elif gap_ms >= letter_gap:
            self._flush_receive_symbol_buffer(state_key, append_word_space=False)

    def _refresh_tx_ban_state(self):
        self.label_morse_sent.setText(self.SENT_CODE_BANNED)
        self.status_transmit_banned = True
        self.transmit_banned_timer.start(max(100, int(self.rx_tx_lock_tail_ms)))

    def _consume_received_press(
        self,
        state_key,
        state,
        press_ms,
        gap_before_ms,
        same_channel,
        my_channel,
        arm_finalize_timers=True,
    ):
        press_ms = max(1, int(press_ms))
        gap_before_ms = max(0, int(gap_before_ms))
        symbol = self._duration_to_symbol(press_ms, state)

        if same_channel:
            state["symbol_buffer"] = str(state.get("symbol_buffer", "")) + symbol
            self._append_received_morse(symbol)
            self.start_record_receive(symbol)
            self.receive_message_processor.receive_message(
                5,
                [press_ms, gap_before_ms],
                play_audio=bool(self.receive_buzz_status),
            )
            if arm_finalize_timers:
                self._arm_rx_finalize_timers(state_key, state)
            return

        result = self.process_side_channel(self.channel_name, my_channel, range_limit=self._side_channel_range)
        if result["is_within_range"]:
            self.receive_message_processor.receive_message(
                result["channel_id"],
                [press_ms, gap_before_ms],
                play_audio=False,
            )

    def _finalize_receive_letter_from_timer(self):
        if self._rx_active_same_key is None:
            return
        state = self._rx_event_states.get(self._rx_active_same_key)
        if not state:
            return
        has_symbol = bool(str(state.get("symbol_buffer", "")))
        self._flush_receive_symbol_buffer(self._rx_active_same_key, append_word_space=False)
        if has_symbol:
            self._rx_word_timer.start(max(50, int(self._rx_word_tail_delay_ms)))

    def _finalize_receive_word_from_timer(self):
        if self._rx_active_same_key is None:
            return
        self._flush_receive_symbol_buffer(self._rx_active_same_key, append_word_space=True)
        self._rx_active_same_key = None
        self._rx_word_tail_delay_ms = 0

    def _force_finalize_stuck_keydown(self):
        state_key = self._rx_active_same_key
        if state_key is None:
            return
        state = self._rx_event_states.get(state_key)
        if not state or not state.get("is_down"):
            return

        down_time_ms = int(state.get("down_time_ms") or 0)
        prev_up = state.get("last_up_time_ms")
        press_ms = int(state.get("max_hold_timeout_ms", max(self.dot_duration, self.dash_duration)))
        gap_before_ms = max(0, down_time_ms - int(prev_up)) if prev_up is not None else 0
        same_channel = str(state.get("channel")) == str(self.channel_name)
        my_channel = int(state.get("channel", self.channel_name))
        state["is_down"] = False
        state["down_time_ms"] = None
        state["last_up_time_ms"] = down_time_ms + press_ms
        self._consume_received_press(
            state_key=state_key,
            state=state,
            press_ms=press_ms,
            gap_before_ms=gap_before_ms,
            same_channel=same_channel,
            my_channel=my_channel,
            arm_finalize_timers=same_channel,
        )

    def process_messages(self, message):
        try:
            data = json.loads(message)
        except Exception:
            return

        payload = self._extract_key_event_payload(data)
        if not payload:
            return

        sender_call = payload["myCall"]
        if sender_call.lower() == str(self.my_call).strip().lower():
            return

        state_key = self._rx_state_key(payload)
        state = self._rx_event_states.get(state_key)
        if state is None:
            self._drop_stale_session_states(payload)
            state = self._new_rx_state(payload)
            self._rx_event_states[state_key] = state

        seq = int(payload["seq"])
        if seq <= int(state.get("last_seq", -1)):
            return

        event_time_ms = int(payload["event_time_ms"])
        event_type = payload["event"]
        last_event_type = str(state.get("last_event_type", ""))
        last_event_time = int(state.get("last_event_time_ms", -1))
        if (
            event_type == last_event_type
            and last_event_time >= 0
            and 0 <= (event_time_ms - last_event_time) <= self._rx_debounce_window_ms
        ):
            return

        state["last_seq"] = seq
        state["last_event_type"] = event_type
        state["last_event_time_ms"] = event_time_ms
        state["last_rx_wallclock_ms"] = int(time.monotonic() * 1000)

        state["dot_ms_hint"] = payload["dot_ms_hint"]
        state["dash_ms_hint"] = payload["dash_ms_hint"]
        state["letter_gap_ms_hint"] = payload["letter_gap_ms_hint"]
        state["word_gap_ms_hint"] = payload["word_gap_ms_hint"]
        state["max_hold_timeout_ms"] = max(1200, payload["dash_ms_hint"] * 4)

        my_channel = int(payload["myChannel"])
        same_channel = str(my_channel) == str(self.channel_name)
        if same_channel:
            self.call_of_sender = sender_call
            self.label_morse_received.setText(
                f'{self.RECEIVED_CODE} {self.call_of_sender} {self.tr("正在发射")}'
            )
            self._refresh_tx_ban_state()

        if event_type == "down":
            if same_channel:
                self._cancel_rx_finalize_timers()


            if state.get("is_down") and state.get("down_time_ms") is not None:
                prev_down_ms = int(state["down_time_ms"])
                prev_up = state.get("last_up_time_ms")
                gap_before_ms = max(0, prev_down_ms - int(prev_up)) if prev_up is not None else 0
                max_hold_ms = int(state.get("max_hold_timeout_ms", max(self.dot_duration, self.dash_duration)))
                if event_time_ms > prev_down_ms:
                    press_ms = min(max_hold_ms, max(1, event_time_ms - prev_down_ms))
                else:
                    press_ms = max(1, min(max_hold_ms, int(state.get("dash_ms_hint", self.dash_duration))))
                state["is_down"] = False
                state["down_time_ms"] = None
                state["last_up_time_ms"] = prev_down_ms + press_ms
                self._consume_received_press(
                    state_key=state_key,
                    state=state,
                    press_ms=press_ms,
                    gap_before_ms=gap_before_ms,
                    same_channel=same_channel,
                    my_channel=my_channel,
                    arm_finalize_timers=False,
                )

            if same_channel:
                gap_ms = None
                if state.get("last_up_time_ms") is not None:
                    gap_ms = max(0, event_time_ms - int(state["last_up_time_ms"]))
                self._apply_receive_gap(state_key, state, gap_ms)

            state["is_down"] = True
            state["down_time_ms"] = event_time_ms
            if same_channel:
                self._arm_rx_force_up_timer(state_key, state)
            return


        if not state.get("is_down") or state.get("down_time_ms") is None:
            return

        down_time_ms = int(state["down_time_ms"])
        press_ms = max(1, event_time_ms - down_time_ms)
        prev_up = state.get("last_up_time_ms")
        gap_before_ms = max(0, down_time_ms - int(prev_up)) if prev_up is not None else 0

        state["is_down"] = False
        state["down_time_ms"] = None
        state["last_up_time_ms"] = event_time_ms
        if same_channel:
            self._rx_force_up_timer.stop()
        self._consume_received_press(
            state_key=state_key,
            state=state,
            press_ms=press_ms,
            gap_before_ms=gap_before_ms,
            same_channel=same_channel,
            my_channel=my_channel,
            arm_finalize_timers=same_channel,
        )

    def process_side_channel(self, current_channel, side_channel, range_limit=5):

        try:
            current_channel = int(current_channel)
            side_channel = int(side_channel)
            range_limit = int(range_limit)
        except (TypeError, ValueError):
            return {
                "side_channel": side_channel,
                "is_within_range": False,
                "channel_id": None
            }


        min_channel = current_channel - range_limit
        max_channel = current_channel + range_limit


        if min_channel <= side_channel <= max_channel:

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

    def on_connection_status_change(self, is_connected, error_message=None):

        was_connecting = self.is_connecting
        self._set_connecting_state(False)

        if is_connected:



            self.is_connected = is_connected
            self.btn_connect_and_disconnect.setText(self.tr("断开连接"))
            self.signal_light.set_state(2)
            self.label_conn_state.setText(self.tr("状态：已连接"))
            self._sync_topic_targets(apply_now=True)
        else:

            self.is_connected = is_connected
            self._topic_switch_timer.stop()
            self._pending_send_msgs.clear()
            self._send_flush_timer.stop()
            self._rx_event_states.clear()
            self._rx_active_same_key = None
            self._cancel_rx_finalize_timers()
            self.label_conn_state.setText(self.tr("状态：未连接"))

            self.btn_connect_and_disconnect.setText(self.tr("连接服务器"))
            self.signal_light.set_state(0)
            if was_connecting and not self._disconnect_requested:
                self.label_conn_state.setText(self.tr("状态：连接失败"))
                detail = error_message or getattr(self.client, "last_error", "") or self.tr("连接失败，请检查服务器地址、账号密码或网络")
                self._last_connect_error = str(detail)
                QMessageBox.warning(self, self.tr("错误"), str(detail))
            self._disconnect_requested = False

    def _refresh_send_runtime(self):
        self.dot_duration = int(self.config_manager.get_dot_time())
        self.dash_duration = int(self.config_manager.get_dash_time())
        self.letter_interval_duration = int(self.config_manager.get_letter_interval_duration_time())
        self.word_interval_duration = int(self.config_manager.get_word_interval_duration_time())
        self.keyer_mode = str(self.config_manager.get_keyer_mode() or "straight").lower()
        self.rx_tx_lock_tail_ms = int(self.config_manager.get_rx_tx_lock_tail_ms())
        self.send_buzz_status = self.config_manager.get_send_buzz_status()
        self.receive_buzz_status = self.config_manager.get_receive_buzz_status()
        self.saved_key = self.config_manager.get_keyborad_key().split(',')
        if hasattr(self, "tx_runtime") and self.tx_runtime:
            self.tx_runtime.refresh_runtime(
                dot_duration=self.dot_duration,
                dash_duration=self.dash_duration,
                letter_interval_duration=self.letter_interval_duration,
                word_interval_duration=self.word_interval_duration,
                keyer_mode=self.keyer_mode,
                send_buzz_status=self.send_buzz_status,
                saved_key=self.saved_key,
            )

    def _to_keyer_mode(self, mode_text):
        return self.tx_runtime.to_keyer_mode(mode_text)

    def _is_straight_mode(self):
        return self.tx_runtime.is_straight_mode()

    def _tx_now_ms(self):
        now_ms = int(time.monotonic() * 1000)
        return max(0, now_ms - self._tx_clock_origin_ms)

    def _normalize_tx_event_time_ms(self, event_time_ms):
        current = int(max(0, event_time_ms))
        if current <= self._tx_last_event_time_ms:
            current = self._tx_last_event_time_ms + 1
        self._tx_last_event_time_ms = current
        return current

    def _parse_saved_keys(self):
        return self.tx_runtime.parse_saved_keys()

    def _prepare_manual_press(self, max_interval_seconds=10):
        self.tx_runtime.prepare_manual_press(max_interval_seconds=max_interval_seconds)

    def _stop_send_gap_timers(self):
        self.word_timer.stop()
        self.letter_timer.stop()

    def _tx_runtime_send_event(self, event_type, event_time_ms):
        self.send_key_event_to_server(event_type, event_time_ms)

    def _tx_runtime_on_manual_down(self):
        self.morsecode_visualizer.start_generating(5)
        self.signal_light.set_state(1)

    def _tx_runtime_on_manual_up_begin(self):
        self.morsecode_visualizer.stop_generating(5)
        self.signal_light.set_state(2)

    def _tx_runtime_on_manual_symbol(self, morse_code, duration_ms, gap_ms, manual_duration_ms):
        self.update_sent_label(morse_code, duration_ms, gap_ms)
        fps_ms = max(1, int(getattr(self.morsecode_visualizer, "fps_ms", 40) or 40))
        if manual_duration_ms < float(fps_ms):
            self.show_visualizer(
                morse_code,
                keydown_ms=max(0.5, manual_duration_ms),
                gap_ms=gap_ms,
            )
            self.signal_light.switch_to_red_for_duration(max(1, int(math.ceil(max(1.0, manual_duration_ms)))))

    def _tx_runtime_on_auto_symbol(self, event: AutoElementEvent):
        self.show_visualizer(event.symbol, event.keydown_ms, event.gap_ms)
        self.signal_light.switch_to_red_for_duration(event.keydown_ms)
        self.update_sent_label(event.symbol, event.keydown_ms, event.gap_ms)

    def _tx_runtime_on_auto_stopped(self):
        return

    def on_btn_send_message_pressed(self):

        if self.tx_runtime.press_manual(
            ready=True,
            allow_transmit=(not self.status_transmit_banned),
            max_interval_seconds=50,
        ):
            self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
            self.btn_send_message.setIcon(FIF.SEND_FILL)


    def on_btn_send_message_released(self):

        if self.tx_runtime.release_manual():
            self.setFocusPolicy(Qt.FocusPolicy.ClickFocus)
            self.btn_send_message.setIcon(FIF.SEND)

    def keyPressEvent(self, event):

        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.tx_runtime.handle_key_press(
            key=event.key(),
            is_auto_repeat=event.isAutoRepeat(),
            ready=True,
            allow_transmit=(not self.status_transmit_banned),
            max_interval_seconds=10,
        )

    def keyReleaseEvent(self, event):

        self.setFocusPolicy(Qt.FocusPolicy.ClickFocus)

        self.tx_runtime.handle_key_release(
            key=event.key(),
            is_auto_repeat=event.isAutoRepeat(),
        )

    def determine_morse_character(self, duration):

        return self.tx_runtime.determine_morse_character(duration)


    def update_sent_label(self, morse_code, play_time, play_interval):


        self.start_record_send(morse_code, play_time, play_interval)


        self._append_morse_out(morse_code)

    def send_key_event_to_server(self, event_type, event_time_ms):
        if event_type not in ("down", "up"):
            return

        if not self.is_connected:
            return

        normalized_time_ms = self._normalize_tx_event_time_ms(event_time_ms)
        self._tx_event_seq += 1
        json_data = {
            "protocol": self._protocol_name,
            "version": self._protocol_version,
            "session_id": self._tx_session_id,
            "seq": self._tx_event_seq,
            "myCall": self.my_call,
            "myChannel": int(self.channel_name),
            "event": event_type,
            "event_time_ms": normalized_time_ms,
            "keyer_mode": self.keyer_mode,
            "dot_ms_hint": int(self.dot_duration),
            "dash_ms_hint": int(self.dash_duration),
            "letter_gap_ms_hint": int(self.letter_interval_duration),
            "word_gap_ms_hint": int(self.word_interval_duration),
        }

        message = json.dumps(json_data, ensure_ascii=False, separators=(",", ":"))
        self._pending_send_msgs.append(message)
        if len(self._pending_send_msgs) > 2000:
            self._pending_send_msgs.popleft()
        if not self._send_flush_timer.isActive():
            self._send_flush_timer.start()

    def _flush_send_queue(self):
        if not self.is_connected or not hasattr(self, "client") or self.client is None:
            self._pending_send_msgs.clear()
            self._send_flush_timer.stop()
            return

        budget = 40
        while self._pending_send_msgs and budget > 0:
            msg = self._pending_send_msgs.popleft()
            self.client.send_message(msg)
            budget -= 1

        if not self._pending_send_msgs:
            self._send_flush_timer.stop()

    def start_letter_timer(self):

        self.letter_timer.start(self.letter_interval_duration)

    def start_word_timer(self):

        self.word_timer.start(self.word_interval_duration)

    def handle_letter_timeout(self):
        self._append_morse_out("/")


        self.current_message_to_record += "/"


        self.start_word_timer()


        extracted_mores_code = self.extract_cleaned_parts(self.morse_code)
        self.morse_code_translation_temp = self.translator.letter_to_morse(extracted_mores_code)
        self._append_send_translation_out(self.morse_code_translation_temp)

    def handle_word_timeout(self):
        self._append_morse_out("//")


        self.current_message_to_record += "//"


        self._append_send_translation_out(" ")

    def handle_transmit_banned_timeout(self):


        self.status_transmit_banned = False


        self.label_morse_sent.setText(self.SENT_CODE)


        self.label_morse_received.setText(f'{self.RECEIVED_CODE}')

    def handle_link_record_timeout(self):

        if self.is_sending or self.is_receiving:

            duration = self.get_connection_duration()

            direction = 'Send' if self.is_sending else 'Receive'


            self.handle_link_record(
                self.current_message_to_record,
                direction,
                duration,
                self.current_message_play_time,
                self.current_message_play_time_invertal
            )


            self.current_message_to_record = ""
            self.current_message_play_time = ""
            self.current_message_play_time_invertal = ""


            self.is_sending = False
            self.is_receiving = False


            self.timer_link_record.stop()

    def handle_link_record(self, message, direction, duration, play_time=0, play_time_interval=0):

        if direction == "Send":

            record = {
                'time': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'message': message,
                'direction': direction,
                'duration': duration,
                'play_time': play_time,
                'play_time_interval': play_time_interval
            }
        else:

            record = {
                'time': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'message': message,
                'direction': direction,
                'duration': duration,
                'sender': self.call_of_sender
            }


        self.database_tool.write_qso_record(record)

    def get_connection_duration(self):

        if self.start_record_time:

            return (datetime.now() - self.start_record_time).total_seconds()
        return 0

    def start_record_receive(self, char):


        if not self.is_receiving and not self.is_sending:
            self.start_record_time = datetime.now()


        if self.is_sending:
            duration = self.get_connection_duration()
            direction = 'Receive'
            self.handle_link_record(char, direction, duration)


        self.current_message_to_record += char


        self.is_receiving = True


        self.timer_link_record.start()

    def start_record_send(self, char, play_time, play_time_interval):


        if not self.is_sending and not self.is_receiving:
            self.start_record_time = datetime.now()


        if self.is_receiving:
            duration = self.get_connection_duration()
            direction = 'Send'
            self.handle_link_record(char, direction, duration)


        self.current_message_to_record += char


        if self.current_message_play_time:
            self.current_message_play_time += "," + str(play_time)
            self.current_message_play_time_invertal += "," + str(play_time_interval)
        else:
            self.current_message_play_time = str(play_time)
            self.current_message_play_time_invertal = str(play_time_interval)


        self.is_sending = True


        self.timer_link_record.start()

    def extract_cleaned_parts(self, input_data):

        if isinstance(input_data, str):

            if input_data.endswith("/"):
                input_data = input_data[:-1]

            cleaned_str = re.sub(r"[^.\-/]", "", input_data)

            groups = cleaned_str.split("///")
            cleaned_groups = []
            for group in groups:
                parts = group.split("/")
                cleaned_parts = [part.strip() for part in parts if part.strip()]
                if cleaned_parts:
                    cleaned_groups.append(cleaned_parts)
            return cleaned_groups[-1][-1]
        elif isinstance(input_data, list):

            cleaned_results = []
            for item in input_data:
                cleaned_result = self.extract_cleaned_parts(item)
                if cleaned_result:
                    cleaned_results.append(cleaned_result)
            return cleaned_results
        return []

    def clean_screen(self):


        self.edit_morse_code.setText("")
        self.edit_morse_received.setText("")
        self.edit_send_translation.setText("")
        self.edit_received_translation.setText("")
        self.morse_code_translation = ""
        self.morse_code = ""
        self._last_raw_tail = None
        self._last_decode_text = None
        self._last_decision_tail = []
        self._last_decision_active_index = -2

    def about(self):

        dialog = AboutDialog(self)
        dialog.move(self.center_point_x, self.center_point_y)
        dialog.exec()

    def check_qso(self):

        qso = QsoRecordDialog()
        qso.move(self.center_point_x, self.center_point_y)
        qso.exec()

    def general_setting(self):

        dialog = GeneralSettingDialog(self)
        dialog.move(self.center_point_x, self.center_point_y)

        if dialog.exec() == QDialog.Accepted:
            self._refresh_send_runtime()
            self.is_translation_visible()

            self.label_keybord_hint.setText(f'Keyboard sending: Dot {dialog.key_one} Dash {dialog.key_two}')


            self.set_my_call()


            self.set_visualizer_visibility()

            old_buzz = self.buzz
            if self.context and hasattr(self.context, "recreate_buzzer"):
                new_buzz = self.context.recreate_buzzer()
            else:
                new_buzz = self.create_buzzer()
            self.buzz = new_buzz
            if hasattr(self, "tx_runtime") and self.tx_runtime:
                self.tx_runtime.buzzer = new_buzz
            processor = getattr(self, "receive_message_processor", None)
            channels = getattr(processor, "channels", None)
            if isinstance(channels, dict):
                for channel in channels.values():
                    channel.buzz = new_buzz
            if old_buzz is not new_buzz and old_buzz and hasattr(old_buzz, "close"):
                try:
                    old_buzz.close()
                except Exception:
                    pass

    def transmitter_setting(self):

        dialog = TransmitterSettingDialog(self)
        dialog.move(self.center_point_x, self.center_point_y)

        if dialog.exec() == QDialog.Accepted:
            self._refresh_send_runtime()
            self.label_dot_duration.setText(f'Dot interval: {self.config_manager.get_dot_time()}ms')

    def morse_key_modifty_setting(self):

        dialog = KeyModifierDialog(self)
        dialog.move(self.center_point_x, self.center_point_y)
        dialog.exec()


    def show_common_phrases_action(self):

        self.table_tool_communication_words.show()

    def show_reference_table_action(self):

        self.table_tool_morse_code.show()

    def is_translation_visible(self):

        if not self.config_manager.get_translation_visibility():

            self.edit_morse_code.setEchoMode(QLineEdit.Password)
            self.edit_morse_received.setEchoMode(QLineEdit.Password)
            self.edit_received_translation.setEchoMode(QLineEdit.Password)
            self.edit_send_translation.setEchoMode(QLineEdit.Password)
        else:

            self.edit_morse_code.setEchoMode(QLineEdit.Normal)
            self.edit_morse_received.setEchoMode(QLineEdit.Normal)
            self.edit_received_translation.setEchoMode(QLineEdit.Normal)
            self.edit_send_translation.setEchoMode(QLineEdit.Normal)

    def set_my_call(self):

        self.my_call = str(self.config_manager.get_my_call() or "").strip()
        if self.my_call and self.my_call.lower() != "none":
            self.label_my_call.setText(f'{self.my_call.upper()}')
        else:
            self.label_my_call.setText("")

    def set_visualizer_visibility(self):

        if self.config_manager.get_visualizer_visibility():
            self.morsecode_visualizer.show()
        else:
            self.morsecode_visualizer.hide()

    def show_visualizer(self, Morsechar, keydown_ms=None, gap_ms=None):

        if keydown_ms is not None:
            fps_ms = int(getattr(self.morsecode_visualizer, "fps_ms", 40))
            fps_ms = max(1, fps_ms)
            height_frames = max(1, int(math.ceil(float(keydown_ms) / float(fps_ms))))
            actual_gap = self.dot_duration if gap_ms is None else max(1, int(gap_ms))
            self.morsecode_visualizer.generate_blocks(
                channel_idx=5,
                count=1,
                height=height_frames,
                gap_ms=actual_gap,
            )
            return


        if Morsechar == self.dot:
            self.morsecode_visualizer.generate_blocks(height=15)
        else:
            self.morsecode_visualizer.generate_blocks(height=45)

    def set_font_size(self):

        font_size = self.config_manager.get_sender_font_size()
        font = QFont()
        font.setFamily("Arial")
        font.setPointSize(font_size)
        self.edit_morse_code.setFont(font)
        self.edit_morse_received.setFont(font)
        self.edit_send_translation.setFont(font)
        self.edit_received_translation.setFont(font)

    def check_myCall(self):

        my_call = str(self.config_manager.get_my_call() or "").strip()
        return bool(my_call) and my_call.lower() != "none"
