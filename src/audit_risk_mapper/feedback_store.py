from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

VALID_FEEDBACK = {"helpful", "relevant_but_lower_priority", "not_applicable_to_case", "needs_more_information"}


def init_store(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as con:
        con.execute(
            """
            CREATE TABLE IF NOT EXISTS feedback (
                feedback_id TEXT PRIMARY KEY,
                scenario_id TEXT NOT NULL,
                procedure_id TEXT NOT NULL,
                feedback_type TEXT NOT NULL,
                feedback_reason TEXT,
                created_at TEXT NOT NULL,
                input_snapshot TEXT,
                model_version TEXT,
                dataset_version TEXT
            )
            """
        )


def save_feedback(path: Path, scenario_id: str, procedure_id: str, feedback_type: str, feedback_reason: str = "", input_snapshot: dict | None = None, model_version: str = "rules-v0", dataset_version: str = "seed-v0") -> str:
    if feedback_type not in VALID_FEEDBACK:
        raise ValueError(f"Invalid feedback_type: {feedback_type}")
    init_store(path)
    feedback_id = str(uuid4())
    with sqlite3.connect(path) as con:
        con.execute(
            "INSERT INTO feedback VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                feedback_id, scenario_id, procedure_id, feedback_type, feedback_reason,
                datetime.now(timezone.utc).isoformat(), json.dumps(input_snapshot or {}, ensure_ascii=False),
                model_version, dataset_version,
            ),
        )
    return feedback_id
