from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


def _as_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on", "y"}


def _split_csv(value: str | None) -> tuple[str, ...]:
    if not value:
        return ()
    return tuple(item.strip() for item in value.split(",") if item.strip())


@dataclass(frozen=True)
class Settings:
    bot_name: str
    prefix: str
    owner_numbers: frozenset[str]
    session_db: Path
    app_db: Path
    max_download_mb: int
    welcome_default: bool
    auto_responder: bool
    strike_limit: int
    toxic_words: tuple[str, ...]

    @classmethod
    def load(cls) -> "Settings":
        load_dotenv()
        session_db = Path(os.getenv("SESSION_DB", "data/whatsapp-session.db"))
        app_db = Path(os.getenv("APP_DB", "data/daffo-botz.db"))
        session_db.parent.mkdir(parents=True, exist_ok=True)
        app_db.parent.mkdir(parents=True, exist_ok=True)
        Path("downloads").mkdir(parents=True, exist_ok=True)
        return cls(
            bot_name=os.getenv("BOT_NAME", "Daffo-Botz"),
            prefix=os.getenv("PREFIX", "."),
            owner_numbers=frozenset(_split_csv(os.getenv("OWNER_NUMBERS"))),
            session_db=session_db,
            app_db=app_db,
            max_download_mb=max(5, int(os.getenv("MAX_DOWNLOAD_MB", "80"))),
            welcome_default=_as_bool(os.getenv("WELCOME_DEFAULT"), True),
            auto_responder=_as_bool(os.getenv("AUTO_RESPONDER"), True),
            strike_limit=max(1, int(os.getenv("STRIKE_LIMIT", "3"))),
            toxic_words=tuple(w.lower() for w in _split_csv(os.getenv("TOXIC_WORDS"))),
        )
