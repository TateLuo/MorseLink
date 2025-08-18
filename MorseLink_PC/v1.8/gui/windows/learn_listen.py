import time, gc

from utils.morse_learn_helper import MorseLearnHelper

from PyQt5.QtWidgets import (QWidget, 

                            QVBoxLayout, 

                            QHBoxLayout,

                            QListWidgetItem,

                            QLabel,

                            QSplitter,
                            
                            QPushButton
                            )

from PyQt5.QtCore import Qt

from PyQt5.QtGui import QColor, QTextCursor, QColor, QFont

from utils.sound import BuzzerSimulator

from utils.translator import MorseCodeTranslator

from utils.config_manager import ConfigManager

from utils.database_tool import DatabaseTool


from service.signal.pyqt_signal import MySignal


from qfluentwidgets import (TextEdit,

                            PushButton,

                            ListWidget,

                            ComboBox,

                            InfoBarIcon,

                            InfoBar,

                            PushButton,

                            ProgressRing,

                            InfoBarPosition,

                            ProgressBar
                            )

from qfluentwidgets import FluentIcon as FIF


class LearnListen(QWidget):

    def __init__(self, stackedWidget):
        super().__init__()

        self.stackedWidget = stackedWidget  # 初始化堆栈窗口

        self.setWindowTitle("MorseLink")  # 设置窗口标题

        self.resize(700, 380)  # 设置窗口大小


        # 初始化变量
        self.init_variable()

        # 初始化用户界面
        self.init_ui()

        # 初始化一些设置
        self.init_setting()

    def init_ui(self):
        # 主布局
        self.layout_main = QHBoxLayout()
        self.setLayout(self.layout_main)

        # 使用 QSplitter 允许左右布局可调整大小
        splitter = QSplitter(Qt.Horizontal)

        # 左侧布局 - 课程选择
        self.left_widget = QWidget()
        self.vbox_lesson_select = QVBoxLayout(self.left_widget)

        # 课程类型选择下拉菜单
        self.combo_lesson_type = ComboBox()
        self.combo_lesson_type.addItems([self.tr("字母和符号"), self.tr("Q短语"), self.tr("缩写词"), self.tr("句子"), self.tr("呼号")])
        self.combo_lesson_type.currentIndexChanged.connect(self.on_select)  # 连接选择变化信号
        self.vbox_lesson_select.addWidget(self.combo_lesson_type)

        # 课程内容列表
        self.list_widget = ListWidget()
        self.list_widget.setFixedWidth(150)  # 设置固定宽度

        # 列表项点击事件
        self.list_widget.itemClicked.connect(self.on_item_clicked)
        self.vbox_lesson_select.addWidget(self.list_widget)

        # 课程音频播放进度条
        self.current_audio_progressBar = ProgressBar()
        self.current_audio_progressBar.setContentsMargins(0, 0, 0, 0)  # 设置内容边距
        self.current_audio_progressBar.setVisible(False)  # 初始设置为不可见
        self.vbox_lesson_select.addWidget(self.current_audio_progressBar)

        # 右侧布局 - 输入框、控制按钮和结果
        self.right_widget = QWidget()
        self.vbox_test = QVBoxLayout(self.right_widget)

        # 当前课程显示
        self.current_lesson_button = QPushButton(self.tr("当前课程：未选择"))
        # 设置字体大小
        font = QFont()
        font.setBold(True)  # 设置为粗体
        font.setPointSize(16)  # 设置字体大小为16
        self.current_lesson_button.setFont(font)

        # 设置文本左对齐
        self.current_lesson_button.setStyleSheet("text-align: left;background-color: transparent; color: black;")

        # 绑定点击事件，点击播放示例
        self.current_lesson_button.clicked.connect(self.lesson_titel_click)
        self.vbox_test.addWidget(self.current_lesson_button)

        # 设置字体
        font = QFont("Arial", 12)  # 设置字体为Arial，大小为12

        # 用户输入框和正确答案框
        self.input_box = TextEdit()
        self.input_box.setPlaceholderText(self.tr("输入您听到的内容"))  # 设置占位符文本
        self.vbox_test.addWidget(self.input_box)
        self.cursor_inputbox = self.input_box.textCursor()  # 获取文本光标
        self.input_box.setFont(font)

        self.correct_answer_box = TextEdit()
        self.correct_answer_box.setReadOnly(True)  # 设置为只读
        self.correct_answer_box.setPlaceholderText(self.tr("正确答案将显示在这里"))  # 设置占位符文本
        self.cursor_answerbox = QTextCursor(self.correct_answer_box.document())  # 获取文本光标
        self.correct_answer_box.setFont(font)
        self.vbox_test.addWidget(self.correct_answer_box)

        # 水平布局（按钮 + 准确率标签）
        self.hbox_controls = QHBoxLayout()

        # 准确率显示标签
        self.accuracy_label = QLabel(self.tr("正确率: 0%"))

        # 准确率圆形进度条
        self.accuracy_progressRing = ProgressRing(self)
        self.accuracy_progressRing.setFixedSize(40, 40)  # 设置固定大小
        self.accuracy_progressRing.setVisible(False)  # 初始设置为不可见
        self.hbox_controls.addWidget(self.accuracy_progressRing)

        # 播放按钮
        self.play_button = PushButton(FIF.PLAY, self.tr("播放"), self)
        self.play_button.clicked.connect(self.play_morse_code)  # 连接点击事件
        self.hbox_controls.addWidget(self.play_button)

        # 检查结果按钮
        self.check_button = PushButton(FIF.SEARCH, self.tr("检查结果"), self)
        self.check_button.clicked.connect(self.check_result)  # 连接点击事件
        self.hbox_controls.addWidget(self.check_button)

        # 将按钮行添加到右侧主布局
        self.vbox_test.addLayout(self.hbox_controls)

        # 将左右布局添加到分隔器中
        splitter.addWidget(self.left_widget)
        splitter.addWidget(self.right_widget)

        # 设置初始比例，右侧内容更大
        splitter.setStretchFactor(1, 2)

        # 将分隔器添加到主布局中
        self.layout_main.addWidget(splitter)

    def init_variable(self):
        # 初始化信号
        self.signal = MySignal()
        self.signal.update_listen_progress_signal.connect(self.update_play_progress)  # 连接进度更新信号

        # 当前课程字符
        self.current_lesson_char = []

        # 当前课程句子
        self.current_lesson_sentences = ""

        # 初始化摩尔斯助手（随机字符生成器）
        self.helper = MorseLearnHelper()

        # 初始化翻译器
        self.translator = MorseCodeTranslator()

        # 初始化蜂鸣器
        self.buzzer = BuzzerSimulator()
        self.buzzer.set_playback_callback(self.playback_status_listener)  # 设置播放回调

        # 初始化配置文件助手
        self.configer = ConfigManager()

        # 初始化数据库工具
        self.db_tool = DatabaseTool()

        # 初始化当前课程内容数组
        self.current_lesson_array = ""

        # 初始化当前课程核心内容
        self.current_lesson_core_element = ""

        # 当前课程进度
        self.current_lesson_progress = ""

    def init_setting(self):
        """初始化一些设置"""
        self.lesson_type = self.get_lesson_type(self.combo_lesson_type.currentIndex())  # 获取课程类型
        self.update_list(self.lesson_type)  # 更新课程列表

    def on_item_clicked(self, item):
        """列表点击事件"""
        self.current_lesson_array = item.data(Qt.UserRole + 1)  # 获取课程内容数组

        # 设置课程标题
        self.current_lesson_button.setText(f"{item.text()}")

        # 设置当前课程核心元素，核心元素占比较大
        self.current_lesson_core_element = item.data(Qt.UserRole + 5)

        # 获取当前课程进度
        self.current_lesson_progress = self.db_tool.get_progress_by_title(self.current_lesson_core_element)

        # 设置当前课程进度
        self.accuracy_progressRing.setTextVisible(True)  # 显示文本
        self.accuracy_progressRing.setVisible(True)  # 设置为可见
        self.accuracy_progressRing.setValue(self.current_lesson_progress)  # 设置进度值

        # 将播放进度条设置为0
        self.current_audio_progressBar.setValue(0)

        # 将两个输入框清空
        self.input_box.setText("")
        self.correct_answer_box.setText("")

        # 清空当前课程句子
        self.current_lesson_sentences = ""

    def check_result(self):
        """检查用户输入结果"""
        
        if self.current_lesson_sentences != "":  # 如果有当前课程句子
            self.correct_answer_box.clear()  # 清空正确答案框

            input_text = self.input_box.toPlainText()  # 获取用户输入文本
            total_chars = len(self.current_lesson_sentences)  # 获取总字符数

            # 转换为小写以进行比较，忽略大小写
            input_text_lower = input_text.lower()
            lesson_sentences_lower = self.current_lesson_sentences.lower()

            formatted_answer = ""

            # 处理答案框，将用户输入与标准答案进行比较
            for i in range(total_chars):
                if i < len(input_text_lower):
                    # 如果输入正确（忽略大小写），保持原始显示
                    if input_text_lower[i] == lesson_sentences_lower[i]:
                        formatted_answer += self.current_lesson_sentences[i]  # 保持原始大小写
                    else:
                        # 如果输入错误，突出显示错误
                        formatted_answer += f"<span style='background-color:yellow;'>{self.current_lesson_sentences[i]}</span>"
                else:
                    # 如果用户未输入，标记为浅色高亮
                    formatted_answer += f"<span style='background-color:lightgray;'>{self.current_lesson_sentences[i]}</span>"

            # 设置正确答案框显示
            self.correct_answer_box.setHtml(formatted_answer)

            # 处理用户输入框，包括多余输入和未输入部分
            highlighted_input = ""

            for i in range(len(input_text)):
                if i < total_chars:
                    # 正确输入部分保持原样（忽略大小写）
                    if input_text_lower[i] == lesson_sentences_lower[i]:
                        highlighted_input += input_text[i]  # 保持用户的原始大小写
                    else:
                        # 用户输入错误部分高亮
                        highlighted_input += f"<span style='background-color:yellow;'>{input_text[i]}</span>"
                else:
                    # 用户多余输入部分高亮
                    highlighted_input += f"<span style='background-color:orange;'>{input_text[i]}</span>"

            # 如果用户输入不足，补充并高亮缺失部分
            if len(input_text) < total_chars:
                missing_length = total_chars - len(input_text)
                # 用 '*' 替换未输入部分并高亮
                highlighted_input += f"<span style='background-color:lightgray;'>{'*' * missing_length}</span>"

            # 设置用户输入框显示
            self.input_box.setHtml(highlighted_input)

            # 计算正确字符数
            correct_chars = sum(1 for i in range(min(len(input_text_lower), total_chars))
                                if input_text_lower[i] == lesson_sentences_lower[i])

            # 计算准确率并显示
            accuracy = (correct_chars / total_chars) * 100 if total_chars > 0 else 0
            self.accuracy_progressRing.setValue(int(accuracy))

            # 更新数据库状态
            if accuracy > 90:
                self.db_tool.update_status_by_title(self.current_lesson_core_element, 1)  # 更新状态为1
            else:
                self.db_tool.update_status_by_title(self.current_lesson_core_element, 0)  # 更新状态为0

            self.db_tool.update_progress_by_title(self.current_lesson_core_element, int(accuracy))  # 更新进度

        else:
            self.input_box.setText("")  # 清空输入框
            self.createInfoInfoBar(self.tr("提示"), self.tr("请先播放随机音频"))  # 提示用户先播放音频

        self.update_list(self.lesson_type)  # 更新课程列表




    def play_morse_code(self):
        """组装字符并播放"""
        if self.play_button.text() == self.tr("播放"):  # 如果按钮文本为"播放"
            self.input_box.setText("")  # 清空输入框
            self.correct_answer_box.setText("")  # 清空正确答案框

            # 获取点、划、字母间隔和单词间隔的时间
            self.dot_time = self.configer.get_dot_time()
            self.dash_time = self.configer.get_dash_time()
            self.letter_interval_duration = self.configer.get_letter_interval_duration_time()
            self.word_interval_duration = self.configer.get_word_interval_duration_time()

            if self.lesson_type and self.current_lesson_array != "":
                # 获取随机句子
                random_sentence = self.helper.generate_random_data(
                    self.current_lesson_array.split(","),
                    self.lesson_type,
                    self.current_lesson_core_element,
                    self.configer.get_listen_weight(),
                    self.configer.get_min_word_length(),
                    self.configer.get_max_word_length(),
                    self.configer.get_min_groups(),
                    self.configer.get_max_groups()
                )

                print(random_sentence)  # 打印随机句子

                morse_code = self.translator.text_to_morse(random_sentence)  # 将句子转换为摩尔斯电码
                self.current_lesson_sentences = random_sentence  # 保存当前课程句子

                print(morse_code)  # 打印摩尔斯电码

                # 播放摩尔斯电码
                self.buzzer.play_morse_code(
                    morse_code,
                    self.dot_time,
                    self.dash_time,
                    self.letter_interval_duration,
                    self.word_interval_duration
                )
            else:
                self.createInfoInfoBar(self.tr("停止"), self.tr("请先选择课程"))  # 提示用户先选择课程
            
        elif self.play_button.text() == self.tr("停止"):  # 如果按钮文本为"停止"
            self.buzzer.stop_playing_morse_code()  # 停止播放摩尔斯电码
            # 重置播放进度条
            self.current_audio_progressBar.setValue(0)

    def playback_status_listener(self, status):
        """播放状态回调执行"""
        if status == "started":  # 播放开始
            self.play_button.setIcon(FIF.PAUSE)  # 设置按钮图标为暂停
            self.play_button.setText(self.tr("停止"))  # 设置按钮文本为"停止"
            self.list_widget.setEnabled(False)  # 禁用列表
            self.check_button.setEnabled(False)  # 禁用检查按钮

        elif isinstance(status, (int, float)):  # 如果状态为进度值
            self.signal.update_listen_progress_signal.emit(status)  # 发射进度信号

        elif status == "finished":  # 播放结束
            self.play_button.setEnabled(True)  # 启用播放按钮
            self.list_widget.setEnabled(True)  # 启用列表
            self.check_button.setEnabled(True)  # 启用检查按钮
            self.play_button.setIcon(FIF.PLAY)  # 设置按钮图标为播放
            self.play_button.setText(self.tr("播放"))  # 设置按钮文本为"播放"
            gc.collect()  # 垃圾回收
            self.buzzer.sound_for_test_listen = None  # 清空测试听音的声音

    def on_select(self, index):
        """下拉选择变化事件"""
        self.lesson_type = self.get_lesson_type(index)  # 获取课程类型
        self.update_list(self.lesson_type)  # 更新课程列表


    def update_list(self, lesson_type):
        """更新列表"""
        self.list_widget.clear()  # 清空现有的项目
        lessons = self.db_tool.get_listening_lessons_by_type(lesson_type)  # 根据课程类型获取课程列表

        for index, lesson in enumerate(lessons):
            title = lesson.get("title", self.tr("no"))  # 获取课程标题，如果没有则返回"无标题"
            content = lesson.get("content", self.tr("no content"))  # 获取课程内容，如果没有则返回"无内容"

            item = QListWidgetItem(f'Lesson {index+1}: {title}')  # 创建课程项，格式为 "课程 {index+1}: {title}"
            item.setData(Qt.UserRole, lesson.get("type", self.tr("no type")))  # 设置课程类型数据，如果没有则返回"无类型"
            item.setData(Qt.UserRole + 1, content)  # 设置课程内容数据
            item.setData(Qt.UserRole + 2, lesson.get("note", self.tr("no note")))  # 设置课程备注数据，如果没有则返回"无备注"
            item.setData(Qt.UserRole + 3, lesson.get("status", 0))  # 设置课程状态数据
            item.setData(Qt.UserRole + 4, lesson.get("progress", 0))  # 设置课程进度数据
            item.setData(Qt.UserRole + 5, title)  # 设置课程标题数据

            # 检查课程状态是否为1
            if lesson.get("status") == 1:
                item.setBackground(QColor(144, 238, 144))  # 如果状态为1，设置背景为浅绿色

            self.list_widget.addItem(item)  # 将课程项添加到列表中




    def get_lesson_type(self, index):
        """根据输入的索引返回相应的英文课程类型"""
        translation_list = [
            "letter",        # 0: "字母和符号"
            "QAbbreviation",  # 1: "Q短语"
            "Abbreviation",   # 2: "缩写"
            "sentences",     # 3: "句子"
            "callSign"       # 4: "呼号"
        ]
        
        if 0 <= index < len(translation_list):
            return translation_list[index]
        else:
            return "Unknown"  # 如果索引超出范围则返
   
    def update_play_progress(self, data):
        """Update audio playback progress"""
        self.current_audio_progressBar.setVisible(True)
        self.current_audio_progressBar.setValue(data)

    def lesson_titel_click(self):
        self.dot_time = self.configer.get_dot_time()
        self.dash_time = self.configer.get_dash_time()
        self.letter_interval_duration = self.configer.get_letter_interval_duration_time()
        self.word_interval_duration = self.configer.get_word_interval_duration_time()

        morse_code = self.translator.text_to_morse(self.current_lesson_core_element)
        self.buzzer.play_morse_code(
            morse_code,
            self.dot_time,
            self.dash_time,
            self.letter_interval_duration,
            self.word_interval_duration
        )

    
    

    def createInfoInfoBar(self, title, content):

        content = content

        w = InfoBar(

            icon=InfoBarIcon.INFORMATION,

            title= title,

            content=content,

            orient=Qt.Vertical,    # vertical layout

            isClosable=True,

            position=InfoBarPosition.BOTTOM,

            duration=2000,

            parent=self
        )

        w.show()