# -*- coding: utf-8 -*-

from PySide6.QtCore import Qt
from PySide6.QtGui import QKeySequence
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QSizePolicy,
    QSpacerItem,
    QVBoxLayout,
)
from ui_widgets import ComboBox, PushButton, Slider, SpinBox

from utils.config_manager import ConfigManager
from utils.database_tool import DatabaseTool


class GeneralSettingDialog(QDialog):
    FACTORY_DEFAULTS = {
        "language": "zh",
        "sender_font_size": 15,
        "keyer_mode": "straight",
        "single_dual_policy": "dah_priority",
        "paddle_memory_enabled": True,
        "rx_tx_lock_tail_ms": 800,
        "keyborad_key": "81,87",
        "send_buzz_status": True,
        "receive_buzz_status": True,
        "translation_visibility": True,
        "visualizer_visibility": True,
        "buzz_freq": 800,
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(self.tr("一般设置"))
        self.resize(500, 470)

        if parent is not None and hasattr(parent, "config_manager"):
            self.config_manager = parent.config_manager
        else:
            self.config_manager = ConfigManager()

        self._loading = False
        self._capture_stage = None
        self._captured_dah_key = None
        self._pending_data_reset = False

        if parent is not None and hasattr(parent, "context") and parent.context and hasattr(parent.context, "create_database_tool"):
            self.db_tool = parent.context.create_database_tool()
        else:
            self.db_tool = DatabaseTool()

        self._init_draft()
        self._init_ui()
        self._apply_draft_to_ui()

    def _init_draft(self):
        self.initial = {
            "language": self._normalize_language(self.config_manager.get_language()),
            "sender_font_size": int(self.config_manager.get_sender_font_size()),
            "keyer_mode": str(self.config_manager.get_keyer_mode() or "straight").lower(),
            "single_dual_policy": str(self.config_manager.get_single_dual_policy() or "dah_priority").lower(),
            "paddle_memory_enabled": bool(self.config_manager.get_paddle_memory_enabled()),
            "rx_tx_lock_tail_ms": int(self.config_manager.get_rx_tx_lock_tail_ms()),
            "keyborad_key": str(self.config_manager.get_keyborad_key() or "81,87"),
            "send_buzz_status": bool(self.config_manager.get_send_buzz_status()),
            "receive_buzz_status": bool(self.config_manager.get_receive_buzz_status()),
            "translation_visibility": bool(self.config_manager.get_translation_visibility()),
            "visualizer_visibility": bool(self.config_manager.get_visualizer_visibility()),
            "buzz_freq": int(self.config_manager.get_buzz_freq()),
        }
        self.draft = dict(self.initial)

    @staticmethod
    def _normalize_language(value):
        text = str(value or "").strip().lower()
        if text in ("en", "en_us", "en-us", "english"):
            return "en"
        return "zh"

    def _init_ui(self):
        self.main_vbox = QVBoxLayout(self)
        self.main_vbox.setSpacing(10)

        language_row = QHBoxLayout()
        self.label_language = QLabel(self.tr("界面语言:"))
        self.combo_language = ComboBox(self)
        self.language_options = [
            ("zh", self.tr("简体中文")),
            ("en", self.tr("English")),
        ]
        for _, text in self.language_options:
            self.combo_language.addItem(text)
        language_row.addWidget(self.label_language)
        language_row.addWidget(self.combo_language)
        self.main_vbox.addLayout(language_row)

        font_row = QHBoxLayout()
        self.label_font = QLabel(self.tr("字体大小:"))
        self.spin_font = SpinBox(self)
        self.spin_font.setRange(8, 36)
        font_row.addWidget(self.label_font)
        font_row.addWidget(self.spin_font)
        self.main_vbox.addLayout(font_row)

        mode_row = QHBoxLayout()
        self.label_mode = QLabel(self.tr("键控模式:"))
        self.combo_mode = ComboBox(self)
        self.keyer_mode_options = [
            ("straight", self.tr("手键")),
            ("single", self.tr("Single Paddle")),
            ("iambic_a", self.tr("Iambic A")),
            ("iambic_b", self.tr("Iambic B")),
        ]
        for _, text in self.keyer_mode_options:
            self.combo_mode.addItem(text)
        mode_row.addWidget(self.label_mode)
        mode_row.addWidget(self.combo_mode)
        self.main_vbox.addLayout(mode_row)

        policy_row = QHBoxLayout()
        self.label_policy = QLabel(self.tr("Single 双按策略:"))
        self.label_policy_value = QLabel(self.tr("DAH 优先（固定）"))
        policy_row.addWidget(self.label_policy)
        policy_row.addWidget(self.label_policy_value)
        self.main_vbox.addLayout(policy_row)

        tail_row = QHBoxLayout()
        self.label_tail = QLabel(self.tr("接收后禁发尾巴(ms):"))
        self.spin_tail = SpinBox(self)
        self.spin_tail.setRange(100, 5000)
        self.spin_tail.setSingleStep(50)
        tail_row.addWidget(self.label_tail)
        tail_row.addWidget(self.spin_tail)
        self.main_vbox.addLayout(tail_row)

        key_row = QHBoxLayout()
        self.label_key = QLabel(self.tr("键盘发送:"))
        self.label_key_value = QLabel("")
        self.btn_change_key = PushButton(self.tr("设置按键"))
        key_row.addWidget(self.label_key)
        key_row.addWidget(self.label_key_value, 1)
        key_row.addWidget(self.btn_change_key)
        self.main_vbox.addLayout(key_row)

        send_audio_row = QHBoxLayout()
        self.label_send_audio = QLabel("")
        self.btn_send_audio = PushButton(self.tr("切换"))
        send_audio_row.addWidget(self.label_send_audio)
        send_audio_row.addWidget(self.btn_send_audio)
        self.main_vbox.addLayout(send_audio_row)

        recv_audio_row = QHBoxLayout()
        self.label_recv_audio = QLabel("")
        self.btn_recv_audio = PushButton(self.tr("切换"))
        recv_audio_row.addWidget(self.label_recv_audio)
        recv_audio_row.addWidget(self.btn_recv_audio)
        self.main_vbox.addLayout(recv_audio_row)

        freq_row = QHBoxLayout()
        self.label_freq = QLabel("")
        self.slider_freq = Slider(Qt.Horizontal, self)
        self.slider_freq.setRange(300, 1000)
        self.slider_freq.setFixedWidth(220)
        freq_row.addWidget(self.label_freq)
        freq_row.addWidget(self.slider_freq)
        self.main_vbox.addLayout(freq_row)

        trans_row = QHBoxLayout()
        self.label_translation = QLabel("")
        self.btn_translation = PushButton(self.tr("切换"))
        trans_row.addWidget(self.label_translation)
        trans_row.addWidget(self.btn_translation)
        self.main_vbox.addLayout(trans_row)

        visual_row = QHBoxLayout()
        self.label_visual = QLabel("")
        self.btn_visual = PushButton(self.tr("切换"))
        visual_row.addWidget(self.label_visual)
        visual_row.addWidget(self.btn_visual)
        self.main_vbox.addLayout(visual_row)

        self.label_capture_hint = QLabel("")
        self.label_capture_hint.setStyleSheet("color:#c56a00;")
        self.main_vbox.addWidget(self.label_capture_hint)

        bottom = QHBoxLayout()
        self.btn_restore = PushButton(self.tr("恢复出厂设置"))
        bottom.addWidget(self.btn_restore)
        spacer = QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)
        bottom.addItem(spacer)
        self.btn_cancel = PushButton(self.tr("取消"))
        self.btn_save = PushButton(self.tr("保存"))
        bottom.addWidget(self.btn_cancel)
        bottom.addWidget(self.btn_save)
        self.main_vbox.addLayout(bottom)

        self.spin_font.valueChanged.connect(lambda v: self._set_draft("sender_font_size", int(v)))
        self.combo_language.currentIndexChanged.connect(self._on_language_changed)
        self.combo_mode.currentIndexChanged.connect(self._on_keyer_mode_changed)
        self.spin_tail.valueChanged.connect(lambda v: self._set_draft("rx_tx_lock_tail_ms", int(v)))
        self.slider_freq.valueChanged.connect(self._on_freq_changed)

        self.btn_change_key.clicked.connect(self._start_key_capture)
        self.btn_send_audio.clicked.connect(self._toggle_send_audio)
        self.btn_recv_audio.clicked.connect(self._toggle_receive_audio)
        self.btn_translation.clicked.connect(self._toggle_translation)
        self.btn_visual.clicked.connect(self._toggle_visualizer)
        self.btn_restore.clicked.connect(self._restore_factory_defaults)
        self.btn_cancel.clicked.connect(self.cancel)
        self.btn_save.clicked.connect(self.save)

    def _set_draft(self, key, value):
        if self._loading:
            return
        self.draft[key] = value
        if key in ("send_buzz_status", "receive_buzz_status", "translation_visibility", "visualizer_visibility"):
            self._refresh_switch_labels()

    def _parse_key_pair(self, raw_text):
        text = str(raw_text or "").strip().strip('"').strip("'")
        parts = [p.strip() for p in text.split(",") if p.strip()]
        if len(parts) < 2:
            return 81, 87
        try:
            return int(parts[0]), int(parts[1])
        except Exception:
            return 81, 87

    def _key_name(self, key_code: int):
        text = QKeySequence(int(key_code)).toString()
        if text == " ":
            return self.tr("空格")
        return text or str(key_code)

    def _render_key_label(self):
        dah_key, dit_key = self._parse_key_pair(self.draft["keyborad_key"])
        self.label_key_value.setText(f"{self._key_name(dah_key)}, {self._key_name(dit_key)}")

    def _refresh_switch_labels(self):
        self.label_send_audio.setText(
            self.tr("发送蜂鸣声: ") + (self.tr("已启用") if self.draft["send_buzz_status"] else self.tr("已禁用"))
        )
        self.label_recv_audio.setText(
            self.tr("接收蜂鸣声: ") + (self.tr("已启用") if self.draft["receive_buzz_status"] else self.tr("已禁用"))
        )
        self.label_translation.setText(
            self.tr("消息显示与翻译: ") + (self.tr("已启用") if self.draft["translation_visibility"] else self.tr("已禁用"))
        )
        self.label_visual.setText(
            self.tr("摩尔斯电码动画: ") + (self.tr("已启用") if self.draft["visualizer_visibility"] else self.tr("已禁用"))
        )
        self.label_freq.setText(self.tr("蜂鸣器频率: {0} Hz").format(int(self.draft["buzz_freq"])))

    def _apply_draft_to_ui(self):
        self._loading = True
        try:
            self.spin_font.setValue(int(self.draft["sender_font_size"]))

            lang_idx = 0
            for idx, (lang_key, _) in enumerate(self.language_options):
                if lang_key == str(self.draft["language"]):
                    lang_idx = idx
                    break
            self.combo_language.setCurrentIndex(lang_idx)

            mode_idx = 0
            for idx, (mode_key, _) in enumerate(self.keyer_mode_options):
                if mode_key == str(self.draft["keyer_mode"]):
                    mode_idx = idx
                    break
            self.combo_mode.setCurrentIndex(mode_idx)
            self.spin_tail.setValue(int(self.draft["rx_tx_lock_tail_ms"]))
            self.slider_freq.setValue(int(self.draft["buzz_freq"]))
            self.label_capture_hint.setText("")
            self._refresh_switch_labels()
            self._render_key_label()
        finally:
            self._loading = False

    def _on_keyer_mode_changed(self):
        if self._loading:
            return
        mode_key, _ = self.keyer_mode_options[self.combo_mode.currentIndex()]
        self.draft["keyer_mode"] = mode_key

    def _on_language_changed(self):
        if self._loading:
            return
        lang_key, _ = self.language_options[self.combo_language.currentIndex()]
        self.draft["language"] = lang_key

    def _on_freq_changed(self, value):
        self._set_draft("buzz_freq", int(value))
        self._refresh_switch_labels()

    def _toggle_send_audio(self):
        self._set_draft("send_buzz_status", not bool(self.draft["send_buzz_status"]))

    def _toggle_receive_audio(self):
        self._set_draft("receive_buzz_status", not bool(self.draft["receive_buzz_status"]))

    def _toggle_translation(self):
        self._set_draft("translation_visibility", not bool(self.draft["translation_visibility"]))

    def _toggle_visualizer(self):
        self._set_draft("visualizer_visibility", not bool(self.draft["visualizer_visibility"]))

    def _factory_defaults_snapshot(self):
        return dict(self.FACTORY_DEFAULTS)

    def _restore_factory_defaults(self):
        result = QMessageBox.question(
            self,
            self.tr("恢复出厂设置"),
            self.tr("将恢复当前页面默认值，并在保存时重置课程进度和清空通联记录，是否继续？"),
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if result != QMessageBox.Yes:
            return

        self.draft = self._factory_defaults_snapshot()
        self._pending_data_reset = True
        self._capture_stage = None
        self._captured_dah_key = None
        self._apply_draft_to_ui()
        self.label_capture_hint.setText(self.tr("已恢复默认值；点击“保存”后将同时重置课程进度并清空通联记录"))

    def _start_key_capture(self):
        self._capture_stage = "dah"
        self._captured_dah_key = None
        self.label_capture_hint.setText(self.tr("请按下 Dah 键（按 Esc 取消）"))

    def keyPressEvent(self, event):
        if self._capture_stage is None:
            super().keyPressEvent(event)
            return

        key = int(event.key())
        if key == Qt.Key_Escape:
            self._capture_stage = None
            self._captured_dah_key = None
            self.label_capture_hint.setText(self.tr("按键设置已取消"))
            return

        if self._capture_stage == "dah":
            self._captured_dah_key = key
            self._capture_stage = "dit"
            self.label_capture_hint.setText(self.tr("请按下 Dit 键"))
            return

        if self._capture_stage == "dit":
            if key == self._captured_dah_key:
                QMessageBox.warning(self, self.tr("错误"), self.tr("Dah 与 Dit 不能使用同一个键"))
                return
            self.draft["keyborad_key"] = f"{int(self._captured_dah_key)},{key}"
            self._capture_stage = None
            self._captured_dah_key = None
            self.label_capture_hint.setText(self.tr("按键设置完成"))
            self._render_key_label()
            return

    def _snapshot(self):
        snap = dict(self.draft)
        lang_key, _ = self.language_options[self.combo_language.currentIndex()]
        snap["language"] = lang_key
        snap["sender_font_size"] = int(self.spin_font.value())
        snap["rx_tx_lock_tail_ms"] = int(self.spin_tail.value())
        snap["buzz_freq"] = int(self.slider_freq.value())
        mode_key, _ = self.keyer_mode_options[self.combo_mode.currentIndex()]
        snap["keyer_mode"] = mode_key
        dah_key, dit_key = self._parse_key_pair(self.draft["keyborad_key"])
        snap["keyborad_key"] = f"{dah_key},{dit_key}"
        return snap

    def _is_dirty(self):
        current = self._snapshot()
        initial = dict(self.initial)
        dah_key, dit_key = self._parse_key_pair(initial["keyborad_key"])
        initial["keyborad_key"] = f"{dah_key},{dit_key}"
        return current != initial or bool(self._pending_data_reset)

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

    def save(self):
        snapshot = self._snapshot()
        language_before = self._normalize_language(self.initial.get("language", "zh"))
        language_after = self._normalize_language(snapshot.get("language", "zh"))
        self.config_manager.set_language(language_after)
        self.config_manager.set_sender_font_size(snapshot["sender_font_size"])
        self.config_manager.set_keyer_mode(snapshot["keyer_mode"])
        self.config_manager.set_single_dual_policy("dah_priority")
        self.config_manager.set_paddle_memory_enabled(bool(snapshot["paddle_memory_enabled"]))
        self.config_manager.set_rx_tx_lock_tail_ms(snapshot["rx_tx_lock_tail_ms"])
        self.config_manager.set_keyborad_key(snapshot["keyborad_key"])
        self.config_manager.set_send_buzz_status(bool(snapshot["send_buzz_status"]))
        self.config_manager.set_receive_buzz_status(bool(snapshot["receive_buzz_status"]))
        self.config_manager.set_translation_visibility(bool(snapshot["translation_visibility"]))
        self.config_manager.set_visualizer_visibility(bool(snapshot["visualizer_visibility"]))
        self.config_manager.set_buzz_freq(snapshot["buzz_freq"])
        if self._pending_data_reset:
            try:
                self.db_tool.reset_user_progress_and_records()
            except Exception as e:
                QMessageBox.warning(self, self.tr("错误"), self.tr("重置课程进度/通联记录失败：{0}").format(str(e)))
                return
            self.config_manager.set_value("Training/tutorial_done", False)
            self._pending_data_reset = False
        self.config_manager.sync()
        if language_after != language_before:
            QMessageBox.information(self, self.tr("语言切换提示"), self.tr("语言切换将在重启应用后生效。"))
        self.accept()

    def cancel(self):
        if self._confirm_discard_if_dirty():
            self.reject()

    def closeEvent(self, event):
        if self._confirm_discard_if_dirty():
            event.accept()
            return
        event.ignore()

