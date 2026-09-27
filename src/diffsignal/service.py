from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
import difflib
import hashlib

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .content import normalize_content
from .fetcher import fetch_url
from .models import Change, Monitor, Snapshot, utcnow


@dataclass(frozen=True, slots=True)
class CheckResult:
    status: str
    changed: bool
    change_id: int | None = None


def build_diff(before: str, after: str, limit: int = 100_000) -> str:
    difference = "".join(
        difflib.unified_diff(
            before.splitlines(keepends=True),
            after.splitlines(keepends=True),
            fromfile="previous",
            tofile="current",
            n=3,
        )
    )
    if len(difference) > limit:
        return difference[:limit] + "\n... diff truncated ...\n"
    return difference


async def check_monitor(session: AsyncSession, monitor_id: int) -> CheckResult:
    monitor = await session.get(Monitor, monitor_id)
    if monitor is None:
        raise LookupError("monitor not found")

    now = utcnow()
    latest = await session.scalar(
        select(Snapshot).where(Snapshot.monitor_id == monitor.id).order_by(Snapshot.id.desc()).limit(1)
    )
    try:
        fetched = await fetch_url(
            monitor.url,
            etag=latest.etag if latest else None,
            last_modified=latest.last_modified if latest else None,
        )
        monitor.last_checked_at = now
        monitor.next_check_at = now + timedelta(minutes=monitor.interval_minutes)
        monitor.last_error = None
        if fetched.not_modified:
            monitor.last_status = "unchanged"
            await session.commit()
            return CheckResult("unchanged", False)

        normalized = normalize_content(fetched.body or "", fetched.content_type, monitor.ignore_selector)
        content_hash = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
        if latest and latest.content_hash == content_hash:
            monitor.last_status = "unchanged"
            monitor.last_hash = content_hash
            await session.commit()
            return CheckResult("unchanged", False)

        snapshot = Snapshot(
            monitor_id=monitor.id,
            content_hash=content_hash,
            normalized_text=normalized,
            etag=fetched.etag,
            last_modified=fetched.last_modified,
        )
        session.add(snapshot)
        await session.flush()
        monitor.last_hash = content_hash

        if latest is None:
            monitor.last_status = "baseline"
            await session.commit()
            return CheckResult("baseline", False)

        change = Change(
            monitor_id=monitor.id,
            snapshot_id=snapshot.id,
            diff=build_diff(latest.normalized_text, normalized),
        )
        session.add(change)
        await session.flush()
        monitor.last_status = "changed"
        await session.commit()
        return CheckResult("changed", True, change.id)
    except Exception as error:
        monitor.last_checked_at = now
        monitor.next_check_at = now + timedelta(minutes=monitor.interval_minutes)
        monitor.last_status = "error"
        monitor.last_error = str(error)[:500]
        await session.commit()
        return CheckResult("error", False)
