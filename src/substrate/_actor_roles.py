from __future__ import annotations

import psycopg
from psycopg.sql import SQL

from ._errors import ErrorCode, SubstrateError


def register_actor_role(
    conn: psycopg.Connection,
    actor_id: str,
    role: str,
) -> None:
    existing = conn.execute(
        SQL(
            "SELECT 1 FROM actor_roles WHERE actor_id = %s AND role = %s"
        ),
        [actor_id, role],
    ).fetchone()
    if existing is not None:
        return
    conn.execute(
        SQL(
            "INSERT INTO actor_roles (actor_id, role) VALUES (%s, %s)"
        ),
        [actor_id, role],
    )


def unregister_actor_role(
    conn: psycopg.Connection,
    actor_id: str,
    role: str,
) -> None:
    result = conn.execute(
        SQL(
            "DELETE FROM actor_roles WHERE actor_id = %s AND role = %s"
        ),
        [actor_id, role],
    )
    if result.rowcount == 0:
        raise SubstrateError(
            ErrorCode.ACTOR_ROLE_NOT_REGISTERED,
            f"Actor {actor_id!r} does not have role {role!r}",
        )


def list_actor_roles(
    conn: psycopg.Connection,
    actor_id: str | None = None,
) -> list[dict]:
    if actor_id is not None:
        rows = conn.execute(
            SQL(
                "SELECT actor_id, role, created_at FROM actor_roles "
                "WHERE actor_id = %s ORDER BY role"
            ),
            [actor_id],
        ).fetchall()
    else:
        rows = conn.execute(
            SQL(
                "SELECT actor_id, role, created_at FROM actor_roles "
                "ORDER BY actor_id, role"
            ),
        ).fetchall()
    return [dict(r) for r in rows]


def check_actor_role_authorized(
    conn: psycopg.Connection,
    actor_id: str,
    claimed_role: str,
) -> None:
    """Verify that *actor_id* is authorized for *claimed_role*.

    Per FR-24, enforcement only applies to actors with at least one
    registered role.  If the actor has **zero** entries in
    ``actor_roles``, the check passes silently — the actor is assumed
    to be outside the RBAC surface and is trusted based on the
    workflow's ``allowed_roles`` check alone.
    """
    rows = conn.execute(
        SQL(
            "SELECT role FROM actor_roles WHERE actor_id = %s"
        ),
        [actor_id],
    ).fetchall()
    if not rows:
        return
    allowed = {r["role"] for r in rows}
    if claimed_role not in allowed:
        raise SubstrateError(
            ErrorCode.ACTOR_ROLE_NOT_AUTHORIZED,
            f"Actor {actor_id!r} is not authorized for role {claimed_role!r}. "
            f"Allowed roles: {sorted(allowed)}",
            detail={
                "actor_id": actor_id,
                "claimed_role": claimed_role,
                "allowed_roles": sorted(allowed),
            },
        )
