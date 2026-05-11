from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Literal

from ._errors import ErrorCode, SubstrateError
from ._types import Event

_VALID_ACTOR_KINDS = frozenset({"agent", "human", "system"})


def validate_actor_kind(actor_kind: str) -> None:
    if actor_kind not in _VALID_ACTOR_KINDS:
        raise SubstrateError(
            ErrorCode.INVALID_ACTOR_KIND,
            f"Invalid actor_kind {actor_kind!r}. Must be one of {sorted(_VALID_ACTOR_KINDS)}",
        )


def validate_ttl(ttl_seconds: int) -> None:
    if ttl_seconds <= 0:
        raise SubstrateError(
            ErrorCode.INVALID_ARGUMENT,
            "ttl_seconds must be positive",
        )


def validate_not_before(not_before: datetime | None, now: datetime) -> None:
    if not_before is not None and not_before > now:
        raise SubstrateError(
            ErrorCode.NOT_BEFORE_FUTURE,
            f"Work item not_before is {not_before.isoformat()}, cannot claim yet",
        )


def resolve_transition(
    transitions: list[dict],
    current_state: str,
    transition_name: str,
    workflow_name: str,
    workflow_version: int,
) -> dict:
    for t in transitions:
        if t["name"] == transition_name and t["from_state"] == current_state:
            return t
    raise SubstrateError(
        ErrorCode.INVALID_TRANSITION,
        f"Transition {transition_name!r} not valid from state "
        f"{current_state!r} in {workflow_name!r} v{workflow_version}",
    )


def check_role_gating(
    allowed_roles: list[str],
    actor_metadata: dict | None,
    transition_name: str,
) -> str | None:
    if not allowed_roles:
        return None
    role = (actor_metadata or {}).get("role")
    if role not in allowed_roles:
        raise SubstrateError(
            ErrorCode.ROLE_NOT_PERMITTED,
            f"Role {role!r} not permitted for transition {transition_name!r}",
        )
    return role


def check_actor_role_authorized(
    registered_roles: set[str],
    actor_id: str,
    claimed_role: str,
) -> None:
    if not registered_roles:
        return
    if claimed_role not in registered_roles:
        raise SubstrateError(
            ErrorCode.ACTOR_ROLE_NOT_AUTHORIZED,
            f"Actor {actor_id!r} is not authorized for role {claimed_role!r}. "
            f"Allowed roles: {sorted(registered_roles)}",
            detail={
                "actor_id": actor_id,
                "claimed_role": claimed_role,
                "allowed_roles": sorted(registered_roles),
            },
        )


def check_append_blocked(
    transitions: list[dict],
    transition: str | None,
    workflow_name: str,
) -> None:
    if transition is None:
        return
    for t in transitions:
        if t["name"] == transition:
            raise SubstrateError(
                ErrorCode.TRANSITION_VIA_APPEND_BLOCKED,
                f"Transition {transition!r} is defined in workflow "
                f"{workflow_name!r}. Use Substrate.transition() instead.",
            )


def check_idempotency(
    existing_event: Event | None,
    actor_id: str,
    transition: str | None,
) -> Event | None:
    if existing_event is None:
        return None
    if actor_id is not None and existing_event.actor_id != actor_id:
        raise SubstrateError(
            ErrorCode.IDEMPOTENCY_COLLISION_WITH_DIFFERENT_PAYLOAD,
            f"event_id {existing_event.event_id} already used by actor {existing_event.actor_id!r}"
            + (f", not {actor_id!r}" if actor_id else ""),
        )
    if transition is not None and existing_event.transition != transition:
        raise SubstrateError(
            ErrorCode.IDEMPOTENCY_COLLISION_WITH_DIFFERENT_PAYLOAD,
            f"event_id {existing_event.event_id} already used with transition "
            f"{existing_event.transition!r}, not {transition!r}",
        )
    return existing_event


def check_expected_seq(
    current_next_seq: int,
    expected_event_seq: int | None,
) -> None:
    if expected_event_seq is not None and current_next_seq != expected_event_seq:
        raise SubstrateError(
            ErrorCode.CONCURRENT_MODIFICATION,
            f"Expected event_seq {expected_event_seq}, but current next is {current_next_seq}",
        )


def validate_link_type(
    link_types: list[dict],
    from_type: str,
    to_type: str,
    link_type: str,
) -> None:
    for lt in link_types:
        if (
            lt["name"] == link_type
            and lt["source_type"] == from_type
            and lt["target_type"] == to_type
        ):
            return
    raise SubstrateError(
        ErrorCode.LINK_TYPE_NOT_ALLOWED,
        f"Link type {link_type!r} not allowed between {from_type!r} and {to_type!r}",
    )


def should_escalate(
    attempt_threshold: int | None,
    has_escalated: bool,
    attempt_number: int,
) -> bool:
    if attempt_threshold is None or attempt_number < attempt_threshold:
        return False
    return not has_escalated


