import time

import serial
import serial.tools.list_ports
from PySide6.QtCore import QCoreApplication, QObject, QThread, Signal, Slot
from PySide6.QtWidgets import (
    QButtonGroup,
    QComboBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QRadioButton,
    QVBoxLayout,
)


def _tr(text: str) -> str:
    return QCoreApplication.translate("KeyModifierDialog", text)


class _SerialWorker(QObject):
    finished = Signal(bool, str, object)

    def __init__(self, op: str, port_name: str, payload: bytes | None = None):
        super().__init__()
        self.op = op
        self.port_name = str(port_name or "").strip()
        self.payload = payload

    @staticmethod
    def _read_all(port):
        raw = b""
        end_at = time.monotonic() + 1.2
        while time.monotonic() < end_at:
            chunk = port.read(64)
            if chunk:
                raw += chunk
                end_at = time.monotonic() + 0.25
            elif raw:
                break
        return raw

    @staticmethod
    def _parse_read_response(raw: bytes):
        lines = [line.strip() for line in raw.split(b"\r\n") if line.strip()]
        if len(lines) < 6:
            raise ValueError(_tr("报文格式错误：返回字段不足"))

        key1_hex = lines[1].decode("ascii", errors="ignore")
        key2_hex = lines[2].decode("ascii", errors="ignore")
        key1_model = lines[4].decode("ascii", errors="ignore")
        key2_model = lines[5].decode("ascii", errors="ignore")

        key1_value = int(key1_hex, 16)
        key2_value = int(key2_hex, 16)
        model1 = int(float(key1_model))
        model2 = int(float(key2_model))

        return {
            "key1_value": key1_value,
            "key2_value": key2_value,
            "key1_model": model1,
            "key2_model": model2,
        }

    @Slot()
    def run(self):
        if not self.port_name:
            self.finished.emit(False, _tr("端口未选择，请先选择串口。"), None)
            return

        try:
            with serial.Serial(self.port_name, 9600, timeout=0.25, write_timeout=0.5) as port:
                port.reset_input_buffer()
                port.reset_output_buffer()

                if self.op == "read":
                    port.write(b"\x02\x03")
                    raw = self._read_all(port)
                    if not raw:
                        self.finished.emit(
                            False,
                            _tr("设备无响应，请检查端口是否正确、线缆是否连接。"),
                            None,
                        )
                        return
                    parsed = self._parse_read_response(raw)
                    self.finished.emit(True, _tr("读取成功"), parsed)
                    return

                if self.op == "write":
                    if not self.payload:
                        self.finished.emit(False, _tr("写入数据为空。"), None)
                        return
                    port.write(self.payload)
                    port.flush()
                    self.finished.emit(True, _tr("写入成功"), None)
                    return

                self.finished.emit(False, _tr("未知串口操作。"), None)
        except serial.SerialException as e:
            self.finished.emit(False, _tr("串口错误：{0}").format(e), None)
        except ValueError as e:
            self.finished.emit(False, str(e), None)
        except Exception as e:
            self.finished.emit(False, _tr("操作失败：{0}").format(e), None)


class KeyModifierDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._serial_thread = None
        self._serial_worker = None
        self._pending_op = None
        self.init_ui()
        self.populate_ports()

    def init_ui(self):
        self.setWindowTitle(self.tr("连接器设置"))
        layout = QVBoxLayout(self)

        self.port_label = QLabel(self.tr("选择串口:"))
        layout.addWidget(self.port_label)
        self.port_combo = QComboBox()
        layout.addWidget(self.port_combo)

        self.refresh_button = QPushButton(self.tr("刷新串口列表"))
        self.refresh_button.clicked.connect(self.refresh_ports)
        layout.addWidget(self.refresh_button)

        self.read_keys_button = QPushButton(self.tr("读取按键"))
        self.read_keys_button.clicked.connect(self.read_keys)
        layout.addWidget(self.read_keys_button)

        self.key1_label = QLabel(self.tr("按键1:"))
        layout.addWidget(self.key1_label)
        self.key1_radio_group = QButtonGroup(self)
        self.key1_keyboard_radio = QRadioButton(self.tr("键盘"))
        self.key1_mouse_radio = QRadioButton(self.tr("鼠标"))
        self.key1_function_key_radio = QRadioButton(self.tr("功能键"))
        self.key1_keyboard_radio.setChecked(True)
        self.key1_radio_group.addButton(self.key1_keyboard_radio)
        self.key1_radio_group.addButton(self.key1_mouse_radio)
        self.key1_radio_group.addButton(self.key1_function_key_radio)
        key1_radio_layout = QHBoxLayout()
        key1_radio_layout.addWidget(self.key1_keyboard_radio)
        key1_radio_layout.addWidget(self.key1_mouse_radio)
        key1_radio_layout.addWidget(self.key1_function_key_radio)
        layout.addLayout(key1_radio_layout)

        self.key1_input = QLineEdit()
        layout.addWidget(self.key1_input)
        self.key1_dropdown = QComboBox()
        self.key1_dropdown.setVisible(False)
        layout.addWidget(self.key1_dropdown)
        self.function_key_dropdown1 = QComboBox()
        self.function_key_dropdown1.setVisible(False)
        layout.addWidget(self.function_key_dropdown1)

        self.key2_label = QLabel(self.tr("按键2:"))
        layout.addWidget(self.key2_label)
        self.key2_radio_group = QButtonGroup(self)
        self.key2_keyboard_radio = QRadioButton(self.tr("键盘"))
        self.key2_mouse_radio = QRadioButton(self.tr("鼠标"))
        self.key2_function_key_radio = QRadioButton(self.tr("功能键"))
        self.key2_keyboard_radio.setChecked(True)
        self.key2_radio_group.addButton(self.key2_keyboard_radio)
        self.key2_radio_group.addButton(self.key2_mouse_radio)
        self.key2_radio_group.addButton(self.key2_function_key_radio)
        key2_radio_layout = QHBoxLayout()
        key2_radio_layout.addWidget(self.key2_keyboard_radio)
        key2_radio_layout.addWidget(self.key2_mouse_radio)
        key2_radio_layout.addWidget(self.key2_function_key_radio)
        layout.addLayout(key2_radio_layout)

        self.key2_input = QLineEdit()
        layout.addWidget(self.key2_input)
        self.key2_dropdown = QComboBox()
        self.key2_dropdown.setVisible(False)
        layout.addWidget(self.key2_dropdown)
        self.function_key_dropdown2 = QComboBox()
        self.function_key_dropdown2.setVisible(False)
        layout.addWidget(self.function_key_dropdown2)

        self.save_button = QPushButton(self.tr("写入按键"))
        self.save_button.clicked.connect(self.save_keys)
        layout.addWidget(self.save_button)

        self.status_label = QLabel(self.tr("状态：就绪"))
        layout.addWidget(self.status_label)

        self.hint_label = QLabel(
            self.tr(
                "注意：\n"
                "1. 先选择正确串口，再执行读取或写入。\n"
                "2. 操作中按钮会锁定，请等待完成。\n"
                "3. 若端口错误或设备无响应，请更换端口重试。"
            )
        )
        self.hint_label.setWordWrap(True)
        layout.addWidget(self.hint_label)

        self.mouse_left_key = self.tr("左键")
        self.mouse_right_key = self.tr("右键")
        self.mouse_middle_key = self.tr("中键")
        self.key_ctrl = self.tr("Ctrl")

        self.key1_radio_group.buttonToggled.connect(self.update_key1_input_layout)
        self.key2_radio_group.buttonToggled.connect(self.update_key2_input_layout)
        self.update_key1_input_layout()
        self.update_key2_input_layout()

    def populate_ports(self):
        self.port_combo.clear()
        for port in serial.tools.list_ports.comports():
            self.port_combo.addItem(port.device)

    def refresh_ports(self):
        self.populate_ports()

    def set_controls_enabled(self, enabled):
        for w in (
            self.port_combo,
            self.refresh_button,
            self.read_keys_button,
            self.key1_keyboard_radio,
            self.key1_mouse_radio,
            self.key1_function_key_radio,
            self.key2_keyboard_radio,
            self.key2_mouse_radio,
            self.key2_function_key_radio,
            self.key1_input,
            self.key2_input,
            self.key1_dropdown,
            self.key2_dropdown,
            self.function_key_dropdown1,
            self.function_key_dropdown2,
            self.save_button,
        ):
            w.setEnabled(enabled)

    def update_key1_input_layout(self):
        self.key1_input.setVisible(False)
        self.key1_dropdown.setVisible(False)
        self.function_key_dropdown1.setVisible(False)
        if self.key1_keyboard_radio.isChecked():
            self.key1_input.setVisible(True)
        elif self.key1_mouse_radio.isChecked():
            self.key1_dropdown.clear()
            self.key1_dropdown.addItems([self.mouse_left_key, self.mouse_right_key, self.mouse_middle_key])
            self.key1_dropdown.setVisible(True)
        elif self.key1_function_key_radio.isChecked():
            self.function_key_dropdown1.clear()
            self.function_key_dropdown1.addItems([self.key_ctrl])
            self.function_key_dropdown1.setVisible(True)

    def update_key2_input_layout(self):
        self.key2_input.setVisible(False)
        self.key2_dropdown.setVisible(False)
        self.function_key_dropdown2.setVisible(False)
        if self.key2_keyboard_radio.isChecked():
            self.key2_input.setVisible(True)
        elif self.key2_mouse_radio.isChecked():
            self.key2_dropdown.clear()
            self.key2_dropdown.addItems([self.mouse_left_key, self.mouse_right_key, self.mouse_middle_key])
            self.key2_dropdown.setVisible(True)
        elif self.key2_function_key_radio.isChecked():
            self.function_key_dropdown2.clear()
            self.function_key_dropdown2.addItems([self.key_ctrl])
            self.function_key_dropdown2.setVisible(True)

    @staticmethod
    def _mouse_button_to_hex(button_index):
        return {0: 0x01, 1: 0x02, 2: 0x04}.get(button_index, 0x01)

    @staticmethod
    def _hex_to_mouse_button(hex_value):
        return {0x01: 0, 0x02: 1, 0x04: 2}.get(hex_value, 0)

    @staticmethod
    def _char_to_hex(text: str):
        s = str(text or "")
        if len(s) != 1:
            raise ValueError(_tr("键盘模式仅支持单个字符，请输入 1 个字符。"))
        return ord(s)

    def _collect_single_key_payload(self, is_key1=True):
        if is_key1:
            keyboard_radio = self.key1_keyboard_radio
            mouse_radio = self.key1_mouse_radio
            function_radio = self.key1_function_key_radio
            input_text = self.key1_input.text()
            dropdown = self.key1_dropdown
            key_name = self.tr("按键1")
        else:
            keyboard_radio = self.key2_keyboard_radio
            mouse_radio = self.key2_mouse_radio
            function_radio = self.key2_function_key_radio
            input_text = self.key2_input.text()
            dropdown = self.key2_dropdown
            key_name = self.tr("按键2")

        if mouse_radio.isChecked():
            key_hex = self._mouse_button_to_hex(dropdown.currentIndex())
            return key_hex, 0x04, 0x00

        if function_radio.isChecked():
            return 0x80, 0x00, 0xFF

        if keyboard_radio.isChecked():
            try:
                key_hex = self._char_to_hex(input_text)
            except ValueError as e:
                raise ValueError(f"{key_name}：{e}") from e
            return key_hex, 0x00, 0xFF

        raise ValueError(self.tr("{0} 未设置。").format(key_name))

    def _build_write_payload(self):
        key1_hex, key1func, key1f = self._collect_single_key_payload(is_key1=True)
        key2_hex, key2func, key2f = self._collect_single_key_payload(is_key1=False)
        key3_hex = 0x77
        key3func = 0x00
        padding = b"\xFF" * 144
        return (
            b"\x02"
            + bytes([key1_hex, key2_hex, key3_hex, key1func, key2func, key3func, key1f, key2f])
            + padding
            + b"\x00"
            + b"\x03"
        )

    def _run_serial_task(self, op: str, payload: bytes | None = None):
        if self._serial_thread is not None:
            return
        port_name = self.port_combo.currentText().strip()
        self._pending_op = op
        self.set_controls_enabled(False)
        self.status_label.setText(self.tr("状态：处理中..."))

        self._serial_thread = QThread(self)
        self._serial_worker = _SerialWorker(op=op, port_name=port_name, payload=payload)
        self._serial_worker.moveToThread(self._serial_thread)
        self._serial_thread.started.connect(self._serial_worker.run)
        self._serial_worker.finished.connect(self._on_serial_task_finished)
        self._serial_worker.finished.connect(self._serial_thread.quit)
        self._serial_worker.finished.connect(self._serial_worker.deleteLater)
        self._serial_thread.finished.connect(self._serial_thread.deleteLater)
        self._serial_thread.finished.connect(self._clear_serial_handles)
        self._serial_thread.start()

    def _clear_serial_handles(self):
        self._serial_thread = None
        self._serial_worker = None
        self._pending_op = None

    def read_keys(self):
        self._run_serial_task("read")

    def save_keys(self):
        try:
            payload = self._build_write_payload()
        except ValueError as e:
            QMessageBox.warning(self, self.tr("错误"), str(e))
            return
        self._run_serial_task("write", payload=payload)

    def _on_serial_task_finished(self, ok: bool, message: str, data):
        self.set_controls_enabled(True)
        self.status_label.setText(self.tr("状态：就绪") if ok else self.tr("状态：失败"))

        if not ok:
            QMessageBox.warning(self, self.tr("错误"), message)
            return

        if self._pending_op == "read":
            self._apply_read_result(data or {})
            QMessageBox.information(self, self.tr("成功"), self.tr("读取按键成功。"))
        elif self._pending_op == "write":
            QMessageBox.information(self, self.tr("成功"), self.tr("按键已写入。"))

        self._pending_op = None

    def _apply_read_result(self, data):
        key1_value = int(data.get("key1_value", 0))
        key2_value = int(data.get("key2_value", 0))
        key1_model = int(data.get("key1_model", 0))
        key2_model = int(data.get("key2_model", 0))

        if key1_model == 0:
            if key1_value >= 128:
                self.key1_function_key_radio.setChecked(True)
                self.function_key_dropdown1.setCurrentIndex(0)
            else:
                self.key1_keyboard_radio.setChecked(True)
                self.key1_input.setText(chr(key1_value))
        else:
            self.key1_mouse_radio.setChecked(True)
            self.key1_dropdown.setCurrentIndex(self._hex_to_mouse_button(key1_value))

        if key2_model == 0:
            if key2_value >= 128:
                self.key2_function_key_radio.setChecked(True)
                self.function_key_dropdown2.setCurrentIndex(0)
            else:
                self.key2_keyboard_radio.setChecked(True)
                self.key2_input.setText(chr(key2_value))
        else:
            self.key2_mouse_radio.setChecked(True)
            self.key2_dropdown.setCurrentIndex(self._hex_to_mouse_button(key2_value))

    def closeEvent(self, event):
        if self._serial_thread is not None and self._serial_thread.isRunning():
            QMessageBox.information(self, self.tr("提示"), self.tr("串口操作进行中，请稍候再关闭。"))
            event.ignore()
            return
        super().closeEvent(event)
