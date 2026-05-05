from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Generic, TypeVar

T = TypeVar("T")


class ActorKind(Enum):
    AGENT = "AGENT"
    HUMAN = "HUMAN"
    SYSTEM = "SYSTEM"


@dataclass(frozen=True)
class ActorIdentity:
    actor_id: str
    actor_kind: ActorKind
    actor_metadata: dict | None = None
    key_id: str | None = None

    def to_dict(self) -> dict:
        return {
            "actor_id": self.actor_id,
            "actor_kind": self.actor_kind.value,
            "actor_metadata": self.actor_metadata,
            "key_id": self.key_id,
        }

    @classmethod
    def from_dict(cls, data: dict) -> ActorIdentity:
        return cls(
            actor_id=data["actor_id"],
            actor_kind=ActorKind(data["actor_kind"]),
            actor_metadata=data.get("actor_metadata"),
            key_id=data.get("key_id"),
        )


@dataclass(frozen=True)
class Event:
    event_id: uuid.UUID
    work_item_id: uuid.UUID
    event_seq: int
    actor_id: str
    actor_kind: str
    actor_metadata: dict | None
    key_id: str
    workflow_name: str
    workflow_version: int
    timestamp: datetime
    transition: str | None
    payload: dict | None
    payload_canonical_hash: bytes
    signature: bytes
    canonical_envelope: bytes | None = None

    def to_dict(self) -> dict:
        d = {
            "event_id": str(self.event_id),
            "work_item_id": str(self.work_item_id),
            "event_seq": self.event_seq,
            "actor_id": self.actor_id,
            "actor_kind": self.actor_kind,
            "actor_metadata": self.actor_metadata,
            "key_id": self.key_id,
            "workflow_name": self.workflow_name,
            "workflow_version": self.workflow_version,
            "timestamp": self.timestamp.isoformat(),
            "transition": self.transition,
            "payload": self.payload,
            "payload_canonical_hash": self.payload_canonical_hash.hex(),
            "signature": self.signature.hex(),
        }
        if self.canonical_envelope is not None:
            d["canonical_envelope"] = self.canonical_envelope.hex()
        return d

    @classmethod
    def from_dict(cls, data: dict) -> Event:
        return cls(
            event_id=uuid.UUID(data["event_id"]),
            work_item_id=uuid.UUID(data["work_item_id"]),
            event_seq=data["event_seq"],
            actor_id=data["actor_id"],
            actor_kind=data["actor_kind"],
            actor_metadata=data.get("actor_metadata"),
            key_id=data["key_id"],
            workflow_name=data["workflow_name"],
            workflow_version=data["workflow_version"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            transition=data.get("transition"),
            payload=data.get("payload"),
            payload_canonical_hash=bytes.fromhex(data["payload_canonical_hash"]),
            signature=bytes.fromhex(data["signature"]),
            canonical_envelope=(
                bytes.fromhex(data["canonical_envelope"])
                if data.get("canonical_envelope")
                else None
            ),
        )


@dataclass(frozen=True)
class WorkItem:
    work_item_id: uuid.UUID
    workflow_name: str
    workflow_version: int
    work_item_type: str
    current_state: str
    custom_fields: dict
    needs_review: bool
    not_before: datetime | None
    last_event_seq: int
    last_event_at: datetime
    next_event_seq: int
    claimed_by: str | None
    claim_expires_at: datetime | None

    def to_dict(self) -> dict:
        return {
            "work_item_id": str(self.work_item_id),
            "workflow_name": self.workflow_name,
            "workflow_version": self.workflow_version,
            "work_item_type": self.work_item_type,
            "current_state": self.current_state,
            "custom_fields": self.custom_fields,
            "needs_review": self.needs_review,
            "not_before": self.not_before.isoformat() if self.not_before else None,
            "last_event_seq": self.last_event_seq,
            "last_event_at": self.last_event_at.isoformat(),
            "next_event_seq": self.next_event_seq,
            "claimed_by": self.claimed_by,
            "claim_expires_at": (
                self.claim_expires_at.isoformat()
                if self.claim_expires_at
                else None
            ),
        }

    @classmethod
    def from_dict(cls, data: dict) -> WorkItem:
        return cls(
            work_item_id=uuid.UUID(data["work_item_id"]),
            workflow_name=data["workflow_name"],
            workflow_version=data["workflow_version"],
            work_item_type=data["work_item_type"],
            current_state=data["current_state"],
            custom_fields=data["custom_fields"],
            needs_review=data["needs_review"],
            not_before=(
                datetime.fromisoformat(data["not_before"])
                if data.get("not_before")
                else None
            ),
            last_event_seq=data["last_event_seq"],
            last_event_at=datetime.fromisoformat(data["last_event_at"]),
            next_event_seq=data["next_event_seq"],
            claimed_by=data.get("claimed_by"),
            claim_expires_at=(
                datetime.fromisoformat(data["claim_expires_at"])
                if data.get("claim_expires_at")
                else None
            ),
        )


@dataclass(frozen=True)
class Claim:
    work_item_id: uuid.UUID
    actor_id: str
    acquired_at: datetime
    expires_at: datetime
    attempt_number: int

    def to_dict(self) -> dict:
        return {
            "work_item_id": str(self.work_item_id),
            "actor_id": self.actor_id,
            "acquired_at": self.acquired_at.isoformat(),
            "expires_at": self.expires_at.isoformat(),
            "attempt_number": self.attempt_number,
        }

    @classmethod
    def from_dict(cls, data: dict) -> Claim:
        return cls(
            work_item_id=uuid.UUID(data["work_item_id"]),
            actor_id=data["actor_id"],
            acquired_at=datetime.fromisoformat(data["acquired_at"]),
            expires_at=datetime.fromisoformat(data["expires_at"]),
            attempt_number=data["attempt_number"],
        )


@dataclass(frozen=True)
class CustomFieldDef:
    name: str
    type: str
    required: bool = False
    default_value: Any = None
    ui_visible: bool = False
    enum_values: list[str] | None = None
    target_work_item_type: str | None = None

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "type": self.type,
            "required": self.required,
            "default_value": self.default_value,
            "ui_visible": self.ui_visible,
            "enum_values": self.enum_values,
            "target_work_item_type": self.target_work_item_type,
        }

    @classmethod
    def from_dict(cls, data: dict) -> CustomFieldDef:
        return cls(
            name=data["name"],
            type=data["type"],
            required=data.get("required", False),
            default_value=data.get("default_value"),
            ui_visible=data.get("ui_visible", False),
            enum_values=data.get("enum_values"),
            target_work_item_type=data.get("target_work_item_type"),
        )


