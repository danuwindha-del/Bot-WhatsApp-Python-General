from __future__ import annotations

import sqlite3
import threading
from pathlib import Path


class SQLiteStore:
    def __init__(self, path: Path, welcome_default: bool = True):
        self.path = path
        self.welcome_default = welcome_default
        self._lock = threading.RLock()
        self._conn = sqlite3.connect(path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self) -> None:
        with self._lock, self._conn:
            self._conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS group_settings (
                    group_jid TEXT PRIMARY KEY,
                    anti_link INTEGER NOT NULL DEFAULT 0,
                    anti_toxic INTEGER NOT NULL DEFAULT 0,
                    welcome INTEGER NOT NULL DEFAULT 1
                );
                CREATE TABLE IF NOT EXISTS strikes (
                    group_jid TEXT NOT NULL,
                    user_jid TEXT NOT NULL,
                    count INTEGER NOT NULL DEFAULT 0,
                    PRIMARY KEY(group_jid, user_jid)
                );
                """
            )

    def _ensure_group(self, group_jid: str) -> None:
        with self._lock, self._conn:
            self._conn.execute(
                "INSERT OR IGNORE INTO group_settings(group_jid, welcome) VALUES(?, ?)",
                (group_jid, int(self.welcome_default)),
            )

    def get_group_settings(self, group_jid: str) -> dict[str, bool]:
        self._ensure_group(group_jid)
        with self._lock:
            row = self._conn.execute(
                "SELECT anti_link, anti_toxic, welcome FROM group_settings WHERE group_jid=?",
                (group_jid,),
            ).fetchone()
        return {
            "anti_link": bool(row["anti_link"]),
            "anti_toxic": bool(row["anti_toxic"]),
            "welcome": bool(row["welcome"]),
        }

    def set_group_flag(self, group_jid: str, flag: str, enabled: bool) -> None:
        if flag not in {"anti_link", "anti_toxic", "welcome"}:
            raise ValueError("Unknown group setting")
        self._ensure_group(group_jid)
        with self._lock, self._conn:
            self._conn.execute(
                f"UPDATE group_settings SET {flag}=? WHERE group_jid=?",
                (int(enabled), group_jid),
            )

    def add_strike(self, group_jid: str, user_jid: str) -> int:
        with self._lock, self._conn:
            self._conn.execute(
                """
                INSERT INTO strikes(group_jid, user_jid, count) VALUES(?, ?, 1)
                ON CONFLICT(group_jid, user_jid) DO UPDATE SET count=count+1
                """,
                (group_jid, user_jid),
            )
            row = self._conn.execute(
                "SELECT count FROM strikes WHERE group_jid=? AND user_jid=?",
                (group_jid, user_jid),
            ).fetchone()
        return int(row["count"])

    def reset_strike(self, group_jid: str, user_jid: str) -> None:
        with self._lock, self._conn:
            self._conn.execute(
                "DELETE FROM strikes WHERE group_jid=? AND user_jid=?",
                (group_jid, user_jid),
            )

    def close(self):
        with self._lock:self._conn.close()
