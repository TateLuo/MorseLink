import sys
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QPushButton
from PyQt5.QtGui import QPainter, QColor, QBrush, QRadialGradient, QPen
from PyQt5.QtCore import Qt, QSize, QTimer


class SignalLightWidget(QWidget):
    """自定义信号灯控件，支持红绿状态切换和自动恢复功能"""
    
    def __init__(self, diameter=50):
        """
        初始化信号灯控件
        
        Args:
            diameter (int): 信号灯直径，默认50像素
        """
        super().__init__()
        self.light_state = 2    # 初始状态为绿灯 (2)
        self.padding = 5        # 灯光周围的内边距
        self.diameter = diameter  # 灯光直径
        
        # 初始化定时器
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.switch_to_green)

    def set_state(self, state):
        """
        设置信号灯状态
        
        Args:
            state (int): 
                1 - 红灯
                2 - 绿灯
                其他值 - 关闭状态
        """
        self.light_state = state
        self.update()

    def set_diameter(self, diameter):
        """
        设置灯光直径
        
        Args:
            diameter (int): 新的灯光直径（像素）
        """
        self.diameter = diameter
        self.update()

    def sizeHint(self):
        """返回控件的建议大小"""
        return QSize(self.diameter + 2 * self.padding, 
                    self.diameter + 2 * self.padding)

    def minimumSizeHint(self):
        """返回控件的最小建议大小"""
        return QSize(30, 30)

    def paintEvent(self, event):
        """执行控件绘制操作"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)  # 启用抗锯齿
        
        # 设置无边框画笔
        painter.setPen(QPen(Qt.NoPen))

        # 计算绘制参数
        widget_width = self.diameter
        widget_height = self.diameter
        radius = self.diameter // 2
        center_x = self.width() // 2
        center_y = self.height() // 2

        # 绘制深灰色背景（灯罩）
        dark_gray = QColor(50, 50, 50, 200)  # 半透明深灰色
        painter.setBrush(QBrush(dark_gray))
        painter.drawEllipse(center_x - radius, center_y - radius,
                           widget_width, widget_height)

        # 根据状态设置渐变效果
        gradient = QRadialGradient(center_x, center_y, radius)
        if self.light_state == 1:    # 红灯
            gradient.setColorAt(0, QColor(255, 0, 0, 255))  # 中心亮红色
            gradient.setColorAt(1, QColor(128, 0, 0, 50))   # 边缘暗红色
        elif self.light_state == 2:  # 绿灯
            gradient.setColorAt(0, QColor(0, 255, 0, 255))  # 中心亮绿色
            gradient.setColorAt(1, QColor(0, 128, 0, 50))   # 边缘暗绿色
        else:                        # 关闭状态
            gradient.setColorAt(0, QColor(50, 50, 50, 255))  # 中心深灰色
            gradient.setColorAt(1, QColor(30, 30, 30, 50))   # 边缘更暗灰色

        # 绘制主灯光
        painter.setBrush(QBrush(gradient))
        painter.drawEllipse(
            center_x - radius + self.padding,
            center_y - radius + self.padding,
            widget_width - 2 * self.padding,
            widget_height - 2 * self.padding
        )

        # 添加高光效果（模拟灯光反射）
        highlight_gradient = QRadialGradient(
            center_x - radius // 3, 
            center_y - radius // 3, 
            radius // 2
        )
        highlight_gradient.setColorAt(0, QColor(255, 255, 255, 100))  # 半透明白色
        highlight_gradient.setColorAt(1, QColor(255, 255, 255, 0))    # 渐变透明

        painter.setBrush(QBrush(highlight_gradient))
        painter.drawEllipse(
            center_x - radius + self.padding,
            center_y - radius + self.padding,
            (widget_width - 2 * self.padding) // 2,
            (widget_height - 2 * self.padding) // 2
        )

    def switch_to_green(self):
        """自动切换为绿灯状态并停止定时器"""
        self.set_state(2)
        self.timer.stop()

    def switch_to_red_for_duration(self, duration_ms):
        """
        切换为红灯并持续指定时间
        
        Args:
            duration_ms (int): 红灯持续时间（毫秒）
        """
        self.set_state(1)
        self.timer.start(duration_ms)