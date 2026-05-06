from __future__ import annotations

import importlib.resources
from pathlib import Path

import structlog

from ._connection import ConnectionManager

log = structlog.get_logger()


def _migrations_dir() -> Path:
    pkg = importlib.resources.files("substrate")
    candidate = Path(str(pkg)).joinpath("migrations")
    if candidate.is_dir():
        return candidate
    fallback = Path(str(pkg)).parent.parent / "migrations"
    if fallback.is_dir():
        return fallback
    raise FileNotFoundError("Cannot locate migrations/ directory")


def discover_migrations() -> list[tuple[int, Path]]:
    migrations_dir = _migrations_dir()
    result = []
    for p in sorted(migrations_dir.glob("*.sql")):
        stem = p.stem
        try:
            version = int(stem.split("_", 1)[0])
        except (ValueError, IndexError):
            continue
        result.append((version, p))
    result.sort(key=lambda x: x[0])
    return result


def applied_versions(mgr: ConnectionManager) -> set[int]:
    with mgr.transaction() as conn:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS _substrate_migrations "
            "(version INTEGER PRIMARY KEY, applied_at TIMESTAMPTZ NOT NULL DEFAULT now())"
        )
        rows = conn.execute(
            "SELECT version FROM _substrate_migrations ORDER BY version"
        ).fetchall()
        return {row["version"] for row in rows}


def run_migrations(mgr: ConnectionManager) -> list[int]:
    all_migrations = discover_migrations()
    applied = applied_versions(mgr)
    pending = [(v, p) for v, p in all_migrations if v not in applied]

    if not pending:
        log.info("migrations.up_to_date", project=mgr.project)
        return []

    applied_now = []
    for version, path in pending:
        sql = path.read_text()
        with mgr.transaction() as conn:
            conn.execute(sql)
            conn.execute(
                "INSERT INTO _substrate_migrations (version) VALUES (%s)",
                [version],
            )
        applied_now.append(version)
        log.info(
            "migrations.applied",
            project=mgr.project,
            version=version,
            path=path.name,
        )

    return applied_now


def check_migrations_current(mgr: ConnectionManager) -> None:
    all_migrations = discover_migrations()
    if not all_migrations:
        return
    max_available = max(v for v, _ in all_migrations)
    applied = applied_versions(mgr)
    if max_available not in applied:
        from ._errors import ErrorCode, SubstrateError

        raise SubstrateError(
            ErrorCode.MIGRATION_REQUIRED,
            f"Migrations pending: schema {mgr.schema!r} has applied "
            f"{sorted(applied)}, latest available is {max_available}. "
            "Run substrate migrations before starting.",
        )
