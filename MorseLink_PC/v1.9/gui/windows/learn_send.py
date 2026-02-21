import re
from utils.morse_learn_helper import MorseLearnHelper
from PySide6.QtWidgets import (QWidget,
                            QVBoxLayout,
                            QHBoxLayout,
                            QListWidgetItem,
                            QLabel,
                            QSplitter,
                            QPushButton
                            )
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor, QTextCursor, QColor, QFont
from utils.sound import BuzzerSimulator
from utils.translator import MorseCodeTranslator
from utils.config_manager import ConfigManager
from utils.database_tool import DatabaseTool
from utils.difficulty_profile import compute_timing_ms
from service.keying_controller import AutoElementEvent
from service.tx_keying_runtime import TxKeyingRuntime
from utils.training_feedback import (
    align_sequences,
    render_alignment_html,
    build_alignment_summary_text,
)
from ui_widgets import (TextEdit,
                            PushButton,
                            ListWidget,
                            ComboBox,
                            InfoBarIcon,
                            InfoBar,
                            PushButton,
                            ProgressRing,
                            InfoBarPosition
                            )

from ui_widgets import FluentIcon as FIF


LEGACY_LEARN_WPM = 16
LEGACY_LISTEN_WEIGHT = 0.6
LEGACY_MIN_WORD_LENGTH = 4
LEGACY_MAX_WORD_LENGTH = 5
LEGACY_MIN_GROUPS = 4
LEGACY_MAX_GROUPS = 5


