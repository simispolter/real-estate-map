from __future__ import annotations

import asyncio
import os
from pathlib import Path
import re

import asyncpg

from app.core.config import get_settings


def _database_url() -> str:
    return get_settings().database_url.replace("postgresql+asyncpg://", "postgresql://", 1)


def _migrations_dir() -> Path:
    configured = os.getenv("MIGRATIONS_DIR")
    if configured:
        return Path(configured)

    return Path(__file__).resolve().parents[4] / "infra" / "db" / "migrations"


_DOLLAR_TAG_PATTERN = re.compile(r"\$[A-Za-z0-9_]*\$")


def _split_sql_statements(sql: str) -> list[str]:
    statements: list[str] = []
    buffer: list[str] = []
    in_single_quote = False
    in_line_comment = False
    dollar_tag: str | None = None
    index = 0

    while index < len(sql):
        char = sql[index]
        next_char = sql[index + 1] if index + 1 < len(sql) else ""

        if in_line_comment:
            buffer.append(char)
            if char == "\n":
                in_line_comment = False
            index += 1
            continue

        if dollar_tag:
            if sql.startswith(dollar_tag, index):
                buffer.append(dollar_tag)
                index += len(dollar_tag)
                dollar_tag = None
                continue

            buffer.append(char)
            index += 1
            continue

        if not in_single_quote and char == "-" and next_char == "-":
            buffer.extend(["-", "-"])
            index += 2
            in_line_comment = True
            continue

        if char == "'":
            buffer.append(char)
            if in_single_quote and next_char == "'":
                buffer.append(next_char)
                index += 2
                continue
            in_single_quote = not in_single_quote
            index += 1
            continue

        if not in_single_quote and char == "$":
            match = _DOLLAR_TAG_PATTERN.match(sql, index)
            if match:
                dollar_tag = match.group(0)
                buffer.append(dollar_tag)
                index += len(dollar_tag)
                continue

        if not in_single_quote and char == ";":
            statement = "".join(buffer).strip()
            if statement:
                statements.append(statement)
            buffer = []
            index += 1
            continue

        buffer.append(char)
        index += 1

    tail = "".join(buffer).strip()
    if tail:
        statements.append(tail)

    return statements


async def apply_migrations() -> None:
    migrations_dir = _migrations_dir()
    if not migrations_dir.exists():
        raise FileNotFoundError(f"Migration directory not found: {migrations_dir}")

    connection: asyncpg.Connection | None = None
    last_error: Exception | None = None

    for _ in range(30):
        try:
            connection = await asyncpg.connect(_database_url())
            break
        except Exception as exc:  # pragma: no cover - retry path
            last_error = exc
            await asyncio.sleep(1)

    if connection is None:
        raise RuntimeError("Could not connect to the database to apply migrations.") from last_error

    try:
        await connection.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_migrations (
                filename TEXT PRIMARY KEY,
                applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
            """
        )

        applied = {
            row["filename"]
            for row in await connection.fetch("SELECT filename FROM schema_migrations")
        }
        project_master_exists = bool(
            await connection.fetchval("SELECT to_regclass('public.project_master')")
        )
        value_origin_exists = bool(
            await connection.fetchval(
                """
                SELECT 1
                FROM information_schema.columns
                WHERE table_name = 'field_provenance'
                  AND column_name = 'value_origin_type'
                """
            )
        )

        if project_master_exists and not applied:
            baseline = [
                "0001_extensions.sql",
                "0002_core_schema.sql",
                "0003_phase2_nullable_report_publish_date.sql",
            ]
            if value_origin_exists:
                baseline.append("0004_value_origin_type.sql")

            for filename in baseline:
                await connection.execute(
                    "INSERT INTO schema_migrations (filename) VALUES ($1) ON CONFLICT (filename) DO NOTHING",
                    filename,
                )

            applied = {
                row["filename"]
                for row in await connection.fetch("SELECT filename FROM schema_migrations")
            }

        for migration_file in sorted(migrations_dir.glob("*.sql")):
            if migration_file.name in applied:
                continue

            for statement in _split_sql_statements(migration_file.read_text(encoding="utf-8")):
                await connection.execute(statement)
            await connection.execute(
                "INSERT INTO schema_migrations (filename) VALUES ($1)",
                migration_file.name,
            )
    finally:
        await connection.close()


if __name__ == "__main__":
    asyncio.run(apply_migrations())
