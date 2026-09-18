import json
import sqlite3
from datetime import datetime, timezone

RUN_COLS = "id, kind, account_id, reading_id, input_json, result_json, created_at"


def insert(
    conn: sqlite3.Connection,
    kind: str,
    payload: dict,
    result: dict,
    account_id: int | None = None,
    reading_id: int | None = None,
) -> int:
    now = datetime.now(timezone.utc).isoformat()
    cur = conn.execute(
        """
        INSERT INTO calc_runs(kind, account_id, reading_id, input_json, result_json, created_at)
        VALUES (?,?,?,?,?,?)
        """,
        (
            kind,
            account_id,
            reading_id,
            json.dumps(payload, ensure_ascii=False),
            json.dumps(result, ensure_ascii=False),
            now,
        ),
    )
    conn.commit()
    return int(cur.lastrowid)


def list_recent(conn: sqlite3.Connection, limit: int = 50) -> list[dict]:
    q = f"""
    SELECT {RUN_COLS}
    FROM calc_runs ORDER BY id DESC LIMIT ?
    """
    return [dict(r) for r in conn.execute(q, (limit,)).fetchall()]


def get(conn: sqlite3.Connection, run_id: int) -> dict | None:
    row = conn.execute(f"SELECT {RUN_COLS} FROM calc_runs WHERE id=?", (run_id,)).fetchone()
    return dict(row) if row else None
