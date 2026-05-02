import sqlite3
from dataclasses import dataclass
from .config import DB_PATH


@dataclass
class Result:
    model_name: str
    payload_type: str
    payload_name: str
    input_prompt: str
    output: str
    success: bool
    severity: str
    timestamp: str
    run_number: int
    response_time_ms: int


class ResultsDB:
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS results (
                    id               INTEGER PRIMARY KEY AUTOINCREMENT,
                    model_name       TEXT NOT NULL,
                    payload_type     TEXT NOT NULL,
                    payload_name     TEXT NOT NULL,
                    input_prompt     TEXT NOT NULL,
                    output           TEXT NOT NULL,
                    success          TEXT NOT NULL,
                    severity         TEXT NOT NULL,
                    run_number       INTEGER NOT NULL,
                    response_time_ms INTEGER,
                    timestamp        TEXT NOT NULL
                )
            """)
            conn.commit()

    def insert(self, r: Result):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO results
                    (model_name, payload_type, payload_name, input_prompt,
                     output, success, severity, run_number, response_time_ms, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    r.model_name, r.payload_type, r.payload_name,
                    r.input_prompt, r.output,
                    "yes" if r.success else "no",
                    r.severity, r.run_number, r.response_time_ms, r.timestamp,
                ),
            )
            conn.commit()

    def fetch_all(self) -> list[dict]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("SELECT * FROM results ORDER BY id").fetchall()
            return [dict(r) for r in rows]

    def fetch_stats(self) -> dict:
        with sqlite3.connect(self.db_path) as conn:
            model_rows = conn.execute("""
                SELECT model_name,
                       COUNT(*) as total,
                       SUM(CASE WHEN success='yes' THEN 1 ELSE 0 END) as successes
                FROM results GROUP BY model_name
            """).fetchall()

            type_rows = conn.execute("""
                SELECT payload_type,
                       COUNT(*) as total,
                       SUM(CASE WHEN success='yes' THEN 1 ELSE 0 END) as successes,
                       severity
                FROM results GROUP BY payload_type
            """).fetchall()

            sample_rows = conn.execute("""
                SELECT payload_type, model_name, input_prompt, output, success
                FROM results
                WHERE id IN (
                    SELECT MIN(id) FROM results GROUP BY payload_type, model_name
                )
                ORDER BY payload_type, model_name
            """).fetchall()

        return {
            "model_stats":  [dict(r) for r in model_rows],
            "type_stats":   [dict(r) for r in type_rows],
            "samples":      [dict(r) for r in sample_rows],
        }
