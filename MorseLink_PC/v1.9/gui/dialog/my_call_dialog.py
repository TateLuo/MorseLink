from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QVBoxLayout,
)
from ui_widgets import LineEdit, PushButton

from utils.config_manager import ConfigManager


class MyCallDialog(QDialog):
    """呼号与密码设置。当前版本仍按协议使用明文凭据。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(self.tr("呼号与密码设置"))
        self.resize(420, 280)

        if parent is not None and hasattr(parent, "config_manager"):
            self.config_manager = parent.config_manager
        else:
            self.config_manager = ConfigManager()

        self._init_draft()
        self._init_ui()
        self._apply_draft_to_ui()

    def _init_draft(self):
        self.initial_call = str(self.config_manager.get_my_call() or "").strip()
        self.initial_password = str(self.config_manager.get_password() or "").strip()
        if self.initial_call.lower() == "none":
            self.initial_call = ""
        if self.initial_password.lower() == "none":
            self.initial_password = ""

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        call_label = QLabel(self.tr("呼号:"))
        self.call_input = LineEdit(self)
        self.call_input.setPlaceholderText(self.tr("请输入您的呼号"))
        layout.addWidget(call_label)
        layout.addWidget(self.call_input)

        pwd_label = QLabel(self.tr("密码:"))
        self.pwd_input = LineEdit(self)
        self.pwd_input.setEchoMode(LineEdit.Password)
        self.pwd_input.setPlaceholderText(self.tr("留空表示不修改密码"))
        layout.addWidget(pwd_label)
        layout.addWidget(self.pwd_input)

        confirm_label = QLabel(self.tr("确认密码:"))
        self.confirm_input = LineEdit(self)
        self.confirm_input.setEchoMode(LineEdit.Password)
        self.confirm_input.setPlaceholderText(self.tr("再次输入新密码"))
        layout.addWidget(confirm_label)
        layout.addWidget(self.confirm_input)

        self.label_hint = QLabel(self.tr("提示：当前协议使用明文账号密码认证，后续将支持更加安全的协议。"))
        self.label_hint.setWordWrap(True)
        layout.addWidget(self.label_hint)

        button_layout = QHBoxLayout()
        button_layout.addStretch(1)
        self.cancel_btn = PushButton(self.tr("取消"))
        self.save_btn = PushButton(self.tr("保存"))
        button_layout.addWidget(self.cancel_btn)
        button_layout.addWidget(self.save_btn)
        layout.addLayout(button_layout)

        self.cancel_btn.clicked.connect(self.cancel)
        self.save_btn.clicked.connect(self.save)

    def _apply_draft_to_ui(self):
        self.call_input.setText(self.initial_call)
        self.pwd_input.clear()
        self.confirm_input.clear()

    def _snapshot(self):
        return {
            "call": str(self.call_input.text() or "").strip(),
            "password": str(self.pwd_input.text() or "").strip(),
            "confirm": str(self.confirm_input.text() or "").strip(),
        }

    def _is_dirty(self):
        current = self._snapshot()
        if current["call"] != self.initial_call:
            return True
        return bool(current["password"] or current["confirm"])

    def _confirm_discard_if_dirty(self):
        if not self._is_dirty():
            return True
        result = QMessageBox.question(
            self,
            self.tr("放弃更改"),
            self.tr("有未保存的改动，确认放弃吗？"),
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        return result == QMessageBox.Yes

    def _validate(self):
        data = self._snapshot()
        if not data["call"]:
            QMessageBox.warning(self, self.tr("输入错误"), self.tr("呼号不能为空"))
            return None

        new_password = data["password"]
        confirm = data["confirm"]
        if new_password or confirm:
            if len(new_password) < 6 or len(new_password) > 32:
                QMessageBox.warning(self, self.tr("输入错误"), self.tr("密码长度需在 6-32 位之间"))
                return None
            if new_password != confirm:
                QMessageBox.warning(self, self.tr("输入错误"), self.tr("两次输入的密码不一致"))
                return None

        return data

    def save(self):
        data = self._validate()
        if data is None:
            return

        self.config_manager.set_my_call(data["call"])
        if data["password"]:
            self.config_manager.set_password(data["password"])
        self.config_manager.sync()
        self.accept()

    def cancel(self):
        if self._confirm_discard_if_dirty():
            self.reject()

    def closeEvent(self, event):
        if self._confirm_discard_if_dirty():
            event.accept()
            return
        event.ignore()

