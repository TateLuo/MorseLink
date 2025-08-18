from PyQt5.QtWidgets import QDialog, QVBoxLayout, QLabel, QHBoxLayout, QSpacerItem, QSizePolicy
from PyQt5.QtGui import QDoubleValidator
from utils.config_manager import ConfigManager
from qfluentwidgets import LineEdit, PushButton
from PyQt5.QtCore import Qt

from qfluentwidgets import LineEdit, PushButton, Slider

class LessonSettingDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(self.tr("设置"))  # 设置窗口标题
        self.setGeometry(100, 100, 400, 300)  # 设置窗口大小和位置

        # 初始化配置管理器
        self.config_manager = ConfigManager()

        # 初始化一些变量
        self.min_word_length = self.config_manager.get_min_word_length()  # 获取最小单词长度
        self.max_word_length = self.config_manager.get_max_word_length()  # 获取最大单词长度
        self.min_groups = self.config_manager.get_min_groups()  # 获取最小组数
        self.max_groups = self.config_manager.get_max_groups()  # 获取最大组数
        self.core_weight = self.config_manager.get_listen_weight()  # 获取核心权重

        # 初始化UI
        self.initUI()
        self.initSetting()

    def initUI(self):
        # 主布局
        self.main_vbox = QVBoxLayout()

        # 最小单词长度设置布局
        self.min_word_length_hbox = QHBoxLayout()
        Minimum_word_text = self.tr("生成单词的最小长度: ")
        self.label_current_min_word_length = QLabel(f"{Minimum_word_text}  {self.min_word_length} ")
        self.edit_min_word_length = LineEdit(self)
        self.edit_min_word_length.setPlaceholderText(self.tr("输入最小长度"))
        double_validator = QDoubleValidator(0, 100, 0)  # 允许整数输入
        self.edit_min_word_length.setValidator(double_validator)

        # 将控件添加到最小单词长度布局
        self.min_word_length_hbox.addWidget(self.label_current_min_word_length)
        self.min_word_length_hbox.addWidget(self.edit_min_word_length)

        # 最大单词长度设置布局
        self.max_word_length_hbox = QHBoxLayout()
        Maximum_word_text = self.tr(f"生成单词的最大长度: ")
        self.label_current_max_word_length = QLabel(f"{Maximum_word_text}  {self.max_word_length}")
        self.edit_max_word_length = LineEdit(self)
        self.edit_max_word_length.setPlaceholderText(self.tr("输入最大长度"))
        self.edit_max_word_length.setValidator(double_validator)

        # 将控件添加到最大单词长度布局
        self.max_word_length_hbox.addWidget(self.label_current_max_word_length)
        self.max_word_length_hbox.addWidget(self.edit_max_word_length)

        # 最小组数设置布局
        self.min_groups_hbox = QHBoxLayout()
        Minimum_number_text = self.tr(f"生成的最小组数: ")
        self.label_current_min_groups = QLabel(f"{Minimum_number_text}  {self.min_groups}")
        self.edit_min_groups = LineEdit(self)
        self.edit_min_groups.setPlaceholderText(self.tr("输入最小组数"))
        self.edit_min_groups.setValidator(double_validator)

        # 将控件添加到最小组数布局
        self.min_groups_hbox.addWidget(self.label_current_min_groups)
        self.min_groups_hbox.addWidget(self.edit_min_groups)

        # 最大组数设置布局
        self.max_groups_hbox = QHBoxLayout()
        Maximum_number_text = self.tr(f"生成的最大组数: ")
        self.label_current_max_groups = QLabel(f"{Maximum_number_text}  {self.max_groups}")
        self.edit_max_groups = LineEdit(self)
        self.edit_max_groups.setPlaceholderText(self.tr("输入最大组数"))
        self.edit_max_groups.setValidator(double_validator)

        # 将控件添加到最大组数布局
        self.max_groups_hbox.addWidget(self.label_current_max_groups)
        self.max_groups_hbox.addWidget(self.edit_max_groups)

        # 核心权重调整布局
        self.set_core_weight_hbox = QHBoxLayout()
        self.label_set_core_weight = QLabel(self.tr('核心权重 (0 到 1):'))
        self.slider_set_core_weight = Slider(Qt.Horizontal, self)
        self.slider_set_core_weight.setFixedWidth(200)
        self.slider_set_core_weight.setRange(0, 100)  # 设置范围从0到100
        self.slider_set_core_weight.setValue(50)  # 默认值为0.5
        self.slider_set_core_weight.valueChanged.connect(self.update_core_weight_label)

        self.label_current_core_weight = QLabel(self.tr('当前权重: 0.5'))

        self.set_core_weight_hbox.addWidget(self.label_set_core_weight)
        self.set_core_weight_hbox.addWidget(self.slider_set_core_weight)
        self.set_core_weight_hbox.addWidget(self.label_current_core_weight)

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
        self.main_vbox.addLayout(self.min_word_length_hbox)
        self.main_vbox.addLayout(self.max_word_length_hbox)
        self.main_vbox.addLayout(self.min_groups_hbox)
        self.main_vbox.addLayout(self.max_groups_hbox)
        self.main_vbox.addLayout(self.set_core_weight_hbox)
        self.main_vbox.addLayout(self.final_hbox)

        self.setLayout(self.main_vbox)

    def initSetting(self):
        # 初始化设置
        self.slider_set_core_weight.setValue(int(self.core_weight * 100))  # 设置滑块到核心权重

    # 更新权重标签的方法
    def update_core_weight_label(self):
        self.core_weight = self.slider_set_core_weight.value() / 100.0  # 转换为0到1之间的值
        Current_weight_text = self.tr(f'当前权重: ')
        self.label_current_core_weight.setText(f'{Current_weight_text} + {self.core_weight:.2f}')

    def save(self):
        # 保存设置
        if self.edit_min_word_length.text() != "":
            self.min_word_length = int(self.edit_min_word_length.text())
            self.config_manager.set_min_word_length(self.min_word_length)

        if self.edit_max_word_length.text() != "":
            self.max_word_length = int(self.edit_max_word_length.text())
            self.config_manager.set_max_word_length(self.max_word_length)

        if self.edit_min_groups.text() != "":
            self.min_groups = int(self.edit_min_groups.text())
            self.config_manager.set_min_groups(self.min_groups)

        if self.edit_max_groups.text() != "":
            self.max_groups = int(self.edit_max_groups.text())
            self.config_manager.set_max_groups(self.max_groups)

        # 保存核心权重
        self.config_manager.set_listen_weight(self.core_weight)

        self.accept()  # 关闭对话框

    def cancel(self):
        self.accept()  # 不保存设置，直接关闭对话框