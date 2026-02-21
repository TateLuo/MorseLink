import time
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QDialog,
    QStackedWidget,
    QSizePolicy,
)
from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices, QAction, QActionGroup
from ui_widgets import InfoBarPosition, InfoBar, InfoBarIcon

# 瀵煎叆鑷畾涔夋ā鍧?
from gui.dialog.my_call_dialog import MyCallDialog
from gui.dialog.general_setting_dialog import GeneralSettingDialog
from gui.dialog.about_dialog import AboutDialog
from gui.dialog.qso_record_dialog import QsoRecordDialog
from gui.dialog.key_modifier_dialog import KeyModifierDialog
from gui.dialog.transmitter_setting_dialog import TransmitterSettingDialog
from gui.dialog.server_setting_dialog import ServerSettingDialog
from utils.config_manager import ConfigManager
from utils.multi_tablet_tool import MultiTableTool
from gui.windows.qso_online import QSOOline
from gui.windows.training_home import TrainingHome


class MainUI(QMainWindow):
    """主窗口类，负责应用程序的主界面和功能管理。"""

    DEFAULT_WIDTH = 1200
    DEFAULT_HEIGHT = 760
    MIN_UI_SCALE = 0.75
    MAX_UI_SCALE = 1.65
    
    def __init__(self, context=None):
        """初始化主窗口"""
        super().__init__()
        self.context = context

        # 窗口初始化
        self.resize(self.DEFAULT_WIDTH, self.DEFAULT_HEIGHT)
        self.setMinimumSize(self.DEFAULT_WIDTH, self.DEFAULT_HEIGHT)
        self.center()

        # 缩放相关参数
        self.last_resize_time = 0
        self.resize_interval = 0.1
        self._current_ui_scale = 1.0
        self._base_menu_font_size = None

        # 配置管理
        self.config_manager = self.context.config_manager if self.context else ConfigManager()
        self.setWindowTitle(f"MorseLink_{self.config_manager.get_current_version()}")

        # 初始化界面
        self.init_ui()
        self._apply_ui_scale(self._compute_ui_scale())

    def center(self):
        """将窗口居中显示。"""
        screen = QApplication.primaryScreen().availableGeometry()  # 获取屏幕尺寸
        size = self.geometry()                      # 获取窗口尺寸

        # 计算居中坐标
        self.center_point_x = int((screen.width() - size.width()) / 2)
        self.center_point_y = int((screen.height() - size.height()) / 2)
        self.move(self.center_point_x, self.center_point_y)

    def init_ui(self):
        """Initialize main UI pages and menu."""
        self.create_menu_bar()

        self.stackedWidget = QStackedWidget(self)
        self.stackedWidget.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)
        self.setCentralWidget(self.stackedWidget)

        self.page_morsechat = QSOOline(self.stackedWidget, context=self.context)
        self.page_training_home = TrainingHome(self.stackedWidget, context=self.context)

        for page in (self.page_morsechat, self.page_training_home):
            page.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)
            page.setMinimumSize(0, 0)
            self.stackedWidget.addWidget(page)

        self.table_tool_morse_code = MultiTableTool("morse_code")
        self.table_tool_communication_words = MultiTableTool("communication_words")

    def create_menu_bar(self):
        """创建菜单栏及其相关操作。"""
        menu_bar = self.menuBar()

        # ========================== 设置菜单 ==========================
        menu_setting = menu_bar.addMenu(self.tr("设置"))

        # 鍛煎彿鍜屽瘑鐮佽缃?
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

        # 鏈嶅姟鍣ㄨ缃?
        server_setting_action = QAction(self.tr("服务器设置"), self)
        server_setting_action.triggered.connect(self.server_setting)
        menu_setting.addAction(server_setting_action)

        # 连接器设置
        key_modifier_action = QAction(self.tr("MorseLink连接器设置"), self)
        key_modifier_action.triggered.connect(self.morse_key_modifty_setting)
        menu_setting.addAction(key_modifier_action)

        # ========================== 主功能菜单 ==========================
        # QSO记录查看
        qso_record_action = QAction(self.tr("QSO记录"), self)
        qso_record_action.triggered.connect(self.check_qso)
        menu_bar.addAction(qso_record_action)

        # 页面切换操作
        self.change_view_OSQ_action = QAction(self.tr("在线通联"), self)
        self.change_view_OSQ_action.triggered.connect(self.change_view_OSQ)
        menu_bar.addAction(self.change_view_OSQ_action)

        self.change_view_training_action = QAction(self.tr("开始训练"), self)
        self.change_view_training_action.triggered.connect(self.change_view_training)
        menu_bar.addAction(self.change_view_training_action)

        # ========================== 帮助菜单 ==========================
        help_menu = menu_bar.addMenu(self.tr("帮助"))
        
        # 常用短语
        common_phrases_action = QAction(self.tr("常用短语"), self)
        common_phrases_action.triggered.connect(self.show_common_phrases_action)
        help_menu.addAction(common_phrases_action)

        # 电码参考表
        reference_table_action = QAction(self.tr("参考表"), self)
        reference_table_action.triggered.connect(self.show_reference_table_action)
        help_menu.addAction(reference_table_action)

        # 使用说明
        manual_action = QAction(self.tr("使用说明"), self)
        manual_action.triggered.connect(self.show_manual_action)
        help_menu.addAction(manual_action)

        # 关于页面
        about_action = QAction(self.tr("关于"), self)
        about_action.triggered.connect(self.about)
        menu_bar.addAction(about_action)

    def clean_screen(self):
        """清理屏幕显示内容。"""
        self.edit_morse_code.setText("")
        self.edit_morse_received.setText("")
        self.edit_send_translation.setText("")
        self.edit_received_translation.setText("")
        self.morse_code_translation = ""
        self.morse_code = ""

    def about(self):
        """显示关于对话框。"""
        dialog = AboutDialog(self)
        dialog.move(self.center_point_x, self.center_point_y)
        dialog.exec()

    def check_qso(self):
        """显示QSO通联记录对话框。"""
        qso = QsoRecordDialog()
        qso.move(self.center_point_x, self.center_point_y)
        qso.exec()

    def _safe_close_buzzer(self, buzzer):
        if buzzer and hasattr(buzzer, "close"):
            try:
                buzzer.close()
            except Exception:
                pass

    def _refresh_send_runtime_pages(self):
        for page in (self.page_morsechat, self.page_training_home):
            refresh = getattr(page, "_refresh_send_runtime", None)
            if callable(refresh):
                refresh()
                continue
            refresh = getattr(page, "refresh_send_runtime", None)
            if callable(refresh):
                refresh()

    def _recreate_runtime_buzzers(self):
        online_old = getattr(self.page_morsechat, "buzz", None)
        if self.context and hasattr(self.context, "recreate_buzzer"):
            online_new = self.context.recreate_buzzer()
        else:
            online_new = self.page_morsechat.create_buzzer()
        self.page_morsechat.buzz = online_new
        tx_runtime = getattr(self.page_morsechat, "tx_runtime", None)
        if tx_runtime is not None:
            tx_runtime.buzzer = online_new

        processor = getattr(self.page_morsechat, "receive_message_processor", None)
        channels = getattr(processor, "channels", None)
        if isinstance(channels, dict):
            for channel in channels.values():
                channel.buzz = online_new
        if online_old is not online_new:
            self._safe_close_buzzer(online_old)

        recreate = getattr(self.page_training_home, "recreate_buzzers", None)
        if callable(recreate):
            recreate()

    def _apply_general_settings_immediately(self):
        self._refresh_send_runtime_pages()
        self.page_morsechat.is_translation_visible()
        self.page_morsechat.set_my_call()
        self.page_morsechat.set_visualizer_visibility()
        self.page_morsechat.set_font_size()
        self._recreate_runtime_buzzers()
    
    def my_call_setting(self):
        dialog = MyCallDialog(self)
        dialog.move(self.center_point_x, self.center_point_y)
        if dialog.exec() == QDialog.Accepted:
            self.page_morsechat.set_my_call()

    def general_setting(self):
        """处理通用设置。"""
        dialog = GeneralSettingDialog(self)
        dialog.move(self.center_point_x, self.center_point_y)
        if dialog.exec() == QDialog.Accepted:
            self._apply_general_settings_immediately()

    def transmitter_setting(self):
        """处理发射设置。"""
        dialog = TransmitterSettingDialog(self)
        dialog.move(self.center_point_x, self.center_point_y)
        if dialog.exec() == QDialog.Accepted:
            self._refresh_send_runtime_pages()

    def server_setting(self):
        """处理服务器设置。"""
        dialog = ServerSettingDialog(self)
        dialog.move(self.center_point_x, self.center_point_y)
        if dialog.exec() == QDialog.Accepted:
            self.config_manager.sync()

    def morse_key_modifty_setting(self):
        """显示连接器设置对话框。"""
        dialog = KeyModifierDialog(self)
        dialog.move(self.center_point_x, self.center_point_y)
        dialog.exec()

    def show_common_phrases_action(self):
        """显示常用短语对照表。"""
        self.table_tool_communication_words.show()

    def show_reference_table_action(self):
        """显示摩尔斯电码参考表。"""
        self.table_tool_morse_code.show()
   
    def show_manual_action(self):
        """显示使用说明。"""
        # 使用默认浏览器跳转到指定网址
        url = QUrl("https://github.com/TateLuo/MorseLink/wiki")
        QDesktopServices.openUrl(url)
        

    def change_view_OSQ(self):
        """切换到在线通联界面。"""
        self.stackedWidget.setCurrentIndex(0)

    def change_view_training(self):
        """切换到训练主界面。"""
        self.stackedWidget.setCurrentIndex(1)

    def resizeEvent(self, event):
        """处理窗口大小调整事件。"""
        current_time = time.time()
        if current_time - self.last_resize_time > self.resize_interval:
            self.resize_morse_visualizer(event)
            self._apply_ui_scale(self._compute_ui_scale(event.size()))
            self.last_resize_time = current_time
        event.accept()

    def _compute_ui_scale(self, size=None) -> float:
        size = size if size is not None else self.size()
        scale_w = size.width() / float(self.DEFAULT_WIDTH)
        scale_h = size.height() / float(self.DEFAULT_HEIGHT)
        scale = min(scale_w, scale_h)
        return max(self.MIN_UI_SCALE, min(self.MAX_UI_SCALE, scale))

    def _apply_ui_scale(self, scale: float):
        if abs(scale - self._current_ui_scale) < 0.02:
            return
        self._current_ui_scale = scale
        self._apply_menu_scale(scale)
        for page in (self.page_morsechat, self.page_training_home):
            if hasattr(page, "apply_ui_scale"):
                page.apply_ui_scale(scale)

    def _apply_menu_scale(self, scale: float):
        menu_bar = self.menuBar()
        if self._base_menu_font_size is None:
            base = menu_bar.font().pointSizeF()
            self._base_menu_font_size = base if base > 0 else 10.0
        font = menu_bar.font()
        font.setPointSizeF(max(9.0, self._base_menu_font_size * scale))
        menu_bar.setFont(font)
        for action in menu_bar.actions():
            action.setFont(font)
            menu = action.menu()
            if menu:
                menu.setFont(font)
                for sub_action in menu.actions():
                    sub_action.setFont(font)

    def resize_morse_visualizer(self, event):
        """调整摩尔斯可视化组件大小。"""
        new_height = event.size().height()
        if new_height != self.height:
            pass
    def closeEvent(self, event):
        """处理窗口关闭事件。"""
        stop_training = getattr(self.page_training_home, "stop_training", None)
        if callable(stop_training):
            stop_training()

        unique_buzzers = []
        seen_ids = set()
        for buzzer in (
            getattr(self.page_morsechat, "buzz", None),
            getattr(getattr(self.page_training_home, "rx_runner", None), "buzzer", None),
            getattr(getattr(self.page_training_home, "tx_runner", None), "buzzer", None),
            getattr(getattr(self.page_training_home, "page_tutorial", None), "buzzer", None),
        ):
            if buzzer is None:
                continue
            marker = id(buzzer)
            if marker in seen_ids:
                continue
            seen_ids.add(marker)
            unique_buzzers.append(buzzer)

        for buzzer in unique_buzzers:
            if buzzer and hasattr(buzzer, "close"):
                try:
                    buzzer.close()
                except Exception:
                    pass
        if hasattr(self, "page_morsechat") and getattr(self.page_morsechat, "client", None):
            self.page_morsechat.client.close()
        super().closeEvent(event)

    def create_info_bar(self, title, content, position=InfoBarPosition.BOTTOM):
        """创建信息提示条。"""
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




