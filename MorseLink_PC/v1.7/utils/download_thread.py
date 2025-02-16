import os
import requests
from PyQt5.QtWidgets import QMessageBox, QWidget
from PyQt5.QtCore import QThread, pyqtSignal
from utils.config_manager import ConfigManager
from gui.dialog.download_dialog import DownloadDialog

class DownloadHelper(QWidget):
    def __init__(self):
        super().__init__()
        self.config_manager = ConfigManager()
        # 修改对话框标题和成功提示为中文
        self.download_dialog = DownloadDialog(self.tr("下载中"), self.tr("下载成功！"))

    def start_download(self, API, version=""):
        """开始下载"""
        host = self.config_manager.get_server_url()
        url = f"http://{host}:5000/download/{API}"
        
        if API == 'newVersion':
            resources_dir = os.path.join(os.getcwd(),"resources")
            os.makedirs(resources_dir, exist_ok=True)
            save_path = os.path.join(resources_dir, f"MorseLink_{version}.exe")
            message = self.tr("发现新版本，是否下载？")
        elif API == "database":
            resources_dir = os.path.join(os.getcwd(), "resources", "database")
            os.makedirs(resources_dir, exist_ok=True)
            save_path = os.path.join(resources_dir, "database.db")
            message = self.tr("是否下载新数据库？这将重置您的现有数据！\n下载完成后请重启程序。")

        if os.path.exists(save_path):
            # 修改提示框内容为中文
            reply = QMessageBox.question(self, self.tr('提示'),
                                         message,
                                         QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if reply == QMessageBox.No:
                self.config_manager.set_first_run_status(False)
                return

        self.download_thread = DownloadThread(url, save_path)
        self.download_thread.progress.connect(self.update_progress)
        self.download_thread.finished.connect(self.download_finished)
        self.download_thread.start()

    def update_progress(self, value):
        self.download_dialog.show()
        self.download_dialog.update_progress(value)

    def download_finished(self, success):
        if success:
            self.download_dialog.close()
            self.config_manager.set_first_run_status(False)
            # 修改成功提示为中文
            QMessageBox.information(self, self.tr("成功"), self.tr("下载成功！"))
        else:
            # 修改错误提示为中文并修复拼写错误
            QMessageBox.critical(self, self.tr("错误"), self.tr("下载失败！"))

class DownloadThread(QThread):
    progress = pyqtSignal(int)
    finished = pyqtSignal(bool)

    def __init__(self, url, save_path):
        super().__init__()
        self.url = url
        self.save_path = save_path

    def run(self):
        try:
            response = requests.get(self.url, stream=True)
            response.raise_for_status()

            total_size = int(response.headers.get('content-length', 0))
            downloaded_size = 0

            with open(self.save_path, 'wb') as f:
                for data in response.iter_content(chunk_size=1024):
                    f.write(data)
                    downloaded_size += len(data)
                    progress = (downloaded_size / total_size) * 100
                    self.progress.emit(int(progress))

            self.finished.emit(True)
        except requests.exceptions.RequestException as e:
            print(f"下载失败: {e}")
            self.finished.emit(False)
        except Exception as e:
            print(f"发生错误: {e}")
            self.finished.emit(False)