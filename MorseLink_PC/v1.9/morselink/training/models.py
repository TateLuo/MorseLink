from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal


@dataclass
class TrainingMetrics:
    rx_acc: float | None = None
    rx_latency_ms: float | None = None
    tx_rhythm: float | None = None
    tx_decode_match: float | None = None
    tx_score: float | None = None


@dataclass
class TrainingResult:
    mode: Literal["rx", "tx"]
    target_text: str
    user_text: str = ""
    decoded_text: str = ""
    metrics: TrainingMetrics = field(default_factory=TrainingMetrics)
    per_char_errors: dict[str, int] = field(default_factory=dict)
    confusion_pairs: dict[tuple[str, str], int] = field(default_factory=dict)
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class UnitStepDef:
    step_id: str
    mode: Literal["rx", "tx"]
    question_count: int
    no_hint: bool = False
    focus: Literal["accuracy", "speed", "rhythm"] = "accuracy"
    output_length: int = 8
    continuous: bool = True
    rx_gap_scale: float | None = None


@dataclass
class UnitDef:
    unit_index: int
    name: str
    steps: list[UnitStepDef]
    objective: str = ""
    added_chars: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    charset: list[str] = field(default_factory=list)
    pool_selector: dict[str, int] = field(default_factory=dict)
    is_boss: bool = False
    xp_reward: int = 10


@dataclass
class StageDef:
    stage_id: int
    name: str
    units: list[UnitDef]
    xp_goal: int
    unlock_chars: list[str] = field(default_factory=list)
    subtitle: str = ""


@dataclass
class RoundTask:
    mode: Literal["rx", "tx"]
    stage_id: int
    stage_name: str
    unit_index: int
    unit_name: str
    unit_objective: str
    unit_added_chars: list[str]
    unit_tags: list[str]
    level_id: int
    level_name: str
    step_id: str
    question_count: int
    targets: list[str]
    no_hint: bool = False
    focus: Literal["accuracy", "speed", "rhythm"] = "accuracy"
    is_boss: bool = False
    output_length: int = 8
    continuous: bool = True
    rx_gap_scale: float = 1.0
    tx_len_bonus: int = 0
    timing: dict[str, int] = field(default_factory=dict)
