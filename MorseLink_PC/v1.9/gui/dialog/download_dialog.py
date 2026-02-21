from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel
from ui_widgets import ProgressBar, PushButton


class DownloadDialog(QDialog):
    def __init__(self, title, message):
        super().__init__()
        self.setWindowTitle(title)

        
        # 创建布局
        self.layout = QVBoxLayout(self)
        
        # 创建文本标签
        self.label = QLabel(message, self)
        self.layout.addWidget(self.label)
        
        # 创建进度条
        self.progress_bar = ProgressBar(self)
        self.progress_bar.setRange(0, 100)  # 设置进度范围
        self.layout.addWidget(self.progress_bar)
        
        # 创建关闭按钮
        self.close_button = PushButton(self.tr("Close"), self)
        self.close_button.clicked.connect(self.close)
        self.layout.addWidget(self.close_button)
        
        self.setLayout(self.layout)

    def update_progress(self, value):
        """更新进度条的值"""
        self.progress_bar.setValue(value)