def validate_read_events_filters(
    before_seq: int | None,
    work_item_id: uuid.UUID | None,
    start: datetime | None,
    end: datetime | None,
) -> None:
    if before_seq is not None and work_item_id is None:
        raise SubstrateError(
            ErrorCode.INVALID_FILTER,
            "before_seq requires work_item_id",
        )
    if (start is None) != (end is None):
        raise SubstrateError(
            ErrorCode.INVALID_FILTER,
            "start and end must be provided together",
        )


@dataclass(frozen=True)
class ClaimAcquireResult:
    action: Literal["extend", "acquire", "steal"]
    acquired_at: datetime
    expires_at: datetime
    attempt_number: int
    prior_actor_id: str | None
    event_transition: Literal["claim_acquired", "claim_stolen"] | None
    event_payload: dict | None


def resolve_claim_acquire(
    wi_not_before: datetime | None,
    claim_actor_id: str | None,
    claim_expires_at: datetime | None,
    claim_acquired_at: datetime | None,
    claim_attempt_number: int | None,
    wi_attempt_number: int,
    actor_id: str,
    ttl_seconds: int,
    now: datetime,
) -> ClaimAcquireResult:
    validate_not_before(wi_not_before, now)

    has_active_claim = (
        claim_actor_id is not None
        and claim_expires_at is not None
        and claim_expires_at >= now
    )

    if has_active_claim:
        if claim_actor_id == actor_id:
            new_expires = now + timedelta(seconds=ttl_seconds)
            return ClaimAcquireResult(
                action="extend",
                acquired_at=claim_acquired_at,
                expires_at=new_expires,
                attempt_number=claim_attempt_number,
                prior_actor_id=None,
                event_transition=None,
                event_payload=None,
            )
        raise SubstrateError(
            ErrorCode.CLAIM_CONTESTED,
            f"Work item is already claimed by {claim_actor_id}",
        )

    has_expired_claim = claim_actor_id is not None
    prior_actor_id = claim_actor_id if has_expired_claim else None
    attempt_number = wi_attempt_number + 1

    acquired_at = now
    expires_at = acquired_at + timedelta(seconds=ttl_seconds)

    if has_expired_claim:
        return ClaimAcquireResult(
            action="steal",
            acquired_at=acquired_at,
            expires_at=expires_at,
            attempt_number=attempt_number,
            prior_actor_id=prior_actor_id,
            event_transition="claim_stolen",
            event_payload={
                "prior_actor_id": prior_actor_id,
                "new_actor_id": actor_id,
                "attempt_number": attempt_number,
            },
        )

    return ClaimAcquireResult(
        action="acquire",
        acquired_at=acquired_at,
        expires_at=expires_at,
        attempt_number=attempt_number,
        prior_actor_id=None,
        event_transition="claim_acquired",
        event_payload={
            "actor_id": actor_id,
            "ttl_seconds": ttl_seconds,
            "attempt_number": attempt_number,
        },
    )


@dataclass(frozen=True)
class HeartbeatResult:
    new_expires_at: datetime
    acquired_at: datetime
    attempt_number: int


def resolve_heartbeat(
    claim_state: dict | None,
    actor_id: str,
    ttl_seconds: int,
    expected_attempt_number: int | None,
    work_item_id: uuid.UUID,
    now: datetime,
) -> HeartbeatResult:
    validate_ttl(ttl_seconds)

    if claim_state is None:
        raise SubstrateError(
            ErrorCode.CLAIM_NOT_FOUND,
            f"No claim found for work item {work_item_id}",
        )

    if claim_state["actor_id"] != actor_id:
        raise SubstrateError(
            ErrorCode.CLAIM_LOST,
            f"Claim on {work_item_id} is now held by {claim_state['actor_id']}, not {actor_id}",
        )

    if (
        expected_attempt_number is not None
        and claim_state["attempt_number"] != expected_attempt_number
    ):
        raise SubstrateError(
            ErrorCode.CLAIM_LOST,
            f"Claim attempt_number is {claim_state['attempt_number']}, "
            f"expected {expected_attempt_number}",
        )

    new_expires = now + timedelta(seconds=ttl_seconds)
    return HeartbeatResult(
        new_expires_at=new_expires,
        acquired_at=claim_state["acquired_at"],
        attempt_number=claim_state["attempt_number"],
    )


def validate_release(
    claim_state: dict | None,
    actor_id: str,
    work_item_id: uuid.UUID,
) -> None:
    if claim_state is None:
        raise SubstrateError(
            ErrorCode.CLAIM_NOT_FOUND,
            f"No claim found for work item {work_item_id}",
        )
    if claim_state["actor_id"] != actor_id:
        raise SubstrateError(
            ErrorCode.CLAIM_LOST,
            f"Claim on {work_item_id} is held by {claim_state['actor_id']}, not {actor_id}",
        )


def validate_work_item_exists(
    work_item: object,
    work_item_id: uuid.UUID,
) -> None:
    if work_item is None:
        raise SubstrateError(
            ErrorCode.WORK_ITEM_NOT_FOUND,
            f"Work item {work_item_id} not found",
        )
