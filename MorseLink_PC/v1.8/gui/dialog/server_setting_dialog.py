from PyQt5.QtWidgets import QDialog, QVBoxLayout, QLabel, QHBoxLayout, QSpacerItem, QSizePolicy, QListWidget, QMenu, QAction, QInputDialog, QMessageBox
from qfluentwidgets import LineEdit, PushButton
from PyQt5.QtCore import Qt
from utils.config_manager import ConfigManager
import re


class ServerSettingDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(self.tr("服务器设置"))
        self.setGeometry(100, 100, 400, 400)

        # 初始化配置管理器
        self.config_manager = ConfigManager()

        # 获取服务器信息
        self.current_server = self.config_manager.get_server_url()
        self.servers_string = self.config_manager.get_server_customized_url()
        self.servers = []
        
        # 当前选中的服务器
        self.selected_server = self.current_server

        self.initUI()
        self.load_servers_list()  # 加载服务器列表
    
    def initUI(self):
        # 主布局
        self.main_vbox = QVBoxLayout()
        self.main_vbox.setSpacing(15)
        
        # 1. 当前选择的服务器
        self.current_server_layout = QHBoxLayout()
        self.lbl_current_server = QLabel(self.tr("当前选择的服务器:"))
        self.lbl_current_value = QLabel(self.current_server)
        self.lbl_current_value.setAlignment(Qt.AlignCenter)
        self.current_server_layout.addWidget(self.lbl_current_server)
        self.current_server_layout.addWidget(self.lbl_current_value)
        self.main_vbox.addLayout(self.current_server_layout)
        
        # 2. 可选服务器列表
        self.main_vbox.addWidget(QLabel(self.tr("可选服务器列表:")))
        
        # 创建服务器列表控件
        self.server_list = QListWidget()
        self.server_list.itemClicked.connect(self.on_server_selected)
        self.server_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.server_list.customContextMenuRequested.connect(self.show_context_menu)
        self.main_vbox.addWidget(self.server_list)
        
        # 3. 添加自定义服务器
        self.add_server_layout = QVBoxLayout()
        self.lbl_add_server = QLabel(self.tr("添加自定义服务器:"))
        
        self.server_input_layout = QHBoxLayout()
        self.input_server = LineEdit(self)
        self.input_server.setPlaceholderText(self.tr("输入服务器URL"))
        self.btn_add_server = PushButton(self.tr("添加"))
        self.btn_add_server.clicked.connect(self.add_custom_server)
        
        self.server_input_layout.addWidget(self.input_server)
        self.server_input_layout.addWidget(self.btn_add_server)
        self.add_server_layout.addWidget(self.lbl_add_server)
        self.add_server_layout.addLayout(self.server_input_layout)
        self.main_vbox.addLayout(self.add_server_layout)
        
        # 4. 操作按钮
        self.btn_layout = QHBoxLayout()
        spacer = QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)
        self.btn_layout.addItem(spacer)
        self.btn_cancel = PushButton(self.tr("取消"))
        self.btn_confirm = PushButton(self.tr("确认"))
        self.btn_cancel.clicked.connect(self.cancel)
        self.btn_confirm.clicked.connect(self.confirm)
        self.btn_layout.addWidget(self.btn_cancel)
        self.btn_layout.addWidget(self.btn_confirm)
        self.main_vbox.addLayout(self.btn_layout)

        self.setLayout(self.main_vbox)
    
    def load_servers_list(self):
        """加载并显示服务器列表"""
        # 获取并处理服务器字符串
        self.servers_string = self.config_manager.get_server_customized_url()
        self.servers = []
        
        if self.servers_string:
            # 分割服务器字符串并去除空项
            self.servers = [server.strip() for server in self.servers_string.split(',') if server.strip()]
        
        # 清空列表控件并重新加载
        self.server_list.clear()
        for server in self.servers:
            self.server_list.addItem(server)
        
        # 选中当前服务器
        for i in range(self.server_list.count()):
            if self.server_list.item(i).text() == self.current_server:
                self.server_list.setCurrentRow(i)
                break
    
    def on_server_selected(self, item):
        """当选择服务器时更新当前选择的服务器"""
        self.selected_server = item.text()
        self.lbl_current_value.setText(self.selected_server)
    
    def show_context_menu(self, position):
        item = self.server_list.itemAt(position)
        if item is None:
            return
        
        menu = QMenu()
        action_modify = menu.addAction(self.tr("修改"))
        action_delete = menu.addAction(self.tr("删除"))
        
        action = menu.exec_(self.server_list.mapToGlobal(position))
        
        if action == action_modify:
            self.modify_server(item)
        elif action == action_delete:
            self.delete_server(item)
    
    def modify_server(self, item):
        old_text = item.text()
        text, ok = QInputDialog.getText(self, self.tr("修改服务器"), self.tr("输入新的服务器URL:"), LineEdit.Normal, old_text)
        if ok and text:
            if not self.is_valid_url(text):
                QMessageBox.warning(self, self.tr("错误"), self.tr("无效的服务器URL格式"))
                return
            
            item.setText(text)
            self.update_servers_config()
            
            # 如果修改的是当前选中的服务器，更新选中
            if self.selected_server == old_text:
                self.selected_server = text
                self.lbl_current_value.setText(text)
    
    def delete_server(self, item):
        old_text = item.text()
        row = self.server_list.row(item)
        self.server_list.takeItem(row)
        self.update_servers_config()
        
        # 如果删除的是当前选中的服务器，清空选中
        if self.selected_server == old_text:
            self.selected_server = ""
            self.lbl_current_value.setText("")
    
    def update_servers_config(self):
        servers = [self.server_list.item(i).text() for i in range(self.server_list.count())]
        self.servers = servers
        self.servers_string = ','.join(servers)
        self.config_manager.set_server_customized_url(self.servers_string)
    
    def add_custom_server(self):
        """添加自定义服务器到列表"""
        url = self.input_server.text().strip()
        if not url:
            return
        
        if not self.is_valid_url(url):
            QMessageBox.warning(self, self.tr("错误"), self.tr("无效的服务器URL格式"))
            return
        
        # 检查是否已存在
        if url in self.servers:
            self.input_server.clear()
            return
        
        # 构建新的服务器字符串
        new_servers = self.servers_string if self.servers_string else ""
        if new_servers:
            new_servers += ","
        new_servers += url
        
        # 保存配置并刷新列表
        self.config_manager.set_server_customized_url(new_servers)
        self.load_servers_list()
        self.input_server.clear()

    
    def is_valid_url(self, url):
        """
        验证字符串是否为合法的IPv4地址（格式：192.168.1.1）
        
        参数:
            ip (str): 待验证的IP字符串
            
        返回:
            bool: 如果是有效IPv4地址返回True，否则返回False
        """
        pattern = re.compile(
            r'^'  # 字符串开始
            r'(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.'  # 0-255 + 点
            r'(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.'  # 0-255 + 点
            r'(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.'  # 0-255 + 点
            r'(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)'  # 0-255
            r'$'  # 字符串结束
        )
        return pattern.match(url) is not None
    
    def confirm(self):
        """确认服务器选择并保存配置"""
        # 保存选择的服务器
        if self.selected_server and self.selected_server in self.servers:
            self.config_manager.set_server_url(self.selected_server)
        else:
            if self.selected_server:
                QMessageBox.warning(self, self.tr("警告"), self.tr("选中的服务器不存在于列表中"))
        self.accept()
    
    def cancel(self):
        """取消设置并关闭对话框"""
        self.reject()