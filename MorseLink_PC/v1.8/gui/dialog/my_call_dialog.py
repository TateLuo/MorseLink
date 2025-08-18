from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QMessageBox, QDialogButtonBox
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import Qt
from qfluentwidgets import LineEdit, PushButton, Slider, SpinBox
from utils.config_manager import ConfigManager

class MyCallDialog(QDialog):
    """呼号和密码设置对话框"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("呼号与密码设置")
        self.setWindowIcon(QIcon("settings_icon.png"))  # 可替换为实际图标路径
        self.setFixedSize(400, 250)
        
        self.init_ui()
        self.init_data()
        
    def init_ui(self):
        """初始化用户界面"""
        layout = QVBoxLayout()
        
        # 呼号设置区域
        call_layout = QVBoxLayout()
        call_label = QLabel("呼号:")
        self.call_input = LineEdit()
        self.call_input.setPlaceholderText("请输入您的呼号")
        call_layout.addWidget(call_label)
        call_layout.addWidget(self.call_input)
        
        # 密码设置区域
        pwd_layout = QVBoxLayout()
        pwd_label = QLabel("密码:")
        self.pwd_input = LineEdit()
        self.pwd_input.setPlaceholderText("6-20位字母数字组合")
        self.pwd_input.setEchoMode(LineEdit.Password)
        pwd_layout.addWidget(pwd_label)
        pwd_layout.addWidget(self.pwd_input)
        
        # 密码确认区域
        confirm_layout = QVBoxLayout()
        confirm_label = QLabel("确认密码:")
        self.confirm_input = LineEdit()
        self.confirm_input.setPlaceholderText("请再次输入密码")
        self.confirm_input.setEchoMode(LineEdit.Password)
        confirm_layout.addWidget(confirm_label)
        confirm_layout.addWidget(self.confirm_input)
        
        # 按钮区域 - 使用两个QPushButton
        button_layout = QHBoxLayout()
        button_layout.addStretch(1)  # 左侧添加弹簧使按钮右对齐
        
        # 创建取消按钮
        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.clicked.connect(self.reject)
        
        # 创建保存按钮
        self.save_btn = QPushButton("保存")
        self.save_btn.setDefault(True)  # 设置为默认按钮
        self.save_btn.clicked.connect(self.validate_inputs)
        
        #按钮加到布局中
        button_layout.addWidget(self.cancel_btn)
        button_layout.addWidget(self.save_btn)
        
        # 组合所有布局
        layout.addLayout(call_layout)
        layout.addLayout(pwd_layout)
        layout.addLayout(confirm_layout)
        layout.addLayout(button_layout)


        
        self.setLayout(layout)
    
    def init_data(self):
        """加载现有配置数据"""
        self.configer = ConfigManager()
        self.my_call = self.configer.get_my_call()
        self.password = self.configer.get_password()
        
        # 存在配置时才预填充
        if self.my_call or self.password:
            self.call_input.setText(self.my_call or "")
            self.pwd_input.setText("")  # 不显示实际密码
            # 提供提示说明密码已设置
            self.pwd_input.setPlaceholderText("已设置密码，输入新密码可更改")
            self.confirm_input.setPlaceholderText("再次输入新密码")

    def validate_inputs(self):
        """验证用户输入"""
        call = self.call_input.text().strip()
        password = self.pwd_input.text().strip()
        confirm_pwd = self.confirm_input.text().strip()
        
        # 验证呼号
        if not call:
            QMessageBox.warning(self, "输入错误", "呼号不能为空")
            return
        
        # 验证密码
        if password:  # 如果有密码输入才验证
            # 验证密码长度
            if len(password) < 6 or len(password) > 20:
                QMessageBox.warning(self, "输入错误", "密码长度需在6-20位之间")
                return
            
            # 验证密码格式
            if not any(char.isalpha() for char in password) or not any(char.isdigit() for char in password):
                QMessageBox.warning(self, "输入错误", "密码需包含字母和数字")
                return
            
            # 验证密码一致性
            if password != confirm_pwd:
                QMessageBox.warning(self, "输入错误", "两次输入的密码不一致")
                return
        
        # 安全存储密码（不存储明文）
        self.configer.set_my_call(call)
        if password:
            self.configer.set_password(password)
        
        # 所有验证通过
        self.accept()