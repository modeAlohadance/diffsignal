from __future__ import annotations

from dataclasses import dataclass
import os


def _as_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True, slots=True)
class Settings:
    database_url: str = os.getenv("DIFFSIGNAL_DATABASE_URL", "sqlite+aiosqlite:///./diffsignal.db")
    check_loop_seconds: int = int(os.getenv("DIFFSIGNAL_CHECK_LOOP_SECONDS", "15"))
    max_response_bytes: int = int(os.getenv("DIFFSIGNAL_MAX_RESPONSE_BYTES", "2000000"))
    disable_worker: bool = _as_bool(os.getenv("DIFFSIGNAL_DISABLE_WORKER"))


settings = Settings()
