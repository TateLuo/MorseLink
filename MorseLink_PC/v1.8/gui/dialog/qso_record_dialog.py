# -*- coding: utf-8 -*-
"""
模块名称：QSO记录管理对话框
功能说明：实现通信记录(QSO)的查看、删除和摩尔斯电码可视化功能
"""

from PyQt5.QtWidgets import (QDialog, QListWidgetItem, QVBoxLayout, QAction,
                             QListWidget, QGraphicsView, QGraphicsScene, QGraphicsRectItem)
from PyQt5.QtCore import Qt
from utils.database_tool import DatabaseTool
from utils.translator import MorseCodeTranslator
from qfluentwidgets import RoundMenu


class QsoRecordDialog(QDialog):
    """QSO记录管理对话框"""

    def __init__(self, parent=None):
        """
        初始化记录对话框
        :param parent: 父窗口对象
        """
        super().__init__(parent)
        # 窗口基本设置
        self.setWindowTitle(self.tr("QSO Records"))
        self.setGeometry(100, 100, 500, 400)

        # 工具类初始化
        self.db_tool = DatabaseTool()       # 数据库操作工具
        self.translator = MorseCodeTranslator()  # 摩尔斯电码转换器

        # UI初始化
        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self):
        """初始化用户界面组件"""
        # 创建记录列表控件
        self.list_widget = QListWidget(self)
        self.list_widget.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.list_widget.setStyleSheet("background-color: rgba(255, 255, 255, 0); border: none;")

        # 主布局设置
        layout = QVBoxLayout()
        layout.addWidget(self.list_widget)
        self.setLayout(layout)

        # 加载初始数据
        self._load_records()

    def _connect_signals(self):
        """连接信号与槽"""
        self.list_widget.setContextMenuPolicy(Qt.CustomContextMenu)
        self.list_widget.customContextMenuRequested.connect(self._show_context_menu)

    def _load_records(self):
        """从数据库加载通信记录"""
        records = self.db_tool.read_qso_record()
        if not records:
            self.list_widget.addItem(self.tr("未找到记录."))
            return

        for record in records:
            self._add_record_item(record)

    def _add_record_item(self, record):
        """
        添加单个记录到列表
        :param record: 记录字典，包含id和data字段
        """
        record_data = record["data"]
        item_text = self._format_record_text(record_data)
        
        # 创建列表项
        list_item = QListWidgetItem(item_text)
        list_item.setData(Qt.UserRole, record["id"])                # 存储记录ID
        list_item.setData(Qt.UserRole + 1, record_data["message"])  # 存储原始电码

        # 存储播放时间数据（如果存在）
        if "play_time" in record_data:
            list_item.setData(Qt.UserRole + 2, record_data["play_time"])
            list_item.setData(Qt.UserRole + 3, record_data["play_time_interval"])

        self.list_widget.addItem(list_item)

    def _format_record_text(self, record_data):
        """
        格式化记录显示文本
        :param record_data: 记录数据字典
        :return: 格式化后的字符串
        """
        # 时间格式化处理
        time_str = record_data["time"][:16]  # 截取前16个字符
        duration = f"00:{int(record_data['duration']):02d}"  # 持续时间格式化
        
        # 消息内容处理
        message = self.translator.morse_to_text(record_data['message'])
        direction = record_data['direction']
        
        # 构建显示文本
        if "sender" in record_data:
            return f"{time_str} {duration}\n[{direction}] [{record_data['sender']}] {message}"
        return f"{time_str} {duration}\n[{direction}] {message}"

    def _show_context_menu(self, position):
        """显示右键上下文菜单"""
        item = self.list_widget.itemAt(position)
        if not item:
            return

        # 创建圆形菜单
        menu = RoundMenu(self)
        self._add_menu_actions(menu, item)
        menu.exec_(self.list_widget.viewport().mapToGlobal(position))

    def _add_menu_actions(self, menu, item):
        """为菜单添加操作项"""
        # 删除操作
        delete_action = QAction(self.tr("删除"), self)
        delete_action.triggered.connect(lambda: self._delete_record(item))
        menu.addAction(delete_action)

        # 显示电码操作
        show_morse_action = QAction(self.tr("显示为电码"), self)
        show_morse_action.triggered.connect(lambda: self._display_as_morse(item))
        menu.addAction(show_morse_action)

        # 可视化操作
        visual_action = QAction(self.tr("电码可视化"), self)
        visual_action.triggered.connect(lambda: self._visualize_morse(item))
        menu.addAction(visual_action)

        # 取消操作
        cancel_action = QAction(self.tr("取消"), self)
        cancel_action.triggered.connect(menu.close)
        menu.addAction(cancel_action)

    def _delete_record(self, item):
        """删除选中的记录"""
        row = self.list_widget.row(item)
        self.list_widget.takeItem(row)
        record_id = item.data(Qt.UserRole)
        self.db_tool.delete_qso_record_by_id(record_id)

    def _display_as_morse(self, item):
        """显示原始摩尔斯电码"""
        original_text = item.text()
        morsecode = item.data(Qt.UserRole + 1)
        modified_text = self._replace_message_with_morse(original_text, morsecode)
        item.setText(modified_text)
        self.list_widget.update()

    def _visualize_morse(self, item):
        """显示电码可视化窗口"""
        if "Send" in item.text():
            play_time = str(item.data(Qt.UserRole + 2)).split(",")
            intervals = str(item.data(Qt.UserRole + 3)).split(",")
            self._show_waterfall_graph(play_time, intervals)
        self.list_widget.update()

    def _replace_message_with_morse(self, original, morsecode):
        """
        将消息替换为原始摩尔斯电码
        :param original: 原始显示文本
        :param morsecode: 摩尔斯电码字符串
        :return: 修改后的显示文本
        """
        lines = original.split('\n')
        if len(lines) < 2:
            return self.tr("输入字符串少于两行")

        # 查找最后一个']'位置
        index = lines[1].rfind(']')
        if index != -1:
            new_line = lines[1][:index+1] + morsecode
        else:
            new_line = lines[1]

        return f"{lines[0]}\n{new_line}"

    def _show_waterfall_graph(self, lengths, distances):
        """显示瀑布流图对话框"""
        window = WaterfallGraph(lengths, distances)
        window.exec_()


