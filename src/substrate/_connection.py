from __future__ import annotations

import re
from collections.abc import Generator
from contextlib import contextmanager

import psycopg
from psycopg.rows import dict_row
from psycopg.sql import SQL, Identifier
from psycopg_pool import ConnectionPool

from ._errors import ErrorCode, SubstrateError

_SCHEMA_RE = re.compile(r"^[a-z_][a-z0-9_]{0,62}$")


def validate_project_name(name: str) -> str:
    if not _SCHEMA_RE.match(name):
        raise ValueError(
            f"Invalid project name {name!r}: must be 1-63 chars, lowercase "
            "alphanumeric/underscore, start with letter or underscore"
        )
    return name


def _configure_session(conn: psycopg.Connection) -> None:
    conn.execute("SET synchronous_commit = on")
    conn.commit()


class ConnectionManager:
    def __init__(
        self,
        dsn: str,
        project: str,
        pool_min: int = 1,
        pool_max: int = 10,
    ) -> None:
        self._schema = validate_project_name(project)
        self._project = project
        self._pool = ConnectionPool(
            dsn,
            min_size=pool_min,
            max_size=pool_max,
            open=False,
            configure=_configure_session,
            kwargs={"row_factory": dict_row},
        )

    @property
    def project(self) -> str:
        return self._project

    @property
    def schema(self) -> str:
        return self._schema

    def open(self) -> None:
        self._pool.open()

    def close(self) -> None:
        self._pool.close()

    @contextmanager
    def connect(self) -> Generator[psycopg.Connection, None, None]:
        with self._pool.connection() as conn:
            yield conn

    @contextmanager
    def transaction(self) -> Generator[psycopg.Connection, None, None]:
        with self._pool.connection() as conn:
            with conn.transaction():
                conn.execute(
                    SQL("SET LOCAL search_path TO {}").format(
                        Identifier(self._schema)
                    )
                )
                yield conn

    def schema_exists(self) -> bool:
        with self._pool.connection() as conn:
            row = conn.execute(
                "SELECT 1 FROM information_schema.schemata WHERE schema_name = %s",
                [self._schema],
            ).fetchone()
            return row is not None

    def create_schema(self) -> None:
        with self._pool.connection() as conn:
            conn.execute(
                SQL("CREATE SCHEMA IF NOT EXISTS {}").format(
                    Identifier(self._schema)
                )
            )

    def ensure_schema(self) -> None:
        if not self.schema_exists():
            raise SubstrateError(
                ErrorCode.DB_NOT_FOUND,
                f"Project schema {self._schema!r} does not exist. "
                "Use Substrate.create_project() to initialize it.",
            )
