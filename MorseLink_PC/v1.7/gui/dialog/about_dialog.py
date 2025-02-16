from PyQt5.QtWidgets import QDialog, QVBoxLayout, QLabel, QTextBrowser, QWidget
from PyQt5.QtGui import QFont, QIcon
from PyQt5.QtCore import Qt
from utils.config_manager import ConfigManager


class AboutDialog(QDialog):
    """关于对话框，展示软件版本信息和开发者联系方式"""
    
    def __init__(self, parent=None):
        """
        初始化关于对话框
        
        Args:
            parent (QWidget): 父级窗口组件，默认为None
        """
        super().__init__(parent)

        # 窗口基础设置
        self.setWindowTitle(self.tr("关于"))
        self.setGeometry(100, 100, 400, 200)
        self.configer = ConfigManager()

        # 初始化界面布局
        self.init_ui()

    def init_ui(self):
        """初始化用户界面组件"""
        # 创建主布局
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(10, 10, 10, 10)  # 设置外边距
        main_layout.setSpacing(10)                      # 设置组件间距

        # 添加标题标签
        title_label = QLabel(self.tr("关于 MorseLink"))
        title_label.setFont(QFont("Arial", 16, QFont.Bold))
        main_layout.addWidget(title_label)

        # 创建背景容器（实现半透明效果）
        background_widget = self.create_background_widget()
        main_layout.addWidget(background_widget)

        self.setLayout(main_layout)

    def create_background_widget(self):
        """
        创建带半透明背景的内容容器
        
        Returns:
            QWidget: 包含说明内容的背景部件
        """
        # 背景容器设置
        container = QWidget()
        container.setStyleSheet("""
            background-color: rgba(200, 200, 200, 180);
            border-radius: 10px;
        """)
        container.setFixedSize(380, 150)

        # 创建文本浏览器组件
        text_browser = self.create_text_browser()
        
        # 设置容器布局
        container_layout = QVBoxLayout(container)
        container_layout.addWidget(text_browser)

        return container

    def create_text_browser(self):
        """
        创建说明文本浏览器
        
        Returns:
            QTextBrowser: 包含版本信息和联系方式的文本组件
        """
        browser = QTextBrowser()
        browser.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)  # 禁用垂直滚动条
        browser.setOpenExternalLinks(True)                        # 允许打开外部链接
        browser.setStyleSheet("background: transparent;")         # 透明背景
        browser.setFont(QFont("Arial", 12))

        # 设置HTML内容
        browser.setHtml(f"""
            <p>MorseLink 由 BI4MOL 业余时间开发，欢迎通过 GitHub 提交建议或加入微信交流群。</p>
            <p>GitHub 主页: 
                <a href='https://github.com/TateLuo/morsechat'>GitHub</a>
            </p>
            <p>QRZ 主页: 
                <a href='https://www.qrz.com/db/BI4MOL'>QRZ</a>
            </p>
            <p>HamCQ 论坛主页: 
                <a href='https://forum.hamcq.cn/u/4790'>HamCQ</a>
            </p>
            <p>软件版本: {self.configer.get_current_version()}</p>
        """)
        return browser

    def save(self):
        """保存设置并关闭对话框（保留接口供后续扩展使用）"""
        self.accept()