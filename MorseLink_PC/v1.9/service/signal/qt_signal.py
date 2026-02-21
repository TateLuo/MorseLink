from PySide6.QtCore import Signal, QObject

# 定义信号
class MySignal(QObject):
    process_received_signal = Signal(str)  # 发报界面，在回调中更新ui
    
    update_listen_progress_signal = Signal(int)  # 听力界面在回调中更新播放进度