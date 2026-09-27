from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager, suppress
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Response, status
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .config import settings
from .db import get_session, init_db
from .models import Change, Monitor
from .schemas import ChangeRead, CheckRead, MonitorCreate, MonitorRead
from .security import UnsafeUrlError, ensure_public_url
from .service import check_monitor
from .worker import run_worker


@asynccontextmanager
async def lifespan(_: FastAPI):
    await init_db()
    task = None if settings.disable_worker else asyncio.create_task(run_worker())
    try:
        yield
    finally:
        if task:
            task.cancel()
            with suppress(asyncio.CancelledError):
                await task


app = FastAPI(title="DiffSignal", version="0.1.0", lifespan=lifespan)
static_dir = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=static_dir), name="static")


@app.get("/", include_in_schema=False)
async def dashboard() -> FileResponse:
    return FileResponse(static_dir / "index.html")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/monitors", response_model=MonitorRead, status_code=status.HTTP_201_CREATED)
async def create_monitor(payload: MonitorCreate, session: AsyncSession = Depends(get_session)) -> Monitor:
    try:
        await ensure_public_url(payload.url)
    except UnsafeUrlError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    monitor = Monitor(**payload.model_dump())
    session.add(monitor)
    await session.commit()
    await session.refresh(monitor)
    return monitor


@app.get("/api/monitors", response_model=list[MonitorRead])
async def list_monitors(session: AsyncSession = Depends(get_session)) -> list[Monitor]:
    return list(await session.scalars(select(Monitor).order_by(Monitor.id.desc())))


@app.get("/api/monitors/{monitor_id}", response_model=MonitorRead)
async def get_monitor(monitor_id: int, session: AsyncSession = Depends(get_session)) -> Monitor:
    monitor = await session.get(Monitor, monitor_id)
    if monitor is None:
        raise HTTPException(status_code=404, detail="monitor not found")
    return monitor


@app.post("/api/monitors/{monitor_id}/check", response_model=CheckRead)
async def run_check(monitor_id: int, session: AsyncSession = Depends(get_session)) -> CheckRead:
    if await session.get(Monitor, monitor_id) is None:
        raise HTTPException(status_code=404, detail="monitor not found")
    result = await check_monitor(session, monitor_id)
    return CheckRead(status=result.status, changed=result.changed, change_id=result.change_id)


@app.get("/api/monitors/{monitor_id}/changes", response_model=list[ChangeRead])
async def list_changes(monitor_id: int, session: AsyncSession = Depends(get_session)) -> list[Change]:
    if await session.get(Monitor, monitor_id) is None:
        raise HTTPException(status_code=404, detail="monitor not found")
    return list(
        await session.scalars(
            select(Change).where(Change.monitor_id == monitor_id).order_by(Change.id.desc()).limit(100)
        )
    )


@app.delete("/api/monitors/{monitor_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_monitor(monitor_id: int, session: AsyncSession = Depends(get_session)) -> Response:
    monitor = await session.get(Monitor, monitor_id)
    if monitor is None:
        raise HTTPException(status_code=404, detail="monitor not found")
    await session.delete(monitor)
    await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
