import sys
import requests
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QLabel, QLineEdit, QTextEdit, QPushButton, QCheckBox, QMessageBox

class UpdateManager(QWidget):
    def __init__(self, server_ip):
        super().__init__()
        self.server_url = f'http://117.72.10.141:5000/version'
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle('更新公告管理')

        layout = QVBoxLayout()

        # 版本输入
        self.version_label = QLabel('版本:')
        self.version_input = QLineEdit()
        layout.addWidget(self.version_label)
        layout.addWidget(self.version_input)

        # 下载链接输入
        self.download_label = QLabel('下载链接:')
        self.download_input = QLineEdit()
        layout.addWidget(self.download_label)
        layout.addWidget(self.download_input)

        # 公告内容输入
        self.announcement_label = QLabel('公告内容:')
        self.announcement_input = QTextEdit()
        layout.addWidget(self.announcement_label)
        layout.addWidget(self.announcement_input)

        # 是否更新
        self.is_update_checkbox = QCheckBox('是否有更新')
        layout.addWidget(self.is_update_checkbox)

        # 是否展示公告
        self.show_announcement_checkbox = QCheckBox('是否展示公告')
        layout.addWidget(self.show_announcement_checkbox)

        # 提交按钮
        self.submit_button = QPushButton('提交')
        self.submit_button.clicked.connect(self.submit_update_info)
        layout.addWidget(self.submit_button)

        self.setLayout(layout)

    def submit_update_info(self):
        version = self.version_input.text().strip()
        download_url = self.download_input.text().strip()
        announcement = self.announcement_input.toPlainText().strip()
        is_update_available = self.is_update_checkbox.isChecked()
        show_announcement = self.show_announcement_checkbox.isChecked()

        # 校验输入数据
        '''
        if not version or not download_url or not announcement:
            QMessageBox.warning(self, '输入错误', '版本、下载链接和公告内容不能为空！')
            return
        '''
        
        # 创建要发送的数据
        data = {
            'version': version,
            'downloadurl': download_url,
            'announcement': announcement,
            'is_update_available': is_update_available,
            'show_announcement': show_announcement
        }

        # 发送更新请求
        try:
            response = requests.post(self.server_url, json=data)
            if response.status_code == 200:
                QMessageBox.information(self, '成功', '更新公告已成功提交！')
            else:
                QMessageBox.warning(self, '失败', '提交失败，请检查服务器状态！')
        except Exception as e:
            QMessageBox.critical(self, '错误', f'发生错误: {str(e)}')

if __name__ == "__main__":
    app = QApplication(sys.argv)
    server_ip = '127.0.0.1'  # 服务器 IP
    manager = UpdateManager(server_ip)
    manager.show()
    sys.exit(app.exec_())
