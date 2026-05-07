from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import psycopg
from psycopg.sql import SQL

from ._errors import ErrorCode, SubstrateError
from ._types import Claim


def _row_to_claim(row: dict) -> Claim:
    return Claim(
        work_item_id=row["work_item_id"],
        actor_id=row["actor_id"],
        acquired_at=row["acquired_at"],
        expires_at=row["expires_at"],
        attempt_number=row["attempt_number"],
    )


def acquire_claim(
    conn: psycopg.Connection,
    work_item_id: uuid.UUID,
    actor_id: str,
    ttl_seconds: int,
    key_set,
    event_id: uuid.UUID | None = None,
) -> tuple[Claim, bool, bool]:
    from ._events import append_event, lock_work_item

    wi = lock_work_item(conn, work_item_id)
    if wi is None:
        raise SubstrateError(
            ErrorCode.WORK_ITEM_NOT_FOUND,
            f"Work item {work_item_id} not found",
        )

    now = datetime.now(UTC)

    if wi["not_before"] is not None and wi["not_before"] > now:
        raise SubstrateError(
            ErrorCode.NOT_BEFORE_FUTURE,
            f"Work item not_before is {wi['not_before'].isoformat()}, cannot claim yet",
        )

    existing_claim = conn.execute(
        SQL("SELECT * FROM claims WHERE work_item_id = %s"),
        [work_item_id],
    ).fetchone()

    if existing_claim is not None and existing_claim["expires_at"] >= now:
        if existing_claim["actor_id"] == actor_id:
            new_expires = now + timedelta(seconds=ttl_seconds)
            conn.execute(
                SQL("UPDATE claims SET expires_at = %s WHERE work_item_id = %s"),
                [new_expires, work_item_id],
            )
            conn.execute(
                SQL(
                    "UPDATE work_items_current SET claim_expires_at = %s "
                    "WHERE work_item_id = %s"
                ),
                [new_expires, work_item_id],
            )
            return Claim(
                work_item_id=work_item_id,
                actor_id=actor_id,
                acquired_at=existing_claim["acquired_at"],
                expires_at=new_expires,
                attempt_number=existing_claim["attempt_number"],
            ), False, False
        raise SubstrateError(
            ErrorCode.CLAIM_CONTESTED,
            f"Work item {work_item_id} is already claimed by {existing_claim['actor_id']}",
        )

    prior_actor_id = None
    attempt_number = 1
    if existing_claim is not None:
        attempt_number = existing_claim["attempt_number"] + 1
        prior_actor_id = existing_claim["actor_id"]

    acquired_at = now
    expires_at = acquired_at + timedelta(seconds=ttl_seconds)

    if existing_claim is not None:
        conn.execute(
            SQL(
                "UPDATE claims SET actor_id = %s, acquired_at = %s, "
                "expires_at = %s, attempt_number = %s "
                "WHERE work_item_id = %s"
            ),
            [actor_id, acquired_at, expires_at, attempt_number, work_item_id],
        )
    else:
        conn.execute(
            SQL(
                "INSERT INTO claims "
                "(work_item_id, actor_id, acquired_at, expires_at, attempt_number) "
                "VALUES (%s, %s, %s, %s, %s)"
            ),
            [work_item_id, actor_id, acquired_at, expires_at, attempt_number],
        )

    conn.execute(
        SQL(
            "UPDATE work_items_current SET claimed_by = %s, claim_expires_at = %s "
            "WHERE work_item_id = %s"
        ),
        [actor_id, expires_at, work_item_id],
    )

    event_id = event_id or uuid.uuid4()
    if prior_actor_id is not None:
        append_event(
            conn=conn,
            work_item_id=work_item_id,
            actor_id=actor_id,
            actor_kind="system",
            actor_metadata=None,
            key_set=key_set,
            workflow_name=wi["workflow_name"],
            workflow_version=wi["workflow_version"],
            transition="claim_stolen",
            payload={
                "prior_actor_id": prior_actor_id,
                "new_actor_id": actor_id,
                "attempt_number": attempt_number,
            },
            event_id=event_id,
            _prelocked_wi=wi,
        )
    else:
        append_event(
            conn=conn,
            work_item_id=work_item_id,
            actor_id=actor_id,
            actor_kind="system",
            actor_metadata=None,
            key_set=key_set,
            workflow_name=wi["workflow_name"],
            workflow_version=wi["workflow_version"],
            transition="claim_acquired",
            payload={
                "actor_id": actor_id,
                "ttl_seconds": ttl_seconds,
                "attempt_number": attempt_number,
            },
            event_id=event_id,
            _prelocked_wi=wi,
        )

    stolen = prior_actor_id is not None
    escalated = _check_escalation(conn, wi, attempt_number, key_set)

    claim = Claim(
        work_item_id=work_item_id,
        actor_id=actor_id,
        acquired_at=acquired_at,
        expires_at=expires_at,
        attempt_number=attempt_number,
    )
    return claim, escalated, stolen


