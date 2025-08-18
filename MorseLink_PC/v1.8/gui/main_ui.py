import time
import os
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QAction, QDialog,
    QDesktopWidget, 
    QStackedWidget,
    
)
from PyQt5.QtCore import Qt, QUrl
from PyQt5.QtGui import QDesktopServices
from qfluentwidgets import InfoBarPosition, InfoBar, InfoBarIcon

# 导入自定义模块
from gui.dialog.my_call_dialog import MyCallDialog
from gui.dialog.general_setting_dialog import GeneralSettingDialog
from gui.dialog.about_dialog import AboutDialog
from gui.dialog.qso_record_dialog import QsoRecordDialog
from gui.dialog.key_modifier_dialog import KeyModifierDialog
from gui.dialog.transmitter_setting_dialog import TransmitterSettingDialog
from gui.dialog.lesson_setting_dialog import LessonSettingDialog
from gui.dialog.server_setting_dialog import ServerSettingDialog
from utils.sound import BuzzerSimulator
from utils.config_manager import ConfigManager
from utils.multi_tablet_tool import MultiTableTool
from gui.windows.qso_online import QSOOline
from gui.windows.learn_listen import LearnListen
from gui.windows.learn_send import LearnSend
from utils.download_thread import DownloadHelper


class MainUI(QMainWindow):
    """主窗口类，负责应用程序的主要界面和功能管理"""
    
    def __init__(self):
        """初始化主窗口"""
        super().__init__()
        
        # 窗口初始化设置
        self.resize(800, 600)
        self.center()
        
        # 窗口调整相关参数
        self.last_resize_time = 0    # 记录上次调整大小的时间
        self.resize_interval = 0.1   # 调整间隔时间（秒）

        # 初始化配置管理器
        self.config_manager = ConfigManager()
        self.setWindowTitle(f"MorseLink_{self.config_manager.get_current_version()}")

        # 初始化界面组件
        self.init_ui()

        # 检查首次运行状态
        self.check_first_run()

    def center(self):
        """将窗口居中显示"""
        screen = QDesktopWidget().screenGeometry()  # 获取屏幕尺寸
        size = self.geometry()                      # 获取窗口尺寸

        # 计算居中坐标
        self.center_point_x = int((screen.width() - size.width()) / 2)
        self.center_point_y = int((screen.height() - size.height()) / 2)
        self.move(self.center_point_x, self.center_point_y)

    def init_ui(self):
        """初始化用户界面组件"""
        # 设置中心部件
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)

        # 创建菜单栏
        self.create_menu_bar()

        # 创建堆叠窗口组件
        self.stackedWidget = QStackedWidget(self)
        self.setCentralWidget(self.stackedWidget)

        # 初始化各功能页面
        self.page_morsechat = QSOOline(self.stackedWidget)      # 莫尔斯聊天页面
        self.page_learn_listen = LearnListen(self.stackedWidget)     # 听力训练页面
        self.page_learn_send = LearnSend(self.stackedWidget)         # 发报训练页面

        # 将页面添加到堆叠组件
        self.stackedWidget.addWidget(self.page_morsechat)
        self.stackedWidget.addWidget(self.page_learn_listen)
        self.stackedWidget.addWidget(self.page_learn_send)

        # 初始化帮助工具页面（需在主线程创建）
        self.table_tool_morse_code = MultiTableTool("morse_code")
        self.table_tool_communication_words = MultiTableTool("communication_words")

    def create_menu_bar(self):
        """创建菜单栏及其相关操作"""
        menu_bar = self.menuBar()

        # ========================== 设置菜单 ==========================
        menu_setting = menu_bar.addMenu(self.tr("设置"))

        # 呼号和密码设置
        my_call_setting_action = QAction(self.tr("呼号和密码设置"), self)
        my_call_setting_action.triggered.connect(self.my_call_setting)
        menu_setting.addAction(my_call_setting_action)
        
        # 通用设置
        general_setting_action = QAction(self.tr("一般设置"), self)
        general_setting_action.triggered.connect(self.general_setting)
        menu_setting.addAction(general_setting_action)

        # 发射设置
        transmitter_setting_action = QAction(self.tr("发射设置"), self)
        transmitter_setting_action.triggered.connect(self.transmitter_setting)
        menu_setting.addAction(transmitter_setting_action)

        # 课程设置
        lesson_setting_action = QAction(self.tr("课程设置"), self)
        lesson_setting_action.triggered.connect(self.listening_setting)
        menu_setting.addAction(lesson_setting_action)

        # 服务器设置
        server_setting_action = QAction(self.tr("服务器设置"), self)
        server_setting_action.triggered.connect(self.server_setting)
        menu_setting.addAction(server_setting_action)

        # 连接器设置
        key_modifier_action = QAction(self.tr("MorseLink连接器设置"), self)
        key_modifier_action.triggered.connect(self.morse_key_modifty_setting)
        menu_setting.addAction(key_modifier_action)

        # ========================== 主要功能菜单 ==========================
        # QSO记录查看
        qso_record_action = QAction(self.tr("QSO记录"), self)
        qso_record_action.triggered.connect(self.check_qso)
        menu_bar.addAction(qso_record_action)

        # 界面切换操作
        self.change_view_OSQ_action = QAction(self.tr("在线通联"), self)
        self.change_view_OSQ_action.triggered.connect(self.change_view_OSQ)
        menu_bar.addAction(self.change_view_OSQ_action)

        self.change_view_listen_action = QAction(self.tr("听力训练"), self)
        self.change_view_listen_action.triggered.connect(self.change_view_listen)
        menu_bar.addAction(self.change_view_listen_action)

        self.change_view_send_action = QAction(self.tr("发报训练"), self)
        self.change_view_send_action.triggered.connect(self.change_view_send)
        menu_bar.addAction(self.change_view_send_action)

        # ========================== 帮助菜单 ==========================
        help_menu = menu_bar.addMenu(self.tr("帮助"))
        
        # 常用短语表
        common_phrases_action = QAction(self.tr("常用短语"), self)
        common_phrases_action.triggered.connect(self.show_common_phrases_action)
        help_menu.addAction(common_phrases_action)

        # 电码参照表
        reference_table_action = QAction(self.tr("参照表"), self)
        reference_table_action.triggered.connect(self.show_reference_table_action)
        help_menu.addAction(reference_table_action)

        #使用说明
        manual_action = QAction(self.tr("使用说明"), self)
        manual_action.triggered.connect(self.show_manual_action)
        help_menu.addAction(manual_action)

        # 关于页面
        about_action = QAction(self.tr("关于"), self)
        about_action.triggered.connect(self.about)
        menu_bar.addAction(about_action)

    def clean_screen(self):
        """清理屏幕显示内容"""
        self.edit_morse_code.setText("")
        self.edit_morse_received.setText("")
        self.edit_send_translation.setText("")
        self.edit_received_translation.setText("")
        self.morse_code_translation = ""
        self.morse_code = ""

    def about(self):
        """显示关于对话框"""
        dialog = AboutDialog(self)
        dialog.move(self.center_point_x, self.center_point_y)
        dialog.exec_()

    def check_qso(self):
        """显示QSO通联记录对话框"""
        qso = QsoRecordDialog()
        qso.move(self.center_point_x, self.center_point_y)
        qso.exec()
    
    def my_call_setting(self):
        dialog = MyCallDialog(self)
        dialog.move(self.center_point_x, self.center_point_y)
        if dialog.exec_() == QDialog.Accepted:
            pass

    def general_setting(self):
        """处理通用设置"""
        dialog = GeneralSettingDialog(self)
        dialog.move(self.center_point_x, self.center_point_y)
        if dialog.exec_() == QDialog.Accepted:
            # 更新点时间间隔设置
            self.page_morsechat.dot_duration = int(self.config_manager.get_dot_time())
            
            # 更新界面显示相关设置
            self.page_morsechat.is_translation_visible()
            
            # 更新自动键状态
            autokey_status = self.config_manager.get_autokey_status()
            self.page_morsechat.autokey_status = autokey_status
            self.page_learn_send.autokey_status = autokey_status
            
            # 更新蜂鸣器状态
            send_buzz_status = self.config_manager.get_send_buzz_status()
            self.page_morsechat.send_buzz_status = send_buzz_status
            self.page_learn_listen.send_buzz_status = send_buzz_status
            self.page_learn_send.send_buzz_status = send_buzz_status
            self.page_morsechat.receive_buzz_status = self.config_manager.get_receive_buzz_status()
            
            # 更新键盘键位设置
            keyboard_keys = self.config_manager.get_keyborad_key().split(',')
            self.page_morsechat.saved_key = keyboard_keys
            self.page_learn_send.saved_key = keyboard_keys
            
            # 更新呼号信息
            self.page_morsechat.set_my_call()
            
            # 更新可视化组件显示状态
            self.page_morsechat.set_visualizer_visibility()
            
            # 重新初始化蜂鸣器
            self.page_morsechat.buzz = BuzzerSimulator()
            self.page_learn_listen.buzzer = BuzzerSimulator()
            self.page_learn_send.buzzer = BuzzerSimulator()
            
            # 更新字体大小设置
            self.page_morsechat.set_font_size()

    def transmitter_setting(self):
        """处理发射设置"""
        dialog = TransmitterSettingDialog(self)
        dialog.move(self.center_point_x, self.center_point_y)
        if dialog.exec_() == QDialog.Accepted:
            # 更新莫尔斯码时间参数
            self.page_morsechat.dot_duration = int(self.config_manager.get_dot_time())
            self.page_morsechat.dash_duration = self.config_manager.get_dash_time()
            self.page_morsechat.letter_interval_duration = self.config_manager.get_letter_interval_duration_time()
            self.page_morsechat.word_interval_duration = self.config_manager.get_word_interval_duration_time()

    def listening_setting(self):
        """处理听力课程设置"""
        dialog = LessonSettingDialog(self)
        dialog.move(self.center_point_x, self.center_point_y)
        dialog.exec_()

    def server_setting(self):
        """处理服务器设置"""
        dialog = ServerSettingDialog(self)
        dialog.move(self.center_point_x, self.center_point_y)
        dialog.exec_()

    def morse_key_modifty_setting(self):
        """显示电键连接器设置对话框"""
        dialog = KeyModifierDialog(self)
        dialog.move(self.center_point_x, self.center_point_y)
        dialog.exec_()

    def show_common_phrases_action(self):
        """显示常用短语对照表"""
        self.table_tool_communication_words.show()

    def show_reference_table_action(self):
        """显示莫尔斯电码参照表"""
        self.table_tool_morse_code.show()
   
    def show_manual_action(self):
        """显示使用说明"""
        # 使用默认浏览器跳转到指定网址
        url = QUrl("https://github.com/TateLuo/MorseLink/wiki")  # 替换为你的网址
        QDesktopServices.openUrl(url)
        

    def change_view_OSQ(self):
        """切换到在线通联界面"""
        self.stackedWidget.setCurrentIndex(0)

    def change_view_listen(self):
        """切换到听力训练界面"""
        self.stackedWidget.setCurrentIndex(1)

    def change_view_send(self):
        """切换到发报训练界面"""
        self.stackedWidget.setCurrentIndex(2)

    def resizeEvent(self, event):
        """处理窗口大小调整事件"""
        current_time = time.time()
        if current_time - self.last_resize_time > self.resize_interval:
            self.resize_morse_visualizer(event)
            self.last_resize_time = current_time
        event.accept()

    def resize_morse_visualizer(self, event):
        """调整莫尔斯码可视化组件大小"""
        new_height = event.size().height()
        if new_height != self.height:
            pass  # 实际调整逻辑需要根据具体实现补充
            # 示例：self.page_morsechat.morsecode_visualizer.set_height(new_height)

    def check_first_run(self):
        """检查首次运行状态并执行初始化操作"""
        if self.config_manager.get_first_run_status():
            self.download_helper = DownloadHelper()
            self.download_helper.start_download("database")

    def closeEvent(self, event):
        """处理窗口关闭事件"""
        if self.page_learn_listen.buzzer.is_playing:
            self.page_learn_listen.buzzer.stop_playing_morse_code()
        super().closeEvent(event)

    def create_info_bar(self, title, content, position=InfoBarPosition.BOTTOM):
        """创建信息提示条
        
        Args:
            title (str): 提示标题
            content (str): 提示内容
            position (InfoBarPosition): 显示位置，默认为底部
        """
        InfoBar(
            icon=InfoBarIcon.INFORMATION,
            title=title,
            content=content,
            orient=Qt.Vertical,
            isClosable=True,
            position=position,
            duration=2000,
            parent=self
        ).show()