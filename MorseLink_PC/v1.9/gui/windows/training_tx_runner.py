from __future__ import annotations

import re
import time
from collections import defaultdict

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout, QWidget

from service.keying_controller import AutoElementEvent
from service.tx_keying_runtime import TxKeyingRuntime
from ui_widgets import PushButton, TextEdit
from ui_widgets import FluentIcon as FIF

from morselink.training.models import RoundTask, TrainingMetrics, TrainingResult
from utils.config_manager import ConfigManager
from utils.sound import BuzzerSimulator
from utils.training_feedback import align_sequences
from utils.translator import MorseCodeTranslator


class TrainingTxRunner(QWidget):
    mode = "tx"

    def __init__(self, context=None, parent=None) -> None:
        super().__init__(parent)
        self.context = context
        self.configer = self.context.config_manager if self.context else ConfigManager()
        self.translator = MorseCodeTranslator()
        self.buzzer = self._create_buzzer()
        self.setFocusPolicy(Qt.StrongFocus)

        self._task: RoundTask | None = None
        self._on_done = None
        self._index = 0
        self._started_ms = 0.0

        self._all_morse_inputs: list[str] = []
        self._all_decoded_inputs: list[str] = []
        self._all_events: list[list[dict[str, float]]] = []
        self._sum_decode_match = 0.0
        self._sum_rhythm = 0.0
        self._sum_score = 0.0
        self._round_count = 0
        self._current_submitted = False
        self._current_feedback_text = ""
        self._current_decoded_text = ""
        self._per_char_errors: dict[str, int] = defaultdict(int)
        self._confusions: dict[tuple[str, str], int] = defaultdict(int)

        self._current_morse = ""
        self._current_events: list[dict[str, float]] = []

        self._init_ui()
        self._init_runtime()

    def _create_buzzer(self):
        if self.context and hasattr(self.context, "create_buzzer"):
            return self.context.create_buzzer()
        return BuzzerSimulator()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(10)

        top_card = QWidget(self)
        top_card.setObjectName("txTopCard")
        top_row = QHBoxLayout(top_card)
        top_row.setContentsMargins(12, 8, 12, 8)
        top_row.setSpacing(10)

        self.label_title = QLabel(self.tr("发报 (Tx)"), top_card)
        self.label_title.setObjectName("txTitleChip")
        top_row.addWidget(self.label_title)

        self.label_progress = QLabel(self.tr("未开始"), top_card)
        self.label_progress.setObjectName("txProgress")
        top_row.addWidget(self.label_progress)
        top_row.addStretch(1)

        self.label_submit_state = QLabel(self.tr("状态：未提交"), top_card)
        self.label_submit_state.setObjectName("txSubmitState")
        top_row.addWidget(self.label_submit_state)
        layout.addWidget(top_card)

        question_card = QWidget(self)
        question_card.setObjectName("txQuestionCard")
        question_layout = QVBoxLayout(question_card)
        question_layout.setContentsMargins(14, 12, 14, 12)
        question_layout.setSpacing(8)

        self.label_question_caption = QLabel(self.tr("本题目标"), question_card)
        self.label_question_caption.setObjectName("txCaption")
        question_layout.addWidget(self.label_question_caption)

        self.label_question = QLabel(self.tr("题目将在这里显示"), question_card)
        self.label_question.setObjectName("txQuestionText")
        self.label_question.setWordWrap(True)
        self.label_question.setMinimumHeight(52)
        question_layout.addWidget(self.label_question)
        layout.addWidget(question_card)

        answer_card = QWidget(self)
        answer_card.setObjectName("txAnswerCard")
        answer_layout = QVBoxLayout(answer_card)
        answer_layout.setContentsMargins(14, 12, 14, 12)
        answer_layout.setSpacing(8)

        self.label_morse_caption = QLabel(self.tr("发报串"), answer_card)
        self.label_morse_caption.setObjectName("txCaption")
        answer_layout.addWidget(self.label_morse_caption)

        self.input_box = TextEdit(answer_card)
        self.input_box.setReadOnly(True)
        self.input_box.setPlaceholderText(self.tr("发报生成的摩尔斯串"))
        self.input_box.setObjectName("txInputBox")
        self.input_box.setMinimumHeight(92)
        answer_layout.addWidget(self.input_box)

        self.label_decoded_caption = QLabel(self.tr("译码结果"), answer_card)
        self.label_decoded_caption.setObjectName("txCaption")
        answer_layout.addWidget(self.label_decoded_caption)

        self.decoded_box = TextEdit(answer_card)
        self.decoded_box.setReadOnly(True)
        self.decoded_box.setPlaceholderText(self.tr("提交后显示译码结果"))
        self.decoded_box.setObjectName("txDecodedBox")
        self.decoded_box.setMinimumHeight(92)
        answer_layout.addWidget(self.decoded_box)

        self.label_feedback = QLabel(self.tr("等待开始"), answer_card)
        self.label_feedback.setWordWrap(True)
        self.label_feedback.setObjectName("txFeedback")
        answer_layout.addWidget(self.label_feedback)
        layout.addWidget(answer_card, 1)

        action_card = QWidget(self)
        action_card.setObjectName("txActionCard")
        action_row = QHBoxLayout(action_card)
        action_row.setContentsMargins(12, 10, 12, 10)
        action_row.setSpacing(8)

        self.label_timing = QLabel(self.tr("WPM -- | Farn --"), action_card)
        self.label_timing.setObjectName("txTiming")
        action_row.addWidget(self.label_timing, 1)

        self.cw_button = PushButton(FIF.SEND, self.tr("按键发报"), action_card)
        self.cw_button.setObjectName("txSendButton")
        self.cw_button.setCursor(Qt.PointingHandCursor)
        self.cw_button.pressed.connect(self.on_btn_send_message_pressed)
        self.cw_button.released.connect(self.on_btn_send_message_released)
        action_row.addWidget(self.cw_button)

        self.submit_button = PushButton(FIF.SEARCH, self.tr("提交"), action_card)
        self.submit_button.setObjectName("txSecondaryButton")
        self.submit_button.setCursor(Qt.PointingHandCursor)
        self.submit_button.clicked.connect(self.submit_current_answer)
        action_row.addWidget(self.submit_button)

        self.next_button = PushButton(self.tr("下一题"), action_card)
        self.next_button.setObjectName("txPrimaryButton")
        self.next_button.setCursor(Qt.PointingHandCursor)
        self.next_button.clicked.connect(self.next_question)
        action_row.addWidget(self.next_button)

        layout.addWidget(action_card)

        self._apply_styles()

    def _apply_styles(self) -> None:
        self.setStyleSheet(
            """
            QWidget#txTopCard, QWidget#txQuestionCard, QWidget#txAnswerCard, QWidget#txActionCard {
                background: #f6f8fc;
                border: 1px solid #d7e2f2;
                border-radius: 12px;
            }
            QLabel#txTitleChip {
                background: qlineargradient(
                    x1: 0, y1: 0, x2: 1, y2: 0,
                    stop: 0 #dfe8ff,
                    stop: 1 #cfdcff
                );
                color: #2c4f9a;
                border: 1px solid #b3c4ef;
                border-radius: 16px;
                padding: 4px 12px;
                font-weight: 700;
            }
            QLabel#txProgress {
                color: #2c3e5d;
                font-size: 14px;
                font-weight: 700;
            }
            QLabel#txSubmitState {
                background: #edf2ff;
                color: #35558f;
                border: 1px solid #c4d1ec;
                border-radius: 12px;
                padding: 3px 10px;
            }
            QLabel#txCaption {
                color: #526888;
                font-weight: 600;
            }
            QLabel#txQuestionText {
                color: #1d2b3f;
                font-size: 20px;
                font-weight: 700;
                letter-spacing: 1px;
            }
            QTextEdit#txInputBox, QTextEdit#txDecodedBox {
                background: #ffffff;
                border: 1px solid #c8d6ea;
                border-radius: 10px;
                padding: 8px;
                selection-background-color: #a5cbff;
            }
            QLabel#txFeedback {
                color: #375171;
                background: #edf4ff;
                border: 1px solid #c9dbf4;
                border-radius: 8px;
                padding: 8px;
            }
            QLabel#txTiming {
                color: #3d5473;
                font-weight: 600;
            }
            QPushButton#txSendButton {
                color: #ffffff;
                background: qlineargradient(
                    x1: 0, y1: 0, x2: 1, y2: 0,
                    stop: 0 #5ca6ff,
                    stop: 1 #2f78eb
                );
                border: 1px solid #2d71da;
                border-radius: 8px;
                min-height: 34px;
                padding: 0 14px;
                font-weight: 700;
            }
            QPushButton#txSendButton:hover {
                background: #428ce8;
            }
            QPushButton#txSecondaryButton {
                background: #ffffff;
                color: #2e4564;
                border: 1px solid #c6d3e7;
                border-radius: 8px;
                min-height: 34px;
                padding: 0 16px;
                font-weight: 600;
            }
            QPushButton#txSecondaryButton:hover {
                background: #f1f5fb;
            }
            QPushButton#txPrimaryButton {
                background: qlineargradient(
                    x1: 0, y1: 0, x2: 1, y2: 0,
                    stop: 0 #4e9dff,
                    stop: 1 #2972e8
                );
                color: #ffffff;
                border: 1px solid #286ddb;
                border-radius: 8px;
                min-height: 34px;
                padding: 0 18px;
                font-weight: 700;
            }
            QPushButton#txPrimaryButton:hover {
                background: #3e86ee;
            }
            """
        )

    def _update_timing_hint(self) -> None:
        if self._task is None:
            self.label_timing.setText(self.tr("WPM -- | Farn --"))
            return
        timing = self._task.timing
        wpm = int(timing.get("wpm", 16))
        dot_ms = max(1, int(timing.get("dot_ms", 80)))
        letter_gap_ms = max(1, int(timing.get("letter_gap_ms", dot_ms * 3)))
        farn_wpm = max(5, int(round(1200.0 / max(1.0, float(letter_gap_ms) / 3.0))))
        self.label_timing.setText(
            self.tr("WPM {0}  Farn {1}  Dot {2}ms").format(wpm, farn_wpm, dot_ms)
        )

    def _build_bias_feedback(self, result) -> str:
        if result.missing > result.extra and result.missing >= result.replace:
            return self.tr("偏置反馈：漏码偏多，建议拉开字符间隔。")
        if result.extra > result.missing and result.extra >= result.replace:
            return self.tr("偏置反馈：多码偏多，建议减少粘连与误触。")
        if result.replace > 0:
            return self.tr("偏置反馈：错码偏多，建议先稳节奏再提速。")
        return self.tr("偏置反馈：整体平衡，继续保持。")

    def _build_error_detail(self, result, max_items: int = 3) -> str:
        total_errors = int(result.replace) + int(result.missing) + int(result.extra)
        if total_errors <= 0:
            return self.tr("错误点：无")

        details: list[str] = []
        for cell in result.cells:
            if cell.status == "correct":
                continue
            if cell.status == "replace":
                pos = (int(cell.expected_index) + 1) if int(cell.expected_index) >= 0 else (int(cell.actual_index) + 1)
                details.append(self.tr("第{0}位 {1}->{2}").format(pos, cell.expected, cell.actual))
            elif cell.status == "missing":
                pos = (int(cell.expected_index) + 1) if int(cell.expected_index) >= 0 else int(result.total_expected) + 1
                details.append(self.tr("第{0}位漏发({1})").format(pos, cell.expected))
            elif cell.status == "extra":
                pos = (int(cell.actual_index) + 1) if int(cell.actual_index) >= 0 else int(result.total_expected) + 1
                details.append(self.tr("第{0}位多发({1})").format(pos, cell.actual))

            if len(details) >= max_items:
                break

        suffix = self.tr(" 等{0}处").format(total_errors) if total_errors > len(details) else ""
        return self.tr("错误点：") + "；".join(details) + suffix

    def _init_runtime(self) -> None:
        self.letter_timer = QTimer(self)
        self.letter_timer.setSingleShot(True)
        self.letter_timer.timeout.connect(self.handle_letter_timeout)

        self.word_timer = QTimer(self)
        self.word_timer.setSingleShot(True)
        self.word_timer.timeout.connect(self.handle_word_timeout)

        self.tx_runtime = TxKeyingRuntime(
            parent=self,
            buzzer=self.buzzer,
            get_wpm=self._get_training_wpm,
            on_stop_gap_timers=self._stop_gap_timers,
            on_start_letter_timer=self.start_letter_timer,
            on_manual_symbol=self._tx_runtime_on_manual_symbol,
            on_auto_symbol=self._tx_runtime_on_auto_symbol,
        )

    def _get_training_wpm(self) -> int:
        if self._task is not None and self._task.timing:
            return int(self._task.timing.get("wpm", 16))
        return 16

    def _stop_gap_timers(self) -> None:
        self.letter_timer.stop()
        self.word_timer.stop()

    def _refresh_runtime(self) -> None:
        timing = self._task.timing if self._task is not None else {}
        dot_duration = int(timing.get("dot_ms", 80))
        dash_duration = int(timing.get("dash_ms", dot_duration * 3))
        letter_interval_duration = int(timing.get("letter_gap_ms", dot_duration * 3))
        word_interval_duration = int(timing.get("word_gap_ms", dot_duration * 7))
        keyer_mode = str(self.configer.get_keyer_mode() or "straight").lower()
        send_buzz_status = self.configer.get_send_buzz_status()
        saved_key = self.configer.get_keyborad_key().split(",")

        self.letter_interval_duration = letter_interval_duration
        self.word_interval_duration = word_interval_duration

        self.tx_runtime.refresh_runtime(
            dot_duration=dot_duration,
            dash_duration=dash_duration,
            letter_interval_duration=letter_interval_duration,
            word_interval_duration=word_interval_duration,
            keyer_mode=keyer_mode,
            send_buzz_status=send_buzz_status,
            saved_key=saved_key,
        )
        self._update_timing_hint()

    def refresh_runtime(self) -> None:
        self._refresh_runtime()

    def recreate_buzzer(self) -> None:
        old = self.buzzer
        self.buzzer = self._create_buzzer()
        self.tx_runtime.buzzer = self.buzzer
        if old is not self.buzzer and old and hasattr(old, "close"):
            try:
                old.close()
            except Exception:
                pass

    def start_round(self, task: RoundTask, on_done) -> None:
        self._task = task
        self._on_done = on_done
        self._index = 0

        self._all_morse_inputs = []
        self._all_decoded_inputs = []
        self._all_events = []
        self._sum_decode_match = 0.0
        self._sum_rhythm = 0.0
        self._sum_score = 0.0
        self._round_count = 0
        self._current_submitted = False
        self._current_feedback_text = ""
        self._current_decoded_text = ""
        self.label_submit_state.setText(self.tr("状态：未提交"))
        self._per_char_errors = defaultdict(int)
        self._confusions = defaultdict(int)
        self.cw_button.setIcon(FIF.SEND)
        self.label_feedback.setText(self.tr("开始按键发报。"))

        self._refresh_runtime()
        self._update_timing_hint()
        self._show_current_question()

    def stop_round(self) -> None:
        self._stop_gap_timers()
        self.tx_runtime.stop_all(notify=False)
        self._task = None
        self._on_done = None
        self._current_submitted = False
        self._current_feedback_text = ""
        self._current_decoded_text = ""
        self.cw_button.setEnabled(True)
        self.cw_button.setIcon(FIF.SEND)
        self.label_submit_state.setText(self.tr("状态：已停止"))
        self.label_progress.setText(self.tr("已停止"))
        self.label_timing.setText(self.tr("WPM -- | Farn --"))
        self.label_feedback.setText(self.tr("训练已停止。"))

    def _show_current_question(self) -> None:
        if self._task is None:
            return
        if self._index >= len(self._task.targets):
            self._finish_round()
            return

        self._update_timing_hint()
        self._stop_gap_timers()
        self.tx_runtime.stop_all(notify=False)
        self._current_morse = ""
        self._current_events = []
        self._current_submitted = False
        self._current_feedback_text = ""
        self._current_decoded_text = ""
        self.input_box.clear()
        self.decoded_box.clear()
        self.cw_button.setEnabled(True)
        self.cw_button.setIcon(FIF.SEND)
        self.label_submit_state.setText(self.tr("状态：未提交"))
        self.label_feedback.setText(self.tr("点击“提交”查看结果，或直接“下一题”。"))

        target = self._task.targets[self._index]
        self.label_progress.setText(
            self.tr("题目 {0}/{1}").format(self._index + 1, len(self._task.targets))
        )
        display_text = self.tr("题目隐藏，请直接发报") if self._task.no_hint else target
        self.label_question.setText(display_text)
        self._started_ms = time.monotonic() * 1000.0
        self.setFocus(Qt.OtherFocusReason)

    def on_btn_send_message_pressed(self) -> None:
        if self._task is None or self._current_submitted:
            return
        if self.tx_runtime.press_manual(
            ready=True,
            allow_transmit=True,
            max_interval_seconds=50,
        ):
            self.cw_button.setIcon(FIF.SEND_FILL)

    def on_btn_send_message_released(self) -> None:
        if self._task is None or self._current_submitted:
            return
        if self.tx_runtime.release_manual():
            self.cw_button.setIcon(FIF.SEND)

    def keyPressEvent(self, event) -> None:
        if self._task is None or self._current_submitted:
            super().keyPressEvent(event)
            return
        self.tx_runtime.handle_key_press(
            key=event.key(),
            is_auto_repeat=event.isAutoRepeat(),
            ready=True,
            allow_transmit=True,
            max_interval_seconds=10,
        )

    def keyReleaseEvent(self, event) -> None:
        if self._task is None or self._current_submitted:
            super().keyReleaseEvent(event)
            return
        self.tx_runtime.handle_key_release(
            key=event.key(),
            is_auto_repeat=event.isAutoRepeat(),
        )

    def _append_symbol(self, symbol: str) -> None:
        self._current_morse += symbol
        self.input_box.setPlainText(self._current_morse)

    def _tx_runtime_on_manual_symbol(self, morse_code, duration_ms, gap_ms, manual_duration_ms) -> None:
        self._append_symbol(morse_code)
        self._current_events.append(
            {
                "symbol": str(morse_code),
                "duration_ms": float(max(1.0, manual_duration_ms or duration_ms)),
                "gap_ms": float(max(0.0, gap_ms)),
            }
        )

    def _tx_runtime_on_auto_symbol(self, event: AutoElementEvent) -> None:
        self._append_symbol(event.symbol)
        self._current_events.append(
            {
                "symbol": str(event.symbol),
                "duration_ms": float(max(1, int(event.keydown_ms))),
                "gap_ms": float(max(0, int(event.gap_ms))),
            }
        )

    def start_letter_timer(self) -> None:
        self.letter_timer.start(self.letter_interval_duration)

    def start_word_timer(self) -> None:
        self.word_timer.start(self.word_interval_duration)

    def handle_letter_timeout(self) -> None:
        if self._current_submitted:
            return
        self._current_morse += "/"
        self.input_box.setPlainText(self._current_morse)
        self.start_word_timer()

    def handle_word_timeout(self) -> None:
        if self._current_submitted:
            return
        self._current_morse += "//"
        self.input_box.setPlainText(self._current_morse)

    @staticmethod
    def _normalize_morse(raw: str) -> str:
        value = re.sub(r"[^.\-/]", "", str(raw or ""))
        value = value.rstrip("/")
        if not value:
            return ""

        chunks: list[str] = []
        i = 0
        while i < len(value):
            ch = value[i]
            if ch != "/":
                chunks.append(ch)
                i += 1
                continue
            j = i
            while j < len(value) and value[j] == "/":
                j += 1
            run_len = j - i
            chunks.append("/") if run_len == 1 else chunks.append("///")
            i = j
        return "".join(chunks)

    @staticmethod
    def _update_error_maps(
        result,
        per_char_errors: dict[str, int],
        confusions: dict[tuple[str, str], int],
    ) -> None:
        for cell in result.cells:
            if cell.status == "correct":
                continue
            expected = (cell.expected or "").strip().upper()
            actual = (cell.actual or "").strip().upper()
            if expected:
                per_char_errors[expected] += 1
            if expected and actual and expected != actual:
                confusions[(expected, actual)] += 1

    def _compute_rhythm_score(self, events: list[dict[str, float]]) -> float:
        if self._task is None or not events:
            return 0.0

        timing = self._task.timing
        dot_ms = float(max(1, int(timing.get("dot_ms", 80))))
        dash_ms = float(max(1, int(timing.get("dash_ms", dot_ms * 3))))
        letter_gap_ms = float(max(1, int(timing.get("letter_gap_ms", dot_ms * 3))))
        word_gap_ms = float(max(1, int(timing.get("word_gap_ms", dot_ms * 7))))

        duration_err = 0.0
        duration_count = 0
        gap_err = 0.0
        gap_count = 0

        for event in events:
            symbol = str(event.get("symbol", ""))
            duration = float(max(1.0, event.get("duration_ms", 1.0)))
            expected_duration = dot_ms if symbol == "." else dash_ms
            duration_err += abs(duration - expected_duration) / expected_duration
            duration_count += 1

            gap_ms = float(max(0.0, event.get("gap_ms", 0.0)))
            if gap_ms > 0:
                candidates = [dot_ms, letter_gap_ms, word_gap_ms]
                best = min(abs(gap_ms - val) / val for val in candidates)
                gap_err += best
                gap_count += 1

        avg_duration_err = (duration_err / duration_count) if duration_count else 1.0
        avg_gap_err = (gap_err / gap_count) if gap_count else avg_duration_err

        duration_penalty = min(100.0, avg_duration_err * 100.0)
        gap_penalty = min(100.0, avg_gap_err * 100.0)
        rhythm = 100.0 - (duration_penalty * 0.7 + gap_penalty * 0.3)
        return max(0.0, min(100.0, rhythm))

    def _commit_current_answer(self, show_feedback: bool) -> bool:
        if self._task is None or self._index >= len(self._task.targets):
            return False
        if self._current_submitted:
            if show_feedback:
                if self._current_decoded_text:
                    self.decoded_box.setPlainText(self._current_decoded_text)
                if self._current_feedback_text:
                    self.label_feedback.setText(self._current_feedback_text)
            self.label_submit_state.setText(self.tr("状态：已提交，可下一题"))
            return True

        self._stop_gap_timers()

        target = self._task.targets[self._index]
        morse_input = self._normalize_morse(self._current_morse)
        decoded = self.translator.morse_to_text(morse_input).strip().upper() if morse_input else ""

        decode_result = align_sequences(
            list(target.upper()),
            list(decoded.upper()),
            normalize=lambda ch: str(ch).upper(),
        )
        self._update_error_maps(decode_result, self._per_char_errors, self._confusions)

        decode_match = float(decode_result.accuracy)
        rhythm = self._compute_rhythm_score(self._current_events)
        raw_score = 0.6 * decode_match + 0.4 * rhythm
        tx_score = round(raw_score, 2)

        self._all_morse_inputs.append(morse_input)
        self._all_decoded_inputs.append(decoded)
        self._all_events.append(list(self._current_events))
        self._sum_decode_match += decode_match
        self._sum_rhythm += rhythm
        self._sum_score += raw_score
        self._round_count += 1

        total_errors = int(decode_result.replace) + int(decode_result.missing) + int(decode_result.extra)
        judge_text = self.tr("正确") if total_errors == 0 else self.tr("有误")
        detail_text = self._build_error_detail(decode_result)
        bias_text = self._build_bias_feedback(decode_result)
        feedback_text = self.tr("本题判定：{0} | 准确率 {1:.1f}% | {2} | 节奏 {3:.1f} | 总分 {4:.1f} | {5}").format(
            judge_text,
            float(decode_result.accuracy),
            detail_text,
            float(rhythm),
            float(tx_score),
            bias_text,
        )
        self._current_submitted = True
        self._current_feedback_text = feedback_text
        self._current_decoded_text = decoded
        self.cw_button.setEnabled(False)
        self.label_submit_state.setText(self.tr("状态：已提交，可下一题"))
        if show_feedback:
            self.decoded_box.setPlainText(decoded)
            self.label_feedback.setText(feedback_text)
        return True

    def submit_current_answer(self) -> None:
        self._commit_current_answer(show_feedback=True)

    def next_question(self) -> None:
        if self._task is None or self._index >= len(self._task.targets):
            return
        if not self._commit_current_answer(show_feedback=False):
            return
        self._index += 1
        self._show_current_question()

    def _finish_round(self) -> None:
        if self._task is None or self._on_done is None:
            return

        count = max(1, int(self._round_count))
        avg_decode_match = self._sum_decode_match / float(count)
        avg_rhythm = self._sum_rhythm / float(count)
        avg_score = self._sum_score / float(count)

        result = TrainingResult(
            mode="tx",
            target_text=" || ".join(self._task.targets),
            user_text=" || ".join(self._all_morse_inputs),
            decoded_text=" || ".join(self._all_decoded_inputs),
            metrics=TrainingMetrics(
                tx_rhythm=round(avg_rhythm, 2),
                tx_decode_match=round(avg_decode_match, 2),
                tx_score=round(avg_score, 2),
            ),
            per_char_errors=dict(self._per_char_errors),
            confusion_pairs=dict(self._confusions),
            raw={
                "question_count": len(self._task.targets),
                "timing": dict(self._task.timing),
            },
        )

        self.label_progress.setText(self.tr("本轮完成"))
        self.label_feedback.setText(
            self.tr("发报解码：{0:.1f}% | 节奏：{1:.1f} | 总分：{2:.1f}").format(
                avg_decode_match,
                avg_rhythm,
                avg_score,
            )
        )

        callback = self._on_done
        self._on_done = None
        callback(result)

    def apply_ui_scale(self, scale: float) -> None:
        factor = max(0.8, min(1.6, float(scale)))
        font = self.font()
        base = 10.0
        font.setPointSizeF(max(8.0, base * factor))
        self.setFont(font)
