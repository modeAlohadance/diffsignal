from __future__ import annotations

import asyncio

from sqlalchemy import or_, select

from .config import settings
from .db import SessionFactory
from .models import Monitor, utcnow
from .service import check_monitor


async def run_worker() -> None:
    while True:
        try:
            async with SessionFactory() as session:
                monitor_ids = list(
                    await session.scalars(
                        select(Monitor.id).where(
                            Monitor.enabled.is_(True),
                            or_(Monitor.next_check_at.is_(None), Monitor.next_check_at <= utcnow()),
                        )
                    )
                )
            for monitor_id in monitor_ids:
                async with SessionFactory() as session:
                    await check_monitor(session, monitor_id)
        except asyncio.CancelledError:
            raise
        except Exception:
            pass
        await asyncio.sleep(settings.check_loop_seconds)
