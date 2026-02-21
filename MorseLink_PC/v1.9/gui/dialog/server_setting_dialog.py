import ipaddress
import os
import re
from urllib.parse import urlparse

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QMenu,
    QMessageBox,
    QSpinBox,
    QSpacerItem,
    QSizePolicy,
    QWidget,
    QVBoxLayout,
)
from ui_widgets import LineEdit, PushButton

from utils.config_manager import ConfigManager


class ServerSettingDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(self.tr("服务器设置"))
        self.resize(520, 460)

        if parent is not None and hasattr(parent, "config_manager"):
            self.config_manager = parent.config_manager
        else:
            self.config_manager = ConfigManager()

        self._init_draft()
        self.init_ui()
        self._reload_list_widget()

    def _init_draft(self):
        self.initial_scheme = str(self.config_manager.get_server_scheme() or "mqtt").strip().lower()
        if self.initial_scheme not in ("mqtt", "mqtts"):
            self.initial_scheme = "mqtt"
        self.initial_host = str(self.config_manager.get_server_host() or "").strip()
        self.initial_port = int(self.config_manager.get_server_active_port())
        self.initial_tls_ca_certs = str(self.config_manager.get_server_tls_ca_certs() or "").strip()
        self.initial_tls_use_cert = bool(self.config_manager.get_server_tls_use_cert())
        endpoints_text = self.config_manager.get_server_customized_endpoints()
        self.initial_endpoints = self._parse_endpoints_text(endpoints_text, self.initial_scheme)
        current_endpoint = self._compose_endpoint(self.initial_scheme, self.initial_host, self.initial_port)
        if current_endpoint and current_endpoint not in self.initial_endpoints:
            self.initial_endpoints.insert(0, current_endpoint)
        if not self.initial_endpoints and current_endpoint:
            self.initial_endpoints = [current_endpoint]

        self.draft_endpoints = list(self.initial_endpoints)
        self.selected_endpoint = current_endpoint if current_endpoint else (self.draft_endpoints[0] if self.draft_endpoints else "")

    def init_ui(self):
        self.main_vbox = QVBoxLayout(self)
        self.main_vbox.setSpacing(10)

        self.current_layout = QHBoxLayout()
        self.lbl_current_server = QLabel(self.tr("当前选择:"))
        self.lbl_current_value = QLabel(self.selected_endpoint or "--")
        self.lbl_current_value.setAlignment(Qt.AlignCenter)
        self.current_layout.addWidget(self.lbl_current_server)
        self.current_layout.addWidget(self.lbl_current_value, 1)
        self.main_vbox.addLayout(self.current_layout)

        self.main_vbox.addWidget(QLabel(self.tr("服务器列表 (mqtt://host:port 或 mqtts://host:port):")))
        self.server_list = QListWidget()
        self.server_list.itemClicked.connect(self._on_server_selected)
        self.server_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.server_list.customContextMenuRequested.connect(self._show_context_menu)
        self.main_vbox.addWidget(self.server_list)

        self.main_vbox.addWidget(QLabel(self.tr("添加服务器:")))
        add_layout = QHBoxLayout()
        self.protocol_combo = QComboBox(self)
        self.protocol_combo.addItems(["mqtt", "mqtts"])
        self.protocol_combo.setCurrentText(self.initial_scheme)
        self.protocol_combo.currentTextChanged.connect(self._on_protocol_changed)
        self.input_host = LineEdit(self)
        self.input_host.setPlaceholderText(self.tr("主机，例如 mqtt.example.com 或 192.168.1.10"))
        self.input_port = QSpinBox(self)
        self.input_port.setRange(1, 65535)
        self.input_port.setValue(self.initial_port)
        self.btn_add_server = PushButton(self.tr("添加"))
        self.btn_add_server.clicked.connect(self._add_server)
        add_layout.addWidget(self.protocol_combo)
        add_layout.addWidget(self.input_host, 1)
        add_layout.addWidget(self.input_port)
        add_layout.addWidget(self.btn_add_server)
        self.main_vbox.addLayout(add_layout)

        self.lbl_tls_settings = QLabel(self.tr("MQTTS/TLS 设置:"))
        self.main_vbox.addWidget(self.lbl_tls_settings)

        self.tls_path_container = QWidget(self)
        self.tls_path_container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        tls_path_layout = QHBoxLayout(self.tls_path_container)
        tls_path_layout.setContentsMargins(0, 0, 0, 0)
        self.input_tls_ca_certs = LineEdit(self)
        self.input_tls_ca_certs.setPlaceholderText(self.tr("CA 证书路径（可选，PEM/CRT/CER）"))
        self.input_tls_ca_certs.setText(self.initial_tls_ca_certs)
        self.btn_browse_tls_ca_certs = PushButton(self.tr("浏览"))
        self.btn_browse_tls_ca_certs.clicked.connect(self._browse_tls_ca_certs)
        tls_path_layout.addWidget(self.input_tls_ca_certs, 1)
        tls_path_layout.addWidget(self.btn_browse_tls_ca_certs)
        self.main_vbox.addWidget(self.tls_path_container)

        self.check_tls_use_cert = QCheckBox(self.tr("启用证书校验（关闭则默认跳过）"), self)
        self.check_tls_use_cert.setChecked(self.initial_tls_use_cert)
        self.check_tls_use_cert.toggled.connect(self._on_tls_use_cert_toggled)
        self.main_vbox.addWidget(self.check_tls_use_cert)

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

        self._on_tls_use_cert_toggled(self.check_tls_use_cert.isChecked())
        self._update_tls_controls_visibility(self.initial_scheme)

    @staticmethod
    def _normalize_scheme(scheme: str, default: str = "mqtt") -> str:
        value = str(scheme or "").strip().lower()
        return value if value in ("mqtt", "mqtts") else default

    @staticmethod
    def _default_port_for_scheme(scheme: str) -> int:
        return 8883 if str(scheme).lower() == "mqtts" else 1883

    def _on_protocol_changed(self, value: str):
        scheme = self._normalize_scheme(value, self.initial_scheme)
        default_port = self._default_port_for_scheme(scheme)
        current_port = int(self.input_port.value())
        if current_port in (1883, 8883):
            self.input_port.setValue(default_port)
        self._update_tls_controls_visibility(scheme)

    def _update_tls_controls_visibility(self, scheme: str):
        normalized_scheme = self._normalize_scheme(scheme, self.initial_scheme)
        visible = normalized_scheme == "mqtts"
        self.lbl_tls_settings.setVisible(visible)
        self.tls_path_container.setVisible(visible)
        self.check_tls_use_cert.setVisible(visible)

    def _on_tls_use_cert_toggled(self, checked: bool):
        enabled = bool(checked)
        self.input_tls_ca_certs.setEnabled(enabled)
        self.btn_browse_tls_ca_certs.setEnabled(enabled)

    def _browse_tls_ca_certs(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            self.tr("选择 CA 证书"),
            str(self.input_tls_ca_certs.text() or "").strip(),
            self.tr("证书文件 (*.pem *.crt *.cer);;所有文件 (*)"),
        )
        if file_path:
            self.input_tls_ca_certs.setText(file_path)

    def _parse_endpoints_text(self, text: str, default_scheme: str = "mqtt"):
        endpoints = []
        seen = set()
        default_scheme = self._normalize_scheme(default_scheme, "mqtt")
        raw = str(text or "").strip().strip('"').strip("'")
        if not raw:
            return endpoints
        for token in raw.split(","):
            token = token.strip().strip('"').strip("'")
            if not token:
                continue
            scheme, host, port = self._parse_endpoint(
                token,
                default_scheme=default_scheme,
                default_port=self._default_port_for_scheme(default_scheme),
            )
            if not host:
                continue
            endpoint = self._compose_endpoint(scheme, host, port)
            low = endpoint.lower()
            if low in seen:
                continue
            seen.add(low)
            endpoints.append(endpoint)
        return endpoints

    def _parse_endpoint(self, text: str, default_scheme: str = "mqtt", default_port: int | None = None):
        default_scheme = self._normalize_scheme(default_scheme, "mqtt")
        if default_port is None:
            default_port = self._default_port_for_scheme(default_scheme)
        raw = str(text or "").strip().strip('"').strip("'")
        if not raw:
            return default_scheme, "", int(default_port)

        has_scheme = "://" in raw
        source = raw if has_scheme else f"{default_scheme}://{raw}"
        try:
            parsed = urlparse(source)
            scheme = self._normalize_scheme(parsed.scheme, default_scheme)
            host = (parsed.hostname or "").strip()
            if parsed.port is not None:
                port = int(parsed.port)
            elif has_scheme:
                port = self._default_port_for_scheme(scheme)
            else:
                port = int(default_port)
            return scheme, host, port
        except Exception:
            return default_scheme, raw, int(default_port)

    def _compose_endpoint(self, scheme: str, host: str, port: int):
        scheme = self._normalize_scheme(scheme, "mqtt")
        return f"{scheme}://{str(host).strip()}:{int(port)}"

    def _reload_list_widget(self):
        self.server_list.clear()
        for endpoint in self.draft_endpoints:
            self.server_list.addItem(endpoint)

        if self.selected_endpoint:
            for i in range(self.server_list.count()):
                if self.server_list.item(i).text() == self.selected_endpoint:
                    self.server_list.setCurrentRow(i)
                    break
        self.lbl_current_value.setText(self.selected_endpoint or "--")

    def _on_server_selected(self, item):
        self.selected_endpoint = item.text().strip()
        self.lbl_current_value.setText(self.selected_endpoint or "--")
        scheme, host, port = self._parse_endpoint(
            self.selected_endpoint,
            default_scheme=self.initial_scheme,
            default_port=self.initial_port,
        )
        if host:
            self.protocol_combo.setCurrentText(scheme)
            self.input_host.setText(host)
            self.input_port.setValue(int(port))

    def _show_context_menu(self, position):
        item = self.server_list.itemAt(position)
        if item is None:
            return

        menu = QMenu(self)
        action_modify = menu.addAction(self.tr("修改"))
        action_delete = menu.addAction(self.tr("删除"))
        action = menu.exec(self.server_list.mapToGlobal(position))

        if action == action_modify:
            self._modify_server(item)
        elif action == action_delete:
            self._delete_server(item)

    def _modify_server(self, item):
        old_endpoint = item.text().strip()
        text, ok = QInputDialog.getText(
            self,
            self.tr("修改服务器"),
            self.tr("输入新的 mqtt://host:port 或 mqtts://host:port"),
            QLineEdit.Normal,
            old_endpoint,
        )
        if not ok:
            return
        new_text = str(text or "").strip()
        if not new_text:
            return
        base_scheme, _, _ = self._parse_endpoint(
            old_endpoint,
            default_scheme=self.initial_scheme,
            default_port=self.initial_port,
        )
        scheme, host, port = self._parse_endpoint(
            new_text,
            default_scheme=base_scheme,
            default_port=self.input_port.value(),
        )
        if not self._is_valid_host(host):
            QMessageBox.warning(self, self.tr("错误"), self.tr("主机格式无效"))
            return
        if not (1 <= int(port) <= 65535):
            QMessageBox.warning(self, self.tr("错误"), self.tr("端口范围必须是 1~65535"))
            return

        new_endpoint = self._compose_endpoint(scheme, host, port)
        if new_endpoint.lower() != old_endpoint.lower() and self._endpoint_exists(new_endpoint):
            QMessageBox.warning(self, self.tr("错误"), self.tr("该服务器已存在"))
            return

        row = self.server_list.row(item)
        self.draft_endpoints[row] = new_endpoint
        if self.selected_endpoint.lower() == old_endpoint.lower():
            self.selected_endpoint = new_endpoint
        self._reload_list_widget()

    def _delete_server(self, item):
        endpoint = item.text().strip()
        row = self.server_list.row(item)
        if 0 <= row < len(self.draft_endpoints):
            self.draft_endpoints.pop(row)
        if self.selected_endpoint.lower() == endpoint.lower():
            self.selected_endpoint = self.draft_endpoints[0] if self.draft_endpoints else ""
        self._reload_list_widget()

    def _endpoint_exists(self, endpoint: str):
        low = endpoint.lower()
        return any(str(v).lower() == low for v in self.draft_endpoints)

    def _is_valid_host(self, host: str):
        value = str(host or "").strip()
        if not value:
            return False
        if "/" in value or "?" in value or "#" in value:
            return False
        if value.lower() == "localhost":
            return True
        try:
            ipaddress.ip_address(value)
            return True
        except ValueError:
            pass

        if len(value) > 253:
            return False

        domain_re = re.compile(
            r"^(?=.{1,253}$)"
            r"(?!-)[A-Za-z0-9-]{1,63}(?<!-)"
            r"(\.(?!-)[A-Za-z0-9-]{1,63}(?<!-))*$"
        )
        return domain_re.match(value) is not None

    def _add_server(self):
        scheme = self._normalize_scheme(self.protocol_combo.currentText(), self.initial_scheme)
        host = str(self.input_host.text() or "").strip()
        port = int(self.input_port.value())
        if not self._is_valid_host(host):
            QMessageBox.warning(self, self.tr("错误"), self.tr("主机格式无效"))
            return
        endpoint = self._compose_endpoint(scheme, host, port)
        if self._endpoint_exists(endpoint):
            QMessageBox.warning(self, self.tr("错误"), self.tr("该服务器已存在"))
            return
        self.draft_endpoints.append(endpoint)
        self.selected_endpoint = endpoint
        self.input_host.clear()
        self._reload_list_widget()

    def _is_dirty(self):
        if self.draft_endpoints != self.initial_endpoints:
            return True
        initial_selected = self._compose_endpoint(self.initial_scheme, self.initial_host, self.initial_port)
        if str(self.selected_endpoint or "") != str(initial_selected or ""):
            return True

        current_ca = str(self.input_tls_ca_certs.text() or "").strip()
        if current_ca != self.initial_tls_ca_certs:
            return True
        return bool(self.check_tls_use_cert.isChecked()) != bool(self.initial_tls_use_cert)

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

    def confirm(self):
        if not self.draft_endpoints:
            QMessageBox.warning(self, self.tr("错误"), self.tr("请至少保留一个服务器"))
            return

        selected = self.selected_endpoint or self.draft_endpoints[0]
        if not self._endpoint_exists(selected):
            selected = self.draft_endpoints[0]
        scheme, host, port = self._parse_endpoint(
            selected,
            default_scheme=self.initial_scheme,
            default_port=self.initial_port,
        )
        if not host:
            QMessageBox.warning(self, self.tr("错误"), self.tr("当前选择的服务器无效"))
            return

        tls_ca_certs = str(self.input_tls_ca_certs.text() or "").strip()
        tls_use_cert = bool(self.check_tls_use_cert.isChecked())
        if scheme == "mqtts" and tls_use_cert and tls_ca_certs and not os.path.isfile(tls_ca_certs):
            QMessageBox.warning(self, self.tr("错误"), self.tr("CA 证书文件不存在"))
            return

        endpoints_text = ",".join(self.draft_endpoints)
        self.config_manager.set_server_scheme(scheme)
        self.config_manager.set_server_host(host)
        self.config_manager.set_server_active_port(port)
        self.config_manager.set_server_customized_endpoints(endpoints_text)
        self.config_manager.set_server_tls_ca_certs(tls_ca_certs)
        self.config_manager.set_server_tls_use_cert(tls_use_cert)
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

