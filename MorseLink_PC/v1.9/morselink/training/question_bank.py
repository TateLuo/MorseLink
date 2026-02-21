from __future__ import annotations

import math
import random
from dataclasses import dataclass
from typing import Iterable

from utils.database_tool import DatabaseTool


LESSON_TYPES = ("letter", "QAbbreviation", "Abbreviation", "sentences", "callSign")
LETTER_WORD_BANK = (
    "AN",
    "AS",
    "AM",
    "MAN",
    "RAN",
    "ARM",
    "RAM",
    "MARS",
    "MASK",
    "RANK",
    "SANK",
    "MARK",
    "NAME",
    "MEAN",
    "SAME",
    "TONE",
    "NOTE",
    "STONE",
    "SAND",
    "SEND",
    "SEAT",
    "TEAM",
    "TIME",
    "MIND",
    "HAND",
    "HEAD",
    "HEAT",
    "HARD",
    "HEAR",
    "NEAR",
    "EAST",
    "TEAR",
    "TANK",
    "TASK",
    "SITE",
    "NOISE",
    "RADIO",
    "CQ",
    "DE",
    "TU",
    "TNX",
    "TEST",
    "RIG",
    "PWR",
    "ANT",
    "QTH",
    "WX",
    "RST",
    "CALL",
    "COPY",
    "MSG",
    "NAME",
    "UR",
    "MY",
    "HW",
    "GM",
    "GA",
    "GE",
    "GN",
    "FB",
    "BK",
    "AGN",
    "QRM",
    "QRN",
    "QSB",
    "QSY",
    "QRP",
    "QRO",
    "QSL",
    "QSO",
    "TNXFER",
    "MORSE",
    "SIGNAL",
    "REPORT",
)


@dataclass
class TaggedLesson:
    row_index: int
    title: str
    item_type: str
    tokens: list[str]
    difficulty_tag: int
    coverage_chars: set[str]


