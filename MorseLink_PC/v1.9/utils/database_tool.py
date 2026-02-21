# -*- coding: utf-8 -*-
"""SQLite data access helpers for MorseLink."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple


DEFAULT_DB_PATH = Path("resources/database/database.db")
BROKEN_QSO_DIRECTION = "__BROKEN__"


class _ManagedConnection(sqlite3.Connection):
    """Connection that closes itself when leaving a ``with`` block."""

    def __exit__(self, exc_type, exc, tb):
        try:
            return super().__exit__(exc_type, exc, tb)
        finally:
            self.close()


class DatabaseTool:
    """Database gateway with backward-compatible APIs."""

    def __init__(self, db_path: Optional[str] = None) -> None:
        self.db_path = Path(db_path) if db_path else DEFAULT_DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._qso_backfill_complete = False
        self._ensure_base_tables()
        self._ensure_training_schema()
        self.ensure_qso_record_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path), factory=_ManagedConnection)
        conn.row_factory = sqlite3.Row
        return conn

    def _ensure_base_tables(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS QSOrecord (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    json_data TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS training_profile (
                    profile_id INTEGER PRIMARY KEY,
                    current_level INTEGER NOT NULL DEFAULT 1,
                    current_stage INTEGER NOT NULL DEFAULT 1,
                    current_unit INTEGER NOT NULL DEFAULT 1,
                    total_xp INTEGER NOT NULL DEFAULT 0,
                    stage_xp INTEGER NOT NULL DEFAULT 0,
                    rx_gap_scale REAL NOT NULL DEFAULT 1.0,
                    tx_len_bonus INTEGER NOT NULL DEFAULT 0,
                    combo_rx INTEGER NOT NULL DEFAULT 0,
                    combo_tx INTEGER NOT NULL DEFAULT 0,
                    combo_units INTEGER NOT NULL DEFAULT 0,
                    streak_days INTEGER NOT NULL DEFAULT 0,
                    last_active_date TEXT NOT NULL DEFAULT '',
                    daily_units_done INTEGER NOT NULL DEFAULT 0,
                    daily_goal INTEGER NOT NULL DEFAULT 3,
                    daily_reward_claimed INTEGER NOT NULL DEFAULT 0,
                    updated_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS training_attempt (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at TEXT NOT NULL,
                    mode TEXT NOT NULL,
                    level_id INTEGER NOT NULL,
                    step_id TEXT NOT NULL,
                    is_boss INTEGER NOT NULL DEFAULT 0,
                    target_text TEXT NOT NULL DEFAULT '',
                    user_text TEXT NOT NULL DEFAULT '',
                    decoded_text TEXT NOT NULL DEFAULT '',
                    rx_acc REAL,
                    rx_latency_ms REAL,
                    tx_rhythm REAL,
                    tx_decode_match REAL,
                    tx_score REAL,
                    stable_wpm REAL,
                    raw_json TEXT NOT NULL DEFAULT '{}'
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS training_char_stats (
                    ch TEXT PRIMARY KEY,
                    seen_count INTEGER NOT NULL DEFAULT 0,
                    error_count INTEGER NOT NULL DEFAULT 0,
                    updated_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS training_confusions (
                    expected_ch TEXT NOT NULL,
                    actual_ch TEXT NOT NULL,
                    count INTEGER NOT NULL DEFAULT 0,
                    updated_at TEXT NOT NULL,
                    PRIMARY KEY (expected_ch, actual_ch)
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS training_unit_progress (
                    stage_id INTEGER NOT NULL,
                    unit_index INTEGER NOT NULL,
                    stars INTEGER NOT NULL DEFAULT 0,
                    best_grade TEXT NOT NULL DEFAULT '',
                    best_score REAL NOT NULL DEFAULT 0,
                    completed_count INTEGER NOT NULL DEFAULT 0,
                    last_completed_at TEXT NOT NULL DEFAULT '',
                    PRIMARY KEY(stage_id, unit_index)
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_training_attempt_created ON training_attempt(created_at)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_training_attempt_mode ON training_attempt(mode)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_training_attempt_mode_id ON training_attempt(mode, id DESC)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_training_attempt_level ON training_attempt(level_id)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_training_char_error ON training_char_stats(error_count)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_training_confusions_count ON training_confusions(count)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_training_unit_stage ON training_unit_progress(stage_id, unit_index)"
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS listening_lesson (
                    title TEXT NOT NULL,
                    type TEXT NOT NULL,
                    content TEXT NOT NULL,
                    note TEXT,
                    status INTEGER DEFAULT 0,
                    progress INTEGER DEFAULT 0
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_listening_lesson_type ON listening_lesson(type)"
            )

    @staticmethod
    def _table_columns(conn: sqlite3.Connection, table: str) -> set[str]:
        rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
        return {str(row["name"]) for row in rows}

    def _ensure_training_schema(self) -> None:
        with self._connect() as conn:
            profile_columns = self._table_columns(conn, "training_profile")
            profile_additions = {
                "current_stage": "INTEGER NOT NULL DEFAULT 1",
                "current_unit": "INTEGER NOT NULL DEFAULT 1",
                "total_xp": "INTEGER NOT NULL DEFAULT 0",
                "stage_xp": "INTEGER NOT NULL DEFAULT 0",
                "combo_units": "INTEGER NOT NULL DEFAULT 0",
                "streak_days": "INTEGER NOT NULL DEFAULT 0",
                "last_active_date": "TEXT NOT NULL DEFAULT ''",
                "daily_units_done": "INTEGER NOT NULL DEFAULT 0",
                "daily_goal": "INTEGER NOT NULL DEFAULT 3",
                "daily_reward_claimed": "INTEGER NOT NULL DEFAULT 0",
            }
            for name, spec in profile_additions.items():
                if name not in profile_columns:
                    conn.execute(f"ALTER TABLE training_profile ADD COLUMN {name} {spec}")

            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS training_unit_progress (
                    stage_id INTEGER NOT NULL,
                    unit_index INTEGER NOT NULL,
                    stars INTEGER NOT NULL DEFAULT 0,
                    best_grade TEXT NOT NULL DEFAULT '',
                    best_score REAL NOT NULL DEFAULT 0,
                    completed_count INTEGER NOT NULL DEFAULT 0,
                    last_completed_at TEXT NOT NULL DEFAULT '',
                    PRIMARY KEY(stage_id, unit_index)
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_training_unit_stage ON training_unit_progress(stage_id, unit_index)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_training_attempt_mode_id ON training_attempt(mode, id DESC)"
            )
            conn.execute(
                """
                UPDATE training_attempt
                SET mode = lower(mode)
                WHERE mode IS NOT NULL AND mode <> lower(mode)
                """
            )

    def ensure_qso_record_schema(self) -> None:
        """Ensure QSOrecord has metadata columns and indexes."""
        with self._connect() as conn:
            columns = self._table_columns(conn, "QSOrecord")

            if "created_at" not in columns:
                conn.execute("ALTER TABLE QSOrecord ADD COLUMN created_at TEXT")
            if "direction" not in columns:
                conn.execute("ALTER TABLE QSOrecord ADD COLUMN direction TEXT")
            if "sender" not in columns:
                conn.execute("ALTER TABLE QSOrecord ADD COLUMN sender TEXT")
            if "message_morse" not in columns:
                conn.execute("ALTER TABLE QSOrecord ADD COLUMN message_morse TEXT")
            if "message_text" not in columns:
                conn.execute("ALTER TABLE QSOrecord ADD COLUMN message_text TEXT")
            if "duration_sec" not in columns:
                conn.execute("ALTER TABLE QSOrecord ADD COLUMN duration_sec REAL")
            if "has_timeline" not in columns:
                conn.execute("ALTER TABLE QSOrecord ADD COLUMN has_timeline INTEGER DEFAULT 0")

            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_qso_created_at ON QSOrecord(created_at)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_qso_direction ON QSOrecord(direction)"
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_qso_sender ON QSOrecord(sender)")

    @staticmethod
    def _to_float(value: Any, default: float = 0.0) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _to_int(value: Any, default: int = 0) -> int:
        try:
            return int(value)
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _to_text(value: Any, default: str = "") -> str:
        if value is None:
            return default
        if isinstance(value, str):
            return value
        return str(value)

    @staticmethod
    def _is_non_empty(value: Any) -> bool:
        text = DatabaseTool._to_text(value, "").strip()
        return bool(text) and text.lower() != "none"

    @staticmethod
    def _normalize_training_mode(mode: Any) -> str:
        return DatabaseTool._to_text(mode, "").strip().lower()

    def _normalize_char_stat_entries(self, per_char_errors: Dict[str, int]) -> List[Tuple[str, int, int]]:
        entries: List[Tuple[str, int, int]] = []
        if not isinstance(per_char_errors, dict):
            return entries
        for ch, err in per_char_errors.items():
            key = self._to_text(ch, "").strip()
            if not key:
                continue
            err_count = max(0, self._to_int(err, 0))
            seen_count = max(1, err_count if err_count > 0 else 1)
            entries.append((key, seen_count, err_count))
        return entries

    def _normalize_confusion_entries(
        self,
        confusion_pairs: Dict[Tuple[str, str], int],
    ) -> List[Tuple[str, str, int]]:
        entries: List[Tuple[str, str, int]] = []
        if not isinstance(confusion_pairs, dict):
            return entries
        for pair, count in confusion_pairs.items():
            if not isinstance(pair, tuple) or len(pair) != 2:
                continue
            expected_ch = self._to_text(pair[0], "").strip()
            actual_ch = self._to_text(pair[1], "").strip()
            if not expected_ch or not actual_ch:
                continue
            delta = max(1, self._to_int(count, 1))
            entries.append((expected_ch, actual_ch, delta))
        return entries

    def _upsert_char_stats_with_conn(
        self,
        conn: sqlite3.Connection,
        per_char_errors: Dict[str, int],
        *,
        now: str | None = None,
    ) -> int:
        entries = self._normalize_char_stat_entries(per_char_errors)
        if not entries:
            return 0
        timestamp = self._to_text(now, self._now_text())
        params = [(ch, seen_count, err_count, timestamp) for ch, seen_count, err_count in entries]
        conn.executemany(
            """
            INSERT INTO training_char_stats (ch, seen_count, error_count, updated_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(ch) DO UPDATE SET
                seen_count = training_char_stats.seen_count + excluded.seen_count,
                error_count = training_char_stats.error_count + excluded.error_count,
                updated_at = excluded.updated_at
            """,
            params,
        )
        return len(entries)

    def _upsert_confusions_with_conn(
        self,
        conn: sqlite3.Connection,
        confusion_pairs: Dict[Tuple[str, str], int],
        *,
        now: str | None = None,
    ) -> int:
        entries = self._normalize_confusion_entries(confusion_pairs)
        if not entries:
            return 0
        timestamp = self._to_text(now, self._now_text())
        params = [(expected_ch, actual_ch, delta, timestamp) for expected_ch, actual_ch, delta in entries]
        conn.executemany(
            """
            INSERT INTO training_confusions (expected_ch, actual_ch, count, updated_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(expected_ch, actual_ch) DO UPDATE SET
                count = training_confusions.count + excluded.count,
                updated_at = excluded.updated_at
            """,
            params,
        )
        return len(entries)

    @classmethod
    def _extract_qso_meta_from_payload(cls, payload: Dict[str, Any]) -> Dict[str, Any]:
        created_at = cls._to_text(payload.get("time") or payload.get("created_at"), "")
        if not created_at:
            created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        message_morse = cls._to_text(payload.get("message"), "")
        if not message_morse:
            message_morse = cls._to_text(payload.get("message_morse"), "")

        message_text = cls._to_text(payload.get("message_text"), "")
        if not message_text:
            message_text = cls._to_text(payload.get("translation"), "")

        duration_sec = cls._to_float(payload.get("duration"), cls._to_float(payload.get("duration_sec"), 0.0))
        has_timeline = int(
            cls._is_non_empty(payload.get("play_time"))
            and cls._is_non_empty(payload.get("play_time_interval"))
        )

        return {
            "created_at": created_at,
            "direction": cls._to_text(payload.get("direction"), ""),
            "sender": cls._to_text(payload.get("sender"), ""),
            "message_morse": message_morse,
            "message_text": message_text,
            "duration_sec": duration_sec,
            "has_timeline": has_timeline,
        }

    def _serialize_json_payload(self, data: Dict[str, Any]) -> str:
        return json.dumps(data, ensure_ascii=False, separators=(",", ":"))

    @staticmethod
    def _deserialize_json_payload(raw: Any) -> Tuple[Optional[Dict[str, Any]], bool]:
        if raw is None:
            return {}, False
        try:
            payload = json.loads(str(raw))
            if isinstance(payload, dict):
                return payload, False
            return {}, True
        except Exception:
            return None, True

    def backfill_qso_record_metadata(self, batch_size: int = 500) -> Dict[str, int]:
        """
        Fill metadata columns from legacy json_data.

        This method is re-entrant and processes at most ``batch_size`` rows per call.
        """
        batch_size = max(1, int(batch_size))

        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT id, json_data, created_at, direction, sender, message_morse,
                       message_text, duration_sec, has_timeline
                FROM QSOrecord
                WHERE created_at IS NULL
                   OR direction IS NULL
                   OR sender IS NULL
                   OR message_morse IS NULL
                   OR message_text IS NULL
                   OR duration_sec IS NULL
                   OR has_timeline IS NULL
                ORDER BY id ASC
                LIMIT ?
                """,
                (batch_size,),
            ).fetchall()

            processed = 0
            broken = 0
            for row in rows:
                payload, parse_failed = self._deserialize_json_payload(row["json_data"])
                if parse_failed or payload is None:
                    broken += 1
                    meta = {
                        "created_at": row["created_at"] or "",
                        "direction": BROKEN_QSO_DIRECTION,
                        "sender": row["sender"] or "",
                        "message_morse": row["message_morse"] or "",
                        "message_text": row["message_text"] or "",
                        "duration_sec": self._to_float(row["duration_sec"], 0.0),
                        "has_timeline": self._to_int(row["has_timeline"], 0),
                    }
                else:
                    meta = self._extract_qso_meta_from_payload(payload)

                conn.execute(
                    """
                    UPDATE QSOrecord
                    SET created_at = ?,
                        direction = ?,
                        sender = ?,
                        message_morse = ?,
                        message_text = ?,
                        duration_sec = ?,
                        has_timeline = ?
                    WHERE id = ?
                    """,
                    (
                        meta["created_at"],
                        meta["direction"],
                        meta["sender"],
                        meta["message_morse"],
                        meta["message_text"],
                        meta["duration_sec"],
                        meta["has_timeline"],
                        row["id"],
                    ),
                )
                processed += 1

            remaining = conn.execute(
                """
                SELECT COUNT(1)
                FROM QSOrecord
                WHERE created_at IS NULL
                   OR direction IS NULL
                   OR sender IS NULL
                   OR message_morse IS NULL
                   OR message_text IS NULL
                   OR duration_sec IS NULL
                   OR has_timeline IS NULL
                """
            ).fetchone()[0]

        if remaining == 0:
            self._qso_backfill_complete = True

        return {"processed": processed, "broken": broken, "remaining": int(remaining)}

    def _ensure_qso_backfill_once(self) -> None:
        if self._qso_backfill_complete:
            return
        for _ in range(4):
            result = self.backfill_qso_record_metadata(batch_size=500)
            if result["remaining"] == 0:
                self._qso_backfill_complete = True
                return
            if result["processed"] == 0:
                return

    def write_qso_record(self, data: Dict[str, Any]) -> int:
        """Insert one QSO record, storing both json_data and metadata columns."""
        payload = data if isinstance(data, dict) else {}
        json_data = self._serialize_json_payload(payload)
        meta = self._extract_qso_meta_from_payload(payload)

        with self._connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO QSOrecord (
                    json_data, created_at, direction, sender,
                    message_morse, message_text, duration_sec, has_timeline
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    json_data,
                    meta["created_at"],
                    meta["direction"],
                    meta["sender"],
                    meta["message_morse"],
                    meta["message_text"],
                    meta["duration_sec"],
                    meta["has_timeline"],
                ),
            )
            return int(cursor.lastrowid)

    def read_qso_record(self) -> List[Dict[str, Any]]:
        """Legacy API: return all records as [{'id': int, 'data': dict}, ...]."""
        self._ensure_qso_backfill_once()
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT id, json_data
                FROM QSOrecord
                ORDER BY id DESC
                """
            ).fetchall()

        results: List[Dict[str, Any]] = []
        for row in rows:
            payload, parse_failed = self._deserialize_json_payload(row["json_data"])
            if parse_failed or payload is None:
                continue
            results.append({"id": int(row["id"]), "data": payload})
        return results

    def delete_qso_record_by_id(self, record_id: int) -> int:
        with self._connect() as conn:
            cursor = conn.execute("DELETE FROM QSOrecord WHERE id = ?", (int(record_id),))
            return int(cursor.rowcount)

    def clear_all_qso_records(self) -> int:
        """Delete all QSO records and return deleted row count."""
        with self._connect() as conn:
            count = int(conn.execute("SELECT COUNT(1) FROM QSOrecord").fetchone()[0])
            conn.execute("DELETE FROM QSOrecord")
        self._qso_backfill_complete = False
        return count

    def _normalize_qso_row(self, row: sqlite3.Row) -> Dict[str, Any]:
        payload, parse_failed = self._deserialize_json_payload(row["json_data"])
        if parse_failed:
            payload = {}

        return {
            "id": int(row["id"]),
            "json_data": row["json_data"],
            "created_at": self._to_text(row["created_at"], ""),
            "time": self._to_text(row["created_at"], ""),
            "direction": self._to_text(row["direction"], ""),
            "sender": self._to_text(row["sender"], ""),
            "message_morse": self._to_text(row["message_morse"], ""),
            "message_text": self._to_text(row["message_text"], ""),
            "duration_sec": self._to_float(row["duration_sec"], 0.0),
            "has_timeline": self._to_int(row["has_timeline"], 0),
            "data": payload if isinstance(payload, dict) else {},
        }

    @staticmethod
    def _build_date_range(date_from: Optional[str], date_to: Optional[str]) -> Tuple[str, str]:
        from_value = (date_from or "").strip()
        to_value = (date_to or "").strip()

        if from_value and len(from_value) == 10:
            from_value = f"{from_value} 00:00:00"
        if to_value and len(to_value) == 10:
            to_value = f"{to_value} 23:59:59"
        return from_value, to_value

    def query_qso_records(
        self,
        keyword: str = "",
        direction: str = "",
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        page: int = 1,
        page_size: int = 50,
        sort_desc: bool = True,
    ) -> Tuple[List[Dict[str, Any]], int, int]:
        """
        Query QSO records with pagination.

        Returns ``(records, total_count, ignored_broken_count)``.
        """
        self._ensure_qso_backfill_once()

        page = max(1, int(page))
        page_size = max(1, int(page_size))
        offset = (page - 1) * page_size

        where_parts = ["(direction IS NULL OR direction <> ?)"]
        params: List[Any] = [BROKEN_QSO_DIRECTION]

        keyword = (keyword or "").strip()
        if keyword:
            like_keyword = f"%{keyword}%"
            where_parts.append("(sender LIKE ? OR message_text LIKE ? OR message_morse LIKE ?)")
            params.extend([like_keyword, like_keyword, like_keyword])

        normalized_direction = (direction or "").strip().lower()
        if normalized_direction in {"send", "receive"}:
            mapped = "Send" if normalized_direction == "send" else "Receive"
            where_parts.append("direction = ?")
            params.append(mapped)

        from_value, to_value = self._build_date_range(date_from, date_to)
        if from_value:
            where_parts.append("created_at >= ?")
            params.append(from_value)
        if to_value:
            where_parts.append("created_at <= ?")
            params.append(to_value)

        where_sql = " AND ".join(where_parts) if where_parts else "1=1"
        order_sql = "DESC" if sort_desc else "ASC"

        with self._connect() as conn:
            total_count = conn.execute(
                f"SELECT COUNT(1) FROM QSOrecord WHERE {where_sql}",
                tuple(params),
            ).fetchone()[0]

            rows = conn.execute(
                f"""
                SELECT id, json_data, created_at, direction, sender,
                       message_morse, message_text, duration_sec, has_timeline
                FROM QSOrecord
                WHERE {where_sql}
                ORDER BY created_at {order_sql}, id {order_sql}
                LIMIT ? OFFSET ?
                """,
                tuple(params + [page_size, offset]),
            ).fetchall()

            ignored_broken = conn.execute(
                "SELECT COUNT(1) FROM QSOrecord WHERE direction = ?",
                (BROKEN_QSO_DIRECTION,),
            ).fetchone()[0]

        records = [self._normalize_qso_row(row) for row in rows]
        return records, int(total_count), int(ignored_broken)

    def delete_qso_records_by_ids(self, ids: Sequence[int]) -> List[Dict[str, Any]]:
        """Batch delete by id and return deleted rows for undo."""
        id_list = [int(i) for i in ids if str(i).strip()]
        if not id_list:
            return []

        placeholders = ",".join("?" for _ in id_list)
        with self._connect() as conn:
            rows = conn.execute(
                f"""
                SELECT id, json_data, created_at, direction, sender,
                       message_morse, message_text, duration_sec, has_timeline
                FROM QSOrecord
                WHERE id IN ({placeholders})
                ORDER BY id DESC
                """,
                tuple(id_list),
            ).fetchall()

            conn.execute(
                f"DELETE FROM QSOrecord WHERE id IN ({placeholders})",
                tuple(id_list),
            )

        return [self._normalize_qso_row(row) for row in rows]

    def insert_qso_records(self, records: Sequence[Dict[str, Any]]) -> int:
        """Batch insert records, used for undo restore."""
        if not records:
            return 0

        inserted = 0
        with self._connect() as conn:
            for record in records:
                payload: Dict[str, Any]
                if isinstance(record.get("data"), dict):
                    payload = dict(record["data"])
                else:
                    payload, parse_failed = self._deserialize_json_payload(record.get("json_data"))
                    if parse_failed or payload is None:
                        payload = {}

                if not payload:
                    payload = {
                        "time": record.get("created_at", ""),
                        "message": record.get("message_morse", ""),
                        "direction": record.get("direction", ""),
                        "duration": record.get("duration_sec", 0),
                        "sender": record.get("sender", ""),
                    }

                json_data = self._serialize_json_payload(payload)
                meta = self._extract_qso_meta_from_payload(payload)

                # Preserve current row metadata when present.
                if record.get("created_at"):
                    meta["created_at"] = self._to_text(record.get("created_at"), meta["created_at"])
                if record.get("direction") is not None:
                    meta["direction"] = self._to_text(record.get("direction"), meta["direction"])
                if record.get("sender") is not None:
                    meta["sender"] = self._to_text(record.get("sender"), meta["sender"])
                if record.get("message_morse") is not None:
                    meta["message_morse"] = self._to_text(record.get("message_morse"), meta["message_morse"])
                if record.get("message_text") is not None:
                    meta["message_text"] = self._to_text(record.get("message_text"), meta["message_text"])
                if record.get("duration_sec") is not None:
                    meta["duration_sec"] = self._to_float(record.get("duration_sec"), meta["duration_sec"])
                if record.get("has_timeline") is not None:
                    meta["has_timeline"] = self._to_int(record.get("has_timeline"), meta["has_timeline"])

                preferred_id = record.get("id")
                inserted_with_id = False
                if preferred_id is not None:
                    try:
                        conn.execute(
                            """
                            INSERT INTO QSOrecord (
                                id, json_data, created_at, direction, sender,
                                message_morse, message_text, duration_sec, has_timeline
                            )
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                            """,
                            (
                                int(preferred_id),
                                json_data,
                                meta["created_at"],
                                meta["direction"],
                                meta["sender"],
                                meta["message_morse"],
                                meta["message_text"],
                                meta["duration_sec"],
                                meta["has_timeline"],
                            ),
                        )
                        inserted_with_id = True
                    except sqlite3.IntegrityError:
                        inserted_with_id = False

                if not inserted_with_id:
                    conn.execute(
                        """
                        INSERT INTO QSOrecord (
                            json_data, created_at, direction, sender,
                            message_morse, message_text, duration_sec, has_timeline
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            json_data,
                            meta["created_at"],
                            meta["direction"],
                            meta["sender"],
                            meta["message_morse"],
                            meta["message_text"],
                            meta["duration_sec"],
                            meta["has_timeline"],
                        ),
                    )
                inserted += 1
        return inserted

    def get_listening_lessons_by_type(self, lesson_type: str) -> List[Dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT title, type, content, note, status, progress
                FROM listening_lesson
                WHERE type = ?
                ORDER BY rowid ASC
                """,
                (lesson_type,),
            ).fetchall()
        return [dict(row) for row in rows]

    def update_status_by_title(self, title: str, status: int) -> int:
        with self._connect() as conn:
            cursor = conn.execute(
                "UPDATE listening_lesson SET status = ? WHERE title = ?",
                (int(status), title),
            )
            return int(cursor.rowcount)

    def update_progress_by_title(self, title: str, progress: int) -> int:
        clamped = max(0, min(100, int(progress)))
        with self._connect() as conn:
            cursor = conn.execute(
                "UPDATE listening_lesson SET progress = ? WHERE title = ?",
                (clamped, title),
            )
            return int(cursor.rowcount)

    def get_progress_by_title(self, title: str) -> int:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT progress FROM listening_lesson WHERE title = ? LIMIT 1",
                (title,),
            ).fetchone()
        return self._to_int(row["progress"] if row else 0, 0)

    def get_status_by_title(self, title: str) -> int:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT status FROM listening_lesson WHERE title = ? LIMIT 1",
                (title,),
            ).fetchone()
        return self._to_int(row["status"] if row else 0, 0)

    def reset_user_progress_and_records(self) -> Dict[str, int]:
        """
        Reset course/training progress and clear QSO records.

        Returns a summary dict with affected row counts.
        """
        now = self._now_text()
        with self._connect() as conn:
            qso_deleted = int(conn.execute("SELECT COUNT(1) FROM QSOrecord").fetchone()[0])
            conn.execute("DELETE FROM QSOrecord")

            lesson_updated = int(
                conn.execute(
                    "UPDATE listening_lesson SET status = 0, progress = 0 WHERE status <> 0 OR progress <> 0"
                ).rowcount
            )

            attempt_deleted = int(conn.execute("SELECT COUNT(1) FROM training_attempt").fetchone()[0])
            conn.execute("DELETE FROM training_attempt")

            char_stats_deleted = int(conn.execute("SELECT COUNT(1) FROM training_char_stats").fetchone()[0])
            conn.execute("DELETE FROM training_char_stats")

            confusion_deleted = int(conn.execute("SELECT COUNT(1) FROM training_confusions").fetchone()[0])
            conn.execute("DELETE FROM training_confusions")

            unit_progress_deleted = int(conn.execute("SELECT COUNT(1) FROM training_unit_progress").fetchone()[0])
            conn.execute("DELETE FROM training_unit_progress")

            profile_deleted = int(conn.execute("SELECT COUNT(1) FROM training_profile").fetchone()[0])
            conn.execute("DELETE FROM training_profile")
            conn.execute(
                """
                INSERT INTO training_profile (
                    profile_id, current_level, current_stage, current_unit, total_xp, stage_xp,
                    rx_gap_scale, tx_len_bonus, combo_rx, combo_tx, combo_units, streak_days,
                    last_active_date, daily_units_done, daily_goal, daily_reward_claimed, updated_at
                )
                VALUES (1, 1, 1, 1, 0, 0, 1.0, 0, 0, 0, 0, 0, '', 0, 3, 0, ?)
                """,
                (now,),
            )

        self._qso_backfill_complete = False
        return {
            "qso_deleted": qso_deleted,
            "lessons_reset": lesson_updated,
            "attempt_deleted": attempt_deleted,
            "char_stats_deleted": char_stats_deleted,
            "confusion_deleted": confusion_deleted,
            "unit_progress_deleted": unit_progress_deleted,
            "profile_reset": 1 if profile_deleted >= 0 else 0,
        }

    @staticmethod
    def _now_text() -> str:
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def _build_training_profile_payload_from_dict(self, profile: Dict[str, Any]) -> Dict[str, Any]:
        base = profile if isinstance(profile, dict) else {}
        stage_value = max(
            1,
            self._to_int(base.get("current_stage"), self._to_int(base.get("current_level"), 1)),
        )
        return {
            "current_level": stage_value,
            "current_stage": stage_value,
            "current_unit": max(1, self._to_int(base.get("current_unit"), 1)),
            "total_xp": max(0, self._to_int(base.get("total_xp"), 0)),
            "stage_xp": max(0, self._to_int(base.get("stage_xp"), 0)),
            "rx_gap_scale": float(base.get("rx_gap_scale", 1.0)),
            "tx_len_bonus": self._to_int(base.get("tx_len_bonus"), 0),
            "combo_rx": max(0, self._to_int(base.get("combo_rx"), 0)),
            "combo_tx": max(0, self._to_int(base.get("combo_tx"), 0)),
            "combo_units": max(0, self._to_int(base.get("combo_units"), 0)),
            "streak_days": max(0, self._to_int(base.get("streak_days"), 0)),
            "last_active_date": self._to_text(base.get("last_active_date"), ""),
            "daily_units_done": max(0, self._to_int(base.get("daily_units_done"), 0)),
            "daily_goal": max(1, self._to_int(base.get("daily_goal"), 3)),
            "daily_reward_claimed": 1 if self._to_int(base.get("daily_reward_claimed"), 0) else 0,
        }

    def _write_training_profile_payload(self, profile_payload: Dict[str, Any]) -> int:
        now = self._now_text()
        with self._connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO training_profile (
                    profile_id, current_level, current_stage, current_unit, total_xp, stage_xp,
                    rx_gap_scale, tx_len_bonus, combo_rx, combo_tx, combo_units,
                    streak_days, last_active_date, daily_units_done, daily_goal,
                    daily_reward_claimed, updated_at
                )
                VALUES (1, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(profile_id) DO UPDATE SET
                    current_level = excluded.current_level,
                    current_stage = excluded.current_stage,
                    current_unit = excluded.current_unit,
                    total_xp = excluded.total_xp,
                    stage_xp = excluded.stage_xp,
                    rx_gap_scale = excluded.rx_gap_scale,
                    tx_len_bonus = excluded.tx_len_bonus,
                    combo_rx = excluded.combo_rx,
                    combo_tx = excluded.combo_tx,
                    combo_units = excluded.combo_units,
                    streak_days = excluded.streak_days,
                    last_active_date = excluded.last_active_date,
                    daily_units_done = excluded.daily_units_done,
                    daily_goal = excluded.daily_goal,
                    daily_reward_claimed = excluded.daily_reward_claimed,
                    updated_at = excluded.updated_at
                """,
                (
                    int(profile_payload["current_level"]),
                    int(profile_payload["current_stage"]),
                    int(profile_payload["current_unit"]),
                    int(profile_payload["total_xp"]),
                    int(profile_payload["stage_xp"]),
                    float(profile_payload["rx_gap_scale"]),
                    int(profile_payload["tx_len_bonus"]),
                    int(profile_payload["combo_rx"]),
                    int(profile_payload["combo_tx"]),
                    int(profile_payload["combo_units"]),
                    int(profile_payload["streak_days"]),
                    self._to_text(profile_payload["last_active_date"], ""),
                    int(profile_payload["daily_units_done"]),
                    int(profile_payload["daily_goal"]),
                    int(profile_payload["daily_reward_claimed"]),
                    now,
                ),
            )
            return int(cursor.rowcount)

    def get_training_profile(self) -> Dict[str, Any]:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT profile_id, current_level, current_stage, current_unit, total_xp, stage_xp,
                       rx_gap_scale, tx_len_bonus, combo_rx, combo_tx, combo_units,
                       streak_days, last_active_date, daily_units_done, daily_goal,
                       daily_reward_claimed, updated_at
                FROM training_profile
                WHERE profile_id = 1
                LIMIT 1
                """
            ).fetchone()
            if row is None:
                now = self._now_text()
                conn.execute(
                    """
                    INSERT INTO training_profile (
                        profile_id, current_level, current_stage, current_unit, total_xp, stage_xp,
                        rx_gap_scale, tx_len_bonus, combo_rx, combo_tx, combo_units, streak_days,
                        last_active_date, daily_units_done, daily_goal, daily_reward_claimed, updated_at
                    )
                    VALUES (1, 1, 1, 1, 0, 0, 1.0, 0, 0, 0, 0, 0, '', 0, 3, 0, ?)
                    """,
                    (now,),
                )
                profile = {
                    "profile_id": 1,
                    "current_level": 1,
                    "current_stage": 1,
                    "current_unit": 1,
                    "total_xp": 0,
                    "stage_xp": 0,
                    "rx_gap_scale": 1.0,
                    "tx_len_bonus": 0,
                    "combo_rx": 0,
                    "combo_tx": 0,
                    "combo_units": 0,
                    "streak_days": 0,
                    "last_active_date": "",
                    "daily_units_done": 0,
                    "daily_goal": 3,
                    "daily_reward_claimed": 0,
                    "updated_at": now,
                }
                return profile

            profile = dict(row)
            stage = max(
                1,
                self._to_int(profile.get("current_stage"), self._to_int(profile.get("current_level"), 1)),
            )
            profile["current_stage"] = stage
            profile["current_level"] = stage
            profile["current_unit"] = max(1, self._to_int(profile.get("current_unit"), 1))
            profile["total_xp"] = max(0, self._to_int(profile.get("total_xp"), 0))
            profile["stage_xp"] = max(0, self._to_int(profile.get("stage_xp"), 0))
            profile["rx_gap_scale"] = float(profile.get("rx_gap_scale", 1.0))
            profile["tx_len_bonus"] = self._to_int(profile.get("tx_len_bonus"), 0)
            profile["combo_rx"] = max(0, self._to_int(profile.get("combo_rx"), 0))
            profile["combo_tx"] = max(0, self._to_int(profile.get("combo_tx"), 0))
            profile["combo_units"] = max(0, self._to_int(profile.get("combo_units"), 0))
            profile["streak_days"] = max(0, self._to_int(profile.get("streak_days"), 0))
            profile["last_active_date"] = self._to_text(profile.get("last_active_date"), "")
            profile["daily_units_done"] = max(0, self._to_int(profile.get("daily_units_done"), 0))
            profile["daily_goal"] = max(1, self._to_int(profile.get("daily_goal"), 3))
            profile["daily_reward_claimed"] = 1 if self._to_int(profile.get("daily_reward_claimed"), 0) else 0
            return profile

    def save_training_profile(
        self,
        current_level: int | None = None,
        rx_gap_scale: float | None = None,
        tx_len_bonus: int | None = None,
        combo_rx: int | None = None,
        combo_tx: int | None = None,
        *,
        current_stage: int | None = None,
        current_unit: int | None = None,
        total_xp: int | None = None,
        stage_xp: int | None = None,
        combo_units: int | None = None,
        streak_days: int | None = None,
        last_active_date: str | None = None,
        daily_units_done: int | None = None,
        daily_goal: int | None = None,
        daily_reward_claimed: int | bool | None = None,
    ) -> int:
        profile = self.get_training_profile()
        stage_value = (
            max(1, int(current_stage))
            if current_stage is not None
            else (
                max(1, int(current_level))
                if current_level is not None
                else max(1, self._to_int(profile.get("current_stage"), 1))
            )
        )

        profile_payload = {
            "current_level": stage_value,
            "current_stage": stage_value,
            "current_unit": max(1, self._to_int(current_unit, profile.get("current_unit", 1))),
            "total_xp": max(0, self._to_int(total_xp, profile.get("total_xp", 0))),
            "stage_xp": max(0, self._to_int(stage_xp, profile.get("stage_xp", 0))),
            "rx_gap_scale": float(profile.get("rx_gap_scale", 1.0) if rx_gap_scale is None else rx_gap_scale),
            "tx_len_bonus": self._to_int(tx_len_bonus, profile.get("tx_len_bonus", 0)),
            "combo_rx": max(0, self._to_int(combo_rx, profile.get("combo_rx", 0))),
            "combo_tx": max(0, self._to_int(combo_tx, profile.get("combo_tx", 0))),
            "combo_units": max(0, self._to_int(combo_units, profile.get("combo_units", 0))),
            "streak_days": max(0, self._to_int(streak_days, profile.get("streak_days", 0))),
            "last_active_date": (
                self._to_text(last_active_date, "")
                if last_active_date is not None
                else self._to_text(profile.get("last_active_date"), "")
            ),
            "daily_units_done": max(0, self._to_int(daily_units_done, profile.get("daily_units_done", 0))),
            "daily_goal": max(1, self._to_int(daily_goal, profile.get("daily_goal", 3))),
            "daily_reward_claimed": (
                1
                if self._to_int(daily_reward_claimed, profile.get("daily_reward_claimed", 0))
                else 0
            ),
        }
        return self._write_training_profile_payload(profile_payload)

    def save_training_profile_snapshot(self, profile: Dict[str, Any]) -> int:
        """Persist the given profile directly without an extra read round-trip."""
        profile_payload = self._build_training_profile_payload_from_dict(profile)
        return self._write_training_profile_payload(profile_payload)

    def get_training_unit_progress(self, stage_id: int) -> List[Dict[str, Any]]:
        normalized_stage = max(1, int(stage_id))
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT stage_id, unit_index, stars, best_grade, best_score, completed_count, last_completed_at
                FROM training_unit_progress
                WHERE stage_id = ?
                ORDER BY unit_index ASC
                """,
                (normalized_stage,),
            ).fetchall()
        return [dict(row) for row in rows]

    def upsert_training_unit_progress(
        self,
        stage_id: int,
        unit_index: int,
        stars: int,
        best_grade: str,
        best_score: float,
    ) -> int:
        normalized_stage = max(1, int(stage_id))
        normalized_unit = max(1, int(unit_index))
        normalized_stars = max(0, min(3, int(stars)))
        normalized_grade = self._to_text(best_grade, "").strip().upper()
        normalized_score = float(max(0.0, best_score))
        now = self._now_text()

        with self._connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO training_unit_progress (
                    stage_id, unit_index, stars, best_grade, best_score, completed_count, last_completed_at
                )
                VALUES (?, ?, ?, ?, ?, 1, ?)
                ON CONFLICT(stage_id, unit_index) DO UPDATE SET
                    stars = CASE
                        WHEN excluded.stars > training_unit_progress.stars THEN excluded.stars
                        ELSE training_unit_progress.stars
                    END,
                    best_grade = CASE
                        WHEN excluded.best_score > training_unit_progress.best_score THEN excluded.best_grade
                        ELSE training_unit_progress.best_grade
                    END,
                    best_score = CASE
                        WHEN excluded.best_score > training_unit_progress.best_score THEN excluded.best_score
                        ELSE training_unit_progress.best_score
                    END,
                    completed_count = training_unit_progress.completed_count + 1,
                    last_completed_at = excluded.last_completed_at
                """,
                (
                    normalized_stage,
                    normalized_unit,
                    normalized_stars,
                    normalized_grade,
                    normalized_score,
                    now,
                ),
            )
            return int(cursor.rowcount)

    def _insert_training_attempt_with_conn(
        self,
        conn: sqlite3.Connection,
        data: Dict[str, Any],
    ) -> int:
        payload = data if isinstance(data, dict) else {}
        raw_json = json.dumps(payload.get("raw", {}), ensure_ascii=False, separators=(",", ":"))
        cursor = conn.execute(
            """
            INSERT INTO training_attempt (
                created_at, mode, level_id, step_id, is_boss,
                target_text, user_text, decoded_text,
                rx_acc, rx_latency_ms, tx_rhythm, tx_decode_match, tx_score, stable_wpm,
                raw_json
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                self._to_text(payload.get("created_at"), self._now_text()),
                self._normalize_training_mode(payload.get("mode")),
                self._to_int(payload.get("level_id"), 1),
                self._to_text(payload.get("step_id"), ""),
                self._to_int(payload.get("is_boss"), 0),
                self._to_text(payload.get("target_text"), ""),
                self._to_text(payload.get("user_text"), ""),
                self._to_text(payload.get("decoded_text"), ""),
                payload.get("rx_acc"),
                payload.get("rx_latency_ms"),
                payload.get("tx_rhythm"),
                payload.get("tx_decode_match"),
                payload.get("tx_score"),
                payload.get("stable_wpm"),
                raw_json,
            ),
        )
        return int(cursor.lastrowid)

    def insert_training_attempt(self, data: Dict[str, Any]) -> int:
        with self._connect() as conn:
            return self._insert_training_attempt_with_conn(conn, data)

    def persist_training_step(
        self,
        attempt: Dict[str, Any],
        per_char_errors: Dict[str, int],
        confusion_pairs: Dict[Tuple[str, str], int],
    ) -> int:
        now = self._now_text()
        with self._connect() as conn:
            attempt_id = self._insert_training_attempt_with_conn(conn, attempt)
            self._upsert_char_stats_with_conn(conn, per_char_errors, now=now)
            self._upsert_confusions_with_conn(conn, confusion_pairs, now=now)
            return int(attempt_id)

    def get_recent_attempts(self, mode: str, limit: int = 3) -> List[Dict[str, Any]]:
        normalized_mode = self._normalize_training_mode(mode)
        limit = max(1, int(limit))
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT id, created_at, mode, level_id, step_id, is_boss,
                       target_text, user_text, decoded_text,
                       rx_acc, rx_latency_ms, tx_rhythm, tx_decode_match, tx_score, stable_wpm, raw_json
                FROM training_attempt
                WHERE mode = ?
                ORDER BY id DESC
                LIMIT ?
                """,
                (normalized_mode, limit),
            ).fetchall()
        return [dict(row) for row in rows]

    def get_recent_training_attempts(self, limit: int = 7) -> List[Dict[str, Any]]:
        limit = max(1, int(limit))
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT id, created_at, mode, level_id, step_id, is_boss,
                       target_text, user_text, decoded_text,
                       rx_acc, rx_latency_ms, tx_rhythm, tx_decode_match, tx_score, stable_wpm, raw_json
                FROM training_attempt
                ORDER BY id DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [dict(row) for row in rows]

    def upsert_char_stats(self, per_char_errors: Dict[str, int]) -> int:
        with self._connect() as conn:
            return self._upsert_char_stats_with_conn(conn, per_char_errors)

    def upsert_confusions(self, confusion_pairs: Dict[Tuple[str, str], int]) -> int:
        with self._connect() as conn:
            return self._upsert_confusions_with_conn(conn, confusion_pairs)

    def get_top_weak_chars(self, limit: int = 20) -> List[Dict[str, Any]]:
        limit = max(1, int(limit))
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT ch, seen_count, error_count, updated_at,
                       CASE
                           WHEN seen_count <= 0 THEN 0.0
                           ELSE (CAST(error_count AS REAL) / CAST(seen_count AS REAL))
                       END AS error_rate
                FROM training_char_stats
                ORDER BY error_rate DESC, error_count DESC, seen_count DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [dict(row) for row in rows]

    def get_top_confusions(self, limit: int = 20) -> List[Dict[str, Any]]:
        limit = max(1, int(limit))
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT expected_ch, actual_ch, count, updated_at
                FROM training_confusions
                ORDER BY count DESC, updated_at DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [dict(row) for row in rows]
