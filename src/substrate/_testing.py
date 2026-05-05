from __future__ import annotations

from collections.abc import Generator
from contextlib import contextmanager

import psycopg


@contextmanager
def raw_transaction(substrate) -> Generator[psycopg.Connection, None, None]:
    with substrate._mgr.transaction() as conn:
        yield conn


def drop_project_schema(dsn: str, project: str) -> None:
    from psycopg.sql import SQL, Identifier

    conn = psycopg.connect(dsn, autocommit=True)
    conn.execute(SQL("DROP SCHEMA IF EXISTS {} CASCADE").format(Identifier(project)))
    conn.close()
