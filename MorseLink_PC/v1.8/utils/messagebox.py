import sys

from PyQt5.QtCore import *
from PyQt5.QtGui import QColor, QIcon, QMovie, QMoveEvent
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QFrame, QHBoxLayout, QLabel, QPushButton, QGraphicsDropShadowEffect, \
    QApplication


def shadowEffect(obj):
    """
    边框阴影
    :param obj:
    :return:
    """
    shadow = QGraphicsDropShadowEffect()
    shadow.setBlurRadius(10)
    shadow.setColor(QColor(64, 64, 64))
    shadow.setOffset(0, 0)
    obj.setGraphicsEffect(shadow)


class MessageBox(QDialog):
    def __init__(self, *args, **kwargs):
        super(MessageBox, self).__init__(*args, **kwargs)
        self.resize(300, 80)
        self.setMinimumSize(300, 80)
        # Qt.Window 声明这是一个窗口，如果没有Qt会显示不出来
        # Qt.WindowType.FramelessWindowHint 去掉系统自带的边框
        # Qt.WindowType.WindowStaysOnTopHint 将窗口置于最上层
        self.setWindowFlags(Qt.Window | Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)  # 将界面属性设置为半透明

        self.setContentsMargins(5, 5, 5, 5)
        self.animation = None
        # 如果有父控件，弹框显示到父控件中间
        if self.parent():
            self.move(self.parent().frameGeometry().center().x() - self.frameGeometry().width() // 2,
                      self.parent().frameGeometry().center().y() - self.parent().height() // 2 + 100)

        self.setStyleSheet("*{\n"
                           "    font: 12pt \"黑体\";\n"
                           "}\n"
                           "#frame{\n"
                           "    background-color: rgb(0, 0, 0, 0.6);\n"
                           "    border-radius: 35px;\n"
                           "}\n"
                           "#label{\n"
                           "    background-color: none;\n"
                           "    border: none;\n"
                           "}\n"
                           "#pushButton{\n"
                           "    background-color: none;\n"
                           "    border: none;\n"
                           "    color: rgb(255, 255, 255, 0.8);\n"
                           "    text-align: center;\n"
                           "}")

        self.timer = QTimer()
        self.timer.timeout.connect(self.close)
        
        self.verticalLayout = QVBoxLayout(self)
        self.verticalLayout.setContentsMargins(0, 0, 0, 0)
        self.verticalLayout.setObjectName("verticalLayout")
        self.frame = QFrame(self)
        self.frame.setFrameShape(QFrame.StyledPanel)
        self.frame.setFrameShadow(QFrame.Raised)
        self.frame.setObjectName("frame")
        self.verticalLayout_2 = QVBoxLayout(self.frame)
        self.verticalLayout_2.setObjectName("verticalLayout_2")
        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.label = QLabel(self.frame)
        self.label.setMinimumSize(QSize(50, 50))
        self.label.setMaximumSize(QSize(50, 50))
        self.label.setObjectName("label")

        self.pushButton = QPushButton(self.frame)
        self.pushButton.setMinimumSize(QSize(200, 35))
        self.pushButton.setMaximumSize(QSize(10000, 30))
        self.pushButton.setObjectName("pushButton")

        self.verticalLayout_2.addLayout(self.horizontalLayout)
        self.verticalLayout.addWidget(self.frame)
        shadowEffect(self.frame)

        self.show()

    def closeEvent(self, event):
        """
        关闭动画
        :param event:
        :return:
        """
        if self.animation is None:
            self.animation = QPropertyAnimation(self, b'windowOpacity')
            self.animation.setDuration(1000)
            self.animation.setStartValue(1)
            self.animation.setEndValue(0)
            self.animation.finished.connect(self.close)
            self.animation.start()
            event.ignore()

    def addMsgIconAndText(self, icon: QIcon() = None, text: str = None):
        """
        添加图标和文本
        :param icon:
        :param text:
        :return:
        """
        if icon:
            self.pushButton.setIcon(icon)
            self.pushButton.setIconSize(QSize(50, 50))
        if text:
            self.pushButton.setText(text)
        self.pushButton.adjustSize()
        self.horizontalLayout.addWidget(self.pushButton)

    def addMsgGif(self, gif_path):
        """
        添加gif文件
        :param gif_path:
        :return:
        """
        movie = QMovie(gif_path)
        movie.setScaledSize(QSize(50, 50))
        self.label.setMovie(movie)
        movie.start()
        movie.setSpeed(100)
        self.horizontalLayout.addWidget(self.label)

    def setTimerMsec(self, msec: int):
        """
        设置自动关闭时间
        :param msec:
        :return:
        """
        self.timer.start(msec * 1000)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    win = MessageBox()
    win.addMsgIconAndText(text='测试')
    win.setTimerMsec(2)

    win.show()
    sys.exit(app.exec_())

