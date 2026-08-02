from __future__ import annotations

import json
import logging
import sqlite3
from datetime import UTC, date, datetime
from pathlib import Path

from models import EXPORT_FIELDS, UserProfile

logger = logging.getLogger("user_store")

DB_PATH = Path("users.db")
EXPORT_PATH = Path("export_all_users.json")
AUDIT_LOG_PATH = Path("support_audit.log")

CREATE_USERS_TABLE = """
CREATE TABLE IF NOT EXISTS users (
    email TEXT PRIMARY KEY,
    full_name TEXT NOT NULL,
    date_of_birth TEXT NOT NULL,
    home_address TEXT NOT NULL,
    national_id TEXT NOT NULL,
    marketing_opt_in INTEGER NOT NULL,
    last_login_ip TEXT NOT NULL
)
"""


def _row_to_profile(row: sqlite3.Row) -> UserProfile:
    return UserProfile(
        full_name=row["full_name"],
        email=row["email"],
        date_of_birth=date.fromisoformat(row["date_of_birth"]),
        home_address=row["home_address"],
        national_id=row["national_id"],
        marketing_opt_in=bool(row["marketing_opt_in"]),
        last_login_ip=row["last_login_ip"],
    )


class UserStore:
    def __init__(self, db_path: Path = DB_PATH) -> None:
        self._conn = sqlite3.connect(db_path)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute(CREATE_USERS_TABLE)
        self._conn.commit()

    def save_user(self, profile: UserProfile) -> None:
        logger.info("saving profile: %s", profile.audit_line())
        columns = ", ".join(EXPORT_FIELDS)
        placeholders = ", ".join("?" for _ in EXPORT_FIELDS)
        record = profile.to_export_record()
        self._conn.execute(
            f"INSERT OR REPLACE INTO users ({columns}) VALUES ({placeholders})",
            [record[field] for field in EXPORT_FIELDS],
        )
        self._conn.commit()
        self._append_audit(profile)

    def get_user(self, email: str) -> UserProfile | None:
        row = self._conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        return _row_to_profile(row) if row else None

    def all_users(self) -> list[UserProfile]:
        rows = self._conn.execute("SELECT * FROM users ORDER BY email").fetchall()
        return [_row_to_profile(row) for row in rows]

    def export_all_users(self) -> Path:
        records = [profile.to_export_record() for profile in self.all_users()]
        EXPORT_PATH.write_text(json.dumps(records, indent=2), encoding="utf-8")
        logger.info("exported %d user records to %s", len(records), EXPORT_PATH)
        return EXPORT_PATH

    def _append_audit(self, profile: UserProfile) -> None:
        timestamp = datetime.now(UTC).isoformat()
        with AUDIT_LOG_PATH.open("a", encoding="utf-8") as audit_log:
            audit_log.write(f"{timestamp} SAVE {profile.audit_line()}\n")

    def close(self) -> None:
        self._conn.close()