def _check_escalation(
    conn: psycopg.Connection,
    wi: dict,
    attempt_number: int,
    key_set,
) -> bool:
    from ._events import append_event

    wf_row = conn.execute(
        SQL(
            "SELECT definition FROM workflow_registry "
            "WHERE workflow_name = %s AND version = %s"
        ),
        [wi["workflow_name"], wi["workflow_version"]],
    ).fetchone()
    if wf_row is None:
        return False

    threshold = wf_row["definition"].get("attempt_threshold")
    if threshold is None or attempt_number < threshold:
        return False

    existing = conn.execute(
        SQL("SELECT 1 FROM events WHERE work_item_id = %s AND transition = 'escalated'"),
        [wi["work_item_id"]],
    ).fetchone()
    if existing is not None:
        return False

    conn.execute(
        SQL("UPDATE work_items_current SET needs_review = true WHERE work_item_id = %s"),
        [wi["work_item_id"]],
    )

    append_event(
        conn=conn,
        work_item_id=wi["work_item_id"],
        actor_id="system",
        actor_kind="system",
        actor_metadata=None,
        key_set=key_set,
        workflow_name=wi["workflow_name"],
        workflow_version=wi["workflow_version"],
        transition="escalated",
        payload={"attempt_number": attempt_number, "threshold": threshold},
        event_id=uuid.uuid4(),
    )

    return True


def heartbeat_claim(
    conn: psycopg.Connection,
    work_item_id: uuid.UUID,
    actor_id: str,
    ttl_seconds: int,
    expected_attempt_number: int | None = None,
) -> Claim:
    from ._events import lock_work_item

    lock_work_item(conn, work_item_id)

    claim_row = conn.execute(
        SQL("SELECT * FROM claims WHERE work_item_id = %s"),
        [work_item_id],
    ).fetchone()

    if claim_row is None:
        raise SubstrateError(
            ErrorCode.CLAIM_NOT_FOUND,
            f"No claim found for work item {work_item_id}",
        )

    if claim_row["actor_id"] != actor_id:
        raise SubstrateError(
            ErrorCode.CLAIM_LOST,
            f"Claim on {work_item_id} is now held by {claim_row['actor_id']}, not {actor_id}",
        )

    if (
        expected_attempt_number is not None
        and claim_row["attempt_number"] != expected_attempt_number
    ):
        raise SubstrateError(
            ErrorCode.CLAIM_LOST,
            f"Claim attempt_number is {claim_row['attempt_number']}, "
            f"expected {expected_attempt_number}",
        )

    new_expires = datetime.now(UTC) + timedelta(seconds=ttl_seconds)
    conn.execute(
        SQL("UPDATE claims SET expires_at = %s WHERE work_item_id = %s"),
        [new_expires, work_item_id],
    )
    conn.execute(
        SQL("UPDATE work_items_current SET claim_expires_at = %s WHERE work_item_id = %s"),
        [new_expires, work_item_id],
    )

    return Claim(
        work_item_id=work_item_id,
        actor_id=actor_id,
        acquired_at=claim_row["acquired_at"],
        expires_at=new_expires,
        attempt_number=claim_row["attempt_number"],
    )


def release_claim(
    conn: psycopg.Connection,
    work_item_id: uuid.UUID,
    actor_id: str,
    key_set,
    event_id: uuid.UUID | None = None,
) -> None:
    from ._events import append_event, lock_work_item

    wi = lock_work_item(conn, work_item_id)

    claim_row = conn.execute(
        SQL("SELECT * FROM claims WHERE work_item_id = %s"),
        [work_item_id],
    ).fetchone()

    if claim_row is None:
        raise SubstrateError(
            ErrorCode.CLAIM_NOT_FOUND,
            f"No claim found for work item {work_item_id}",
        )

    if claim_row["actor_id"] != actor_id:
        raise SubstrateError(
            ErrorCode.CLAIM_LOST,
            f"Claim on {work_item_id} is held by {claim_row['actor_id']}, not {actor_id}",
        )

    conn.execute(
        SQL("DELETE FROM claims WHERE work_item_id = %s"),
        [work_item_id],
    )
    conn.execute(
        SQL(
            "UPDATE work_items_current SET claimed_by = NULL, claim_expires_at = NULL "
            "WHERE work_item_id = %s"
        ),
        [work_item_id],
    )

    if wi is not None:
        append_event(
            conn=conn,
            work_item_id=work_item_id,
            actor_id=actor_id,
            actor_kind="system",
            actor_metadata=None,
            key_set=key_set,
            workflow_name=wi["workflow_name"],
            workflow_version=wi["workflow_version"],
            transition="claim_released",
            payload={"actor_id": actor_id},
            event_id=event_id or uuid.uuid4(),
            _prelocked_wi=wi,
        )


def sweep_expired_claims(conn: psycopg.Connection, key_set) -> int:
    from ._events import append_event, lock_work_item

    now = datetime.now(UTC)
    result = conn.execute(
        SQL("DELETE FROM claims WHERE expires_at < %s RETURNING work_item_id, actor_id"),
        [now],
    ).fetchall()

    for row in result:
        wi_id = row["work_item_id"]
        prior_actor_id = row["actor_id"]

        wi = lock_work_item(conn, wi_id)

        conn.execute(
            SQL(
                "UPDATE work_items_current SET claimed_by = NULL, claim_expires_at = NULL "
                "WHERE work_item_id = %s AND claimed_by IS NOT NULL"
            ),
            [wi_id],
        )

        if wi is not None:
            append_event(
                conn=conn,
                work_item_id=wi_id,
                actor_id=prior_actor_id or "system",
                actor_kind="system",
                actor_metadata=None,
                key_set=key_set,
                workflow_name=wi["workflow_name"],
                workflow_version=wi["workflow_version"],
                transition="claim_expired",
                payload={
                    "actor_id": prior_actor_id,
                    "expired_at": now.isoformat(),
                },
                event_id=uuid.uuid4(),
                _prelocked_wi=wi,
            )

    return len(result)
