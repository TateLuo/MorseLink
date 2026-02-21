from __future__ import annotations

from typing import Literal, Protocol

from .models import RoundTask, TrainingResult


class RunnerResultCallback(Protocol):
    def __call__(self, result: TrainingResult) -> None:
        ...


class RunnerProtocol(Protocol):
    mode: Literal["rx", "tx"]

    def start_round(self, task: RoundTask, on_done: RunnerResultCallback) -> None:
        ...

    def stop_round(self) -> None:
        ...