@dataclass(frozen=True)
class WorkItemTypeDef:
    name: str
    custom_fields: list[CustomFieldDef]

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "custom_fields": [f.to_dict() for f in self.custom_fields],
        }

    @classmethod
    def from_dict(cls, data: dict) -> WorkItemTypeDef:
        return cls(
            name=data["name"],
            custom_fields=[CustomFieldDef.from_dict(f) for f in data["custom_fields"]],
        )


@dataclass(frozen=True)
class TransitionDef:
    name: str
    from_state: str
    to_state: str
    allowed_roles: list[str]
    validator: str | None
    hooks: list[str]

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "from_state": self.from_state,
            "to_state": self.to_state,
            "allowed_roles": self.allowed_roles,
            "validator": self.validator,
            "hooks": self.hooks,
        }

    @classmethod
    def from_dict(cls, data: dict) -> TransitionDef:
        return cls(
            name=data["name"],
            from_state=data["from_state"],
            to_state=data["to_state"],
            allowed_roles=data["allowed_roles"],
            validator=data.get("validator"),
            hooks=data.get("hooks", []),
        )


@dataclass(frozen=True)
class LinkTypeDef:
    name: str
    source_type: str
    target_type: str

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "source_type": self.source_type,
            "target_type": self.target_type,
        }

    @classmethod
    def from_dict(cls, data: dict) -> LinkTypeDef:
        return cls(
            name=data["name"],
            source_type=data["source_type"],
            target_type=data["target_type"],
        )


@dataclass(frozen=True)
class WorkflowDefinition:
    name: str
    version: int
    substrate_version: str
    states: list[str]
    initial_state: str
    terminal_states: list[str]
    transitions: list[TransitionDef]
    roles: list[str]
    work_item_types: list[WorkItemTypeDef]
    link_types: list[LinkTypeDef]
    attempt_threshold: int | None
    raw_yaml: str

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "version": self.version,
            "substrate_version": self.substrate_version,
            "states": self.states,
            "initial_state": self.initial_state,
            "terminal_states": self.terminal_states,
            "transitions": [t.to_dict() for t in self.transitions],
            "roles": self.roles,
            "work_item_types": [w.to_dict() for w in self.work_item_types],
            "link_types": [lt.to_dict() for lt in self.link_types],
            "attempt_threshold": self.attempt_threshold,
            "raw_yaml": self.raw_yaml,
        }

    @classmethod
    def from_dict(cls, data: dict) -> WorkflowDefinition:
        return cls(
            name=data["name"],
            version=data["version"],
            substrate_version=data["substrate_version"],
            states=data["states"],
            initial_state=data["initial_state"],
            terminal_states=data["terminal_states"],
            transitions=[TransitionDef.from_dict(t) for t in data["transitions"]],
            roles=data["roles"],
            work_item_types=[WorkItemTypeDef.from_dict(w) for w in data["work_item_types"]],
            link_types=[LinkTypeDef.from_dict(lt) for lt in data["link_types"]],
            attempt_threshold=data.get("attempt_threshold"),
            raw_yaml=data["raw_yaml"],
        )


