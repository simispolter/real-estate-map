from collections.abc import AsyncIterator
import logging
import time

from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings

_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None
logger = logging.getLogger("app.performance.sql")


def _condense_sql(statement: str) -> str:
    return " ".join(statement.split())


def _register_sql_timing_listeners(engine: AsyncEngine, slow_query_threshold_ms: int) -> None:
    sync_engine = engine.sync_engine
    if getattr(sync_engine, "_performance_listeners_registered", False):
        return

    @event.listens_for(sync_engine, "before_cursor_execute")
    def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):  # type: ignore[no-untyped-def]
        conn.info.setdefault("query_start_time", []).append(time.perf_counter())

    @event.listens_for(sync_engine, "after_cursor_execute")
    def after_cursor_execute(conn, cursor, statement, parameters, context, executemany):  # type: ignore[no-untyped-def]
        start_times = conn.info.get("query_start_time")
        if not start_times:
            return

        duration_ms = (time.perf_counter() - start_times.pop()) * 1000
        if duration_ms < slow_query_threshold_ms:
            return

        logger.warning(
            "slow_query duration_ms=%.2f rows=%s sql=%s",
            duration_ms,
            cursor.rowcount,
            _condense_sql(statement)[:600],
        )

    @event.listens_for(sync_engine, "handle_error")
    def handle_error(exception_context):  # type: ignore[no-untyped-def]
        start_times = exception_context.connection.info.get("query_start_time")
        if start_times:
            start_times.pop()

    setattr(sync_engine, "_performance_listeners_registered", True)


def get_engine() -> AsyncEngine:
    global _engine
    if _engine is None:
        settings = get_settings()
        _engine = create_async_engine(settings.database_url, future=True, pool_pre_ping=True)
        _register_sql_timing_listeners(_engine, settings.slow_query_threshold_ms)
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(
            bind=get_engine(),
            expire_on_commit=False,
            autoflush=False,
        )
    return _session_factory


async def get_db_session() -> AsyncIterator[AsyncSession]:
    session_factory = get_session_factory()
    async with session_factory() as session:
        yield session
