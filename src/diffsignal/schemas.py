from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class MonitorCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    url: str = Field(min_length=8, max_length=2048)
    ignore_selector: str | None = Field(default=None, max_length=500)
    interval_minutes: int = Field(default=60, ge=1, le=10080)

    @field_validator("name")
    @classmethod
    def strip_name(cls, value: str) -> str:
        return value.strip()


class MonitorRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    url: str
    ignore_selector: str | None
    interval_minutes: int
    enabled: bool
    last_checked_at: datetime | None
    next_check_at: datetime | None
    last_status: str
    last_error: str | None
    created_at: datetime


class ChangeRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    monitor_id: int
    diff: str
    created_at: datetime


class CheckRead(BaseModel):
    status: str
    changed: bool
    change_id: int | None = None
