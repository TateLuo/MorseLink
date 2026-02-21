from __future__ import annotations

import logging
from typing import Callable

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QGridLayout, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from ui_widgets import FluentIcon as FIF
from ui_widgets import PushButton
from utils.sound import BuzzerSimulator
from utils.translator import MorseCodeTranslator

logger = logging.getLogger(__name__)


class TrainingTutorialPage(QWidget):
    """Beginner-first tutorial page (not quiz-based) for Morse fundamentals."""

    MORSE_TABLE = {
        "A": ".-",
        "B": "-...",
        "C": "-.-.",
        "D": "-..",
        "E": ".",
        "F": "..-.",
        "G": "--.",
        "H": "....",
        "I": "..",
        "J": ".---",
        "K": "-.-",
        "L": ".-..",
        "M": "--",
        "N": "-.",
        "O": "---",
        "P": ".--.",
        "Q": "--.-",
        "R": ".-.",
        "S": "...",
        "T": "-",
        "U": "..-",
        "V": "...-",
        "W": ".--",
        "X": "-..-",
        "Y": "-.--",
        "Z": "--..",
        "0": "-----",
        "1": ".----",
        "2": "..---",
        "3": "...--",
        "4": "....-",
        "5": ".....",
        "6": "-....",
        "7": "--...",
        "8": "---..",
        "9": "----.",
        ".": ".-.-.-",
        ",": "--..--",
        "?": "..--..",
        "/": "-..-.",
        "=": "-...-",
        "@": ".--.-.",
        "-": "-....-",
        "!": "-.-.--",
    }

    KEYBOARD_ROWS = [
        ["1", "2", "3", "4", "5", "6", "7", "8", "9", "0"],
        ["Q", "W", "E", "R", "T", "Y", "U", "I", "O", "P"],
        ["A", "S", "D", "F", "G", "H", "J", "K", "L"],
        ["Z", "X", "C", "V", "B", "N", "M"],
        [".", ",", "?", "/", "=", "@", "-", "!"],
    ]

    DOT_MS = 90
    DASH_MS = 270
    LETTER_GAP_MS = 270
    WORD_GAP_MS = 630
    PLAY_RETRY_DELAY_MS = 40

    def __init__(
        self,
        context=None,
        *,
        on_exit: Callable[[bool], None] | None = None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.context = context
        self._on_exit = on_exit
        self.translator = MorseCodeTranslator()
        self.buzzer = self._create_buzzer()

        self._selected_char = "A"
        self._practice_code = ""

        self._init_ui()
        self._apply_styles()
        self._set_selected_char(self._selected_char, autoplay=False)

    def _create_buzzer(self):
        if self.context and hasattr(self.context, "create_buzzer"):
            return self.context.create_buzzer()
        return BuzzerSimulator()

    def recreate_buzzer(self) -> None:
        old = self.buzzer
        self.buzzer = self._create_buzzer()
        if old is not self.buzzer and old and hasattr(old, "close"):
            try:
                old.close()
            except Exception:
                pass

    def stop_audio(self) -> None:
        for method in ("stop_playing_morse_code", "stop_play_for_duration", "stop"):
            if hasattr(self.buzzer, method):
                try:
                    getattr(self.buzzer, method)()
                except Exception:
                    pass

    def load_default_selection(self) -> None:
        self._set_selected_char("A", autoplay=False)
        self._practice_code = ""
        self._refresh_practice_view()

    def _init_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(6, 6, 6, 6)
        root.setSpacing(10)

        self.title_label = QLabel(self.tr("新手教学：先认识点划再进入训练"), self)
        self.title_label.setObjectName("tutorialTitle")
        root.addWidget(self.title_label)

        self.subtitle_label = QLabel(
            self.tr("点击下方键盘卡片学习字符；支持听音、点划输入、间隔理解（/ 为字母间隔，/// 为单词间隔）。"),
            self,
        )
        self.subtitle_label.setWordWrap(True)
        self.subtitle_label.setObjectName("tutorialSubtitle")
        root.addWidget(self.subtitle_label)

        self.hero_card = QWidget(self)
        self.hero_card.setObjectName("tutorialHero")
        hero_row = QHBoxLayout(self.hero_card)
        hero_row.setContentsMargins(12, 10, 12, 10)
        hero_row.setSpacing(8)

        self.btn_finish = PushButton(FIF.PLAY, self.tr("完成教学并进入训练"), self.hero_card)
        self.btn_finish.setObjectName("tutorialPrimaryButton")
        self.btn_finish.setCursor(Qt.PointingHandCursor)
        self.btn_finish.clicked.connect(self._finish_tutorial)
        hero_row.addWidget(self.btn_finish)

        self.btn_skip = PushButton(self.tr("稍后再学（本次跳过）"), self.hero_card)
        self.btn_skip.setObjectName("tutorialSecondaryButton")
        self.btn_skip.setCursor(Qt.PointingHandCursor)
        self.btn_skip.clicked.connect(self._skip_tutorial)
        hero_row.addWidget(self.btn_skip)
        root.addWidget(self.hero_card)

        self.keyboard_card = QWidget(self)
        self.keyboard_card.setObjectName("tutorialCard")
        keyboard_layout = QVBoxLayout(self.keyboard_card)
        keyboard_layout.setContentsMargins(12, 10, 12, 10)
        keyboard_layout.setSpacing(8)

        keyboard_title = QLabel(self.tr("键盘卡片：字母 / 数字 / 常用符号"), self.keyboard_card)
        keyboard_title.setObjectName("tutorialCardTitle")
        keyboard_layout.addWidget(keyboard_title)

        self.keyboard_grid = QGridLayout()
        self.keyboard_grid.setHorizontalSpacing(6)
        self.keyboard_grid.setVerticalSpacing(6)
        for row_idx, row_data in enumerate(self.KEYBOARD_ROWS):
            start_col = max(0, (10 - len(row_data)) // 2)
            for col_idx, token in enumerate(row_data):
                btn = PushButton(token, self.keyboard_card)
                btn.setObjectName("tutorialKeyButton")
                btn.setCursor(Qt.PointingHandCursor)
                btn.clicked.connect(lambda _=False, ch=token: self._set_selected_char(ch, autoplay=True))
                self.keyboard_grid.addWidget(btn, row_idx, start_col + col_idx)
        keyboard_layout.addLayout(self.keyboard_grid)
        root.addWidget(self.keyboard_card)

        self.detail_card = QWidget(self)
        self.detail_card.setObjectName("tutorialCard")
        detail_layout = QVBoxLayout(self.detail_card)
        detail_layout.setContentsMargins(12, 10, 12, 10)
        detail_layout.setSpacing(8)

        detail_title = QLabel(self.tr("当前学习"), self.detail_card)
        detail_title.setObjectName("tutorialCardTitle")
        detail_layout.addWidget(detail_title)

        detail_row = QHBoxLayout()
        detail_row.setSpacing(8)
        self.label_selected_char = QLabel("A", self.detail_card)
        self.label_selected_char.setObjectName("tutorialSelectedChar")
        self.label_selected_char.setAlignment(Qt.AlignCenter)
        self.label_selected_char.setFixedSize(72, 72)
        detail_row.addWidget(self.label_selected_char)

        text_col = QVBoxLayout()
        text_col.setSpacing(4)
        self.label_selected_morse = QLabel(".-", self.detail_card)
        self.label_selected_morse.setObjectName("tutorialSelectedMorse")
        text_col.addWidget(self.label_selected_morse)
        self.label_selected_hint = QLabel("", self.detail_card)
        self.label_selected_hint.setWordWrap(True)
        self.label_selected_hint.setObjectName("tutorialHint")
        text_col.addWidget(self.label_selected_hint)
        detail_row.addLayout(text_col, 1)
        detail_layout.addLayout(detail_row)

        control_row = QHBoxLayout()
        control_row.setSpacing(8)
        self.btn_play_selected = PushButton(FIF.PLAY, self.tr("听一遍"), self.detail_card)
        self.btn_play_selected.setObjectName("tutorialActionButton")
        self.btn_play_selected.setCursor(Qt.PointingHandCursor)
        self.btn_play_selected.clicked.connect(self._play_selected)
        control_row.addWidget(self.btn_play_selected)

        self.btn_add_selected = PushButton(FIF.SEND, self.tr("加入练习串"), self.detail_card)
        self.btn_add_selected.setObjectName("tutorialActionButton")
        self.btn_add_selected.setCursor(Qt.PointingHandCursor)
        self.btn_add_selected.clicked.connect(self._append_selected_to_practice)
        control_row.addWidget(self.btn_add_selected)

        self.btn_play_gap_demo = PushButton(FIF.SEARCH, self.tr("间隔示例"), self.detail_card)
        self.btn_play_gap_demo.setObjectName("tutorialActionButton")
        self.btn_play_gap_demo.setCursor(Qt.PointingHandCursor)
        self.btn_play_gap_demo.clicked.connect(self._play_gap_demo)
        control_row.addWidget(self.btn_play_gap_demo)
        control_row.addStretch(1)
        detail_layout.addLayout(control_row)
        root.addWidget(self.detail_card)

        self.practice_card = QWidget(self)
        self.practice_card.setObjectName("tutorialCard")
        practice_layout = QVBoxLayout(self.practice_card)
        practice_layout.setContentsMargins(12, 10, 12, 10)
        practice_layout.setSpacing(8)

        practice_title = QLabel(self.tr("点划输入体验（听与发）"), self.practice_card)
        practice_title.setObjectName("tutorialCardTitle")
        practice_layout.addWidget(practice_title)

        self.label_practice_code = QLabel(self.tr("输入串："), self.practice_card)
        self.label_practice_code.setObjectName("tutorialPracticeCode")
        self.label_practice_code.setWordWrap(True)
        practice_layout.addWidget(self.label_practice_code)

        self.label_practice_decode = QLabel(self.tr("译码："), self.practice_card)
        self.label_practice_decode.setObjectName("tutorialPracticeDecode")
        self.label_practice_decode.setWordWrap(True)
        practice_layout.addWidget(self.label_practice_decode)

        practice_buttons = QHBoxLayout()
        practice_buttons.setSpacing(6)
        for text, slot in (
            (self.tr("点 ."), self._append_dot),
            (self.tr("划 -"), self._append_dash),
            (self.tr("字母间隔 /"), self._append_letter_gap),
            (self.tr("单词间隔 ///"), self._append_word_gap),
            (self.tr("退格"), self._backspace),
            (self.tr("清空"), self._clear_practice),
        ):
            btn = PushButton(text, self.practice_card)
            btn.setObjectName("tutorialSmallButton")
            btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(slot)
            practice_buttons.addWidget(btn)
        practice_layout.addLayout(practice_buttons)

        play_row = QHBoxLayout()
        play_row.addStretch(1)
        self.btn_play_practice = PushButton(FIF.PLAY, self.tr("播放当前输入"), self.practice_card)
        self.btn_play_practice.setObjectName("tutorialActionButton")
        self.btn_play_practice.setCursor(Qt.PointingHandCursor)
        self.btn_play_practice.clicked.connect(self._play_practice)
        play_row.addWidget(self.btn_play_practice)
        practice_layout.addLayout(play_row)

        root.addWidget(self.practice_card, 1)

    def _apply_styles(self) -> None:
        self.setStyleSheet(
            """
            QLabel#tutorialTitle {
                font-size: 24px;
                font-weight: 700;
                color: #1f304a;
            }
            QLabel#tutorialSubtitle {
                color: #496182;
                font-size: 14px;
                padding-left: 2px;
            }
            QWidget#tutorialHero, QWidget#tutorialCard {
                background: #f6f8fc;
                border: 1px solid #d8e3f4;
                border-radius: 12px;
            }
            QLabel#tutorialCardTitle {
                color: #2e4566;
                font-size: 16px;
                font-weight: 700;
            }
            QPushButton#tutorialPrimaryButton {
                color: #ffffff;
                background: qlineargradient(
                    x1: 0, y1: 0, x2: 1, y2: 0,
                    stop: 0 #4cb7ff,
                    stop: 1 #2e7de7
                );
                border: 1px solid #2b73d8;
                border-radius: 18px;
                min-height: 36px;
                padding: 0 18px;
                font-weight: 700;
            }
            QPushButton#tutorialPrimaryButton:hover {
                background: #3a8fee;
            }
            QPushButton#tutorialSecondaryButton {
                color: #315070;
                background: #ffffff;
                border: 1px solid #c4d2e6;
                border-radius: 18px;
                min-height: 36px;
                padding: 0 16px;
                font-weight: 600;
            }
            QPushButton#tutorialSecondaryButton:hover {
                background: #f1f5fb;
            }
            QPushButton#tutorialKeyButton {
                background: #ffffff;
                color: #1f3c63;
                border: 1px solid #c9d8ec;
                border-radius: 8px;
                min-height: 34px;
                min-width: 34px;
                font-size: 14px;
                font-weight: 700;
            }
            QPushButton#tutorialKeyButton:hover {
                background: #eaf2ff;
                border-color: #86b4f0;
            }
            QLabel#tutorialSelectedChar {
                background: qlineargradient(
                    x1: 0, y1: 0, x2: 0, y2: 1,
                    stop: 0 #e6f4ff,
                    stop: 1 #d4ebff
                );
                color: #1f4d8f;
                border: 2px solid #8ab8ed;
                border-radius: 36px;
                font-size: 28px;
                font-weight: 700;
            }
            QLabel#tutorialSelectedMorse {
                color: #1f2f46;
                font-size: 26px;
                font-weight: 700;
                letter-spacing: 2px;
            }
            QLabel#tutorialHint {
                color: #516888;
                font-size: 14px;
            }
            QLabel#tutorialPracticeCode {
                color: #223855;
                font-size: 18px;
                font-weight: 700;
                background: #ffffff;
                border: 1px solid #c9d8ec;
                border-radius: 8px;
                padding: 8px;
            }
            QLabel#tutorialPracticeDecode {
                color: #3f587b;
                font-size: 16px;
                font-weight: 600;
                background: #edf4ff;
                border: 1px solid #c6daf6;
                border-radius: 8px;
                padding: 8px;
            }
            QPushButton#tutorialActionButton {
                color: #ffffff;
                background: #3a8fee;
                border: 1px solid #2f78db;
                border-radius: 16px;
                min-height: 32px;
                padding: 0 14px;
                font-weight: 700;
            }
            QPushButton#tutorialActionButton:hover {
                background: #2f80e6;
            }
            QPushButton#tutorialSmallButton {
                color: #2c4668;
                background: #ffffff;
                border: 1px solid #c9d7ea;
                border-radius: 8px;
                min-height: 30px;
                padding: 0 10px;
                font-weight: 600;
            }
            QPushButton#tutorialSmallButton:hover {
                background: #eef4fd;
            }
            """
        )

    def _set_selected_char(self, ch: str, *, autoplay: bool = False) -> None:
        normalized = str(ch or "").strip().upper()
        if normalized not in self.MORSE_TABLE:
            return
        self._selected_char = normalized
        morse = self.MORSE_TABLE[normalized]
        self.label_selected_char.setText(normalized)
        self.label_selected_morse.setText(morse)
        self.label_selected_hint.setText(
            self.tr("字符 {0} 对应点划：{1}。点击“听一遍”可听音，点击“加入练习串”可做点划输入。").format(
                normalized, morse
            )
        )
        if autoplay:
            self._play_morse(morse)

    def _play_selected(self) -> None:
        self._play_morse(self.MORSE_TABLE.get(self._selected_char, ""))

    def _append_selected_to_practice(self) -> None:
        morse = self.MORSE_TABLE.get(self._selected_char, "")
        if not morse:
            return
        if self._practice_code and not self._practice_code.endswith("///"):
            if not self._practice_code.endswith("/"):
                self._practice_code += "/"
        self._practice_code += morse
        self._refresh_practice_view()

    def _append_dot(self) -> None:
        self._practice_code += "."
        self._refresh_practice_view()

    def _append_dash(self) -> None:
        self._practice_code += "-"
        self._refresh_practice_view()

    def _append_letter_gap(self) -> None:
        if not self._practice_code:
            return
        if self._practice_code.endswith("///") or self._practice_code.endswith("/"):
            return
        self._practice_code += "/"
        self._refresh_practice_view()

    def _append_word_gap(self) -> None:
        if not self._practice_code:
            return
        if self._practice_code.endswith("///"):
            return
        if self._practice_code.endswith("/"):
            self._practice_code = self._practice_code.rstrip("/") + "///"
        else:
            self._practice_code += "///"
        self._refresh_practice_view()

    def _backspace(self) -> None:
        if not self._practice_code:
            return
        if self._practice_code.endswith("///"):
            self._practice_code = self._practice_code[:-3]
        else:
            self._practice_code = self._practice_code[:-1]
        self._refresh_practice_view()

    def _clear_practice(self) -> None:
        self._practice_code = ""
        self._refresh_practice_view()

    def _refresh_practice_view(self) -> None:
        code_view = self._practice_code if self._practice_code else "-"
        self.label_practice_code.setText(self.tr("输入串：{0}").format(code_view))
        decoded = ""
        if self._practice_code:
            decoded = self.translator.morse_to_text(self._practice_code).strip()
        decode_view = decoded if decoded else self.tr("（暂无可译码内容）")
        self.label_practice_decode.setText(self.tr("译码：{0}").format(decode_view))

    def _play_practice(self) -> None:
        if not self._practice_code:
            return
        self._play_morse(self._practice_code)

    def _play_gap_demo(self) -> None:
        # A/N as letter gap, A N as word gap.
        demo = ".-/-.///.-/-."
        self._play_morse(demo)
        self.label_selected_hint.setText(
            self.tr("间隔示例已播放：字符间隔用 / ，单词间隔用 ///。")
        )

    def _play_morse(self, morse: str) -> None:
        if not morse:
            return
        logger.debug("[TUTORIAL][play] request code=%s", str(morse))
        self.stop_audio()
        if self._start_playback(morse):
            return

        # Shared audio devices may occasionally fail to schedule the first short playback.
        logger.debug("[TUTORIAL][play] first attempt failed, recreate buzzer")
        self.recreate_buzzer()
        if self._start_playback(morse):
            return

        logger.debug(
            "[TUTORIAL][play] recreate attempt failed, retry after %dms",
            int(self.PLAY_RETRY_DELAY_MS),
        )
        QTimer.singleShot(self.PLAY_RETRY_DELAY_MS, lambda m=morse: self._start_playback(m))

    def _start_playback(self, morse: str) -> bool:
        text = str(morse or "").strip()
        if not text:
            return False

        try:
            # Single-element symbols (e.g. E/T) use the direct pulse path for higher reliability.
            if text == ".":
                logger.debug("[TUTORIAL][play] single_dot req_ms=%d", int(self.DOT_MS))
                self.buzzer.play_for_duration(int(self.DOT_MS), True, interval=0)
            elif text == "-":
                logger.debug("[TUTORIAL][play] single_dash req_ms=%d", int(self.DASH_MS))
                self.buzzer.play_for_duration(int(self.DASH_MS), True, interval=0)
            else:
                logger.debug(
                    "[TUTORIAL][play] morse code=%s dot_ms=%d dash_ms=%d letter_gap_ms=%d word_gap_ms=%d",
                    text,
                    int(self.DOT_MS),
                    int(self.DASH_MS),
                    int(self.LETTER_GAP_MS),
                    int(self.WORD_GAP_MS),
                )
                self.buzzer.play_morse_code(
                    text,
                    int(self.DOT_MS),
                    int(self.DASH_MS),
                    int(self.LETTER_GAP_MS),
                    int(self.WORD_GAP_MS),
                )
        except Exception:
            return False

        try:
            return bool(getattr(self.buzzer, "is_playing", False))
        except Exception:
            return True

    def _finish_tutorial(self) -> None:
        self.stop_audio()
        if self._on_exit:
            self._on_exit(True)

    def _skip_tutorial(self) -> None:
        self.stop_audio()
        if self._on_exit:
            self._on_exit(False)
