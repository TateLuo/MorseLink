from __future__ import annotations

import time
from collections import defaultdict

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout, QWidget

from ui_widgets import PushButton, TextEdit
from ui_widgets import FluentIcon as FIF

from morselink.training.models import RoundTask, TrainingMetrics, TrainingResult
from utils.sound import BuzzerSimulator
from utils.training_feedback import align_sequences
from utils.translator import MorseCodeTranslator


class TrainingRxRunner(QWidget):
    mode = "rx"

    def __init__(self, context=None, parent=None) -> None:
        super().__init__(parent)
        self.context = context
        self.translator = MorseCodeTranslator()
        self.buzzer = self._create_buzzer()

        self._task: RoundTask | None = None
        self._on_done = None
        self._index = 0
        self._started_ms = 0.0

        self._answers: list[str] = []
        self._latencies: list[float] = []
        self._total_expected = 0
        self._total_correct = 0
        self._per_char_errors: dict[str, int] = defaultdict(int)
        self._confusions: dict[tuple[str, str], int] = defaultdict(int)
        self._current_submitted = False
        self._current_feedback_text = ""
        self._playback_active = False

        self._init_ui()
        self._bind_playback_callback()

    def _create_buzzer(self):
        if self.context and hasattr(self.context, "create_buzzer"):
            return self.context.create_buzzer()
        return BuzzerSimulator()

    def _bind_playback_callback(self) -> None:
        if hasattr(self.buzzer, "set_playback_callback"):
            try:
                self.buzzer.set_playback_callback(self._on_playback_status)
            except Exception:
                pass

    def _set_play_button(self, playing: bool) -> None:
        self.play_button.setIcon(FIF.PAUSE if playing else FIF.PLAY)
        self.play_button.setText(self.tr("暂停") if playing else self.tr("播放"))

    def _on_playback_status(self, status) -> None:
        if status == "started":
            self._playback_active = True
            QTimer.singleShot(0, lambda: self._set_play_button(True))
            return
        if status in ("finished", "stopped"):
            self._playback_active = False
            QTimer.singleShot(0, lambda: self._set_play_button(False))

    def _is_playback_active(self) -> bool:
        if self._playback_active:
            return True
        try:
            return bool(getattr(self.buzzer, "is_playing", False))
        except Exception:
            return False

    def _build_bias_feedback(self, result) -> str:
        if result.missing > result.extra and result.missing >= result.replace:
            return self.tr("偏置反馈：漏码偏多，建议放慢一点并拉开字符间隔。")
        if result.extra > result.missing and result.extra >= result.replace:
            return self.tr("偏置反馈：多码偏多，建议按键更干净，减少粘连。")
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
                details.append(self.tr("第{0}位漏抄({1})").format(pos, cell.expected))
            elif cell.status == "extra":
                pos = (int(cell.actual_index) + 1) if int(cell.actual_index) >= 0 else int(result.total_expected) + 1
                details.append(self.tr("第{0}位多抄({1})").format(pos, cell.actual))

            if len(details) >= max_items:
                break

        suffix = self.tr(" 等{0}处").format(total_errors) if total_errors > len(details) else ""
        return self.tr("错误点：") + "；".join(details) + suffix

    def _force_stop_playback(self) -> None:
        buzzer = self.buzzer
        if buzzer is None:
            return

        for method in ("stop_playing_morse_code", "stop_play_for_duration", "stop"):
            if not hasattr(buzzer, method):
                continue
            try:
                getattr(buzzer, method)()
            except Exception:
                pass

        deadline = time.monotonic() + 0.08
        while time.monotonic() < deadline:
            try:
                if not bool(getattr(buzzer, "is_playing", False)):
                    return
            except Exception:
                return
            time.sleep(0.005)

        # Fallback: recreate stream to hard-stop any lingering audio.
        try:
            replacement = self._create_buzzer()
        except Exception:
            return

        self.buzzer = replacement
        self._bind_playback_callback()
        if replacement is not buzzer and hasattr(buzzer, "close"):
            try:
                buzzer.close()
            except Exception:
                pass
        self._playback_active = False
        QTimer.singleShot(0, lambda: self._set_play_button(False))

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(10)

        top_card = QWidget(self)
        top_card.setObjectName("rxTopCard")
        top_row = QHBoxLayout(top_card)
        top_row.setContentsMargins(12, 8, 12, 8)
        top_row.setSpacing(10)

        self.label_title = QLabel(self.tr("听写 (Rx)"), top_card)
        self.label_title.setObjectName("rxTitleChip")
        top_row.addWidget(self.label_title)

        self.label_progress = QLabel(self.tr("未开始"), top_card)
        self.label_progress.setObjectName("rxProgress")
        top_row.addWidget(self.label_progress)
        top_row.addStretch(1)

        self.label_submit_state = QLabel(self.tr("状态：未提交"), top_card)
        self.label_submit_state.setObjectName("rxSubmitState")
        top_row.addWidget(self.label_submit_state)
        layout.addWidget(top_card)

        question_card = QWidget(self)
        question_card.setObjectName("rxQuestionCard")
        question_layout = QVBoxLayout(question_card)
        question_layout.setContentsMargins(14, 12, 14, 12)
        question_layout.setSpacing(8)

        self.label_question_caption = QLabel(self.tr("本题内容"), question_card)
        self.label_question_caption.setObjectName("rxCaption")
        question_layout.addWidget(self.label_question_caption)

        question_row = QHBoxLayout()
        question_row.setSpacing(10)
        self.label_question = QLabel(self.tr("题目将在这里显示"), question_card)
        self.label_question.setObjectName("rxQuestionText")
        self.label_question.setWordWrap(True)
        self.label_question.setMinimumHeight(56)
        question_row.addWidget(self.label_question, 1)

        self.play_button = PushButton(FIF.PLAY, self.tr("播放"), question_card)
        self.play_button.setObjectName("rxPlayButton")
        self.play_button.setCursor(Qt.PointingHandCursor)
        self.play_button.clicked.connect(self.toggle_play_current_question)
        question_row.addWidget(self.play_button)
        question_layout.addLayout(question_row)
        layout.addWidget(question_card)

        answer_card = QWidget(self)
        answer_card.setObjectName("rxAnswerCard")
        answer_layout = QVBoxLayout(answer_card)
        answer_layout.setContentsMargins(14, 12, 14, 12)
        answer_layout.setSpacing(8)

        self.label_input_caption = QLabel(self.tr("输入答案"), answer_card)
        self.label_input_caption.setObjectName("rxCaption")
        answer_layout.addWidget(self.label_input_caption)

        self.input_box = TextEdit(answer_card)
        self.input_box.setPlaceholderText(self.tr("输入你听到的内容，词组请用空格分隔"))
        self.input_box.setAcceptRichText(False)
        self.input_box.setMinimumHeight(180)
        self.input_box.setObjectName("rxInputBox")
        answer_layout.addWidget(self.input_box, 1)

        self.label_feedback = QLabel(self.tr("等待开始"), answer_card)
        self.label_feedback.setWordWrap(True)
        self.label_feedback.setObjectName("rxFeedback")
        answer_layout.addWidget(self.label_feedback)
        layout.addWidget(answer_card, 1)

        action_card = QWidget(self)
        action_card.setObjectName("rxActionCard")
        action_row = QHBoxLayout(action_card)
        action_row.setContentsMargins(12, 10, 12, 10)
        action_row.setSpacing(8)

        self.label_timing = QLabel(self.tr("WPM -- | Farn --"), action_card)
        self.label_timing.setObjectName("rxTiming")
        action_row.addWidget(self.label_timing, 1)

        self.submit_button = PushButton(FIF.SEARCH, self.tr("提交"), action_card)
        self.submit_button.setObjectName("rxSecondaryButton")
        self.submit_button.setCursor(Qt.PointingHandCursor)
        self.submit_button.clicked.connect(self.submit_current_answer)
        action_row.addWidget(self.submit_button)

        self.next_button = PushButton(self.tr("下一题"), action_card)
        self.next_button.setObjectName("rxPrimaryButton")
        self.next_button.setCursor(Qt.PointingHandCursor)
        self.next_button.clicked.connect(self.next_question)
        action_row.addWidget(self.next_button)
        layout.addWidget(action_card)

        self._apply_styles()

    def _apply_styles(self) -> None:
        self.setStyleSheet(
            """
            QWidget#rxTopCard, QWidget#rxQuestionCard, QWidget#rxAnswerCard, QWidget#rxActionCard {
                background: #f6f8fc;
                border: 1px solid #d7e2f2;
                border-radius: 12px;
            }
            QLabel#rxTitleChip {
                background: qlineargradient(
                    x1: 0, y1: 0, x2: 1, y2: 0,
                    stop: 0 #d9ecff,
                    stop: 1 #c7ddff
                );
                color: #1e4f9d;
                border: 1px solid #a9c8f0;
                border-radius: 16px;
                padding: 4px 12px;
                font-weight: 700;
            }
            QLabel#rxProgress {
                color: #2c3e5d;
                font-size: 14px;
                font-weight: 700;
            }
            QLabel#rxSubmitState {
                background: #eaf2ff;
                color: #2d5d9b;
                border: 1px solid #b9d0f2;
                border-radius: 12px;
                padding: 3px 10px;
            }
            QLabel#rxCaption {
                color: #526888;
                font-weight: 600;
            }
            QLabel#rxQuestionText {
                color: #1d2b3f;
                font-size: 20px;
                font-weight: 700;
                letter-spacing: 1px;
            }
            QTextEdit#rxInputBox {
                background: #ffffff;
                border: 1px solid #c8d6ea;
                border-radius: 10px;
                padding: 8px;
                selection-background-color: #a5cbff;
            }
            QLabel#rxFeedback {
                color: #375171;
                background: #edf4ff;
                border: 1px solid #c9dbf4;
                border-radius: 8px;
                padding: 8px;
            }
            QLabel#rxTiming {
                color: #3d5473;
                font-weight: 600;
            }
            QPushButton#rxPlayButton {
                color: #ffffff;
                background: qlineargradient(
                    x1: 0, y1: 0, x2: 1, y2: 0,
                    stop: 0 #5aa8ff,
                    stop: 1 #2f78eb
                );
                border: 1px solid #2d71da;
                border-radius: 18px;
                min-height: 36px;
                padding: 0 16px;
                font-weight: 700;
            }
            QPushButton#rxPlayButton:hover {
                background: #418ce8;
            }
            QPushButton#rxSecondaryButton {
                background: #ffffff;
                color: #2e4564;
                border: 1px solid #c6d3e7;
                border-radius: 8px;
                min-height: 34px;
                padding: 0 16px;
                font-weight: 600;
            }
            QPushButton#rxSecondaryButton:hover {
                background: #f1f5fb;
            }
            QPushButton#rxPrimaryButton {
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
            QPushButton#rxPrimaryButton:hover {
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

    def start_round(self, task: RoundTask, on_done) -> None:
        self._task = task
        self._on_done = on_done
        self._index = 0
        self._answers = []
        self._latencies = []
        self._total_expected = 0
        self._total_correct = 0
        self._per_char_errors = defaultdict(int)
        self._confusions = defaultdict(int)
        self._current_submitted = False
        self._current_feedback_text = ""
        self.label_submit_state.setText(self.tr("状态：未提交"))
        self.label_feedback.setText(self.tr("已开始收报轮次"))
        self._update_timing_hint()
        self._show_current_question()

    def stop_round(self) -> None:
        self._task = None
        self._on_done = None
        self._force_stop_playback()
        self._set_play_button(False)
        self._current_submitted = False
        self._current_feedback_text = ""
        self.label_submit_state.setText(self.tr("状态：已停止"))
        self.label_progress.setText(self.tr("已停止"))
        self.label_timing.setText(self.tr("WPM -- | Farn --"))
        self.label_feedback.setText(self.tr("训练已停止。"))

    def recreate_buzzer(self) -> None:
        old = self.buzzer
        self.buzzer = self._create_buzzer()
        self._bind_playback_callback()
        if old is not self.buzzer and old and hasattr(old, "close"):
            try:
                old.close()
            except Exception:
                pass

    def _show_current_question(self) -> None:
        if self._task is None:
            return
        if self._index >= len(self._task.targets):
            self._finish_round()
            return

        self._update_timing_hint()
        target = self._task.targets[self._index]
        display_text = self.tr("题目隐藏，请播放后输入") if self._task.no_hint else target
        self.label_progress.setText(
            self.tr("题目 {0}/{1}").format(self._index + 1, len(self._task.targets))
        )
        self.label_question.setText(display_text)
        self._current_submitted = False
        self._current_feedback_text = ""
        self.input_box.clear()
        self.input_box.setReadOnly(False)
        self.input_box.setFocus()
        self.label_submit_state.setText(self.tr("状态：未提交"))
        self.label_feedback.setText(self.tr("点击“提交”查看结果，或直接“下一题”。"))
        self._started_ms = time.monotonic() * 1000.0
        self.play_current_question()

    def toggle_play_current_question(self) -> None:
        if self._task is None or self._index >= len(self._task.targets):
            return
        if self._is_playback_active():
            self._force_stop_playback()
            self._set_play_button(False)
            return
        self.play_current_question()

    def play_current_question(self) -> None:
        if self._task is None or self._index >= len(self._task.targets):
            return

        self._force_stop_playback()
        target = self._task.targets[self._index]
        morse_code = self.translator.text_to_morse(target)
        timing = self._task.timing
        try:
            self.buzzer.play_morse_code(
                morse_code,
                int(timing.get("dot_ms", 80)),
                int(timing.get("dash_ms", 240)),
                int(timing.get("letter_gap_ms", 240)),
                int(timing.get("word_gap_ms", 560)),
            )
            self._set_play_button(True)
        except Exception:
            # Playback errors should not block training flow.
            pass

    def _commit_current_answer(self, show_feedback: bool) -> bool:
        if self._task is None or self._index >= len(self._task.targets):
            return False
        if self._current_submitted:
            if show_feedback and self._current_feedback_text:
                self.label_feedback.setText(self._current_feedback_text)
            self.label_submit_state.setText(self.tr("状态：已提交，可下一题"))
            return True

        # If audio is still playing when user submits, stop it first.
        self._force_stop_playback()

        target = self._task.targets[self._index]
        actual = self.input_box.toPlainText().strip()
        latency = max(0.0, time.monotonic() * 1000.0 - self._started_ms)

        result = align_sequences(
            list(target),
            list(actual),
            normalize=lambda ch: str(ch).lower(),
        )

        self._answers.append(actual)
        self._latencies.append(latency)
        self._total_expected += int(result.total_expected)
        self._total_correct += int(result.correct)

        for cell in result.cells:
            if cell.status == "correct":
                continue
            expected = (cell.expected or "").strip().upper()
            actual_char = (cell.actual or "").strip().upper()
            if expected:
                self._per_char_errors[expected] += 1
            if expected and actual_char and expected != actual_char:
                self._confusions[(expected, actual_char)] += 1

        total_errors = int(result.replace) + int(result.missing) + int(result.extra)
        judge_text = self.tr("正确") if total_errors == 0 else self.tr("有误")
        detail_text = self._build_error_detail(result)
        bias_text = self._build_bias_feedback(result)
        feedback_text = self.tr("本题判定：{0} | 准确率 {1:.1f}% | {2} | {3}").format(
            judge_text,
            float(result.accuracy),
            detail_text,
            bias_text,
        )
        self._current_submitted = True
        self._current_feedback_text = feedback_text
        self.input_box.setReadOnly(True)
        self.label_submit_state.setText(self.tr("状态：已提交，可下一题"))
        if show_feedback:
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

        total_expected = max(1, int(self._total_expected))
        rx_acc = float(self._total_correct) / float(total_expected) * 100.0
        avg_latency = sum(self._latencies) / float(len(self._latencies)) if self._latencies else 0.0

        result = TrainingResult(
            mode="rx",
            target_text=" || ".join(self._task.targets),
            user_text=" || ".join(self._answers),
            decoded_text="",
            metrics=TrainingMetrics(
                rx_acc=round(rx_acc, 2),
                rx_latency_ms=round(avg_latency, 2),
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
            self.tr("收报均分：{0:.1f}% | 平均反应：{1:.0f}ms").format(rx_acc, avg_latency)
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
