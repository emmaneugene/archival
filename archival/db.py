import json
import sqlite3
from datetime import datetime
from pathlib import Path

from archival.jobs.base import JobResult, JobStatus


def get_connection(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    _init_db(conn)
    return conn


def _init_db(conn: sqlite3.Connection) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_name TEXT NOT NULL,
            status TEXT NOT NULL,
            message TEXT,
            metadata TEXT,
            started_at TEXT NOT NULL,
            finished_at TEXT NOT NULL
        )
    """)
    conn.commit()


def save_run(conn: sqlite3.Connection, job_name: str, result: JobResult) -> int:
    cursor = conn.execute(
        """
        INSERT INTO runs (job_name, status, message, metadata, started_at, finished_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            job_name,
            result.status.value,
            result.message,
            json.dumps(result.metadata) if result.metadata else None,
            result.started_at.isoformat() if result.started_at else None,
            result.finished_at.isoformat() if result.finished_at else None,
        ),
    )
    conn.commit()
    return cursor.lastrowid


def get_runs(
    conn: sqlite3.Connection, job_name: str | None = None, limit: int = 20
) -> list[dict]:
    if job_name:
        cursor = conn.execute(
            """
            SELECT * FROM runs WHERE job_name = ? ORDER BY id DESC LIMIT ?
            """,
            (job_name, limit),
        )
    else:
        cursor = conn.execute(
            """
            SELECT * FROM runs ORDER BY id DESC LIMIT ?
            """,
            (limit,),
        )
    return [dict(row) for row in cursor.fetchall()]