class WaterfallGraph(QDialog):
    """摩尔斯电码可视化对话框"""

    def __init__(self, lengths, distances):
        """
        初始化可视化窗口
        :param lengths: 信号长度列表
        :param distances: 信号间隔列表
        """
        super().__init__()
        # 窗口基本设置
        self.setGeometry(100, 100, 650, 400)
        self.setWindowTitle(self.tr("电码可视化"))

        # 初始化图形界面
        self._setup_visualization(lengths, distances)

    def _setup_visualization(self, lengths, distances):
        """设置可视化组件"""
        self.scene = QGraphicsScene()
        self.view = QGraphicsView(self.scene)
        self.view.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOn)

        # 绘制信号矩形
        self._draw_signal_blocks(lengths, distances)

        # 设置布局
        layout = QVBoxLayout()
        layout.addWidget(self.view)
        self.setLayout(layout)

    def _draw_signal_blocks(self, lengths, distances):
        """
        绘制信号块图形
        :param lengths: 每个信号的长度列表
        :param distances: 信号之间的间隔列表
        """
        start_x = 0  # 初始绘制位置
        for length, distance in zip(lengths, distances):
            # 参数处理
            signal_length = int(float(length)) / 10
            signal_gap = int(float(distance)) / 10 if int(float(distance)) > 10 else 100

            # 创建矩形图形项
            rect_item = QGraphicsRectItem(
                start_x - signal_length,  # X位置（从右向左绘制）
                0,                        # Y位置
                signal_length,            # 宽度
                20                        # 高度
            )
            rect_item.setBrush(Qt.black)
            self.scene.addItem(rect_item)

            # 更新下一个信号的起始位置
            start_x += signal_length + signal_gap