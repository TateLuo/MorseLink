from __future__ import annotations

from dataclasses import dataclass
from difflib import SequenceMatcher
from html import escape
from typing import Callable, Iterable, List, Optional

from PySide6.QtCore import QCoreApplication


def _tr(text: str) -> str:
    return QCoreApplication.translate("TrainingFeedback", text)


@dataclass
class AlignmentCell:
    expected: str
    actual: str
    status: str  # correct | replace | missing | extra
    expected_index: int
    actual_index: int


@dataclass
class AlignmentResult:
    cells: List[AlignmentCell]
    total_expected: int
    correct: int
    replace: int
    missing: int
    extra: int
    accuracy: float
    first_issue_position: Optional[int]


def align_sequences(
    expected_items: Iterable[str],
    actual_items: Iterable[str],
    normalize: Optional[Callable[[str], str]] = None,
) -> AlignmentResult:
    expected = list(expected_items)
    actual = list(actual_items)

    if normalize:
        expected_norm = [normalize(item) for item in expected]
        actual_norm = [normalize(item) for item in actual]
    else:
        expected_norm = expected
        actual_norm = actual

    matcher = SequenceMatcher(a=expected_norm, b=actual_norm, autojunk=False)
    cells: List[AlignmentCell] = []

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            for offset in range(i2 - i1):
                i = i1 + offset
                j = j1 + offset
                cells.append(
                    AlignmentCell(
                        expected=expected[i],
                        actual=actual[j],
                        status="correct",
                        expected_index=i,
                        actual_index=j,
                    )
                )
            continue

        if tag == "delete":
            for i in range(i1, i2):
                cells.append(
                    AlignmentCell(
                        expected=expected[i],
                        actual="",
                        status="missing",
                        expected_index=i,
                        actual_index=-1,
                    )
                )
            continue

        if tag == "insert":
            for j in range(j1, j2):
                cells.append(
                    AlignmentCell(
                        expected="",
                        actual=actual[j],
                        status="extra",
                        expected_index=-1,
                        actual_index=j,
                    )
                )
            continue

        # replace: pair by max span; overflow becomes missing/extra
        span = max(i2 - i1, j2 - j1)
        for offset in range(span):
            has_expected = (i1 + offset) < i2
            has_actual = (j1 + offset) < j2
            if has_expected and has_actual:
                cells.append(
                    AlignmentCell(
                        expected=expected[i1 + offset],
                        actual=actual[j1 + offset],
                        status="replace",
                        expected_index=i1 + offset,
                        actual_index=j1 + offset,
                    )
                )
            elif has_expected:
                cells.append(
                    AlignmentCell(
                        expected=expected[i1 + offset],
                        actual="",
                        status="missing",
                        expected_index=i1 + offset,
                        actual_index=-1,
                    )
                )
            elif has_actual:
                cells.append(
                    AlignmentCell(
                        expected="",
                        actual=actual[j1 + offset],
                        status="extra",
                        expected_index=-1,
                        actual_index=j1 + offset,
                    )
                )

    correct = sum(1 for cell in cells if cell.status == "correct")
    replace = sum(1 for cell in cells if cell.status == "replace")
    missing = sum(1 for cell in cells if cell.status == "missing")
    extra = sum(1 for cell in cells if cell.status == "extra")
    total_expected = len(expected)
    accuracy = (correct / total_expected * 100.0) if total_expected > 0 else 0.0

    first_issue_position = None
    for cell in cells:
        if cell.status == "correct":
            continue
        if cell.expected_index >= 0:
            first_issue_position = cell.expected_index + 1
        else:
            first_issue_position = total_expected + 1
        break

    return AlignmentResult(
        cells=cells,
        total_expected=total_expected,
        correct=correct,
        replace=replace,
        missing=missing,
        extra=extra,
        accuracy=accuracy,
        first_issue_position=first_issue_position,
    )


def _render_token(token: str) -> str:
    if token == "":
        return ""
    if token == " ":
        return "␠"
    return escape(token)


def _badge(text: str, bg: str) -> str:
    return f"<span style='background-color:{bg};border-radius:2px;padding:0 2px;'>{text}</span>"


def render_alignment_html(cells: Iterable[AlignmentCell], side: str, token_joiner: str = "") -> str:
    fragments: List[str] = []
    joiner = "&nbsp;" if token_joiner == " " else escape(token_joiner).replace(" ", "&nbsp;")

    for cell in cells:
        if side == "expected":
            if cell.status == "extra":
                continue

            token = _render_token(cell.expected)
            if not token:
                continue

            if cell.status == "correct":
                fragments.append(token)
            elif cell.status == "replace":
                fragments.append(_badge(_tr("错:{0}").format(token), "#fff1a8"))
            else:  # missing
                fragments.append(_badge(_tr("漏:{0}").format(token), "#e0e0e0"))
            continue

        if side == "actual":
            if cell.status == "missing":
                fragments.append(_badge(_tr("漏:∅"), "#e0e0e0"))
                continue

            token = _render_token(cell.actual)
            if not token:
                continue

            if cell.status == "correct":
                fragments.append(token)
            elif cell.status == "replace":
                fragments.append(_badge(_tr("错:{0}").format(token), "#fff1a8"))
            else:  # extra
                fragments.append(_badge(_tr("多:{0}").format(token), "#ffd8a8"))
            continue

        raise ValueError(f"unsupported side: {side}")

    return joiner.join(fragments)


def build_alignment_summary_text(result: AlignmentResult) -> str:
    parts = [
        _tr("正确 {0}/{1}").format(result.correct, result.total_expected),
        _tr("错码 {0}").format(result.replace),
        _tr("漏码 {0}").format(result.missing),
        _tr("多码 {0}").format(result.extra),
        _tr("准确率 {0}%").format(int(round(result.accuracy))),
    ]
    if result.first_issue_position is not None:
        parts.append(_tr("首错位置 {0}").format(result.first_issue_position))

    hint = _tr("节奏稳定，继续保持。")
    if result.missing > result.extra and result.missing >= result.replace:
        hint = _tr("漏码偏多，建议稍微放慢并关注字符间隔。")
    elif result.extra > result.missing and result.extra >= result.replace:
        hint = _tr("多码偏多，建议抬键更干净、间隔更明确。")
    elif result.replace > 0:
        hint = _tr("错码偏多，建议强化点划时值辨识。")

    parts.append(_tr("建议: {0}").format(hint))
    return " | ".join(parts)