class LearnSend(QWidget):
    """发报训练页面。"""

    def __init__(self, stackedWidget, context=None):
        super().__init__()
        self.context = context

        self.stackedWidget = stackedWidget

        self.setWindowTitle("MorseLink")
        self.setMinimumSize(0, 0)




        self.init_variable()



        self.init_ui()



        self.init_setting()
        self._ui_scale = 1.0
        self._scale_metrics_ready = False
        self._capture_scale_metrics()
        self._max_morse_buffer = 4096


    def create_buzzer(self):
        if self.context and hasattr(self.context, "create_buzzer"):
            return self.context.create_buzzer()
        return BuzzerSimulator()

    def _capture_scale_metrics(self):
        if self._scale_metrics_ready:
            return
        self._scale_metrics_ready = True
        self._base_list_width = self.list_widget.width() if self.list_widget.width() > 0 else 150
        self._base_ring_size = self.accuracy_progressRing.width() if self.accuracy_progressRing.width() > 0 else 40
        self._capture_base_font_metrics()

    def _capture_base_font_metrics(self):
        for w in [self, *self.findChildren(QWidget)]:
            if w.property("_base_font_size") is not None:
                continue
            size = w.font().pointSizeF()
            if size > 0:
                w.setProperty("_base_font_size", size)

    def _apply_font_scale(self, scale: float):
        for w in [self, *self.findChildren(QWidget)]:
            base = w.property("_base_font_size")
            if base is None:
                continue
            f = w.font()
            f.setPointSizeF(max(8.0, float(base) * scale))
            w.setFont(f)

    def apply_ui_scale(self, scale: float):
        self._capture_scale_metrics()
        scale = max(0.75, min(1.65, float(scale)))
        if abs(scale - self._ui_scale) < 0.02:
            return
        self._ui_scale = scale
        self._apply_font_scale(scale)
        self.list_widget.setFixedWidth(max(110, int(round(self._base_list_width * scale))))
        ring_size = max(28, int(round(self._base_ring_size * scale)))
        self.accuracy_progressRing.setFixedSize(ring_size, ring_size)

    def init_ui(self):
        """初始化训练界面布局与控件。"""


        self.layout_main = QHBoxLayout()

        self.setLayout(self.layout_main)


        splitter = QSplitter(Qt.Horizontal)


        self.left_widget = QWidget()

        self.vbox_lesson_select = QVBoxLayout(self.left_widget)


        self.combo_lesson_type = ComboBox()

        self.combo_lesson_type.addItems([
            self.tr("字母和符号"),
            self.tr("Q简语"),
            self.tr("缩略语"),
            self.tr("句子"),
            self.tr("呼号"),
        ])

        self.combo_lesson_type.currentIndexChanged.connect(self.on_select)

        self.vbox_lesson_select.addWidget(self.combo_lesson_type)


        self.list_widget = ListWidget()

        self.list_widget.setFixedWidth(150)


        self.list_widget.itemClicked.connect(self.on_item_clicked)

        self.vbox_lesson_select.addWidget(self.list_widget)


        self.right_widget = QWidget()

        self.vbox_test = QVBoxLayout(self.right_widget)


        self.current_lesson_button = QPushButton(self.tr("当前课程：未选择"))

        font = QFont()
        font.setBold(True)
        font.setPointSize(16)
        self.current_lesson_button.setFont(font)


        self.current_lesson_button.setStyleSheet("text-align: left;background-color: transparent; color: black;")


        self.current_lesson_button.clicked.connect(self.lesson_titel_click)

        self.vbox_test.addWidget(self.current_lesson_button)


        font = QFont("Arial", 12)


        self.question_box = TextEdit()

        self.question_box.setPlaceholderText(self.tr("题目将显示在这里"))

        self.question_box.setReadOnly(True)

        self.vbox_test.addWidget(self.question_box)

        self.cursor_question_box = self.question_box.textCursor()

        self.question_box.setFont(font)


        self.input_box = TextEdit()

        self.input_box.setPlaceholderText(self.tr("发报内容将显示在这里"))

        self.input_box.setReadOnly(True)

        self.vbox_test.addWidget(self.input_box)

        self.cursor_inputbox = self.input_box.textCursor()

        self.input_box.setFont(font)



        self.correct_answer_box = TextEdit()

        self.correct_answer_box.setReadOnly(True)

        self.correct_answer_box.setPlaceholderText(self.tr("正确答案将显示在这里"))

        self.cursor_answerbox = QTextCursor(self.correct_answer_box.document())

        self.correct_answer_box.setFont(font)

        self.vbox_test.addWidget(self.correct_answer_box)



        self.hbox_controls = QHBoxLayout()



        self.accuracy_label = QLabel(self.tr("正确率 0%"))





        self.accuracy_progressRing = ProgressRing(self)

        self.accuracy_progressRing.setFixedSize(40,40)

        self.accuracy_progressRing.setVisible(False)

        self.hbox_controls.addWidget(self.accuracy_progressRing)



        self.CW_button = PushButton(FIF.SEND, self.tr("点击发报"), self)


        self.CW_button.pressed.connect(self.on_btn_send_message_pressed)

        self.CW_button.released.connect(self.on_btn_send_message_released)

        self.hbox_controls.addWidget(self.CW_button)



        self.check_button = PushButton(FIF.SYNC, self.tr("随机出题"), self)

        self.check_button.clicked.connect(self.question_check_button_click)

        self.hbox_controls.addWidget(self.check_button)



        self.vbox_test.addLayout(self.hbox_controls)
        self.result_summary_label = QLabel(self.tr("结果摘要将显示在这里"))
        self.result_summary_label.setWordWrap(True)
        self.vbox_test.addWidget(self.result_summary_label)




        splitter.addWidget(self.left_widget)

        splitter.addWidget(self.right_widget)




        splitter.setStretchFactor(1, 2)




        self.layout_main.addWidget(splitter)


    def init_variable(self):
        """初始化训练状态与工具对象。"""



        self.current_lesson_char = []



        self.current_lesson_sentences = ""




        self.helper = MorseLearnHelper()



        self.translator = MorseCodeTranslator()



        self.buzzer = self.create_buzzer()



        self.configer = self.context.config_manager if self.context else ConfigManager()




        self.db_tool = self.context.create_database_tool() if self.context and hasattr(self.context, "create_database_tool") else DatabaseTool()




        self.current_lesson_array = ""




        self.current_lesson_core_element = ""




        self.current_lesson_progress = ""


    def init_setting(self):
        """加载课程列表并初始化发报运行时。"""



        self.lesson_type = self.get_lesson_type(self.combo_lesson_type.currentIndex())

        self.update_list(self.lesson_type)


        self.initSend()


    def on_item_clicked(self, item):

        self.clean_all_text_box()


        self.check_button.setText(self.tr("随机出题"))
        self.check_button.setIcon(FIF.SYNC)


        self.current_lesson_array = item.data(Qt.UserRole+1)


        self.current_lesson_button.setText(f"{item.text()}")



        self.current_lesson_core_element = item.data(Qt.UserRole+5)



        self.current_lesson_progress = self.db_tool.get_progress_by_title(self.current_lesson_core_element)





        self.accuracy_progressRing.setTextVisible(True)

        self.accuracy_progressRing.setVisible(True)

        self.accuracy_progressRing.setValue(self.current_lesson_progress)




        self.input_box.setText("")

        self.correct_answer_box.setText("")




        self.current_lesson_sentences = ""

    def question_check_button_click(self):
        if self.current_lesson_array:
            btn_text = self.check_button.text()
            if btn_text == self.tr("随机出题"):
                self.clean_all_text_box()
                self.get_morse_code_question()
                self.check_button.setText(self.tr("查看结果"))
                self.check_button.setIcon(FIF.SEARCH)
            else:
                self.check_button.setText(self.tr("随机出题"))
                self.check_button.setIcon(FIF.SYNC)
                self.check_result()
        else:
            self.createInfoInfoBar(self.tr("提示"), self.tr("请先选择课程"))





    def check_result(self):

        if self.question_morse_code == "":
            self.input_box.setText("")
            self.result_summary_label.setText(self.tr("结果摘要将显示在这里"))
            self.createInfoInfoBar(self.tr("提示"), self.tr("请先选择课程。"))
            return

        self.correct_answer_box.clear()
        input_text = self.input_box.toPlainText()

        def split_by_separator(text):
            units = []
            i = 0
            while i < len(text):
                if text[i:i + 3] == "///":
                    units.append("///")
                    i += 3
                elif text[i] == "/":
                    units.append("/")
                    i += 1
                else:
                    segment = ""
                    while i < len(text) and text[i] != "/":
                        segment += text[i]
                        i += 1
                    if segment:
                        units.append(segment)
            return units

        answer_units = split_by_separator(self.question_morse_code)
        input_units = split_by_separator(input_text)
        result = align_sequences(answer_units, input_units, normalize=lambda x: x)

        self.correct_answer_box.setHtml(
            render_alignment_html(result.cells, side="expected", token_joiner=" ")
        )
        self.input_box.setHtml(
            render_alignment_html(result.cells, side="actual", token_joiner=" ")
        )
        self.accuracy_progressRing.setValue(int(result.accuracy))
        self.result_summary_label.setText(build_alignment_summary_text(result))

        status = 1 if result.accuracy > 90 else 0
        progress = int(result.accuracy)
        self.db_tool.update_status_by_title(self.current_lesson_core_element, status)
        self.db_tool.update_progress_by_title(self.current_lesson_core_element, progress)
        self._update_current_lesson_item(status, progress)

    def _update_current_lesson_item(self, status, progress):
        item = self.list_widget.currentItem()
        if item is None:
            return
        item.setData(Qt.UserRole + 3, status)
        item.setData(Qt.UserRole + 4, progress)
        if status == 1:
            item.setBackground(QColor(144, 238, 144))
        else:
            item.setBackground(QColor(Qt.transparent))


    def get_morse_code_question(self):



        if self.lesson_type and self.current_lesson_array != "":



            random_sentence = self.helper.generate_random_data( self.current_lesson_array.split(","),

                                                                self.lesson_type,

                                                                self.current_lesson_core_element,

                                                                LEGACY_LISTEN_WEIGHT,

                                                                LEGACY_MIN_WORD_LENGTH,

                                                                LEGACY_MAX_WORD_LENGTH,

                                                                LEGACY_MIN_GROUPS,

                                                                LEGACY_MAX_GROUPS
                                                                )

            self.question_morse_code = self.translator.text_to_morse(random_sentence)

            self.current_lesson_sentences = random_sentence
            self.question_box.setText(f'{self.tr("题目：")}{self.current_lesson_sentences}')
            return random_sentence

        return ""


    def on_select(self, index):


        self.lesson_type = self.get_lesson_type(self.combo_lesson_type.currentIndex())

        self.update_list(self.lesson_type)


    def update_list(self, lesson_type):

        self.list_widget.clear()
        lessons = self.db_tool.get_listening_lessons_by_type(lesson_type)

        for index, lesson in enumerate(lessons):
            title = lesson.get("title", self.tr("无标题"))
            content = lesson.get("content", self.tr("无内容"))

            item = QListWidgetItem(self.tr("课程 {0}: {1}").format(index + 1, title))
            item.setData(Qt.UserRole, lesson.get("type", self.tr("无类型")))
            item.setData(Qt.UserRole + 1, content)
            item.setData(Qt.UserRole + 2, lesson.get("note", self.tr("无备注")))
            item.setData(Qt.UserRole + 3, lesson.get("status", 0))
            item.setData(Qt.UserRole + 4, lesson.get("progress", 0))
            item.setData(Qt.UserRole + 5, title)


            if lesson.get("status") == 1:
                item.setBackground(QColor(144, 238, 144))

            self.list_widget.addItem(item)




    def get_lesson_type(self, index):

        translation_list = [
            "letter",
            "QAbbreviation",
            "Abbreviation",
            "sentences",
            "callSign"
        ]

        if 0 <= index < len(translation_list):
            return translation_list[index]
        else:
            return "Unknown"



    def lesson_titel_click(self):

        if self.current_lesson_array != "":
            self.createInfoInfoBar(
                self.tr("提示"),
                f"{self.tr('当前课程:')} {self.translator.letter_to_morse_code(self.current_lesson_core_element)}",
                InfoBarPosition.TOP,
            )

    def clean_all_text_box(self):

        self.input_box.setText("")
        self.question_box.setText("")
        self.correct_answer_box.setText("")
        self.result_summary_label.setText(self.tr("结果摘要将显示在这里"))

        self.morse_code = ""




    def createInfoInfoBar(self, title, content, position=InfoBarPosition.BOTTOM):

        content = content

        w = InfoBar(

            icon=InfoBarIcon.INFORMATION,

            title= title,

            content=content,

            orient=Qt.Vertical,

            isClosable=True,

            position=position,

            duration=2000,

            parent=self
        )

        w.show()



    def initSend(self):
        self.morse_code = ""
        self.morse_code_received = ""
        self.morse_code_translation = ""
        self.received_translation = ""
        self.question_morse_code = ""

        self.dot = "."
        self.dash = "-"

        self.letter_timer = QTimer(self)
        self.letter_timer.setSingleShot(True)
        self.letter_timer.timeout.connect(self.handle_letter_timeout)

        self.word_timer = QTimer(self)
        self.word_timer.setSingleShot(True)
        self.word_timer.timeout.connect(self.handle_word_timeout)

        self.tx_runtime = TxKeyingRuntime(
            parent=self,
            buzzer=self.buzzer,
            get_wpm=self._get_training_wpm,
            on_stop_gap_timers=self._stop_gap_timers,
            on_start_letter_timer=self.start_letter_timer,
            on_manual_symbol=self._tx_runtime_on_manual_symbol,
            on_auto_symbol=self._tx_runtime_on_auto_symbol,
        )
        self.key_controller = self.tx_runtime.key_controller
        self._refresh_send_runtime()

    def _get_training_wpm(self):
        return LEGACY_LEARN_WPM

    def _get_training_timing(self):
        return compute_timing_ms(self._get_training_wpm())

    def _stop_gap_timers(self):
        self.word_timer.stop()
        self.letter_timer.stop()

    def _refresh_send_runtime(self):
        timing = self._get_training_timing()
        self.dot_duration = int(timing["dot_ms"])
        self.dash_duration = int(timing["dash_ms"])
        self.letter_interval_duration = int(timing["letter_gap_ms"])
        self.word_interval_duration = int(timing["word_gap_ms"])
        self.keyer_mode = str(self.configer.get_keyer_mode() or "straight").lower()
        self.send_buzz_status = self.configer.get_send_buzz_status()
        self.receive_buzz_status = self.configer.get_receive_buzz_status()
        self.saved_key = self.configer.get_keyborad_key().split(',')
        if hasattr(self, 'tx_runtime') and self.tx_runtime:
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

    def _parse_saved_keys(self):
        return self.tx_runtime.parse_saved_keys()

    def _tx_runtime_on_manual_symbol(self, morse_code, duration_ms, gap_ms, manual_duration_ms):
        self.update_sent_label(morse_code)

    def _tx_runtime_on_auto_symbol(self, event: AutoElementEvent):
        self.update_sent_label(event.symbol)

    def on_btn_send_message_pressed(self):
        if self.current_lesson_sentences == "":
            self.createInfoInfoBar(self.tr("提示"), self.tr("请先随机出题"))
            return
        if self.tx_runtime.press_manual(
            ready=True,
            allow_transmit=True,
            max_interval_seconds=50,
        ):
            self.CW_button.setIcon(FIF.SEND_FILL)

    def on_btn_send_message_released(self):
        if self.tx_runtime.release_manual():
            self.CW_button.setIcon(FIF.SEND)

    def keyPressEvent(self, event):
        self.tx_runtime.handle_key_press(
            key=event.key(),
            is_auto_repeat=event.isAutoRepeat(),
            ready=bool(self.current_lesson_sentences),
            allow_transmit=True,
            max_interval_seconds=10,
        )

    def keyReleaseEvent(self, event):
        self.tx_runtime.handle_key_release(
            key=event.key(),
            is_auto_repeat=event.isAutoRepeat(),
        )

    def determine_morse_character(self, duration):
        return self.tx_runtime.determine_morse_character(duration)


    def update_sent_label(self, morse_code):


        self.morse_code += morse_code
        if len(self.morse_code) > self._max_morse_buffer:
            self.morse_code = self.morse_code[-self._max_morse_buffer:]
            self.input_box.setPlainText(self.morse_code)
            return
        self.input_box.insertPlainText(morse_code)



    def start_letter_timer(self):
        self.letter_timer.start(self.letter_interval_duration)




    def start_word_timer(self):
        self.word_timer.start(self.word_interval_duration)




    def handle_letter_timeout(self):

        self.morse_code += "/"
        if len(self.morse_code) > self._max_morse_buffer:
            self.morse_code = self.morse_code[-self._max_morse_buffer:]
            self.input_box.setPlainText(self.morse_code)
        else:
            self.input_box.insertPlainText("/")

        self.start_word_timer()

        extracted_mores_code = self.extract_cleaned_parts(self.morse_code)
        self.morse_code_translation_temp = self.translator.letter_to_morse(extracted_mores_code)
        self.morse_code_translation += self.morse_code_translation_temp


    def handle_word_timeout(self):

        self.morse_code += "//"
        if len(self.morse_code) > self._max_morse_buffer:
            self.morse_code = self.morse_code[-self._max_morse_buffer:]
            self.input_box.setPlainText(self.morse_code)
        else:
            self.input_box.insertPlainText("//")


        self.morse_code_translation += " "



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





