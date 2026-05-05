from __future__ import annotations

import hashlib
import hmac
from uuid import UUID

from ._jcs import canonicalize


def build_signing_envelope(
    event_id: UUID,
    work_item_id: UUID,
    actor_id: str,
    transition: str | None,
    payload: dict | None,
) -> bytes:
    envelope = {
        "event_id": str(event_id),
        "work_item_id": str(work_item_id),
        "actor_id": actor_id,
        "transition": transition,
        "payload": payload,
    }
    return canonicalize(envelope)


def compute_hmac(envelope_bytes: bytes, key: bytes) -> bytes:
    return hmac.new(key, envelope_bytes, hashlib.sha256).digest()


def compute_canonical_hash(envelope_bytes: bytes) -> bytes:
    return hashlib.sha256(envelope_bytes).digest()


def verify_hmac(envelope_bytes: bytes, signature: bytes, key: bytes) -> bool:
    return hmac.compare_digest(
        hmac.new(key, envelope_bytes, hashlib.sha256).digest(), signature
    )


def sign_event(
    event_id: UUID,
    work_item_id: UUID,
    actor_id: str,
    transition: str | None,
    payload: dict | None,
    key: bytes,
) -> tuple[bytes, bytes, bytes]:
    envelope = build_signing_envelope(event_id, work_item_id, actor_id, transition, payload)
    signature = compute_hmac(envelope, key)
    canonical_hash = compute_canonical_hash(envelope)
    return (signature, canonical_hash, envelope)


def verify_event(
    event_id: UUID,
    work_item_id: UUID,
    actor_id: str,
    transition: str | None,
    payload: dict | None,
    signature: bytes,
    canonical_hash: bytes,
    key: bytes,
    stored_envelope: bytes | None = None,
) -> bool:
    if stored_envelope is not None:
        envelope = stored_envelope
    else:
        envelope = build_signing_envelope(event_id, work_item_id, actor_id, transition, payload)
    if not verify_hmac(envelope, signature, key):
        return False
    if hashlib.sha256(envelope).digest() != canonical_hash:
        return False
    return True
