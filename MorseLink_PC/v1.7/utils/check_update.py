import requests
import json
import webbrowser
from PyQt5.QtWidgets import QMessageBox, QApplication, QWidget
from packaging.version import Version
from utils.download_thread import DownloadHelper

class VersionChecker():
    def __init__(self, current_version, server_ip):
        self.current_version = Version(current_version)
        self.server_url = f'http://{server_ip}:5000/version'

    def check_update(self):
        try:
            resp = requests.get(self.server_url)
            resp.encoding = 'UTF-8'
            
            if resp.status_code != 200:
                return None  # 连接失败时返回 None
            
            data = resp.json()
            self.latest_version = Version(data.get('version'))
            download_url = data.get('downloadurl')
            announcement = data.get('announcement')
            is_update_available = data.get('is_update_available')
            show_announcement = data.get('show_announcement')

            # 检查版本更新
            if self.latest_version <= self.current_version:
                if show_announcement:
                    self.show_announcement(announcement)
                return None  # 版本正常，无需提示
            
            # 弹出选择框询问用户是否下载
            if self.ask_user_to_download(download_url):
                webbrowser.open(download_url)
                return f'跳转至下载页面: {download_url}'
            
            return None  # 用户选择不下载

        except json.JSONDecodeError:
            print("JSON解析失败，请检查响应数据格式。")  # 日志记录
            return None
        except Exception as e:
            print(f"发生错误: {e}")  # 日志记录
            return None

    def ask_user_to_download(self, download_url):
        # 创建选择框（修改为中文提示）
        reply = QMessageBox.question(
            None,
            "更新提示",
            f"发现新版本: {self.latest_version}\n是否要立即更新？",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        return reply == QMessageBox.Yes

    def show_announcement(self, announcement):
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Information)
        msg.setText(announcement)
        msg.setWindowTitle('系统公告')
        msg.setStandardButtons(QMessageBox.Ok)
        msg.button(QMessageBox.Ok).setText('确定')  # 修改按钮文字
        msg.exec_()  # 显示公告弹窗

# 使用示例
if __name__ == "__main__":
    app = QApplication([])
    current_version = '1.0.3'  # 当前版本
    server_ip = '127.0.0.1'   # 服务器 IP
    checker = VersionChecker(current_version, server_ip)
    checker.check_update()