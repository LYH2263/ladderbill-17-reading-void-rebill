import sqlite3
from datetime import datetime, timezone

READING_COLS = "id, account_id, kwh, peak, voided, void_reason, voided_at"


def list_all(conn: sqlite3.Connection, include_voided: bool = False) -> list[dict]:
    sql = f"SELECT {READING_COLS} FROM readings"
    if not include_voided:
        sql += " WHERE voided=0"
    sql += " ORDER BY id"
    return [dict(r) for r in conn.execute(sql).fetchall()]


def for_account(conn: sqlite3.Connection, account_id: int, include_voided: bool = False) -> list[dict]:
    sql = f"SELECT {READING_COLS} FROM readings WHERE account_id=?"
    if not include_voided:
        sql += " AND voided=0"
    sql += " ORDER BY id"
    return [dict(r) for r in conn.execute(sql, (account_id,)).fetchall()]


def get(conn: sqlite3.Connection, reading_id: int) -> dict | None:
    row = conn.execute(
        f"SELECT {READING_COLS} FROM readings WHERE id=?", (reading_id,)
    ).fetchone()
    return dict(row) if row else None


def mark_voided(conn: sqlite3.Connection, reading_id: int, reason: str) -> dict | None:
    now = datetime.now(timezone.utc).isoformat()
    cur = conn.execute(
        "UPDATE readings SET voided=1, void_reason=?, voided_at=? WHERE id=? AND voided=0",
        (reason, now, reading_id),
    )
    conn.commit()
    if cur.rowcount == 0:
        return None
    return get(conn, reading_id)
