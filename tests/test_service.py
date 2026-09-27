from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from diffsignal.db import Base
from diffsignal.fetcher import FetchResult
from diffsignal.models import Change, Monitor
from diffsignal.service import build_diff, check_monitor


def test_diff_contains_added_and_removed_lines():
    result = build_diff("price: 10\nstock: yes\n", "price: 12\nstock: yes\n")
    assert "-price: 10" in result
    assert "+price: 12" in result


def test_diff_is_truncated_at_limit():
    result = build_diff("a\n" * 100, "b\n" * 100, limit=40)
    assert len(result) < 100
    assert "diff truncated" in result


async def test_check_monitor_creates_baseline_then_change(monkeypatch):
    results = iter(
        [
            FetchResult("https://public.test", "price: 10", "text/plain", None, None),
            FetchResult("https://public.test", "price: 12", "text/plain", None, None),
        ]
    )

    async def fake_fetch(*args, **kwargs):
        return next(results)

    monkeypatch.setattr("diffsignal.service.fetch_url", fake_fetch)
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    async with sessions() as session:
        monitor = Monitor(name="Price", url="https://public.test", interval_minutes=60)
        session.add(monitor)
        await session.commit()
        baseline = await check_monitor(session, monitor.id)
        changed = await check_monitor(session, monitor.id)
        stored_changes = list(await session.scalars(select(Change)))

    await engine.dispose()
    assert baseline.status == "baseline"
    assert changed.status == "changed"
    assert changed.changed is True
    assert len(stored_changes) == 1
    assert "-price: 10" in stored_changes[0].diff
    assert "+price: 12" in stored_changes[0].diff
