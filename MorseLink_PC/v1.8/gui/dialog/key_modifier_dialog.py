import sys
import serial
import serial.tools.list_ports
from PyQt5.QtWidgets import QLabel, QVBoxLayout, QPushButton, QComboBox, QLineEdit, QDialog, QRadioButton, QHBoxLayout, QMessageBox, QButtonGroup

class KeyModifierDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.initUI()
        self.serial_port = None

    def initUI(self):
        self.setWindowTitle(self.tr('MorseLink_Connector设置'))
        layout = QVBoxLayout()

        # 串口选择
        self.port_label = QLabel(self.tr('选择串口:'))
        layout.addWidget(self.port_label)

        self.port_combo = QComboBox()
        self.populate_ports()
        layout.addWidget(self.port_combo)

        # 刷新串口按钮
        self.refresh_button = QPushButton(self.tr('刷新串口列表'))
        self.refresh_button.clicked.connect(self.refresh_ports)
        layout.addWidget(self.refresh_button)

        # 读取按键按钮
        self.read_keys_button = QPushButton(self.tr('读取按键'))
        self.read_keys_button.clicked.connect(self.read_keys)
        layout.addWidget(self.read_keys_button)

        # Key1 单选按钮组
        self.key1_label = QLabel(self.tr('按键1:'))
        layout.addWidget(self.key1_label)

        self.key1_radio_group = QButtonGroup(self)  # 创建一个新的按钮组
        self.key1_keyboard_radio = QRadioButton(self.tr('键盘'))
        self.key1_mouse_radio = QRadioButton(self.tr('鼠标'))
        self.key1_function_key_radio = QRadioButton(self.tr('功能键'))
        self.key1_keyboard_radio.setChecked(True)

        self.key1_radio_group.addButton(self.key1_keyboard_radio)
        self.key1_radio_group.addButton(self.key1_mouse_radio)
        self.key1_radio_group.addButton(self.key1_function_key_radio)

        key1_radio_layout = QHBoxLayout()
        key1_radio_layout.addWidget(self.key1_keyboard_radio)
        key1_radio_layout.addWidget(self.key1_mouse_radio)
        key1_radio_layout.addWidget(self.key1_function_key_radio)
        layout.addLayout(key1_radio_layout)

        # Key1 输入框
        self.key1_input = QLineEdit()
        self.key1_input.setVisible(True)  # 默认显示
        layout.addWidget(self.key1_input)

        self.key1_dropdown = QComboBox()
        self.key1_dropdown.setVisible(False)  # 默认隐藏
        layout.addWidget(self.key1_dropdown)

        self.function_key_dropdown1 = QComboBox()
        self.function_key_dropdown1.setVisible(False)  # 默认隐藏
        layout.addWidget(self.function_key_dropdown1)

        # Key2 单选按钮组
        self.key2_label = QLabel(self.tr('按键2:'))
        layout.addWidget(self.key2_label)

        self.key2_radio_group = QButtonGroup(self)  # 创建一个新的按钮组
        self.key2_keyboard_radio = QRadioButton(self.tr('键盘'))
        self.key2_mouse_radio = QRadioButton(self.tr('鼠标'))
        self.key2_function_key_radio = QRadioButton(self.tr('功能键'))
        self.key2_keyboard_radio.setChecked(True)

        self.key2_radio_group.addButton(self.key2_keyboard_radio)
        self.key2_radio_group.addButton(self.key2_mouse_radio)
        self.key2_radio_group.addButton(self.key2_function_key_radio)

        key2_radio_layout = QHBoxLayout()
        key2_radio_layout.addWidget(self.key2_keyboard_radio)
        key2_radio_layout.addWidget(self.key2_mouse_radio)
        key2_radio_layout.addWidget(self.key2_function_key_radio)
        layout.addLayout(key2_radio_layout)

        # Key2 输入框
        self.key2_input = QLineEdit()
        self.key2_input.setVisible(True)  # 默认显示
        layout.addWidget(self.key2_input)

        self.key2_dropdown = QComboBox()
        self.key2_dropdown.setVisible(False)  # 默认隐藏
        layout.addWidget(self.key2_dropdown)

        self.function_key_dropdown2 = QComboBox()
        self.function_key_dropdown2.setVisible(False)  # 默认隐藏
        layout.addWidget(self.function_key_dropdown2)

        # 保存按钮
        self.save_button = QPushButton(self.tr('写入按键'))
        self.save_button.clicked.connect(self.save_keys)
        layout.addWidget(self.save_button)

        self.hint_label = QLabel(
            self.tr(
                '注意: (此功能需要连接硬件设备)<br>'
                '1. 首先检查串口列表，插入设备后刷新列表以找到新端口并选择它。<br>'
                '2. 点击读取或写入后，请稍等片刻；不要疯狂点击。<br>'
                '3. 如果选择了错误的端口，点击读取或写入后卡住是正常现象。<br>'
                '<a href="https://github.com/TateLuo/MorseLink_connector">点击此处了解更多信息</a>'
            )
        )
        self.hint_label.setOpenExternalLinks(True)
        layout.addWidget(self.hint_label)

        self.setLayout(layout)

        # 初始化控件状态
        self.set_controls_enabled(False)

        # 连接信号
        self.key1_radio_group.buttonToggled.connect(self.update_key1_input_layout)
        self.key2_radio_group.buttonToggled.connect(self.update_key2_input_layout)

        # 初始化变量
        self.mouse_left_key = self.tr("左键")
        self.mouse_right_key = self.tr("右键")
        self.mouse_middle_key = self.tr("中键")
        self.key_ctrl = self.tr("Ctrl")

        # 初始化输入布局
        self.update_key1_input_layout()
        self.update_key2_input_layout()

    def populate_ports(self):
        self.port_combo.clear()
        ports = serial.tools.list_ports.comports()
        for port in ports:
            self.port_combo.addItem(port.device)

    def refresh_ports(self):
        self.set_controls_enabled(False)  # 刷新时禁用控件
        self.populate_ports()
        self.set_controls_enabled(True)   # 刷新完成后启用控件

    def set_controls_enabled(self, enabled):
        self.port_combo.setEnabled(enabled)
        self.read_keys_button.setEnabled(enabled)
        self.key1_keyboard_radio.setEnabled(enabled)
        self.key1_mouse_radio.setEnabled(enabled)
        self.key1_function_key_radio.setEnabled(enabled)
        self.key1_input.setEnabled(enabled)
        self.key2_keyboard_radio.setEnabled(enabled)
        self.key2_mouse_radio.setEnabled(enabled)
        self.key2_function_key_radio.setEnabled(enabled)
        self.key2_input.setEnabled(enabled)
        self.key1_dropdown.setEnabled(enabled)
        self.key2_dropdown.setEnabled(enabled)
        self.function_key_dropdown1.setEnabled(enabled)
        self.function_key_dropdown2.setEnabled(enabled)
        self.save_button.setEnabled(enabled)

    def update_key1_input_layout(self):
        # 清空 Key1 输入框和下拉框
        self.key1_input.setVisible(False)
        self.key1_dropdown.setVisible(False)
        self.function_key_dropdown1.setVisible(False)

        if self.key1_keyboard_radio.isChecked():
            self.key1_input.setVisible(True)
        elif self.key1_mouse_radio.isChecked():
            self.key1_dropdown.clear()
            self.key1_dropdown.addItems([self.mouse_left_key, self.mouse_right_key, self.mouse_middle_key])  # 鼠标选项
            self.key1_dropdown.setVisible(True)
        elif self.key1_function_key_radio.isChecked():
            self.function_key_dropdown1.clear()
            self.function_key_dropdown1.addItems([self.key_ctrl])  # 功能键选项
            self.function_key_dropdown1.setVisible(True)

    def update_key2_input_layout(self):
        # 清空 Key2 输入框和下拉框
        self.key2_input.setVisible(False)
        self.key2_dropdown.setVisible(False)
        self.function_key_dropdown2.setVisible(False)

        if self.key2_keyboard_radio.isChecked():
            self.key2_input.setVisible(True)
        elif self.key2_mouse_radio.isChecked():
            self.key2_dropdown.clear()
            self.key2_dropdown.addItems([self.mouse_left_key, self.mouse_right_key, self.mouse_middle_key])  # 鼠标选项
            self.key2_dropdown.setVisible(True)
        elif self.key2_function_key_radio.isChecked():
            self.function_key_dropdown2.clear()
            self.function_key_dropdown2.addItems([self.key_ctrl])  # 功能键选项
            self.function_key_dropdown2.setVisible(True)

    def reset_controls(self):
        # 重置 Key1 控件
        self.key1_keyboard_radio.setChecked(True)
        self.key1_input.clear()
        self.key1_input.setVisible(True)
        self.key1_dropdown.setVisible(False)
        self.function_key_dropdown1.setVisible(False)

        # 重置 Key2 控件
        self.key2_keyboard_radio.setChecked(True)
        self.key2_input.clear()
        self.key2_input.setVisible(True)
        self.key2_dropdown.setVisible(False)
        self.function_key_dropdown2.setVisible(False)

        # 更新输入布局
        self.update_key1_input_layout()
        self.update_key2_input_layout()

    def get_mouse_button(self, button_index):
        # 定义索引到十六进制值的映射
        index_to_hex = {
            0: 0x01,  # 左键
            1: 0x02,  # 右键
            2: 0x04   # 中键
        }
        return index_to_hex.get(button_index, 0x01)  # 默认返回左键

    def hex_to_mouse_button(self, hex_value):
        # 定义十六进制值到索引的映射
        hex_to_index = {
            0x01: 0,  # 左键
            0x02: 1,  # 右键
            0x04: 2   # 中键
        }
        return hex_to_index.get(hex_value, 0)  # 默认返回左键

    def read_keys(self):
        self.reset_controls()
        try:
            port_name = self.port_combo.currentText()  # 获取选定的端口名
            self.serial_port = serial.Serial(port_name, 9600, timeout=1)  # 打开串口

            # 发送读取命令
            self.serial_port.write(b'\x02\x03')

            # 读取所有可用数据
            all_data = b''
            while True:
                response = self.serial_port.read(1)  # 一次读取一个字节
                if not response:  # 如果没有更多数据则退出循环
                    break
                all_data += response

            # 处理接收到的数据
            lines = all_data.strip().split(b'\r\n')
            if len(lines) >= 4:
                key1_hex = lines[1].strip()  # 第二行
                key2_hex = lines[2].strip()  # 第三行
                
                # 确定按键模式：当前仅支持键盘和鼠标模式
                key1_model = float(lines[4].strip())
                key2_model = float(lines[5].strip())

                # 处理 Key1 输入
                key1_value = int(key1_hex, 16)  # 将十六进制值转换为整数
                if key1_model == 0:
                    if key1_value >= 128:
                        self.key1_function_key_radio.setChecked(True)
                        self.function_key_dropdown1.setCurrentIndex(0)
                    else:
                        self.key1_input.setText(bytes.fromhex(key1_hex.decode()).decode('utf-8'))
                else:
                    self.key1_mouse_radio.setChecked(True)
                    button_index = self.hex_to_mouse_button(key1_value)  # 将十六进制值转换为索引
                    self.key1_dropdown.setCurrentIndex(button_index)
                
                # 处理 Key2 输入
                key2_value = int(key2_hex, 16)  # 将十六进制值转换为整数
                if key2_model == 0:
                    if key2_value >= 128:  # 大于128则为ctrl
                        self.key2_function_key_radio.setChecked(True)
                        self.function_key_dropdown2.setCurrentIndex(0)
                    else:  # 小于128则为普通按键
                        self.key2_input.setText(bytes.fromhex(key2_hex.decode()).decode('utf-8'))
                else:
                    self.key2_mouse_radio.setChecked(True)
                    button_index = self.hex_to_mouse_button(key2_value)  # 将十六进制值转换为索引
                    self.key2_dropdown.setCurrentIndex(button_index)                                        
            else:
                QMessageBox.warning(self, self.tr('错误'), self.tr('读取失败，响应不完整！'))
                print(all_data)
        except Exception as e:
            QMessageBox.warning(self, self.tr('错误'), str(e))
        finally:
            if self.serial_port:
                self.serial_port.close()

    def save_keys(self):
        try:
            key1_hex = None   
            key2_hex = None  
        
            key3_hex = 0x77  # Placeholder for key3
            key3func = 0x00  # Normal key function
            key3f = 0xFF     # Set to 0xFF

            # 处理 Key1
            if self.key1_mouse_radio.isChecked():
                button_index = self.key1_dropdown.currentIndex()  # 获取当前选中的索引
                key1_hex = self.get_mouse_button(button_index)    # 转换为十六进制值
                key1func = 0x04  # Mouse function
                key1f = 0x00     # Set to 0x00
                print(f"Key1 Mouse Button: {hex(key1_hex)}")  # 打印调试信息
            elif self.key1_function_key_radio.isChecked():
                key1_hex = int(self.to_hex(128), 16)  # Convert to hex
                key1func = 0x00  # Normal key function
                key1f = 0xFF     # Set to 0xFF
            elif self.key1_keyboard_radio.isChecked():
                input_text = self.key1_input.text()
                if input_text:
                    key1_hex = int(self.to_hex(input_text), 16)  # Convert to hex
                    key1func = 0x00  # Normal key function
                    key1f = 0xFF     # Set to 0xFF
                else:
                    QMessageBox.information(self, self.tr('错误'), self.tr('按键1不能为空！'))
            else:
                QMessageBox.information(self, self.tr('错误'), self.tr('请设置按键1！'))

            # 处理 Key2
            if self.key2_mouse_radio.isChecked():
                button_index = self.key2_dropdown.currentIndex()  # 获取当前选中的索引
                key2_hex = self.get_mouse_button(button_index)    # 转换为十六进制值
                key2func = 0x04  # Mouse function
                key2f = 0x00     # Set to 0x00
                print(f"Key2 Mouse Button: {hex(key2_hex)}")  # 打印调试信息
            elif self.key2_function_key_radio.isChecked():
                key2_hex = int(self.to_hex(128), 16)  # Convert to hex
                key2func = 0x00  # Normal key function
                key2f = 0xFF     # Set to 0xFF
            elif self.key2_keyboard_radio.isChecked():
                input_text = self.key2_input.text()
                if input_text:
                    key2_hex = int(self.to_hex(input_text), 16)  # Convert to hex
                    key2func = 0x00  # Normal key function
                    key2f = 0xFF     # Set to 0xFF
                else:
                    QMessageBox.information(self, self.tr('错误'), self.tr('按键2不能为空！'))                        
            else:
                QMessageBox.information(self, self.tr('错误'), self.tr('请设置按键2！'))
            
            if key1_hex is not None and key2_hex is not None:
                # Create a 30-byte string filled with 0xFF
                key1string = b'\xFF' * 144

                port_name = self.port_combo.currentText()  # Get selected port name
                self.serial_port = serial.Serial(port_name, 9600, timeout=1)  # Open serial port

                # Prepare data to send
                data_to_send = (
                    b'\x02' + 
                    bytes([key1_hex, key2_hex, key3_hex, key1func, key2func, key3func, key1f, key2f]) + 
                    key1string +  
                    b'\x00' +
                    b'\x03'
                )
                print(f"Data to send: {data_to_send}")  # 打印调试信息
                self.serial_port.write(data_to_send)  # Send save command
                QMessageBox.information(self, self.tr('成功'), self.tr('按键已写入！'))
            else:
                QMessageBox.information(self, self.tr('失败'), self.tr('按键写入失败，出现错误！'))
        except Exception as e:
            QMessageBox.warning(self, self.tr('错误'), str(e))
        finally:
            if self.serial_port:
                self.serial_port.close()

    def to_hex(self, value):
        if isinstance(value, str):
            if value == ' ':
                return "20"
            return value.encode('utf-8').hex()
        elif isinstance(value, (int, float)):
            return hex(int(value))
        else:
            raise ValueError("输入必须是字符串或数字")