class QuestionBank:
    """Content-only generator for training targets."""

    def __init__(self, db_tool: DatabaseTool, seed: int | None = None) -> None:
        self.db_tool = db_tool
        self.random = random.Random(seed)
        self.items_by_type: dict[str, list[TaggedLesson]] = {}
        self._adaptive_chars_cache: tuple[list[str], list[str]] | None = None
        self._build_index()

    @staticmethod
    def _split_tokens(content: str, title: str) -> list[str]:
        raw = [part.strip() for part in str(content or "").split(",")]
        tokens = [token for token in raw if token]
        if not tokens and title:
            tokens = [str(title).strip()]
        return tokens

    @staticmethod
    def _extract_chars(*texts: Iterable[str]) -> set[str]:
        chars: set[str] = set()
        for seq in texts:
            for text in seq:
                for ch in str(text or ""):
                    if ch.isspace() or ch == ",":
                        continue
                    chars.add(ch.upper())
        return chars

    def _build_index(self) -> None:
        for lesson_type in LESSON_TYPES:
            rows = self.db_tool.get_listening_lessons_by_type(lesson_type)
            items: list[TaggedLesson] = []
            total = max(1, len(rows))
            for idx, row in enumerate(rows, start=1):
                title = str(row.get("title", "")).strip()
                content = str(row.get("content", "")).strip()
                tokens = self._split_tokens(content, title)
                difficulty = int(max(1, min(5, math.ceil((idx / float(total)) * 5.0))))
                coverage = self._extract_chars(tokens, [title])
                items.append(
                    TaggedLesson(
                        row_index=idx,
                        title=title,
                        item_type=lesson_type,
                        tokens=tokens,
                        difficulty_tag=difficulty,
                        coverage_chars=coverage,
                    )
                )
            self.items_by_type[lesson_type] = items

    def _select_pool(self, pool_selector: dict[str, int]) -> list[TaggedLesson]:
        pool: list[TaggedLesson] = []
        for lesson_type, count in pool_selector.items():
            items = self.items_by_type.get(str(lesson_type), [])
            if not items:
                continue
            unlock = max(1, int(count))
            pool.extend(items[: min(unlock, len(items))])

        if pool:
            return pool

        for lesson_type in LESSON_TYPES:
            if self.items_by_type.get(lesson_type):
                return list(self.items_by_type[lesson_type])
        return []

    @staticmethod
    def _dedupe_keep_order(tokens: list[str]) -> list[str]:
        result: list[str] = []
        seen: set[str] = set()
        for token in tokens:
            norm = str(token or "").strip()
            if not norm:
                continue
            key = norm.upper()
            if key in seen:
                continue
            seen.add(key)
            result.append(norm)
        return result

    @staticmethod
    def _extract_charset_tokens(charset: list[str]) -> list[str]:
        raw = [str(ch or "").strip().upper() for ch in charset]
        raw = [token for token in raw if token]
        return QuestionBank._dedupe_keep_order(raw)

    def _extract_allowed_tokens(self, pool: list[TaggedLesson]) -> list[str]:
        raw_tokens: list[str] = []
        for item in pool:
            raw_tokens.extend(item.tokens)
        deduped = self._dedupe_keep_order(raw_tokens)
        if deduped:
            return deduped
        return self._dedupe_keep_order([item.title for item in pool])

    @staticmethod
    def _build_weak_tokens(tokens: list[str], weak_chars: list[str]) -> list[str]:
        if not weak_chars:
            return []
        weak_set = {ch.upper() for ch in weak_chars if str(ch).strip()}
        result = []
        for token in tokens:
            upper = token.upper()
            if any(ch in upper for ch in weak_set):
                result.append(token)
        return result

    @staticmethod
    def _build_confusion_tokens(tokens: list[str], confusion_chars: list[str]) -> list[str]:
        if not confusion_chars:
            return []
        confusion_set = {ch.upper() for ch in confusion_chars if str(ch).strip()}
        result = []
        for token in tokens:
            upper = token.upper()
            if any(ch in upper for ch in confusion_set):
                result.append(token)
        return result

    @staticmethod
    def _is_single_letter_tokens(tokens: list[str]) -> bool:
        if not tokens:
            return False
        for token in tokens:
            text = str(token or "").strip().upper()
            if len(text) != 1 or not text.isalpha():
                return False
        return True

    @staticmethod
    def _build_word_candidates_from_charset(charset_tokens: list[str]) -> list[str]:
        allowed = {str(token or "").strip().upper() for token in charset_tokens if str(token or "").strip()}
        if not allowed:
            return []
        words = [word for word in LETTER_WORD_BANK if all(ch in allowed for ch in word)]
        return QuestionBank._dedupe_keep_order(words)

    @staticmethod
    def _letter_char_budget(output_length: int) -> int:
        raw = max(1, int(output_length))
        return max(8, min(24, int(round(raw * 0.22))))

    def _choose_bucket(
        self,
        normal_tokens: list[str],
        weak_tokens: list[str],
        confusion_tokens: list[str],
        force_weak: bool,
    ) -> list[str]:
        if force_weak:
            normal_p, weak_p = 0.30, 0.50
        else:
            normal_p, weak_p = 0.70, 0.20

        draw = self.random.random()
        if draw < normal_p:
            return normal_tokens
        if draw < normal_p + weak_p:
            return weak_tokens if weak_tokens else normal_tokens
        return confusion_tokens if confusion_tokens else normal_tokens

    @staticmethod
    def _compose_target(parts: list[str], mode: str, continuous: bool) -> str:
        if not parts:
            return ""
        if continuous:
            return "".join(part.replace(" ", "") for part in parts)
        if len(parts) == 1 and " " in parts[0]:
            return parts[0]
        if str(mode or "").strip().lower() == "letter":
            return "".join(parts)
        return " ".join(parts)

    def invalidate_adaptive_cache(self) -> None:
        self._adaptive_chars_cache = None

    def _get_adaptive_chars(self) -> tuple[list[str], list[str]]:
        if self._adaptive_chars_cache is not None:
            weak_cached, confusion_cached = self._adaptive_chars_cache
            return list(weak_cached), list(confusion_cached)

        weak_rows = self.db_tool.get_top_weak_chars(limit=20)
        weak_chars = [str(row.get("ch", "")).upper() for row in weak_rows]
        confusion_rows = self.db_tool.get_top_confusions(limit=20)
        confusion_chars: list[str] = []
        for row in confusion_rows:
            confusion_chars.append(str(row.get("expected_ch", "")).upper())
            confusion_chars.append(str(row.get("actual_ch", "")).upper())

        self._adaptive_chars_cache = (list(weak_chars), list(confusion_chars))
        return list(weak_chars), list(confusion_chars)

    def _generate_letter_word_target(
        self,
        *,
        normal_tokens: list[str],
        weak_tokens: list[str],
        confusion_tokens: list[str],
        weak_chars: list[str],
        confusion_chars: list[str],
        force_weak: bool,
        output_length: int,
    ) -> str:
        budget = self._letter_char_budget(output_length)
        word_tokens = self._build_word_candidates_from_charset(normal_tokens)

        if word_tokens:
            weak_word_tokens = self._build_weak_tokens(word_tokens, weak_chars)
            confusion_word_tokens = self._build_confusion_tokens(word_tokens, confusion_chars)

            words: list[str] = []
            char_count = 0
            max_words = max(2, min(12, budget))
            guard = 0
            while char_count < budget and len(words) < max_words and guard < (max_words * 4):
                guard += 1
                bucket = self._choose_bucket(word_tokens, weak_word_tokens, confusion_word_tokens, force_weak)
                token = self.random.choice(bucket).strip().upper()
                if not token:
                    continue
                if words and token == words[-1]:
                    continue
                if words and (char_count + len(token)) > (budget + 2):
                    if char_count >= max(8, budget - 2):
                        break
                words.append(token)
                char_count += len(token)
            if words:
                return " ".join(words)

        # Fallback: no valid words can be composed, emit grouped random letters.
        letters: list[str] = []
        for _ in range(max(5, budget)):
            bucket = self._choose_bucket(normal_tokens, weak_tokens, confusion_tokens, force_weak)
            token = self.random.choice(bucket).strip().upper()
            if token:
                letters.append(token)
        if not letters:
            return ""
        groups = ["".join(letters[i : i + 5]) for i in range(0, len(letters), 5)]
        return " ".join(group for group in groups if group)

    def generate_targets(
        self,
        pool_selector: dict[str, int],
        mode: str,
        question_count: int,
        output_length: int,
        force_weak: bool = False,
        charset: list[str] | None = None,
        continuous: bool = False,
    ) -> list[str]:
        if charset:
            normal_tokens = self._extract_charset_tokens(charset)
        else:
            pool = self._select_pool(pool_selector)
            normal_tokens = self._extract_allowed_tokens(pool)
        if not normal_tokens:
            return [""]

        weak_chars, confusion_chars = self._get_adaptive_chars()

        weak_tokens = self._build_weak_tokens(normal_tokens, weak_chars)
        confusion_tokens = self._build_confusion_tokens(normal_tokens, confusion_chars)
        letter_word_mode = bool(charset) and continuous and self._is_single_letter_tokens(normal_tokens)

        count = max(1, int(question_count))
        unit_count = max(1, int(output_length))

        targets: list[str] = []
        for _ in range(count):
            if letter_word_mode:
                target = self._generate_letter_word_target(
                    normal_tokens=normal_tokens,
                    weak_tokens=weak_tokens,
                    confusion_tokens=confusion_tokens,
                    weak_chars=weak_chars,
                    confusion_chars=confusion_chars,
                    force_weak=force_weak,
                    output_length=unit_count,
                )
                targets.append(" ".join(target.split()))
                continue

            parts: list[str] = []
            for _ in range(unit_count):
                bucket = self._choose_bucket(normal_tokens, weak_tokens, confusion_tokens, force_weak)
                token = self.random.choice(bucket).strip().upper()
                if not token:
                    continue
                if " " in token and not parts and not continuous:
                    parts = [token]
                    break
                parts.append(token)

            if not parts:
                fallback = self.random.choice(normal_tokens).strip().upper()
                parts = [fallback] if fallback else [""]

            target = self._compose_target(parts, mode=mode, continuous=continuous)
            targets.append(" ".join(target.split()))

        return targets
