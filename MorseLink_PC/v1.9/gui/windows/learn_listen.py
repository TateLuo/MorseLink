import gc

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont, QTextCursor
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QListWidgetItem,
    QPushButton,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from ui_widgets import (
    ComboBox,
    InfoBar,
    InfoBarIcon,
    InfoBarPosition,
    ListWidget,
    ProgressBar,
    ProgressRing,
    PushButton,
    TextEdit,
)
from ui_widgets import FluentIcon as FIF

from service.signal.qt_signal import MySignal
from utils.config_manager import ConfigManager
from utils.database_tool import DatabaseTool
from utils.difficulty_profile import compute_timing_ms
from utils.morse_learn_helper import MorseLearnHelper
from utils.sound import BuzzerSimulator
from utils.training_feedback import (
    align_sequences,
    build_alignment_summary_text,
    render_alignment_html,
)
from utils.translator import MorseCodeTranslator


LEGACY_LEARN_WPM = 16
LEGACY_LISTEN_WEIGHT = 0.6
LEGACY_MIN_WORD_LENGTH = 4
LEGACY_MAX_WORD_LENGTH = 5
LEGACY_MIN_GROUPS = 4
LEGACY_MAX_GROUPS = 5


class LearnListen(QWidget):
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

    def create_buzzer(self):
        if self.context and hasattr(self.context, "create_buzzer"):
            return self.context.create_buzzer()
        return BuzzerSimulator()

    def _capture_scale_metrics(self):
        if self._scale_metrics_ready:
            return
        self._scale_metrics_ready = True
        self._base_list_width = self.list_widget.width() if self.list_widget.width() > 0 else 150
        self._base_ring_size = (
            self.accuracy_progressRing.width() if self.accuracy_progressRing.width() > 0 else 40
        )
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
        self.layout_main = QHBoxLayout()
        self.setLayout(self.layout_main)

        splitter = QSplitter(Qt.Horizontal)

        self.left_widget = QWidget()
        self.vbox_lesson_select = QVBoxLayout(self.left_widget)

        self.combo_lesson_type = ComboBox()
        self.combo_lesson_type.addItems(
            [
                self.tr("字母和符号"),
                self.tr("Q简语"),
                self.tr("缩略语"),
                self.tr("句子"),
                self.tr("呼号"),
            ]
        )
        self.combo_lesson_type.currentIndexChanged.connect(self.on_select)
        self.vbox_lesson_select.addWidget(self.combo_lesson_type)

        self.list_widget = ListWidget()
        self.list_widget.setFixedWidth(150)
        self.list_widget.itemClicked.connect(self.on_item_clicked)
        self.vbox_lesson_select.addWidget(self.list_widget)

        self.current_audio_progressBar = ProgressBar()
        self.current_audio_progressBar.setContentsMargins(0, 0, 0, 0)
        self.current_audio_progressBar.setVisible(False)
        self.vbox_lesson_select.addWidget(self.current_audio_progressBar)

        self.right_widget = QWidget()
        self.vbox_test = QVBoxLayout(self.right_widget)

        self.current_lesson_button = QPushButton(self.tr("当前课程：未选择"))
        title_font = QFont()
        title_font.setBold(True)
        title_font.setPointSize(16)
        self.current_lesson_button.setFont(title_font)
        self.current_lesson_button.setStyleSheet(
            "text-align: left;background-color: transparent; color: black;"
        )
        self.current_lesson_button.clicked.connect(self.lesson_titel_click)
        self.vbox_test.addWidget(self.current_lesson_button)

        font = QFont("Arial", 12)

        self.input_box = TextEdit()
        self.input_box.setPlaceholderText(self.tr("请输入你听到的内容"))
        self.input_box.setFont(font)
        self.vbox_test.addWidget(self.input_box)
        self.cursor_inputbox = self.input_box.textCursor()

        self.correct_answer_box = TextEdit()
        self.correct_answer_box.setReadOnly(True)
        self.correct_answer_box.setPlaceholderText(self.tr("正确答案将显示在这里"))
        self.correct_answer_box.setFont(font)
        self.vbox_test.addWidget(self.correct_answer_box)
        self.cursor_answerbox = QTextCursor(self.correct_answer_box.document())

        self.hbox_controls = QHBoxLayout()

        self.accuracy_label = QLabel(self.tr("正确率 0%"))

        self.accuracy_progressRing = ProgressRing(self)
        self.accuracy_progressRing.setFixedSize(40, 40)
        self.accuracy_progressRing.setVisible(False)
        self.hbox_controls.addWidget(self.accuracy_progressRing)

        self.play_button = PushButton(FIF.PLAY, self.tr("播放"), self)
        self.play_button.clicked.connect(self.play_morse_code)
        self.hbox_controls.addWidget(self.play_button)

        self.check_button = PushButton(FIF.SEARCH, self.tr("检查结果"), self)
        self.check_button.clicked.connect(self.check_result)
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
        self.signal = MySignal()
        self.signal.update_listen_progress_signal.connect(self.update_play_progress)

        self.current_lesson_char = []
        self.current_lesson_sentences = ""
        self.current_lesson_array = ""
        self.current_lesson_core_element = ""
        self.current_lesson_progress = ""

        self.helper = MorseLearnHelper()
        self.translator = MorseCodeTranslator()
        self.buzzer = self.create_buzzer()
        self.buzzer.set_playback_callback(self.playback_status_listener)
        self.configer = self.context.config_manager if self.context else ConfigManager()
        if self.context and hasattr(self.context, "create_database_tool"):
            self.db_tool = self.context.create_database_tool()
        else:
            self.db_tool = DatabaseTool()

    def init_setting(self):
        self.lesson_type = self.get_lesson_type(self.combo_lesson_type.currentIndex())
        self.update_list(self.lesson_type)

    def _get_training_timing(self):
        return compute_timing_ms(LEGACY_LEARN_WPM)

    def on_item_clicked(self, item):
        self.current_lesson_array = item.data(Qt.UserRole + 1)
        self.current_lesson_button.setText(f"{item.text()}")
        self.current_lesson_core_element = item.data(Qt.UserRole + 5)
        self.current_lesson_progress = self.db_tool.get_progress_by_title(self.current_lesson_core_element)

        self.accuracy_progressRing.setTextVisible(True)
        self.accuracy_progressRing.setVisible(True)
        self.accuracy_progressRing.setValue(self.current_lesson_progress)
        self.current_audio_progressBar.setValue(0)

        self.input_box.setText("")
        self.correct_answer_box.setText("")
        self.result_summary_label.setText(self.tr("结果摘要将显示在这里"))
        self.current_lesson_sentences = ""

    def check_result(self):
        """Check user input with alignment-based feedback."""
        if self.current_lesson_sentences == "":
            self.input_box.setText("")
            self.result_summary_label.setText(self.tr("结果摘要将显示在这里"))
            self.createInfoInfoBar(self.tr("提示"), self.tr("请先播放随机音频"))
            return

        self.correct_answer_box.clear()
        input_text = self.input_box.toPlainText()
        expected_chars = list(self.current_lesson_sentences)
        input_chars = list(input_text)

        result = align_sequences(
            expected_chars,
            input_chars,
            normalize=lambda ch: ch.lower(),
        )

        self.correct_answer_box.setHtml(
            render_alignment_html(result.cells, side="expected", token_joiner="")
        )
        self.input_box.setHtml(
            render_alignment_html(result.cells, side="actual", token_joiner="")
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

    def play_morse_code(self):
        if self.play_button.text() == self.tr("播放"):
            self.input_box.setText("")
            self.correct_answer_box.setText("")
            self.result_summary_label.setText(self.tr("结果摘要将显示在这里"))
            timing = self._get_training_timing()

            if self.lesson_type and self.current_lesson_array != "":
                random_sentence = self.helper.generate_random_data(
                    self.current_lesson_array.split(","),
                    self.lesson_type,
                    self.current_lesson_core_element,
                    LEGACY_LISTEN_WEIGHT,
                    LEGACY_MIN_WORD_LENGTH,
                    LEGACY_MAX_WORD_LENGTH,
                    LEGACY_MIN_GROUPS,
                    LEGACY_MAX_GROUPS,
                )

                morse_code = self.translator.text_to_morse(random_sentence)
                self.current_lesson_sentences = random_sentence
                self.buzzer.play_morse_code(
                    morse_code,
                    timing["dot_ms"],
                    timing["dash_ms"],
                    timing["letter_gap_ms"],
                    timing["word_gap_ms"],
                )
            else:
                self.createInfoInfoBar(self.tr("提示"), self.tr("请先选择课程"))

        elif self.play_button.text() == self.tr("停止"):
            self.buzzer.stop_playing_morse_code()
            self.current_audio_progressBar.setValue(0)

    def _set_playback_idle_state(self):
        self.play_button.setEnabled(True)
        self.list_widget.setEnabled(True)
        self.check_button.setEnabled(True)
        self.play_button.setIcon(FIF.PLAY)
        self.play_button.setText(self.tr("播放"))

    def playback_status_listener(self, status):
        if status == "started":
            self.play_button.setIcon(FIF.PAUSE)
            self.play_button.setText(self.tr("停止"))
            self.list_widget.setEnabled(False)
            self.check_button.setEnabled(False)
        elif isinstance(status, (int, float)):
            self.signal.update_listen_progress_signal.emit(int(status))
        elif status in ("finished", "stopped"):
            self._set_playback_idle_state()
            gc.collect()
            self.buzzer.sound_for_test_listen = None

    def on_select(self, index):
        self.lesson_type = self.get_lesson_type(index)
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
            "callSign",
        ]
        if 0 <= index < len(translation_list):
            return translation_list[index]
        return "Unknown"

    def update_play_progress(self, data):
        self.current_audio_progressBar.setVisible(True)
        self.current_audio_progressBar.setValue(data)

    def lesson_titel_click(self):
        if self.current_lesson_core_element == "":
            return
        timing = self._get_training_timing()

        morse_code = self.translator.text_to_morse(self.current_lesson_core_element)
        self.buzzer.play_morse_code(
            morse_code,
            timing["dot_ms"],
            timing["dash_ms"],
            timing["letter_gap_ms"],
            timing["word_gap_ms"],
        )

    def createInfoInfoBar(self, title, content):
        w = InfoBar(
            icon=InfoBarIcon.INFORMATION,
            title=title,
            content=content,
            orient=Qt.Vertical,
            isClosable=True,
            position=InfoBarPosition.BOTTOM,
            duration=2000,
            parent=self,
        )
        w.show()

