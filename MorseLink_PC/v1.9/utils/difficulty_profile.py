from __future__ import annotations

from dataclasses import dataclass
from PySide6.QtCore import QCoreApplication


def _tr(text: str) -> str:
    return QCoreApplication.translate("DifficultyProfile", text)


@dataclass(frozen=True)
class DifficultyPreset:
    level: int
    name: str
    training_wpm: int
    min_word_length: int
    max_word_length: int
    min_groups: int
    max_groups: int
    core_weight: float
    description: str


PRESETS = {
    1: DifficultyPreset(
        level=1,
        name="新手",
        training_wpm=10,
        min_word_length=2,
        max_word_length=3,
        min_groups=2,
        max_groups=3,
        core_weight=0.85,
        description="节奏慢，核心字符占比高，适合建立基础手感。",
    ),
    2: DifficultyPreset(
        level=2,
        name="入门",
        training_wpm=12,
        min_word_length=3,
        max_word_length=4,
        min_groups=3,
        max_groups=4,
        core_weight=0.75,
        description="开始引入干扰，保持准确率优先。",
    ),
    3: DifficultyPreset(
        level=3,
        name="基础",
        training_wpm=16,
        min_word_length=4,
        max_word_length=5,
        min_groups=4,
        max_groups=5,
        core_weight=0.60,
        description="常规训练强度，适合日常巩固。",
    ),
    4: DifficultyPreset(
        level=4,
        name="提升",
        training_wpm=20,
        min_word_length=4,
        max_word_length=6,
        min_groups=5,
        max_groups=6,
        core_weight=0.45,
        description="接近实战，重点练稳定节奏和抗干扰。",
    ),
    5: DifficultyPreset(
        level=5,
        name="进阶",
        training_wpm=24,
        min_word_length=5,
        max_word_length=7,
        min_groups=6,
        max_groups=8,
        core_weight=0.30,
        description="信息密度高，关注纠错与连续抄收能力。",
    ),
    6: DifficultyPreset(
        level=6,
        name="实战",
        training_wpm=28,
        min_word_length=6,
        max_word_length=8,
        min_groups=8,
        max_groups=10,
        core_weight=0.20,
        description="高压密集，模拟比赛/实战场景。",
    ),
}


def clamp_level(level: int) -> int:
    try:
        val = int(level)
    except Exception:
        val = 3
    return max(1, min(6, val))


def get_preset(level: int) -> DifficultyPreset:
    return PRESETS[clamp_level(level)]


def compute_timing_ms(training_wpm: int):
    wpm = max(5, min(60, int(training_wpm)))
    dot_ms = round(1200 / wpm)
    dash_ms = dot_ms * 3
    letter_gap_ms = dot_ms * 3
    word_gap_ms = dot_ms * 7
    return {
        "wpm": wpm,
        "dot_ms": dot_ms,
        "dash_ms": dash_ms,
        "letter_gap_ms": letter_gap_ms,
        "word_gap_ms": word_gap_ms,
    }


def preset_summary_text(preset: DifficultyPreset) -> str:
    return (
        f"{_tr('等级')}{preset.level} {_tr(preset.name)} | "
        f"WPM {preset.training_wpm} | "
        f"{_tr('词长')} {preset.min_word_length}-{preset.max_word_length} | "
        f"{_tr('组数')} {preset.min_groups}-{preset.max_groups} | "
        f"{_tr('核心权重')} {preset.core_weight:.2f}"
    )


def preset_name_text(preset: DifficultyPreset) -> str:
    return _tr(preset.name)


def preset_description_text(preset: DifficultyPreset) -> str:
    return _tr(preset.description)
