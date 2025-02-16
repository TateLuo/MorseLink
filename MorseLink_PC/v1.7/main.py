import sys, os
from PyQt5.QtCore import QCoreApplication, Qt
from PyQt5.QtWidgets import QApplication
from gui.main_ui import MainUI
from PyQt5.QtGui import QIcon
from utils.qq import img
from utils.config_manager import ConfigManager 
import base64


def set_icon(QApplication):
    print("开始设置图标")   
    # 将import进来的icon.py里的数据转换成临时文件tmp.ico，作为图标s
    tmp = open("tmp.ico","wb+")  
    tmp.write(base64.b64decode(img))#写入到临时文件中
    tmp.close()
    app_icon = QIcon("tmp.ico")
    QApplication.setWindowIcon(app_icon) #设置图标
    os.remove("tmp.ico")

def set_version(version):
    configer = ConfigManager()
    configer.set_current_version(version)


if __name__ == '__main__':
    #为了支持高DPI的屏幕
    QCoreApplication.setAttribute(Qt.AA_EnableHighDpiScaling)
    #设置软件版本，作为在线更新的对比
    set_version("1.7.0")
    
    #实例化APP
    app = QApplication(sys.argv)
    set_icon(QApplication)

    
    ex = MainUI()
    ex.show()
    #关闭数据库连接
    #ex.database_tool.close()
    sys.exit(app.exec_())