from pathlib import Path
import sqlite3

from audit_risk_mapper.feedback_store import save_feedback


def test_feedback_persists(tmp_path: Path):
    db_path = tmp_path / "feedback.sqlite3"
    feedback_id = save_feedback(db_path, "SCN001", "PROC001", "helpful", "좋음")
    with sqlite3.connect(db_path) as con:
        rows = con.execute("SELECT feedback_id FROM feedback").fetchall()
    assert rows == [(feedback_id,)]
