from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QSizePolicy,
    QSlider,
    QSpacerItem,
    QVBoxLayout,
)
from ui_widgets import PushButton

from utils.config_manager import ConfigManager


class TransmitterSettingDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(self.tr("发射设置"))
        self.resize(460, 280)

        if parent is not None and hasattr(parent, "config_manager"):
            self.config_manager = parent.config_manager
        else:
            self.config_manager = ConfigManager()

        self._loading = False
        self._init_draft()
        self._init_ui()
        self._apply_draft_to_ui()

    @staticmethod
    def _timing_from_wpm(wpm: int):
        wpm = max(5, min(60, int(wpm)))
        dot_ms = int(round(1200 / wpm))
        return {
            "wpm": wpm,
            "dot_ms": dot_ms,
            "dash_ms": 3 * dot_ms,
            "letter_gap_ms": 3 * dot_ms,
            "word_gap_ms": 7 * dot_ms,
        }

    def _init_draft(self):
        initial_wpm = int(self.config_manager.get_wpm())
        self.initial = self._timing_from_wpm(initial_wpm)
        self.draft = dict(self.initial)

    def _init_ui(self):
        self.main_vbox = QVBoxLayout(self)
        self.main_vbox.setSpacing(10)

        self.label_current_wpm = QLabel("")
        self.main_vbox.addWidget(self.label_current_wpm)

        slider_row = QHBoxLayout()
        slider_row.addWidget(QLabel(self.tr("WPM 速率:")))
        self.slider_wpm = QSlider(Qt.Horizontal, self)
        self.slider_wpm.setRange(5, 60)
        slider_row.addWidget(self.slider_wpm, 1)
        self.label_wpm_value = QLabel("")
        slider_row.addWidget(self.label_wpm_value)
        self.main_vbox.addLayout(slider_row)

        self.label_dot = QLabel("")
        self.label_dash = QLabel("")
        self.label_letter_gap = QLabel("")
        self.label_word_gap = QLabel("")
        self.main_vbox.addWidget(self.label_dot)
        self.main_vbox.addWidget(self.label_dash)
        self.main_vbox.addWidget(self.label_letter_gap)
        self.main_vbox.addWidget(self.label_word_gap)

        bottom = QHBoxLayout()
        spacer = QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)
        bottom.addItem(spacer)
        self.btn_cancel = PushButton(self.tr("取消"))
        self.btn_save = PushButton(self.tr("保存"))
        bottom.addWidget(self.btn_cancel)
        bottom.addWidget(self.btn_save)
        self.main_vbox.addLayout(bottom)

        self.slider_wpm.valueChanged.connect(self._on_slider_changed)
        self.btn_cancel.clicked.connect(self.cancel)
        self.btn_save.clicked.connect(self.save)

    def _apply_draft_to_ui(self):
        self._loading = True
        try:
            self.slider_wpm.setValue(int(self.draft["wpm"]))
        finally:
            self._loading = False
        self._refresh_labels()

    def _refresh_labels(self):
        self.label_current_wpm.setText(self.tr("当前发报速度: {0} WPM").format(int(self.draft["wpm"])))
        self.label_wpm_value.setText(f"{int(self.draft['wpm'])} WPM")
        self.label_dot.setText(self.tr("点长度: {0} 毫秒").format(int(self.draft["dot_ms"])))
        self.label_dash.setText(self.tr("划长度: {0} 毫秒").format(int(self.draft["dash_ms"])))
        self.label_letter_gap.setText(self.tr("字母间隔: {0} 毫秒").format(int(self.draft["letter_gap_ms"])))
        self.label_word_gap.setText(self.tr("单词间隔: {0} 毫秒").format(int(self.draft["word_gap_ms"])))

    def _on_slider_changed(self, value):
        if self._loading:
            return
        self.draft = self._timing_from_wpm(int(value))
        self._refresh_labels()

    def _snapshot(self):
        return self._timing_from_wpm(int(self.slider_wpm.value()))

    def _is_dirty(self):
        return self._snapshot() != self.initial

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
        current = self._snapshot()
        self.config_manager.set_wpm(current["wpm"])
        self.config_manager.set_dot_time(current["dot_ms"])
        self.config_manager.set_dash_time(current["dash_ms"])
        self.config_manager.set_letter_interval_duration_time(current["letter_gap_ms"])
        self.config_manager.set_word_interval_duration_time(current["word_gap_ms"])
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

