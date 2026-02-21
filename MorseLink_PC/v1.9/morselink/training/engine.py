from __future__ import annotations

from dataclasses import asdict
from datetime import date, datetime
from typing import Any, Callable

from utils.database_tool import DatabaseTool
from utils.difficulty_profile import compute_timing_ms

from .adaptive_policy import apply_recent_policy
from .level_defs import get_stage_defs
from .models import RoundTask, StageDef, TrainingResult, UnitDef
from .question_bank import QuestionBank


TaskCallback = Callable[[RoundTask], None]
StateCallback = Callable[[dict[str, Any]], None]
FinishCallback = Callable[[dict[str, Any]], None]


class TrainingEngine:
    """Stage/Unit based training coordinator."""

    # Unlock thresholds. Keep centralized to avoid hard-coded values in UI/tests.
    UNIT_UNLOCK_MIN_ACCURACY = 70.0
    UNIT_UNLOCK_MIN_RHYTHM = 65.0
    STAGE_UNLOCK_MIN_ACCURACY = 75.0
    STAGE_UNLOCK_MIN_RHYTHM = 70.0
    STAGE_UNLOCK_MIN_SCORE = 75.0

    def __init__(self, db_tool: DatabaseTool, config_manager) -> None:
        self.db_tool = db_tool
        self.config_manager = config_manager
        self.question_bank = QuestionBank(db_tool=db_tool)
        self.stage_defs: list[StageDef] = get_stage_defs()

        self._on_task: TaskCallback | None = None
        self._on_state: StateCallback | None = None
        self._on_finish: FinishCallback | None = None

        self._running = False
        self._waiting_result = False
        self._current_task: RoundTask | None = None
        self._current_stage: StageDef | None = None
        self._current_unit: UnitDef | None = None
        self._step_index = 0
        self._step_results: list[tuple[RoundTask, TrainingResult]] = []
        self._profile = self.db_tool.get_training_profile()
        self._force_weak_next = False

    def set_callbacks(
        self,
        on_task: TaskCallback | None = None,
        on_state: StateCallback | None = None,
        on_finish: FinishCallback | None = None,
    ) -> None:
        self._on_task = on_task
        self._on_state = on_state
        self._on_finish = on_finish

    @property
    def is_running(self) -> bool:
        return self._running

    def _max_stage_id(self) -> int:
        return max(1, len(self.stage_defs))

    def _clamp_stage_id(self, value: Any) -> int:
        try:
            stage_id = int(value)
        except (TypeError, ValueError):
            stage_id = 1
        return max(1, min(self._max_stage_id(), stage_id))

    @staticmethod
    def _clamp_unit_index(value: Any, unit_total: int) -> int:
        try:
            unit_index = int(value)
        except (TypeError, ValueError):
            unit_index = 1
        return max(1, min(max(1, int(unit_total)), unit_index))

    @staticmethod
    def _clamp_rx_gap_scale(value: Any) -> float:
        try:
            parsed = float(value)
        except (TypeError, ValueError):
            parsed = 1.0
        return max(0.80, min(1.35, parsed))

    @staticmethod
    def _clamp_tx_len_bonus(value: Any) -> int:
        try:
            parsed = int(value)
        except (TypeError, ValueError):
            parsed = 0
        return max(-2, min(4, parsed))

    def _stage_by_id(self, stage_id: int) -> StageDef:
        return self.stage_defs[self._clamp_stage_id(stage_id) - 1]

    def _emit_state(self, payload: dict[str, Any]) -> None:
        if self._on_state:
            self._on_state(payload)

    def _emit_task(self, task: RoundTask) -> None:
        if self._on_task:
            self._on_task(task)

    def _emit_finish(self, payload: dict[str, Any]) -> None:
        if self._on_finish:
            self._on_finish(payload)

    def _stage_progress_map(self, stage_id: int) -> dict[int, dict[str, Any]]:
        rows = self.db_tool.get_training_unit_progress(stage_id)
        return {int(row.get("unit_index", 0)): dict(row) for row in rows}

    def get_dashboard(self, stage_id: int | None = None) -> dict[str, Any]:
        profile = self.db_tool.get_training_profile()
        current_stage_id = self._clamp_stage_id(profile.get("current_stage", profile.get("current_level", 1)))
        view_stage_id = self._clamp_stage_id(stage_id if stage_id is not None else current_stage_id)
        if view_stage_id > current_stage_id:
            view_stage_id = current_stage_id

        stage = self._stage_by_id(view_stage_id)
        progress = self._stage_progress_map(view_stage_id)
        if view_stage_id == current_stage_id:
            current_unit = self._clamp_unit_index(profile.get("current_unit", 1), len(stage.units))
        else:
            current_unit = 1

        cards: list[dict[str, Any]] = []
        completed_count = len(progress)
        default_unit = current_unit
        for unit in stage.units:
            unit_progress = progress.get(unit.unit_index)
            stars = 0
            status = "locked"

            if view_stage_id < current_stage_id:
                if unit_progress:
                    status = "completed"
                    stars = max(1, int(unit_progress.get("stars", 1)))
                else:
                    status = "available"
                    if default_unit == 1:
                        default_unit = unit.unit_index
                completed_count = max(completed_count, len(progress))
            else:
                if unit.unit_index == current_unit:
                    status = "current"
                    if unit_progress:
                        stars = max(1, int(unit_progress.get("stars", 1)))
                elif unit_progress:
                    status = "completed"
                    stars = max(1, int(unit_progress.get("stars", 1)))
                elif unit.unit_index < current_unit:
                    status = "completed"
                    stars = 1
                    completed_count += 1

            cards.append(
                {
                    "unit_index": unit.unit_index,
                    "title": f"Unit {unit.unit_index}",
                    "is_boss": bool(unit.is_boss),
                    "status": status,
                    "stars": stars,
                    "objective": unit.objective,
                    "added_chars": list(unit.added_chars),
                    "tags": list(unit.tags),
                }
            )

        if view_stage_id < current_stage_id:
            available_units = [int(card["unit_index"]) for card in cards if str(card.get("status")) == "available"]
            if available_units:
                default_unit = available_units[0]
            current_unit = max(1, min(len(stage.units), default_unit))

        current_unit_def = stage.units[current_unit - 1]
        return {
            "stage_id": stage.stage_id,
            "stage_name": stage.name,
            "subtitle": stage.subtitle,
            "current_stage": current_stage_id,
            "unlocked_stage_max": current_stage_id,
            "stages": [
                {
                    "stage_id": s.stage_id,
                    "name": s.name,
                    "unlocked": s.stage_id <= current_stage_id,
                    "selected": s.stage_id == stage.stage_id,
                }
                for s in self.stage_defs
            ],
            "unit_total": len(stage.units),
            "current_unit": current_unit,
            "current_unit_objective": current_unit_def.objective,
            "current_unit_added_chars": list(current_unit_def.added_chars),
            "current_unit_tags": list(current_unit_def.tags),
            "completed_units": completed_count,
            "units": cards,
            "daily_goal": max(1, int(profile.get("daily_goal", 3))),
            "daily_units_done": max(0, int(profile.get("daily_units_done", 0))),
            "streak_days": max(0, int(profile.get("streak_days", 0))),
            "total_xp": max(0, int(profile.get("total_xp", 0))),
        }

    def start_training(self, stage_id: int | None = None, unit_index: int | None = None) -> bool:
        if self._running:
            return False

        self._profile = self.db_tool.get_training_profile()
        current_stage_id = self._clamp_stage_id(self._profile.get("current_stage", self._profile.get("current_level", 1)))
        target_stage_id = self._clamp_stage_id(stage_id if stage_id is not None else current_stage_id)
        if target_stage_id > current_stage_id:
            return False

        stage = self._stage_by_id(target_stage_id)
        current_unit = self._clamp_unit_index(self._profile.get("current_unit", 1), len(stage.units))
        progress_map = self._stage_progress_map(target_stage_id)

        if unit_index is None:
            target_unit_index = current_unit
        else:
            target_unit_index = self._clamp_unit_index(unit_index, len(stage.units))
            if (
                target_stage_id == current_stage_id
                and target_unit_index > current_unit
                and target_unit_index not in progress_map
            ):
                return False

        self._current_stage = stage
        self._current_unit = stage.units[target_unit_index - 1]
        self._step_index = 0
        self._step_results = []
        self._current_task = None
        self._running = True
        self._waiting_result = False

        self._emit_state(
            {
                "event": "started",
                "current_stage": stage.stage_id,
                "current_level": stage.stage_id,
                "stage_name": stage.name,
                "unit_index": target_unit_index,
                "unit_total": len(stage.units),
                "unit_objective": self._current_unit.objective,
                "unit_added_chars": list(self._current_unit.added_chars),
                "is_boss": self._current_unit.is_boss,
                "combo_units": int(self._profile.get("combo_units", 0)),
                "daily_goal": int(self._profile.get("daily_goal", 3)),
                "daily_units_done": int(self._profile.get("daily_units_done", 0)),
                "streak_days": int(self._profile.get("streak_days", 0)),
            }
        )
        self.question_bank.invalidate_adaptive_cache()
        self._dispatch_current_step()
        return True

    def stop_training(self) -> bool:
        if not self._running:
            return False
        self._running = False
        self._waiting_result = False
        self._current_task = None
        self._emit_state({"event": "stopped"})
        return True

    def submit_result(self, result: TrainingResult) -> bool:
        if not self._running or not self._waiting_result or self._current_task is None:
            return False
        if result.mode != self._current_task.mode:
            return False

        task = self._current_task
        self._waiting_result = False
        self._persist_step_result(task, result)
        self._update_combo(result)
        self._step_results.append((task, result))

        step_total = len(self._current_unit.steps) if self._current_unit else 0
        self._emit_state(
            {
                "event": "step_done",
                "step_id": task.step_id,
                "mode": task.mode,
                "step_index": self._step_index,
                "step_total": step_total,
            }
        )

        self._step_index += 1
        if self._current_unit is None or self._step_index >= len(self._current_unit.steps):
            self._finalize_unit()
            return True

        self._dispatch_current_step()
        return True

    @staticmethod
    def _stage_base_wpm(stage_id: int) -> int:
        # Stage progression baseline. Keep jumps noticeable but smooth.
        anchors = [12, 16, 20, 24, 27]
        normalized = max(1, int(stage_id))
        if normalized <= len(anchors):
            return anchors[normalized - 1]
        return anchors[-1] + (normalized - len(anchors)) * 2

    @staticmethod
    def _unit_progress_bonus(unit_index: int, unit_total: int) -> int:
        if int(unit_total) <= 1:
            return 0
        ratio = float(max(0, int(unit_index) - 1)) / float(max(1, int(unit_total) - 1))
        return max(0, min(4, int(round(ratio * 3.0))))

    def _auto_wpm_for_step(self, *, focus: str, is_boss: bool) -> int:
        if self._current_stage is None or self._current_unit is None:
            return 16

        stage_id = int(self._current_stage.stage_id)
        unit_index = int(self._current_unit.unit_index)
        unit_total = len(self._current_stage.units)

        base = self._stage_base_wpm(stage_id)
        unit_bonus = self._unit_progress_bonus(unit_index, unit_total)
        boss_bonus = 1 if bool(is_boss) else 0
        focus_bonus = 1 if str(focus).lower() == "speed" else 0
        return max(8, min(35, int(base + unit_bonus + boss_bonus + focus_bonus)))

    def _compute_timing(
        self,
        mode: str,
        *,
        focus: str = "accuracy",
        is_boss: bool = False,
        step_gap_scale: float | None = None,
    ) -> dict[str, int]:
        timing = compute_timing_ms(self._auto_wpm_for_step(focus=focus, is_boss=is_boss))
        if str(mode).lower() != "rx":
            return timing

        profile_scale = self._clamp_rx_gap_scale(self._profile.get("rx_gap_scale", 1.0))
        step_scale = float(step_gap_scale) if step_gap_scale is not None else 1.0
        final_scale = max(0.75, min(1.40, profile_scale * step_scale))
        timing["letter_gap_ms"] = max(1, int(round(timing["letter_gap_ms"] * final_scale)))
        timing["word_gap_ms"] = max(1, int(round(timing["word_gap_ms"] * final_scale)))
        return timing

    def _dispatch_current_step(self) -> None:
        if not self._running or self._current_stage is None or self._current_unit is None:
            return

        step = self._current_unit.steps[self._step_index]
        tx_bonus = self._clamp_tx_len_bonus(self._profile.get("tx_len_bonus", 0)) if step.mode == "tx" else 0
        output_length = max(2, min(120, int(step.output_length) + tx_bonus))

        force_weak = bool(self._force_weak_next and step.mode == "rx")
        pool_selector = dict(self._current_unit.pool_selector or {"letter": 39})
        targets = self.question_bank.generate_targets(
            pool_selector=pool_selector,
            mode=step.mode,
            question_count=step.question_count,
            output_length=output_length,
            force_weak=force_weak,
            charset=list(self._current_unit.charset),
            continuous=bool(step.continuous),
        )
        if force_weak:
            self._force_weak_next = False

        task = RoundTask(
            mode=step.mode,
            stage_id=self._current_stage.stage_id,
            stage_name=self._current_stage.name,
            unit_index=self._current_unit.unit_index,
            unit_name=self._current_unit.name,
            unit_objective=self._current_unit.objective,
            unit_added_chars=list(self._current_unit.added_chars),
            unit_tags=list(self._current_unit.tags),
            level_id=self._current_stage.stage_id,
            level_name=self._current_stage.name,
            step_id=step.step_id,
            question_count=step.question_count,
            targets=targets,
            no_hint=step.no_hint,
            focus=step.focus,
            is_boss=self._current_unit.is_boss,
            output_length=output_length,
            continuous=bool(step.continuous),
            rx_gap_scale=self._clamp_rx_gap_scale(self._profile.get("rx_gap_scale", 1.0)),
            tx_len_bonus=self._clamp_tx_len_bonus(self._profile.get("tx_len_bonus", 0)),
            timing=self._compute_timing(
                step.mode,
                focus=str(step.focus),
                is_boss=bool(self._current_unit.is_boss),
                step_gap_scale=step.rx_gap_scale,
            ),
        )
        self._current_task = task
        self._waiting_result = True
        self._emit_task(task)

    def _persist_step_result(self, task: RoundTask, result: TrainingResult) -> None:
        metrics = result.metrics
        self.db_tool.persist_training_step(
            attempt={
                "mode": result.mode,
                "level_id": task.level_id,
                "step_id": task.step_id,
                "is_boss": 1 if task.is_boss else 0,
                "target_text": result.target_text,
                "user_text": result.user_text,
                "decoded_text": result.decoded_text,
                "rx_acc": metrics.rx_acc,
                "rx_latency_ms": metrics.rx_latency_ms,
                "tx_rhythm": metrics.tx_rhythm,
                "tx_decode_match": metrics.tx_decode_match,
                "tx_score": metrics.tx_score,
                "stable_wpm": float(task.timing.get("wpm", 16)),
                "raw": result.raw,
            },
            per_char_errors=result.per_char_errors,
            confusion_pairs=result.confusion_pairs,
        )

    def _update_combo(self, result: TrainingResult) -> None:
        metrics = result.metrics
        combo_rx = int(self._profile.get("combo_rx", 0))
        combo_tx = int(self._profile.get("combo_tx", 0))

        if result.mode == "rx":
            rx_acc = float(metrics.rx_acc or 0.0)
            combo_rx = combo_rx + 1 if rx_acc >= 95.0 else 0
        elif result.mode == "tx":
            tx_score = float(metrics.tx_score or 0.0)
            combo_tx = combo_tx + 1 if tx_score >= 80.0 else 0

        self._profile["combo_rx"] = combo_rx
        self._profile["combo_tx"] = combo_tx

    @staticmethod
    def _metric_mean(items: list[float]) -> float:
        return (sum(items) / float(len(items))) if items else 0.0

    @staticmethod
    def _grade_for_score(score: float) -> tuple[str, int]:
        if score >= 90.0:
            return "A", 3
        if score >= 75.0:
            return "B", 2
        return "C", 1

    @classmethod
    def _unit_unlock_passed(cls, accuracy: float, rhythm: float) -> bool:
        return float(accuracy) >= cls.UNIT_UNLOCK_MIN_ACCURACY and float(rhythm) >= cls.UNIT_UNLOCK_MIN_RHYTHM

    @classmethod
    def _stage_unlock_passed(
        cls,
        *,
        accuracy: float,
        rhythm: float,
        score: float,
        is_boss: bool,
        is_last_unit: bool,
    ) -> bool:
        if not is_boss or not is_last_unit:
            return False
        return (
            float(accuracy) >= cls.STAGE_UNLOCK_MIN_ACCURACY
            and float(rhythm) >= cls.STAGE_UNLOCK_MIN_RHYTHM
            and float(score) >= cls.STAGE_UNLOCK_MIN_SCORE
        )

    def _apply_daily_progress(self) -> int:
        today = date.today()
        today_text = today.strftime("%Y-%m-%d")
        last_active = str(self._profile.get("last_active_date", "") or "").strip()

        streak_days = max(0, int(self._profile.get("streak_days", 0)))
        daily_units_done = max(0, int(self._profile.get("daily_units_done", 0)))
        daily_goal = max(1, int(self._profile.get("daily_goal", 3)))
        reward_claimed = bool(int(self._profile.get("daily_reward_claimed", 0)))

        if last_active != today_text:
            prev_date = None
            if last_active:
                try:
                    prev_date = datetime.strptime(last_active, "%Y-%m-%d").date()
                except ValueError:
                    prev_date = None
            if prev_date is not None and (today - prev_date).days == 1:
                streak_days = max(1, streak_days + 1)
            else:
                streak_days = 1
            daily_units_done = 0
            reward_claimed = False

        daily_units_done += 1
        bonus_xp = 0
        if daily_units_done >= daily_goal and not reward_claimed:
            bonus_xp = 20
            reward_claimed = True

        self._profile["last_active_date"] = today_text
        self._profile["streak_days"] = streak_days
        self._profile["daily_units_done"] = daily_units_done
        self._profile["daily_goal"] = daily_goal
        self._profile["daily_reward_claimed"] = 1 if reward_claimed else 0
        return bonus_xp

    def _finalize_unit(self) -> None:
        if self._current_stage is None or self._current_unit is None:
            self._running = False
            self._waiting_result = False
            return

        rx_acc_values: list[float] = []
        tx_score_values: list[float] = []
        tx_decode_values: list[float] = []
        tx_rhythm_values: list[float] = []
        for _task, result in self._step_results:
            metrics = result.metrics
            if result.mode == "rx" and metrics.rx_acc is not None:
                rx_acc_values.append(float(metrics.rx_acc))
            if result.mode == "tx":
                if metrics.tx_score is not None:
                    tx_score_values.append(float(metrics.tx_score))
                if metrics.tx_decode_match is not None:
                    tx_decode_values.append(float(metrics.tx_decode_match))
                if metrics.tx_rhythm is not None:
                    tx_rhythm_values.append(float(metrics.tx_rhythm))

        accuracy_values = list(rx_acc_values) + list(tx_decode_values)
        accuracy = self._metric_mean(accuracy_values)
        rhythm = self._metric_mean(tx_rhythm_values if tx_rhythm_values else tx_score_values)
        unit_score = 0.7 * accuracy + 0.3 * rhythm
        grade, stars = self._grade_for_score(unit_score)
        unit_passed = self._unit_unlock_passed(accuracy, rhythm)

        base_xp = int(self._current_unit.xp_reward)
        bonus_xp = self._apply_daily_progress()
        gained_xp = base_xp + bonus_xp

        self._profile["combo_units"] = max(0, int(self._profile.get("combo_units", 0))) + 1
        self._profile["total_xp"] = max(0, int(self._profile.get("total_xp", 0))) + gained_xp
        self._profile["stage_xp"] = max(0, int(self._profile.get("stage_xp", 0))) + gained_xp

        stage_before = int(self._current_stage.stage_id)
        unit_before = int(self._current_unit.unit_index)
        unit_total = len(self._current_stage.units)
        is_last_unit = unit_before >= unit_total
        stage_gate_passed = self._stage_unlock_passed(
            accuracy=accuracy,
            rhythm=rhythm,
            score=unit_score,
            is_boss=bool(self._current_unit.is_boss),
            is_last_unit=is_last_unit,
        )

        if unit_passed:
            self.db_tool.upsert_training_unit_progress(
                stage_id=stage_before,
                unit_index=unit_before,
                stars=stars,
                best_grade=grade,
                best_score=round(unit_score, 2),
            )

        progress_rows = self.db_tool.get_training_unit_progress(stage_before)
        completed_units = len(progress_rows)
        stage_completed_by_units = completed_units >= unit_total
        stage_completed_by_xp = int(self._profile.get("stage_xp", 0)) >= int(self._current_stage.xp_goal)
        stage_completed = stage_completed_by_units or stage_completed_by_xp

        stage_after = stage_before
        unit_after = unit_before
        stage_upgraded = False
        unlocked_chars: list[str] = []
        unlock_block_reason = "none"

        if not unit_passed:
            unlock_block_reason = "unit_threshold_not_met"
        else:
            if stage_before < self._max_stage_id() and stage_completed and stage_gate_passed:
                stage_after = stage_before + 1
                unit_after = 1
                stage_upgraded = True
                self._profile["stage_xp"] = 0
                unlocked_chars = list(self.stage_defs[stage_after - 1].unlock_chars)
            else:
                next_unit = unit_before + 1 if unit_before < unit_total else unit_before
                unit_after = max(int(self._profile.get("current_unit", 1)), next_unit)
                unit_after = max(1, min(unit_total, unit_after))
                if stage_before < self._max_stage_id() and is_last_unit and not stage_gate_passed:
                    unlock_block_reason = "stage_threshold_not_met"
                elif stage_before < self._max_stage_id() and is_last_unit and not stage_completed:
                    unlock_block_reason = "stage_progress_not_ready"

        self._profile["current_stage"] = stage_after
        self._profile["current_level"] = stage_after
        self._profile["current_unit"] = unit_after

        recent_rx = self.db_tool.get_recent_attempts("rx", limit=3)
        recent_tx = self.db_tool.get_recent_attempts("tx", limit=3)
        decision = apply_recent_policy(
            rx_gap_scale=self._clamp_rx_gap_scale(self._profile.get("rx_gap_scale", 1.0)),
            tx_len_bonus=self._clamp_tx_len_bonus(self._profile.get("tx_len_bonus", 0)),
            recent_rx_attempts=recent_rx,
            recent_tx_attempts=recent_tx,
        )
        self._profile["rx_gap_scale"] = decision.rx_gap_scale
        self._profile["tx_len_bonus"] = decision.tx_len_bonus
        self._force_weak_next = bool(decision.force_weak_next)

        self.db_tool.save_training_profile_snapshot(dict(self._profile))
        self.question_bank.invalidate_adaptive_cache()

        payload = {
            "event": "finished",
            "passed": unit_passed,
            "level_before": stage_before,
            "level_after": stage_after,
            "stage_before": stage_before,
            "stage_after": stage_after,
            "unit_before": unit_before,
            "unit_after": unit_after,
            "unit_unlock_passed": unit_passed,
            "stage_unlock_passed": stage_gate_passed,
            "unlock_block_reason": unlock_block_reason,
            "stage_name": self._current_stage.name,
            "unit_name": self._current_unit.name,
            "unit_objective": self._current_unit.objective,
            "unit_added_chars": list(self._current_unit.added_chars),
            "unit_tags": list(self._current_unit.tags),
            "is_boss": bool(self._current_unit.is_boss),
            "rx_avg": round(self._metric_mean(rx_acc_values), 2),
            "tx_avg": round(self._metric_mean(tx_score_values), 2),
            "accuracy": round(accuracy, 2),
            "rhythm": round(rhythm, 2),
            "score": round(unit_score, 2),
            "grade": grade,
            "stars": stars,
            "unit_unlock_min_accuracy": self.UNIT_UNLOCK_MIN_ACCURACY,
            "unit_unlock_min_rhythm": self.UNIT_UNLOCK_MIN_RHYTHM,
            "stage_unlock_min_accuracy": self.STAGE_UNLOCK_MIN_ACCURACY,
            "stage_unlock_min_rhythm": self.STAGE_UNLOCK_MIN_RHYTHM,
            "stage_unlock_min_score": self.STAGE_UNLOCK_MIN_SCORE,
            "xp_base": base_xp,
            "xp_bonus": bonus_xp,
            "xp_gain": gained_xp,
            "combo_units": int(self._profile.get("combo_units", 0)),
            "daily_goal": int(self._profile.get("daily_goal", 3)),
            "daily_units_done": int(self._profile.get("daily_units_done", 0)),
            "streak_days": int(self._profile.get("streak_days", 0)),
            "stage_upgraded": stage_upgraded,
            "unlock_chars": unlocked_chars,
            "next_stage_id": int(self._profile.get("current_stage", stage_after)),
            "next_unit_index": int(self._profile.get("current_unit", unit_after)),
            "profile": dict(self._profile),
            "steps": [
                {
                    "task": asdict(task),
                    "result": {
                        "mode": result.mode,
                        "target_text": result.target_text,
                        "user_text": result.user_text,
                        "decoded_text": result.decoded_text,
                        "metrics": asdict(result.metrics),
                    },
                }
                for task, result in self._step_results
            ],
        }

        self._running = False
        self._waiting_result = False
        self._current_task = None
        self._emit_state(payload)
        self._emit_finish(payload)
