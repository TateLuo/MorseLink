from PyQt5.QtCore import pyqtSignal, QObject

# 定义信号
class MySignal(QObject):
    process_received_signal = pyqtSignal(str)  # 发报界面，在回调中更新ui
    
    update_listen_progress_signal = pyqtSignal(int)  # 听力界面在回调中更新播放进度