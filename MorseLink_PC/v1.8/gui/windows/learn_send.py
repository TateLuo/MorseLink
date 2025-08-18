import time, re
from utils.morse_learn_helper import MorseLearnHelper
from PyQt5.QtWidgets import (QWidget, 
                            QVBoxLayout, 
                            QHBoxLayout,
                            QListWidgetItem,
                            QLabel,
                            QSplitter,                
                            QPushButton
                            )
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QColor, QTextCursor, QColor, QFont
from utils.sound import BuzzerSimulator
from utils.translator import MorseCodeTranslator
from utils.config_manager import ConfigManager
from utils.database_tool import DatabaseTool
from qfluentwidgets import (TextEdit,
                            PushButton,
                            ListWidget,
                            ComboBox,
                            InfoBarIcon,
                            InfoBar,
                            PushButton,
                            ProgressRing,
                            InfoBarPosition
                            )

from qfluentwidgets import FluentIcon as FIF

class LearnSend(QWidget):

    def __init__(self, stackedWidget):
        super().__init__()

        self.stackedWidget = stackedWidget

        self.setWindowTitle("MorseLink")

        self.resize(700, 380)


        #初始化变量

        self.init_variable()


        #初始化 UI
        self.init_ui()


        #初始化一些设置
        self.init_setting()


    def init_ui(self):

        # 主布局
        self.layout_main = QHBoxLayout()

        self.setLayout(self.layout_main)

        # 使用 QSplitter 允许调整左右布局区域的大小
        splitter = QSplitter(Qt.Horizontal)

        # 左侧布局 - 课程选择
        self.left_widget = QWidget()

        self.vbox_lesson_select = QVBoxLayout(self.left_widget)

        # 课程类型选择下拉菜单
        self.combo_lesson_type = ComboBox()

        self.combo_lesson_type.addItems([self.tr("字母和符号"), self.tr("Q短语"), self.tr("缩写词"), self.tr("句子"), self.tr("呼号")])

        self.combo_lesson_type.currentIndexChanged.connect(self.on_select)

        self.vbox_lesson_select.addWidget(self.combo_lesson_type)

        # 课程内容列表
        self.list_widget = ListWidget()

        self.list_widget.setFixedWidth(150)

        # 列表项点击事件
        self.list_widget.itemClicked.connect(self.on_item_clicked)

        self.vbox_lesson_select.addWidget(self.list_widget)

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

        # 设置文本对齐方式为左对齐
        self.current_lesson_button.setStyleSheet("text-align: left;background-color: transparent; color: black;")  # 仅对 Qt 5.13+ 有效

        # 绑定槽函数，点击播放示例
        self.current_lesson_button.clicked.connect(self.lesson_titel_click)

        self.vbox_test.addWidget(self.current_lesson_button)

        # 设置字体
        font = QFont("Arial", 12)  # 设置字体为 Arial，大小为12

        # 问题框
        self.question_box = TextEdit()

        self.question_box.setPlaceholderText(self.tr("题目将显示在此处"))

        self.question_box.setReadOnly(True)  # 设置为只读

        self.vbox_test.addWidget(self.question_box)

        self.cursor_question_box = self.question_box.textCursor()

        self.question_box.setFont(font)

        # 用户输入框
        self.input_box = TextEdit()

        self.input_box.setPlaceholderText(self.tr("发报内容将显示在此处"))

        self.input_box.setReadOnly(True)  # 设置为只读

        self.vbox_test.addWidget(self.input_box)

        self.cursor_inputbox = self.input_box.textCursor()

        self.input_box.setFont(font)


        #正确答案框
        self.correct_answer_box = TextEdit()

        self.correct_answer_box.setReadOnly(True)  # 设置为只读

        self.correct_answer_box.setPlaceholderText(self.tr("答案将显示在此处"))

        self.cursor_answerbox = QTextCursor(self.correct_answer_box.document())

        self.correct_answer_box.setFont(font)

        self.vbox_test.addWidget(self.correct_answer_box)


        #水平布局（按钮 + 准确率标签）
        self.hbox_controls = QHBoxLayout()
        

        #准确率显示标签
        self.accuracy_label = QLabel(self.tr("正确率: 0%"))

        #self.hbox_controls.addWidget(self.accuracy_label)


        #准确率圆环进度条
        self.accuracy_progressRing = ProgressRing(self)

        self.accuracy_progressRing.setFixedSize(40,40)

        self.accuracy_progressRing.setVisible(False)

        self.hbox_controls.addWidget(self.accuracy_progressRing)


        #发报按钮
        self.CW_button = PushButton(FIF.SEND, self.tr("点击发报"), self)

        #发报按钮槽函数按下
        self.CW_button.pressed.connect(self.on_btn_send_message_pressed)
        #发报按钮槽函数松开
        self.CW_button.released.connect(self.on_btn_send_message_released)

        self.hbox_controls.addWidget(self.CW_button)


        #检查结果按钮
        self.check_button = PushButton(FIF.SYNC, self.tr("随机出题"), self)

        self.check_button.clicked.connect(self.question_check_button_click)

        self.hbox_controls.addWidget(self.check_button)


        #将按钮行加入主右侧布局
        self.vbox_test.addLayout(self.hbox_controls)


        #将左右两个布局添加到 splitter 中

        splitter.addWidget(self.left_widget)

        splitter.addWidget(self.right_widget)


        #设置初始比例，右侧内容较大

        splitter.setStretchFactor(1, 2)
        

        #添加 splitter 到主布局

        self.layout_main.addWidget(splitter)


    def init_variable(self):

        #当前课程的字符

        self.current_lesson_char = []

        #当前课程句子

        self.current_lesson_sentences = ""


        #初始化摩斯助手（随机字符生成器）

        self.helper = MorseLearnHelper()

        #初始化翻译器

        self.translator = MorseCodeTranslator()

        #初始化蜂鸣器

        self.buzzer = BuzzerSimulator()

        #初始化配置文件助手

        self.configer = ConfigManager()


        #初始化数据库工具

        self.db_tool = DatabaseTool()


        #初始化当前课程的内容数组

        self.current_lesson_array = ""


        #初始化当前课程主学内容

        self.current_lesson_core_element = ""


        #当前课程进度

        self.current_lesson_progress = ""


    def init_setting(self):

        """初始化一些设置的东西"""

        self.lesson_type = self.get_lesson_type(self.combo_lesson_type.currentIndex())

        self.update_list(self.lesson_type)

        #初始化发报相关
        self.initSend()
        

    def on_item_clicked(self, item):

        """列表点击事件"""
        #清理所有输入框
        self.clean_all_text_box()

        #还原出题按键
        self.check_button.setText(self.tr("随机出题"))
        self.check_button.setIcon(FIF.SYNC)


        self.current_lesson_array = item.data(Qt.UserRole+1)

        #设置课程标题
        self.current_lesson_button.setText(f"{item.text()}")

        #设置当前课程核心元素，核心元素占大比重

        self.current_lesson_core_element = item.data(Qt.UserRole+5)

        #获取当前课程进度

        self.current_lesson_progress = self.db_tool.get_progress_by_title(self.current_lesson_core_element)

        #设置当前课程的进度

        #print(int(self.current_lesson_progress))

        self.accuracy_progressRing.setTextVisible(True)

        self.accuracy_progressRing.setVisible(True)

        self.accuracy_progressRing.setValue(self.current_lesson_progress)


        #设置两个输入框都为空

        self.input_box.setText("")

        self.correct_answer_box.setText("")


        #清空当前课程句子

        self.current_lesson_sentences = ""

    def question_check_button_click(self):
        if self.current_lesson_array:
            btn_text = self.check_button.text()
            if btn_text == self.tr("随机出题"):
                self.clean_all_text_box()
                self.current_lesson_sentences = self.get_morse_code_question()
                self.check_button.setText(self.tr("查看结果"))
                self.check_button.setIcon(FIF.SEARCH)
            else:
                self.check_button.setText(self.tr("随机出题"))
                self.check_button.setIcon(FIF.SYNC)
                self.check_result()
        else:
            self.createInfoInfoBar(self.tr("提示"), self.tr("请先选择课程"))





    def check_result(self):
        """检查用户输入结果"""

        if self.question_morse_code != "":
            self.correct_answer_box.clear()

            input_text = self.input_box.toPlainText()

            # 定义摩尔斯符号单元，包括单个字符和 '///'，以分隔符 `/` 和 `///` 进行分隔
            def split_by_separator(text):
                units = []
                i = 0
                while i < len(text):
                    if text[i:i+3] == "///":
                        units.append("///")
                        i += 3
                    elif text[i] == "/":
                        units.append("/")
                        i += 1
                    else:
                        # 处理被分隔符分隔的内容
                        segment = ""
                        while i < len(text) and text[i] not in ["/", "///"]:
                            segment += text[i]
                            i += 1
                        units.append(segment)
                return units

            # 分别提取用户输入和标准答案的摩尔斯符号单元
            answer_units = split_by_separator(self.question_morse_code)
            input_units = split_by_separator(input_text)

            formatted_answer = ""
            highlighted_input = ""

            # 对比每个符号单元
            for i in range(max(len(answer_units), len(input_units))):
                if i < len(answer_units):
                    # 如果用户有输入对应位置
                    if i < len(input_units):
                        if input_units[i] == answer_units[i]:
                            # 分隔符和被分隔内容均一致
                            formatted_answer += answer_units[i]
                            highlighted_input += input_units[i]
                        else:
                            # 分隔符或内容不一致，标记为错误
                            formatted_answer += f"<span style='background-color:yellow;'>{answer_units[i]}</span>"
                            highlighted_input += f"<span style='background-color:yellow;'>{input_units[i]}</span>"
                    else:
                        # 用户未输入的部分，用浅色高亮表示
                        formatted_answer += f"<span style='background-color:lightgray;'>{answer_units[i]}</span>"
                else:
                    # 用户多余输入的部分，标红显示
                    highlighted_input += f"<span style='background-color:orange;'>{input_units[i]}</span>"

            # 设置正确答案框显示
            self.correct_answer_box.setHtml(formatted_answer)

            # 设置用户输入框显示
            self.input_box.setHtml(highlighted_input)

            # 计算正确字符数
            correct_chars = sum(1 for i in range(min(len(input_units), len(answer_units)))
                                if input_units[i] == answer_units[i])

            # 计算准确率并显示
            accuracy = (correct_chars / len(answer_units)) * 100 if len(answer_units) > 0 else 0
            self.accuracy_progressRing.setValue(int(accuracy))

            # 更新数据库状态
            if accuracy > 90:
                self.db_tool.update_status_by_title(self.current_lesson_core_element, 1)
            else:
                self.db_tool.update_status_by_title(self.current_lesson_core_element, 0)

            self.db_tool.update_progress_by_title(self.current_lesson_core_element, int(accuracy))

        else:
            self.input_box.setText("")
            self.createInfoInfoBar(self.tr("提示"), self.tr("请先选择课程！"))

        self.update_list(self.lesson_type)







    def get_morse_code_question(self):

        """拼凑字符"""
        
        if self.lesson_type and self.current_lesson_array != "":

            #获取随机句子

            random_sentence = self.helper.generate_random_data( self.current_lesson_array.split(","), 

                                                                self.lesson_type,

                                                                self.current_lesson_core_element,

                                                                self.configer.get_listen_weight(),

                                                                self.configer.get_min_word_length(),

                                                                self.configer.get_max_word_length(),

                                                                self.configer.get_min_groups(),

                                                                self.configer.get_max_groups()
                                                                )

            self.question_morse_code = self.translator.text_to_morse(random_sentence)

            self.current_lesson_sentences = random_sentence
            self.question_box.setText(f'{self.tr("Question: ")}{self.current_lesson_sentences}')
            print(self.question_morse_code)
        


    def on_select(self, index):

        """下拉选框变更事件"""

        self.lesson_type = self.get_lesson_type(self.combo_lesson_type.currentIndex())

        self.update_list(self.lesson_type)


    def update_list(self, lesson_type):
        """Update list"""
        self.list_widget.clear()  # Clear existing items
        lessons = self.db_tool.get_listening_lessons_by_type(lesson_type)

        for index, lesson in enumerate(lessons):
            title = lesson.get("title", self.tr("no"))  # "Untitled"
            content = lesson.get("content", self.tr("no content"))  # "No content"

            item = QListWidgetItem(f'Lesson {index+1}: {title}')  # "Lesson {index+1}: {title}"
            item.setData(Qt.UserRole, lesson.get("type", self.tr("no type")))  # "No type"
            item.setData(Qt.UserRole + 1, content)  # Set content data
            item.setData(Qt.UserRole + 2, lesson.get("note", self.tr("no note")))  # "No note"
            item.setData(Qt.UserRole + 3, lesson.get("status", 0))  # Set status data
            item.setData(Qt.UserRole + 4, lesson.get("progress", 0))  # Set progress data
            item.setData(Qt.UserRole + 5, title)  # Set title data

            # Check if status is 1
            if lesson.get("status") == 1:
                item.setBackground(QColor(144, 238, 144))  # Set background to light green

            self.list_widget.addItem(item)


    

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
    

    
    def lesson_titel_click(self):
        '''Event triggered when the course title is clicked'''
        if self.current_lesson_array != "":
            self.createInfoInfoBar(self.tr("提示"), f"{self.tr('当前课程:')} {self.translator.letter_to_morse_code(self.current_lesson_core_element)}", InfoBarPosition.TOP)

    def clean_all_text_box(self):
        '''Clear all text boxes'''
        self.input_box.setText("")
        self.question_box.setText("")
        self.correct_answer_box.setText("")
        # Also clear the Morse code
        self.morse_code = ""

    
    

    def createInfoInfoBar(self, title, content, position=InfoBarPosition.BOTTOM):

        content = content

        w = InfoBar(

            icon=InfoBarIcon.INFORMATION,

            title= title,

            content=content,

            orient=Qt.Vertical,    # vertical layout

            isClosable=True,

            position=position,

            duration=2000,

            parent=self
        )

        w.show()


    '''以下皆和发报有关'''
    def initSend(self):
         # 发报相关参数
        self.start_time = None

        self.morse_code = ""

        self.morse_code_received = ""

        self.morse_code_translation = ""  # 翻译后的摩斯密码字母串（带空格）

        self.received_translation = ""  # 翻译后的摩斯密码字母串（带空格）

        self.dot_duration = int(self.configer.get_dot_time())
        
        self.dash_duration =  int(self.configer.get_dash_time())

        self.dot = "."

        self.dash = "-" 

        self.pressed_keys_autokey = set()

        self.timer_autokey = QTimer(self)

        self.timer_autokey.timeout.connect(self.handle_timer_autokey_timeout)

        #self.interval = 100

        self.current_char_autokey = None

        self.is_sending_autokey = False  # 标志符，表示是否正在发送字符        

        self.is_key_pressed = False

        self.letter_interval_duration = int(self.configer.get_letter_interval_duration_time())  # 字母间隔

        self.word_interval_duration = int(self.configer.get_word_interval_duration_time())  # 单词间隔

        self.autokey_status = self.configer.get_autokey_status()#是否开启自动键模式TURE,FALSE

        self.send_buzz_status = self.configer.get_send_buzz_status()

        self.receive_buzz_status = self.configer.get_receive_buzz_status()
        
        
        # 计时器
        self.gap_time = None

        #字母间隔计时器
        self.letter_timer = QTimer(self)

        self.letter_timer.setSingleShot(True)

        self.letter_timer.timeout.connect(self.handle_letter_timeout)

        #单词间隔计时器
        self.word_timer = QTimer(self)

        self.word_timer.setSingleShot(True)

        self.word_timer.timeout.connect(self.handle_word_timeout)

        #获取保存在配置文件中的两个按键，示例格式"23,12"
        self.saved_key = self.configer.get_keyborad_key().split(',')


    #发报按钮按下事件
    def on_btn_send_message_pressed(self):
        if self.current_lesson_sentences != "":
            if not self.is_key_pressed:
                #修改按钮图标
                self.CW_button.setIcon(FIF.SEND_FILL)
                
                # 蜂鸣器响
                self.buzzer.start(self.send_buzz_status)

                self.start_time = time.time()

                self.is_key_pressed = True

                # 当检测到鼠标继续点击时关闭之前的计时器
                self.word_timer.stop()
                self.letter_timer.stop()
        else:
            self.createInfoInfoBar(self.tr("Tip"), self.tr("请先随机出题!"))
            

    #发报按钮松开事件
    def on_btn_send_message_released(self):
        if self.is_key_pressed:
            #修改按钮图标
            self.CW_button.setIcon(FIF.SEND)
        
            # 蜂鸣器停
            self.buzzer.stop()
            self.pressed_keys_time = (time.time() - self.start_time) * 1000
            
            morse_code = self.determine_morse_character(self.pressed_keys_time)
            
            #将消息发送到服务器
            self.update_sent_label(morse_code)
            
            self.is_key_pressed = False
            
            self.start_letter_timer()

    
    
    #键盘按键触发发报
    def keyPressEvent(self, event):
        """监听键盘按下事件"""
        if not event.isAutoRepeat():
            #判断自动键还是手动
            if not self.autokey_status:
                #手动键
                if event.key() == int(self.saved_key[0]):
                    # 先判断是否可以发射
                    if not self.current_lesson_sentences:
                        #可发射
                        if not self.is_key_pressed:

                            #蜂鸣器响
                            self.buzzer.start(self.send_buzz_status)
                            self.start_time = time.time()
                            self.is_key_pressed = True
                            # 当检测到继续点击时关闭之前的计时器
                            self.word_timer.stop()
                            self.letter_timer.stop()
            else:
                #自动键
                #第一个按键为dot，第二个按键为dash
                if event.key() == int(self.saved_key[0]):
                    self.pressed_keys_autokey.add(int(self.saved_key[0]))
                    if not self.is_sending_autokey:  # 如果没有正在发送
                        self.current_char_autokey = self.dot

                        #处理自动键超时
                        if not self.timer_autokey.isActive():
                            self.handle_timer_autokey_timeout()
                            self.timer_autokey.start(self.dot_duration)
                        self.is_sending_autokey = True

                elif event.key() == int(self.saved_key[1]):
                    self.pressed_keys_autokey.add(int(self.saved_key[1]))
                    if not self.is_sending_autokey:  # 如果没有正在发送
                        self.current_char_autokey = self.dash
                        #处理自动键超时
                        if not self.timer_autokey.isActive():
                            self.handle_timer_autokey_timeout()
                            self.timer_autokey.start(self.dash_duration)
                        self.is_sending_autokey = True
                        # 当检测到继续点击时关闭之前的计时器
                self.word_timer.stop()
                self.letter_timer.stop()


    #键盘松开事件
    def keyReleaseEvent(self, event):
        """键盘监听按键松开事件"""
        if not event.isAutoRepeat():   
            #判断自动键还是手动
            if not self.autokey_status:
                #手动键     
                if self.is_key_pressed:

                    #蜂鸣器停
                    self.buzzer.stop()

                    self.pressed_keys_time = (time.time() - self.start_time) * 1000

                    morse_code = self.determine_morse_character(self.pressed_keys_time)

                    #发送消息至服务器
                    self.update_sent_label(morse_code)

                    self.is_key_pressed = False
                    self.start_letter_timer()
                    
                    #设置按键按下时间以及按下状态
                    self.last_key_pressed_status = True
                    self.last_key_pressed_time = time.time()
            else:

                #如果是自动键

                if event.key() in self.pressed_keys_autokey:


                    self.pressed_keys_autokey.remove(event.key())


                    if event.key() == int(self.saved_key[0]) or event.key() == int(self.saved_key[1]):


                        if not self.pressed_keys_autokey:  # 如果没有其他键被按下


                            self.timer_autokey.stop()


                            self.buzzer.stop_play_for_duration()


                            self.current_char_autokey = None


                            self.is_sending_autokey = False  # 重置发送标志
                            self.start_letter_timer()


    #自动键的超时处理函数
    #关于自动键超时与音频播放备注，
    #自动键超时事件其实是这个按键按下的持续时间，
    #用以判断长按时一段时间内应该响应多少次。
    #而音频播放是否跟手，与其播放时间是否小于超时判断时间正相关
    def handle_timer_autokey_timeout(self):
       #print("自动键")
        if self.current_char_autokey:
            # 交替发送字符状态标志
            if self.current_char_autokey == self.dot:
                #蜂鸣器
                self.buzzer.play_for_duration(50,self.send_buzz_status)

                #再启动一个计时器
                self.timer_autokey.start(self.dot_duration)
                if int(self.saved_key[1]) in self.pressed_keys_autokey:  # 如果 E 键仍然被按下
                    self.current_char_autokey = self.dash  # 切换到划
                else:
                    self.current_char_autokey = self.dot  # 保持点
            else:
                self.timer_autokey.start(self.dash_duration)

                #蜂鸣器
                self.buzzer.play_for_duration(80,self.send_buzz_status)

                if int(self.saved_key[0]) in self.pressed_keys_autokey:  # 如果 W 键仍然被按下
                    self.current_char_autokey = self.dot  # 切换到点
                else:
                    self.current_char_autokey = self.dash  # 保持划
            
            #判断当前字符是点还是划，然后发送对应消息至服务器
            if self.current_char_autokey == self.dot:
                self.update_sent_label(self.current_char_autokey)
            elif self.current_char_autokey == self.dash:
                self.update_sent_label(self.current_char_autokey)



    # 分辨是点还是划
    def determine_morse_character(self, duration):
        '''根据按键时间长短判断是点还是划'''
        if duration < self.dot_duration:
            return "."
        else:
            return "-"


    # 将数据发送至服务，并更新到UI界面
    def update_sent_label(self, morse_code):

        # 显示到屏幕
        self.morse_code += morse_code
        self.input_box.setText(self.morse_code)


    #启动字符间隔计时器
    def start_letter_timer(self):
        self.letter_timer.start(self.letter_interval_duration)



    #启动单词间隔计时器
    def start_word_timer(self):
        self.word_timer.start(self.word_interval_duration)




    def handle_letter_timeout(self):
        # 如果字母计时器超时，添加字母间隔符
        self.morse_code += "/"
        self.input_box.setText(self.morse_code)

        self.start_word_timer()  # 启动单词计时器
        # 翻译为字母
        extracted_mores_code = self.extract_cleaned_parts(self.morse_code)
        self.morse_code_translation_temp = self.translator.letter_to_morse(extracted_mores_code)
        self.morse_code_translation += self.morse_code_translation_temp


    def handle_word_timeout(self):
        # 如果单词计时器超时，添加单词间隔符
        self.morse_code += "//"
        self.input_box.setText(self.morse_code)
        # 判断服务器已连接，才发送

        self.morse_code_translation += " "

    
    # 将字母中的单个反斜杠筛选掉,使用多维数组的方式，///为分组，/为元素分割
    def extract_cleaned_parts(self, input_data):
        """
        从输入数据中提取并清理部分，支持多维数组。
        使用 '///' 区分组，使用 '/' 区分组内元素。
        :param input_data: 输入字符串或多维数组
        :return: 清理后的结果，分组为列表
        """
        if isinstance(input_data, str):
            # 如果是字符串，处理并返回清理后的组
            if input_data.endswith("/"):
                input_data = input_data[:-1]
            # 使用正则表达式筛选出有效的摩斯电码字符
            cleaned_str = re.sub(r"[^.\-/]", "", input_data)
            # 按 '///' 分组，并进一步按 '//' 分隔组内元素
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
        return []  # 如果输入既不是字符串也不是列表，返回空列表
    