@dataclass(frozen=True)
class WorkflowVersion:
    name: str
    version: int
    substrate_version: str
    registered_at: datetime

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "version": self.version,
            "substrate_version": self.substrate_version,
            "registered_at": self.registered_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict) -> WorkflowVersion:
        return cls(
            name=data["name"],
            version=data["version"],
            substrate_version=data["substrate_version"],
            registered_at=datetime.fromisoformat(data["registered_at"]),
        )


@dataclass(frozen=True)
class Link:
    link_id: uuid.UUID
    from_work_item_id: uuid.UUID
    to_work_item_id: uuid.UUID
    link_type: str

    def to_dict(self) -> dict:
        return {
            "link_id": str(self.link_id),
            "from_work_item_id": str(self.from_work_item_id),
            "to_work_item_id": str(self.to_work_item_id),
            "link_type": self.link_type,
        }

    @classmethod
    def from_dict(cls, data: dict) -> Link:
        return cls(
            link_id=uuid.UUID(data["link_id"]),
            from_work_item_id=uuid.UUID(data["from_work_item_id"]),
            to_work_item_id=uuid.UUID(data["to_work_item_id"]),
            link_type=data["link_type"],
        )


@dataclass(frozen=True)
class QueryPage(Generic[T]):
    items: list[T]
    cursor: uuid.UUID | None
    has_more: bool

    def to_dict(self) -> dict:
        return {
            "items": [item.to_dict() if hasattr(item, "to_dict") else item for item in self.items],
            "cursor": str(self.cursor) if self.cursor else None,
            "has_more": self.has_more,
        }


@dataclass(frozen=True)
class ReplayReport:
    table_name: str
    replayed_ok: int
    replayed_drift: int
    halted: int

    def to_dict(self) -> dict:
        return {
            "table_name": self.table_name,
            "replayed_ok": self.replayed_ok,
            "replayed_drift": self.replayed_drift,
            "halted": self.halted,
        }

    @classmethod
    def from_dict(cls, data: dict) -> ReplayReport:
        return cls(
            table_name=data["table_name"],
            replayed_ok=data["replayed_ok"],
            replayed_drift=data["replayed_drift"],
            halted=data["halted"],
        )


@dataclass(frozen=True)
class ReplayReportEntry:
    work_item_id: uuid.UUID
    category: str
    detail: str | None

    def to_dict(self) -> dict:
        return {
            "work_item_id": str(self.work_item_id),
            "category": self.category,
            "detail": self.detail,
        }

    @classmethod
    def from_dict(cls, data: dict) -> ReplayReportEntry:
        return cls(
            work_item_id=uuid.UUID(data["work_item_id"]),
            category=data["category"],
            detail=data.get("detail"),
        )


@dataclass(frozen=True)
class ValidatorContext:
    work_item_id: uuid.UUID
    workflow_name: str
    workflow_version: int
    work_item_type: str
    current_state: str
    new_state: str
    transition_name: str
    payload: dict | None
    custom_fields: dict
    actor_id: str
    actor_metadata: dict | None

    def to_dict(self) -> dict:
        return {
            "work_item_id": str(self.work_item_id),
            "workflow_name": self.workflow_name,
            "workflow_version": self.workflow_version,
            "work_item_type": self.work_item_type,
            "current_state": self.current_state,
            "new_state": self.new_state,
            "transition_name": self.transition_name,
            "payload": self.payload,
            "custom_fields": self.custom_fields,
            "actor_id": self.actor_id,
            "actor_metadata": self.actor_metadata,
        }


@dataclass(frozen=True)
class HookContext:
    hook_queue_id: int
    event_id: uuid.UUID
    work_item_id: uuid.UUID
    hook_name: str
    transition: str | None
    payload: dict | None

    def to_dict(self) -> dict:
        return {
            "hook_queue_id": self.hook_queue_id,
            "event_id": str(self.event_id),
            "work_item_id": str(self.work_item_id),
            "hook_name": self.hook_name,
            "transition": self.transition,
            "payload": self.payload,
        }


@dataclass(frozen=True)
class DeadLetterEntry:
    id: int
    event_id: uuid.UUID
    hook_name: str
    hook_type: str
    payload: dict | None
    retry_count: int
    error_message: str | None
    dead_lettered_at: datetime
    original_hook_queue_id: int | None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "event_id": str(self.event_id),
            "hook_name": self.hook_name,
            "hook_type": self.hook_type,
            "payload": self.payload,
            "retry_count": self.retry_count,
            "error_message": self.error_message,
            "dead_lettered_at": self.dead_lettered_at.isoformat(),
            "original_hook_queue_id": self.original_hook_queue_id,
        }

    @classmethod
    def from_dict(cls, data: dict) -> DeadLetterEntry:
        return cls(
            id=data["id"],
            event_id=uuid.UUID(data["event_id"]),
            hook_name=data["hook_name"],
            hook_type=data["hook_type"],
            payload=data.get("payload"),
            retry_count=data["retry_count"],
            error_message=data.get("error_message"),
            dead_lettered_at=datetime.fromisoformat(data["dead_lettered_at"]),
            original_hook_queue_id=data.get("original_hook_queue_id"),
        )
