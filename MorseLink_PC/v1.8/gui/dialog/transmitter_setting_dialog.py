from PyQt5.QtWidgets import QDialog, QVBoxLayout, QLabel, QHBoxLayout, QSpacerItem, QSizePolicy, QSlider
from PyQt5.QtGui import QDoubleValidator
from PyQt5.QtCore import Qt
from utils.config_manager import ConfigManager
from qfluentwidgets import PushButton

class TransmitterSettingDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(self.tr("设置"))  # 设置窗口标题
        self.setGeometry(100, 100, 400, 300)  # 设置窗口大小和位置

        # 初始化配置管理器
        self.config_manager = ConfigManager()

        # 初始化一些变量
        self.dot_time = self.config_manager.get_dot_time()  # 获取点持续时间
        self.dash_length = self.config_manager.get_dash_time()  # 获取划长度
        self.letter_interval = self.config_manager.get_letter_interval_duration_time()  # 获取字母间隔
        self.word_interval = self.config_manager.get_word_interval_duration_time()  # 获取单词间隔
        self.wpm = self.config_manager.get_wpm()  # 获取发报键速

        # 初始化UI
        self.initUI()
        self.initSetting()

    def initUI(self):
        # 主布局
        self.main_vbox = QVBoxLayout()

        # 点间隔设置布局
        self.dot_interval_hbox = QHBoxLayout()
        self.current_dot_time_text = self.tr("当前点长度: ")
        self.label_current_dot_time = QLabel(f'{self.current_dot_time_text}  {self.dot_time} 毫秒')
        self.label_dot_time = QLabel(f"{self.dot_time} 毫秒")  # 使用 QLabel 替代 LineEdit

        # 将控件添加到点间隔布局
        self.dot_interval_hbox.addWidget(self.label_current_dot_time)
        self.dot_interval_hbox.addWidget(self.label_dot_time)

        # 划长度设置布局
        self.dash_length_hbox = QHBoxLayout()
        self.current_dash_length_text = self.tr("当前划长度: ")
        self.label_current_dash_length = QLabel(f"{self.current_dash_length_text} {self.dash_length} 毫秒")
        self.label_dash_length = QLabel(f"{self.dash_length} 毫秒")  # 使用 QLabel 替代 LineEdit

        # 将控件添加到划长度布局
        self.dash_length_hbox.addWidget(self.label_current_dash_length)
        self.dash_length_hbox.addWidget(self.label_dash_length)

        # 字母间隔设置布局
        self.letter_interval_hbox = QHBoxLayout()
        Current_Letter_Interval = self.tr("当前字母间隔: ")
        self.label_current_letter_interval = QLabel(f"{Current_Letter_Interval}  {self.letter_interval} 毫秒")
        self.label_letter_interval = QLabel(f"{self.letter_interval} 毫秒")  # 使用 QLabel 替代 LineEdit

        # 将控件添加到字母间隔布局
        self.letter_interval_hbox.addWidget(self.label_current_letter_interval)
        self.letter_interval_hbox.addWidget(self.label_letter_interval)

        # 单词间隔设置布局
        self.word_interval_hbox = QHBoxLayout()
        Current_Word_Interval = self.tr(f"当前单词间隔: ")
        self.label_current_word_interval = QLabel(f"{Current_Word_Interval}  {self.word_interval} 毫秒")
        self.label_word_interval = QLabel(f"{self.word_interval} 毫秒")  # 使用 QLabel 替代 LineEdit

        # 将控件添加到单词间隔布局
        self.word_interval_hbox.addWidget(self.label_current_word_interval)
        self.word_interval_hbox.addWidget(self.label_word_interval)

        # WPM 设置布局
        self.wpm_hbox = QHBoxLayout()
        self.label_current_wpm = QLabel(self.tr("WPM 速率:"))
        
        # 使用 QSlider 替代 LineEdit
        self.slider_wpm = QSlider(Qt.Horizontal, self)
        self.slider_wpm.setMinimum(5)  # 设置最小 WPM 值
        self.slider_wpm.setMaximum(60)  # 设置最大 WPM 值
        self.slider_wpm.setValue(self.wpm)  # 设置当前 WPM 值
        self.slider_wpm.valueChanged.connect(self.update_values_from_slider)  # 连接值变化信号

        # 添加一个标签显示当前 WPM 值
        self.label_wpm_value = QLabel(f"{self.wpm} WPM")
        self.label_wpm_value.setAlignment(Qt.AlignCenter)  # 居中对齐

        # 将控件添加到 WPM 布局
        self.wpm_hbox.addWidget(self.label_current_wpm)
        self.wpm_hbox.addWidget(self.slider_wpm)
        self.wpm_hbox.addWidget(self.label_wpm_value)

        # 确认和取消按钮
        self.final_hbox = QHBoxLayout()
        self.btn_cancel = PushButton(self.tr("取消设置"))
        self.btn_save = PushButton(self.tr("保存设置"))
        self.btn_save.clicked.connect(self.save)
        self.btn_cancel.clicked.connect(self.cancel)

        spacer = QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)
        self.final_hbox.addItem(spacer)
        self.final_hbox.addWidget(self.btn_cancel)
        self.final_hbox.addWidget(self.btn_save)

        # 将所有布局添加到主布局
        self.main_vbox.addLayout(self.dot_interval_hbox)
        self.main_vbox.addLayout(self.dash_length_hbox)
        self.main_vbox.addLayout(self.letter_interval_hbox)
        self.main_vbox.addLayout(self.word_interval_hbox)
        self.main_vbox.addLayout(self.wpm_hbox)
        self.main_vbox.addLayout(self.final_hbox)

        self.setLayout(self.main_vbox)

    def initSetting(self):
        self.key_one = ''
        self.key_two = ''

    def update_values_from_slider(self):
        # 获取滑动条的当前值
        wpm = self.slider_wpm.value()
        
        # 更新 WPM 值标签
        self.label_wpm_value.setText(f"{wpm} WPM")
        
        # 计算 dot_time（以毫秒为单位）
        self.dot_time = round(6 / (5 * wpm) * 1000)  # 转换为毫秒并四舍五入
        
        # 计算其他值并四舍五入
        self.dash_length = round(3 * self.dot_time)
        self.letter_interval = round(3 * self.dot_time)
        self.word_interval = round(7 * self.dot_time)
        
        # 更新标签
        self.label_dot_time.setText(f"{self.dot_time} 毫秒")
        self.label_dash_length.setText(f"{self.dash_length} 毫秒")
        self.label_letter_interval.setText(f"{self.letter_interval} 毫秒")
        self.label_word_interval.setText(f"{self.word_interval} 毫秒")

    def save(self):
        # 获取并保存 WPM
        self.wpm = self.slider_wpm.value()
        self.config_manager.set_wpm(self.wpm)

        # 保存其他值
        self.config_manager.set_dot_time(self.dot_time)
        self.config_manager.set_dash_time(self.dash_length)
        self.config_manager.set_letter_interval_duration_time(self.letter_interval)
        self.config_manager.set_word_interval_duration_time(self.word_interval)

        self.accept()  # 关闭对话框
    
    def cancel(self):
        self.accept()