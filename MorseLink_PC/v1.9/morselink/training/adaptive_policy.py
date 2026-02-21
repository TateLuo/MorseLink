from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable


@dataclass
class AdaptiveDecision:
    rx_gap_scale: float
    tx_len_bonus: int
    force_weak_next: bool


def _to_float(value: Any) -> float | None:
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _mean(values: Iterable[float]) -> float | None:
    arr = [float(v) for v in values]
    if not arr:
        return None
    return sum(arr) / float(len(arr))


def apply_recent_policy(
    rx_gap_scale: float,
    tx_len_bonus: int,
    recent_rx_attempts: list[dict[str, Any]],
    recent_tx_attempts: list[dict[str, Any]],
) -> AdaptiveDecision:
    new_gap = float(rx_gap_scale)
    new_bonus = int(tx_len_bonus)
    force_weak = False

    rx_acc_values = [v for v in (_to_float(item.get("rx_acc")) for item in recent_rx_attempts) if v is not None]
    rx_latency_values = [
        v for v in (_to_float(item.get("rx_latency_ms")) for item in recent_rx_attempts) if v is not None
    ]

    if len(rx_acc_values) >= 3:
        rx_mean = _mean(rx_acc_values[:3])
        latency_has_drop = False
        if len(rx_latency_values) >= 3:
            # attempts are ordered DESC by id, so compare newest and oldest in the 3-sample window
            latency_has_drop = rx_latency_values[0] < rx_latency_values[2]

        if rx_mean is not None and rx_mean > 92.0 and latency_has_drop:
            new_gap -= 0.05
        elif rx_mean is not None and rx_mean < 85.0:
            new_gap += 0.08
            force_weak = True

    tx_score_values = [v for v in (_to_float(item.get("tx_score")) for item in recent_tx_attempts) if v is not None]
    if len(tx_score_values) >= 3:
        tx_mean = _mean(tx_score_values[:3])
        if tx_mean is not None and tx_mean > 80.0:
            new_bonus += 1
        elif tx_mean is not None and tx_mean < 65.0:
            new_bonus -= 1

    new_gap = max(0.80, min(1.35, new_gap))
    new_bonus = max(-2, min(4, new_bonus))
    return AdaptiveDecision(rx_gap_scale=new_gap, tx_len_bonus=new_bonus, force_weak_next=force_weak)
