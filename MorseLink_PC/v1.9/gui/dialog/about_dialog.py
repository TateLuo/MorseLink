from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QGuiApplication
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QTextBrowser,
    QVBoxLayout,
)

from utils.check_update import VersionChecker
from utils.config_manager import ConfigManager


class AboutDialog(QDialog):
    """About dialog with project links and quick actions."""

    REPO_URL = "https://github.com/TateLuo/MorseLink"
    RELEASES_URL = "https://github.com/TateLuo/MorseLink/releases"
    WIKI_URL = "https://github.com/TateLuo/MorseLink/wiki"

    def __init__(self, parent=None):
        super().__init__(parent)
        self.configer = ConfigManager()
        self.current_version = str(self.configer.get_current_version() or "0.0.0")

        self.setWindowTitle(self.tr("关于 MorseLink"))
        self.setMinimumSize(520, 360)
        self.resize(620, 420)
        self._init_ui()

    def _init_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 14, 16, 14)
        root.setSpacing(10)

        title = QLabel(f"MorseLink v{self.current_version}")
        title_font = QFont()
        title_font.setPointSize(18)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)

        subtitle = QLabel(
            self.tr("业余无线电通联训练与在线通联工具")
        )
        subtitle.setWordWrap(True)

        browser = QTextBrowser()
        browser.setOpenExternalLinks(True)
        browser.setStyleSheet("background: transparent; border: 1px solid rgba(0,0,0,0.12); border-radius: 8px;")
        browser.setHtml(
            f"""
            <p><b>{self.tr("项目链接")}</b></p>
            <ul>
              <li><a href="{self.REPO_URL}">{self.tr("GitHub 仓库")}</a></li>
              <li><a href="{self.RELEASES_URL}">Releases</a></li>
              <li><a href="{self.WIKI_URL}">{self.tr("Wiki 使用说明")}</a></li>
              <li><a href="https://www.qrz.com/db/BI4MOL">QRZ - BI4MOL</a></li>
            </ul>
            <p><b>{self.tr("当前版本")}</b>: v{self.current_version}</p>
            """
        )

        actions = QHBoxLayout()
        actions.setSpacing(8)

        btn_copy_ver = QPushButton(self.tr("复制版本号"))
        btn_copy_ver.clicked.connect(self._copy_version)

        btn_check_update = QPushButton(self.tr("检查更新"))
        btn_check_update.clicked.connect(self._check_update)

        btn_close = QPushButton(self.tr("关闭"))
        btn_close.clicked.connect(self.accept)
        btn_close.setDefault(True)

        actions.addWidget(btn_copy_ver)
        actions.addWidget(btn_check_update)
        actions.addStretch(1)
        actions.addWidget(btn_close)

        root.addWidget(title)
        root.addWidget(subtitle)
        root.addWidget(browser, 1)
        root.addLayout(actions)

    def _copy_version(self):
        QGuiApplication.clipboard().setText(self.current_version)
        QMessageBox.information(self, self.tr("提示"), self.tr("已复制版本号"))

    def _check_update(self):
        checker = VersionChecker(self.current_version)
        checker.check_update()
