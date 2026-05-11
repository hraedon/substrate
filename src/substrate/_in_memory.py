from __future__ import annotations

import uuid
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from pathlib import Path

from ._contract import (
    check_actor_role_authorized,
    check_append_blocked,
    check_expected_seq,
    check_idempotency,
    check_reserved_transition,
    check_role_gating,
    resolve_claim_acquire,
    resolve_heartbeat,
    resolve_transition,
    should_escalate,
    validate_json_safe_value,
    validate_link_type,
    validate_read_events_filters,
    validate_release,
    validate_ttl,
    validate_work_item_exists,
)
from ._contract import (
    validate_actor_kind as _validate_actor_kind,
)
from ._errors import ErrorCode, SubstrateError
from ._integrity import SUBSTRATE_VERSION
from ._keys import KeySet
from ._signing import sign_event as _sign_event
from ._signing import verify_event as _verify_event
from ._types import (
    ActorRole,
    Claim,
    ConnectionInfo,
    DeadLetterEntry,
    Event,
    HookContext,
    Link,
    QueryPage,
    ReplayReport,
    ValidatorContext,
    WorkflowDefinition,
    WorkflowVersion,
    WorkItem,
)
from ._workflow import (
    compute_content_hash,
    parse_workflow_yaml,
    validate_and_build,
    validate_field_update,
    validate_field_values,
)

_DUMMY_KEY_ID = "in-memory"
_DUMMY_SIG = b"\x00" * 32
_DUMMY_HASH = b"\x00" * 32


def _make_event(
    event_id: uuid.UUID,
    work_item_id: uuid.UUID,
    event_seq: int,
    actor_id: str,
    actor_kind: str,
    actor_metadata: dict | None,
    workflow_name: str,
    workflow_version: int,
    transition: str | None,
    payload: dict | None,
    timestamp: datetime,
    key_set: KeySet | None = None,
) -> Event:
    if key_set is not None:
        key_entry = key_set.active_key()
        signature, canonical_hash, canonical_envelope = _sign_event(
            event_id=event_id,
            work_item_id=work_item_id,
            actor_id=actor_id,
            transition=transition,
            payload=payload,
            key=key_entry.secret,
        )
        return Event(
            event_id=event_id,
            work_item_id=work_item_id,
            event_seq=event_seq,
            actor_id=actor_id,
            actor_kind=actor_kind,
            actor_metadata=actor_metadata,
            key_id=key_entry.key_id,
            workflow_name=workflow_name,
            workflow_version=workflow_version,
            timestamp=timestamp,
            transition=transition,
            payload=payload,
            payload_canonical_hash=canonical_hash,
            signature=signature,
            canonical_envelope=canonical_envelope,
        )
    return Event(
        event_id=event_id,
        work_item_id=work_item_id,
        event_seq=event_seq,
        actor_id=actor_id,
        actor_kind=actor_kind,
        actor_metadata=actor_metadata,
        key_id=_DUMMY_KEY_ID,
        workflow_name=workflow_name,
        workflow_version=workflow_version,
        timestamp=timestamp,
        transition=transition,
        payload=payload,
        payload_canonical_hash=_DUMMY_HASH,
        signature=_DUMMY_SIG,
        canonical_envelope=_DUMMY_SIG,
    )


class InMemorySubstrate:
    def __init__(
        self,
        dsn: str = "",
        project: str = "test",
        hmac_key_path: str = "",
        *,
        pool_min: int = 1,
        pool_max: int = 10,
        prometheus_registry=None,
    ) -> None:
        self._project = project
        self._key_set: KeySet | None = None
        if hmac_key_path:
            self._key_set = KeySet(hmac_key_path)
        self._workflows: dict[tuple[str, int], dict] = {}
        self._workflow_defs: dict[tuple[str, int], WorkflowDefinition] = {}
        self._workflow_hashes: dict[tuple[str, int], bytes] = {}
        self._workflow_registered_at: dict[tuple[str, int], datetime] = {}
        self._work_items: dict[uuid.UUID, dict] = {}
        self._events: dict[uuid.UUID, list[Event]] = {}
        self._event_id_index: dict[uuid.UUID, Event] = {}
        self._claims: dict[uuid.UUID, dict] = {}
        self._links: list[dict] = []
        self._actor_roles: set[tuple[str, str]] = set()
        self._actor_role_created: dict[tuple[str, str], datetime] = {}
        self._validators: dict[str, Callable] = {}
        self._hook_handlers: dict[str, Callable] = {}
        self._hook_queue: list[dict] = []
        self._dead_letter: dict[int, dict] = {}
        self._hook_consumer_running = False

    @classmethod
    def create_project(
        cls,
        dsn: str = "",
        project: str = "test",
        hmac_key_path: str = "",
        *,
        pool_min: int = 1,
        pool_max: int = 10,
        prometheus_registry=None,
    ) -> InMemorySubstrate:
        return cls(
            dsn, project, hmac_key_path,
            pool_min=pool_min, pool_max=pool_max,
            prometheus_registry=prometheus_registry,
        )

    def close(self) -> None:
        pass

    @property
    def project(self) -> str:
        return self._project

    @property
    def substrate_version(self) -> str:
        return SUBSTRATE_VERSION

    @property
    def prometheus_registry(self):
        return None

    @property
    def connection_info(self) -> ConnectionInfo:
        return ConnectionInfo(host=None, port=None, database=None, project=self._project)

    def register_validator(self, name: str, handler: Callable) -> None:
        self._validators[name] = handler

    def register_hook_handler(self, name: str, handler: Callable) -> None:
        self._hook_handlers[name] = handler

    def start_hook_consumer(self) -> None:
        self._hook_consumer_running = True

    def stop_hook_consumer(self) -> None:
        self._hook_consumer_running = False

    def _move_to_dead_letter(
        self,
        entry: dict,
        error_message: str,
    ) -> None:
        entry["status"] = "dead_lettered"
        entry["error_message"] = error_message
        entry["dead_lettered_at"] = datetime.now(UTC)
        self._dead_letter[entry["id"]] = {
            "id": entry["id"],
            "event_id": entry["event_id"],
            "work_item_id": entry.get("work_item_id"),
            "hook_name": entry["hook_name"],
            "hook_type": entry.get("hook_type", "async"),
            "payload": entry.get("payload"),
            "retry_count": entry.get("retry_count", 0),
            "error_message": error_message,
            "dead_lettered_at": entry["dead_lettered_at"],
            "original_hook_queue_id": entry["id"],
        }
        work_item_id = entry.get("work_item_id")
        if work_item_id:
            wi = self._work_items.get(work_item_id)
            if wi is not None:
                self._append_claim_event(
                    wi, uuid.uuid4(), "hook_dead_lettered",
                    {
                        "hook_name": entry["hook_name"],
                        "hook_queue_id": entry["id"],
                        "error_message": error_message,
                    },
                )

    def poll_hooks(self) -> int:
        now = datetime.now(UTC)
        for entry in self._hook_queue:
            if (
                entry.get("status") == "in_progress"
                and entry.get("updated_at") is not None
                and now - entry["updated_at"] > timedelta(minutes=5)
            ):
                entry["status"] = "pending"

        pending = [e for e in self._hook_queue if e.get("status", "pending") == "pending"]
        processed = 0
        for entry in pending:
            handler = self._hook_handlers.get(entry["hook_name"])
            if handler is None:
                self._move_to_dead_letter(entry, f"Handler {entry['hook_name']!r} not registered")
                processed += 1
                continue

            work_item_id = entry.get("work_item_id")
            if work_item_id is None:
                self._move_to_dead_letter(entry, "work_item_id missing from payload")
                processed += 1
                continue

            ctx = HookContext(
                hook_queue_id=entry["id"],
                event_id=entry["event_id"],
                work_item_id=work_item_id,
                hook_name=entry["hook_name"],
                transition=entry.get("transition"),
                payload=entry.get("payload"),
            )

            entry["status"] = "in_progress"
            entry["updated_at"] = datetime.now(UTC)

            try:
                handler(ctx)
                entry["status"] = "completed"
                processed += 1
            except Exception:
                entry["retry_count"] = entry.get("retry_count", 0) + 1
                max_retries = entry.get("max_retries", 3)
                if entry["retry_count"] >= max_retries:
                    self._move_to_dead_letter(entry, "handler failed")
                    processed += 1
                else:
                    entry["status"] = "pending"

        self._hook_queue = [
            e for e in self._hook_queue
            if e.get("status") not in ("completed", "dead_lettered")
        ]
        return processed

    def register_workflow(self, yaml_content: str) -> WorkflowVersion:
        raw_dict = parse_workflow_yaml(yaml_content)
        wf = validate_and_build(raw_dict, yaml_content)
        content_hash = compute_content_hash(wf)
        key = (wf.name, wf.version)

        if key in self._workflows:
            existing_hash = self._workflow_hashes.get(key)
            if existing_hash is not None and existing_hash != content_hash:
                raise SubstrateError(
                    ErrorCode.WORKFLOW_VERSION_CONFLICT,
                    f"Workflow {wf.name!r} v{wf.version} already registered with different content",
                )
            return WorkflowVersion(
                name=key[0],
                version=key[1],
                substrate_version=(
                    self._workflow_defs[key].substrate_version
                ),
                registered_at=self._workflow_registered_at[key],
            )

        now = datetime.now(UTC)
        self._workflows[key] = wf.to_dict()
        self._workflow_defs[key] = wf
        self._workflow_hashes[key] = content_hash
        self._workflow_registered_at[key] = now

        return WorkflowVersion(
            name=wf.name,
            version=wf.version,
            substrate_version=wf.substrate_version,
            registered_at=now,
        )

    def register_workflow_file(self, path: str | Path) -> WorkflowVersion:
        return self.register_workflow(Path(path).read_text())

    def create_work_item(
        self,
        workflow_name: str,
        work_item_type: str,
        actor_id: str,
        actor_kind: str = "agent",
        actor_metadata: dict | None = None,
        *,
        custom_fields: dict | None = None,
        not_before: datetime | None = None,
        event_id: uuid.UUID | None = None,
    ) -> tuple[WorkItem, Event]:
        _validate_actor_kind(actor_kind)
        if event_id is None:
            event_id = uuid.uuid4()

        wf_data, wf, version = self._resolve_wf_def(workflow_name)

        wit_def = None
        for wt in wf.work_item_types:
            if wt.name == work_item_type:
                wit_def = wt
                break
        if wit_def is None:
            raise SubstrateError(
                ErrorCode.WORK_ITEM_TYPE_NOT_DECLARED,
                f"Work-item type {work_item_type!r} not declared in workflow {workflow_name!r}",
            )

        validated_fields = validate_field_values(wf, work_item_type, custom_fields or {})
        self._validate_refs_in_memory(wf_data, work_item_type, validated_fields)

        work_item_id = uuid.uuid4()
        initial_state = wf.initial_state
        now = datetime.now(UTC)

        wi_state = {
            "work_item_id": work_item_id,
            "workflow_name": workflow_name,
            "workflow_version": version,
            "work_item_type": work_item_type,
            "current_state": initial_state,
            "custom_fields": validated_fields,
            "needs_review": False,
            "not_before": not_before,
            "last_event_seq": 0,
            "last_event_at": now,
            "next_event_seq": 1,
            "claimed_by": None,
            "claim_expires_at": None,
            "attempt_number": 0,
        }
        self._work_items[work_item_id] = wi_state

        evt = _make_event(
            event_id=event_id,
            work_item_id=work_item_id,
            event_seq=0,
            actor_id=actor_id,
            actor_kind=actor_kind,
            actor_metadata=actor_metadata,
            workflow_name=workflow_name,
            workflow_version=version,
            transition="created",
            payload={
                "work_item_type": work_item_type,
                "initial_state": initial_state,
                "custom_fields": validated_fields,
                "not_before": not_before.isoformat() if not_before else None,
            },
            timestamp=now,
            key_set=self._key_set,
        )
        self._events.setdefault(work_item_id, []).append(evt)
        self._event_id_index[event_id] = evt

        return self._wi_to_work_item(wi_state), evt

    def append_event(
        self,
        work_item_id: uuid.UUID,
        actor_id: str,
        actor_kind: str = "agent",
        actor_metadata: dict | None = None,
        *,
        transition: str | None = None,
        payload: dict | None = None,
        event_id: uuid.UUID | None = None,
        expected_event_seq: int | None = None,
    ) -> Event:
        _validate_actor_kind(actor_kind)
        if actor_metadata is not None:
            validate_json_safe_value(actor_metadata, "actor_metadata")
        if payload is not None:
            validate_json_safe_value(payload, "payload")
        if event_id is None:
            event_id = uuid.uuid4()

        wi = self._work_items.get(work_item_id)
        validate_work_item_exists(wi, work_item_id)

        if transition is not None:
            check_reserved_transition(transition)
            wf_data = self._workflows.get((wi["workflow_name"], wi["workflow_version"]))
            if wf_data is not None:
                check_append_blocked(
                    wf_data.get("transitions", []),
                    transition,
                    wi["workflow_name"],
                )

        existing = check_idempotency(
            self._event_id_index.get(event_id),
            actor_id,
            transition,
            work_item_id,
        )
        if existing is not None:
            return existing

        check_expected_seq(wi["next_event_seq"], expected_event_seq)

        now = datetime.now(UTC)
        evt = _make_event(
            event_id=event_id,
            work_item_id=work_item_id,
            event_seq=wi["next_event_seq"],
            actor_id=actor_id,
            actor_kind=actor_kind,
            actor_metadata=actor_metadata,
            workflow_name=wi["workflow_name"],
            workflow_version=wi["workflow_version"],
            transition=transition,
            payload=payload,
            timestamp=now,
            key_set=self._key_set,
        )
        self._events.setdefault(work_item_id, []).append(evt)
        self._event_id_index[event_id] = evt

        wi["last_event_seq"] = wi["next_event_seq"]
        wi["last_event_at"] = now
        wi["next_event_seq"] += 1

        return evt

    def transition(
        self,
        work_item_id: uuid.UUID,
        transition_name: str,
        actor_id: str,
        actor_kind: str = "agent",
        actor_metadata: dict | None = None,
        *,
        payload: dict | None = None,
        custom_fields: dict | None = None,
        event_id: uuid.UUID | None = None,
        expected_event_seq: int | None = None,
    ) -> Event:
        _validate_actor_kind(actor_kind)
        if actor_metadata is not None:
            validate_json_safe_value(actor_metadata, "actor_metadata")
        if payload is not None:
            validate_json_safe_value(payload, "payload")
        if event_id is None:
            event_id = uuid.uuid4()

        wi = self._work_items.get(work_item_id)
        validate_work_item_exists(wi, work_item_id)

        wf_key = (wi["workflow_name"], wi["workflow_version"])
        wf_data = self._workflows.get(wf_key)
        if wf_data is None:
            raise SubstrateError(
                ErrorCode.WORKFLOW_NOT_REGISTERED,
                f"Workflow {wi['workflow_name']!r} v{wi['workflow_version']} not found",
            )

        transition_def = resolve_transition(
            wf_data.get("transitions", []),
            wi["current_state"],
            transition_name,
            wi["workflow_name"],
            wi["workflow_version"],
        )

        role = check_role_gating(
            transition_def.get("allowed_roles", []),
            actor_metadata,
            transition_name,
        )
        if role is not None:
            registered = {r for (aid, r) in self._actor_roles if aid == actor_id}
            check_actor_role_authorized(registered, actor_id, role)

        if custom_fields:
            validate_field_update(wf_data, wi["work_item_type"], custom_fields)
            self._validate_refs_in_memory(wf_data, wi["work_item_type"], custom_fields)

        new_state = transition_def["to_state"]

        validator_name = transition_def.get("validator")
        if validator_name:
            handler = self._validators.get(validator_name)
            if handler is not None:
                from ._hooks import run_validator

                ctx = ValidatorContext(
                    work_item_id=work_item_id,
                    workflow_name=wi["workflow_name"],
                    workflow_version=wi["workflow_version"],
                    work_item_type=wi["work_item_type"],
                    current_state=wi["current_state"],
                    new_state=new_state,
                    transition_name=transition_name,
                    payload=payload,
                    custom_fields=wi["custom_fields"] or {},
                    actor_id=actor_id,
                    actor_metadata=actor_metadata,
                )
                run_validator(validator_name, handler, ctx)

        existing = check_idempotency(
            self._event_id_index.get(event_id),
            actor_id,
            transition_name,
            work_item_id,
        )
        if existing is not None:
            return existing

        check_expected_seq(wi["next_event_seq"], expected_event_seq)

        stored_payload = dict(payload) if payload else {}
        if custom_fields:
            stored_payload["custom_fields_update"] = custom_fields
            merged = wi.get("custom_fields") or {}
            wi["custom_fields"] = {**merged, **custom_fields}

        now = datetime.now(UTC)
        evt = _make_event(
            event_id=event_id,
            work_item_id=work_item_id,
            event_seq=wi["next_event_seq"],
            actor_id=actor_id,
            actor_kind=actor_kind,
            actor_metadata=actor_metadata,
            workflow_name=wi["workflow_name"],
            workflow_version=wi["workflow_version"],
            transition=transition_name,
            payload=stored_payload,
            timestamp=now,
            key_set=self._key_set,
        )
        self._events.setdefault(work_item_id, []).append(evt)
        self._event_id_index[event_id] = evt

        wi["current_state"] = new_state
        wi["last_event_seq"] = wi["next_event_seq"]
        wi["last_event_at"] = now
        wi["next_event_seq"] += 1
        wi["claimed_by"] = None
        wi["claim_expires_at"] = None
        self._claims.pop(work_item_id, None)

        hook_names = transition_def.get("hooks", [])
        if hook_names:
            hook_defaults = wf_data.get("hook_defaults") or {}
            max_retries = hook_defaults.get("max_retries", 3)
            for hn in hook_names:
                self._hook_queue.append({
                    "id": len(self._hook_queue) + 1,
                    "event_id": event_id,
                    "work_item_id": work_item_id,
                    "hook_name": hn,
                    "hook_type": "async",
                    "transition": transition_name,
                    "payload": payload,
                    "retry_count": 0,
                    "max_retries": max_retries,
                    "status": "pending",
                    "updated_at": datetime.now(UTC),
                })

        return evt

    def read_events(
        self,
        *,
        work_item_id: uuid.UUID | None = None,
        actor_id: str | None = None,
        start: datetime | None = None,
        end: datetime | None = None,
        transition: str | None = None,
        limit: int = 100,
        before_seq: int | None = None,
    ) -> list[Event]:
        validate_read_events_filters(before_seq, work_item_id, start, end)

        if work_item_id is not None:
            evts = list(self._events.get(work_item_id, []))
            if transition is not None:
                evts = [e for e in evts if e.transition == transition]
            if actor_id is not None:
                evts = [e for e in evts if e.actor_id == actor_id]
            if start is not None and end is not None:
                evts = [e for e in evts if start <= e.timestamp <= end]
            if before_seq is not None:
                evts = [e for e in evts if e.event_seq < before_seq]
                evts.sort(key=lambda e: e.event_seq, reverse=True)
                return list(reversed(evts[:limit]))
            evts.sort(key=lambda e: e.event_seq, reverse=True)
            return list(reversed(evts[:limit]))
        if actor_id is not None:
            evts = [e for el in self._events.values() for e in el]
            evts = [e for e in evts if e.actor_id == actor_id]
            if transition is not None:
                evts = [e for e in evts if e.transition == transition]
            if start is not None and end is not None:
                evts = [e for e in evts if start <= e.timestamp <= end]
            evts.sort(key=lambda e: (e.timestamp, e.event_seq), reverse=True)
            return evts[:limit]
        if start is not None and end is not None:
            evts = [e for el in self._events.values() for e in el]
            evts = [e for e in evts if start <= e.timestamp <= end]
            if transition is not None:
                evts = [e for e in evts if e.transition == transition]
            evts.sort(key=lambda e: e.timestamp)
            return evts[:limit]
        if transition is not None:
            evts = [e for el in self._events.values() for e in el]
            evts = [e for e in evts if e.transition == transition]
            evts.sort(key=lambda e: (e.timestamp, e.event_seq), reverse=True)
            return evts[:limit]
        return []

    def read_events_since(
        self,
        work_item_id: uuid.UUID,
        after_seq: int,
        *,
        limit: int = 100,
    ) -> list[Event]:
        evts = self._events.get(work_item_id, [])
        result = [e for e in evts if e.event_seq > after_seq]
        result.sort(key=lambda e: e.event_seq)
        return result[:limit]

    def query_work_items(
        self,
        *,
        workflow_name: str | None = None,
        workflow_version: int | None = None,
        work_item_types: list[str] | None = None,
        current_states: list[str] | None = None,
        claimed_by: str | None = None,
        claimable_now: bool | None = None,
        needs_review: bool | None = None,
        has_link_type: str | None = None,
        cursor: uuid.UUID | None = None,
        page_size: int = 100,
    ) -> QueryPage[WorkItem]:
        page_size = min(max(1, page_size), 1000)
        items = list(self._work_items.values())

        if cursor is not None:
            items = [wi for wi in items if wi["work_item_id"] > cursor]
        if workflow_name is not None:
            items = [wi for wi in items if wi["workflow_name"] == workflow_name]
        if workflow_version is not None:
            items = [wi for wi in items if wi["workflow_version"] == workflow_version]
        if work_item_types:
            items = [wi for wi in items if wi["work_item_type"] in work_item_types]
        if current_states:
            items = [wi for wi in items if wi["current_state"] in current_states]
        if claimed_by is not None:
            items = [wi for wi in items if wi.get("claimed_by") == claimed_by]
        if needs_review is not None:
            items = [wi for wi in items if wi.get("needs_review") == needs_review]
        if claimable_now is True:
            now = datetime.now(UTC)
            items = [
                wi for wi in items
                if (
                    wi.get("claimed_by") is None
                    or (wi.get("claim_expires_at") and wi["claim_expires_at"] < now)
                )
                and (wi.get("not_before") is None or wi["not_before"] <= now)
            ]
        if has_link_type is not None:
            active = self._active_link_set(has_link_type)
            items = [wi for wi in items if wi["work_item_id"] in active]

        items.sort(key=lambda wi: wi["work_item_id"])
        has_more = len(items) > page_size
        page = items[:page_size]
        next_cursor = page[-1]["work_item_id"] if has_more and page else None

        return QueryPage(
            items=[self._wi_to_work_item(wi) for wi in page],
            cursor=next_cursor,
            has_more=has_more,
        )

    def get_work_item(self, work_item_id: uuid.UUID) -> WorkItem | None:
        wi = self._work_items.get(work_item_id)
        if wi is None:
            return None
        return self._wi_to_work_item(wi)

    def acquire_claim(
        self,
        work_item_id: uuid.UUID,
        actor_id: str,
        ttl_seconds: int = 300,
        *,
        event_id: uuid.UUID | None = None,
        actor_kind: str = "agent",
    ) -> Claim:
        _validate_actor_kind(actor_kind)
        validate_ttl(ttl_seconds)

        wi = self._work_items.get(work_item_id)
        validate_work_item_exists(wi, work_item_id)

        now = datetime.now(UTC)
        existing = self._claims.get(work_item_id)
        claim_state = existing if existing is not None else None

        result = resolve_claim_acquire(
            wi_not_before=wi.get("not_before"),
            claim_actor_id=claim_state["actor_id"] if claim_state else None,
            claim_expires_at=claim_state["expires_at"] if claim_state else None,
            claim_acquired_at=claim_state["acquired_at"] if claim_state else None,
            claim_attempt_number=claim_state["attempt_number"] if claim_state else None,
            wi_attempt_number=wi["attempt_number"],
            actor_id=actor_id,
            ttl_seconds=ttl_seconds,
            now=now,
        )

        claim_data = {
            "actor_id": actor_id,
            "acquired_at": result.acquired_at,
            "expires_at": result.expires_at,
            "attempt_number": result.attempt_number,
        }
        self._claims[work_item_id] = claim_data
        wi["attempt_number"] = result.attempt_number
        wi["claimed_by"] = actor_id
        wi["claim_expires_at"] = result.expires_at

        if result.event_transition is not None:
            eid = event_id or uuid.uuid4()
            self._append_claim_event(
                wi, eid, result.event_transition,
                result.event_payload,
                actor_id=actor_id,
                actor_kind=actor_kind,
            )

        self._check_escalation(wi, result.attempt_number)

        return Claim(
            work_item_id=work_item_id,
            actor_id=actor_id,
            acquired_at=result.acquired_at,
            expires_at=result.expires_at,
            attempt_number=result.attempt_number,
        )

    def heartbeat_claim(
        self,
        work_item_id: uuid.UUID,
        actor_id: str,
        ttl_seconds: int = 300,
        *,
        expected_attempt_number: int | None = None,
    ) -> Claim:
        now = datetime.now(UTC)
        claim = self._claims.get(work_item_id)
        claim_state = claim if claim is not None else None

        result = resolve_heartbeat(
            claim_state=claim_state,
            actor_id=actor_id,
            ttl_seconds=ttl_seconds,
            expected_attempt_number=expected_attempt_number,
            work_item_id=work_item_id,
            now=now,
        )

        claim["expires_at"] = result.new_expires_at
        wi = self._work_items.get(work_item_id)
        if wi is not None:
            wi["claim_expires_at"] = result.new_expires_at

        return Claim(
            work_item_id=work_item_id,
            actor_id=actor_id,
            acquired_at=result.acquired_at,
            expires_at=result.new_expires_at,
            attempt_number=result.attempt_number,
        )

    def release_claim(
        self,
        work_item_id: uuid.UUID,
        actor_id: str,
        *,
        event_id: uuid.UUID | None = None,
        actor_kind: str = "agent",
    ) -> None:
        _validate_actor_kind(actor_kind)
        claim = self._claims.get(work_item_id)
        validate_release(claim, actor_id, work_item_id)

        self._claims.pop(work_item_id, None)
        wi = self._work_items.get(work_item_id)
        if wi is not None:
            wi["claimed_by"] = None
            wi["claim_expires_at"] = None
            self._append_claim_event(
                wi, event_id or uuid.uuid4(), "claim_released",
                {"actor_id": actor_id},
                actor_id=actor_id,
                actor_kind=actor_kind,
            )

    def sweep_expired_claims(self) -> int:
        now = datetime.now(UTC)
        expired = [
            (wid, c) for wid, c in list(self._claims.items())
            if c["expires_at"] < now
        ]
        for wid, claim in expired:
            del self._claims[wid]
            wi = self._work_items.get(wid)
            if wi is not None:
                wi["claimed_by"] = None
                wi["claim_expires_at"] = None
                self._append_claim_event(
                    wi, uuid.uuid4(), "claim_expired",
                    {"actor_id": claim["actor_id"], "expired_at": now.isoformat()},
                    actor_id=claim["actor_id"] or "system",
                )
        return len(expired)

    def create_link(
        self,
        from_work_item_id: uuid.UUID,
        to_work_item_id: uuid.UUID,
        link_type: str,
        actor_id: str,
        actor_kind: str = "agent",
        actor_metadata: dict | None = None,
        *,
        event_id: uuid.UUID | None = None,
        payload: dict | None = None,
    ) -> Link:
        _validate_actor_kind(actor_kind)
        if event_id is None:
            event_id = uuid.uuid4()

        from_wi = self._work_items.get(from_work_item_id)
        to_wi = self._work_items.get(to_work_item_id)
        if from_wi is None or to_wi is None:
            raise SubstrateError(
                ErrorCode.LINK_TARGET_NOT_FOUND,
                "One or both work items not found for link",
            )
        if from_wi["workflow_name"] != to_wi["workflow_name"]:
            raise SubstrateError(
                ErrorCode.LINK_CROSS_PROJECT,
                "Cannot link work items from different projects",
            )

        wf_data = self._workflows.get((from_wi["workflow_name"], from_wi["workflow_version"]))
        if wf_data is not None:
            validate_link_type(
                wf_data.get("link_types", []),
                from_wi["work_item_type"],
                to_wi["work_item_type"],
                link_type,
            )

        link_id = uuid.uuid4()
        link_payload = {
            "link_id": str(link_id),
            "from_work_item_id": str(from_work_item_id),
            "to_work_item_id": str(to_work_item_id),
            "link_type": link_type,
        }
        if payload:
            link_payload["link_payload"] = payload

        self._append_simple_event(
            from_wi, event_id, actor_id, actor_kind, actor_metadata,
            "link_created", link_payload,
        )

        self._links.append({
            "link_id": link_id,
            "from_id": from_work_item_id,
            "to_id": to_work_item_id,
            "link_type": link_type,
            "payload": payload,
        })

        return Link(
            link_id=link_id,
            from_work_item_id=from_work_item_id,
            to_work_item_id=to_work_item_id,
            link_type=link_type,
            payload=payload,
        )

    def remove_link(
        self,
        from_work_item_id: uuid.UUID,
        to_work_item_id: uuid.UUID,
        link_type: str,
        actor_id: str,
        actor_kind: str = "agent",
        actor_metadata: dict | None = None,
        *,
        event_id: uuid.UUID | None = None,
    ) -> None:
        _validate_actor_kind(actor_kind)
        if event_id is None:
            event_id = uuid.uuid4()

        from_wi = self._work_items.get(from_work_item_id)
        to_wi = self._work_items.get(to_work_item_id)
        if from_wi is None or to_wi is None:
            raise SubstrateError(
                ErrorCode.LINK_TARGET_NOT_FOUND,
                "One or both work items not found for link removal",
            )

        has_live = any(
            ln["from_id"] == from_work_item_id
            and ln["to_id"] == to_work_item_id
            and ln["link_type"] == link_type
            and ln.get("active", True)
            for ln in self._links
        )
        if not has_live:
            events = self._events.get(from_work_item_id, [])
            has_created = any(
                e.transition == "link_created"
                and (e.payload or {}).get("to_work_item_id") == str(to_work_item_id)
                and (e.payload or {}).get("link_type") == link_type
                for e in events
            )
            has_removed = any(
                e.transition == "link_removed"
                and (e.payload or {}).get("to_work_item_id") == str(to_work_item_id)
                and (e.payload or {}).get("link_type") == link_type
                for e in events
            )
            if not has_created or has_removed:
                raise SubstrateError(
                    ErrorCode.LINK_NOT_FOUND,
                    f"No live link of type {link_type!r} "
                    f"from {from_work_item_id} to {to_work_item_id}",
                )

        self._append_simple_event(
            from_wi, event_id, actor_id, actor_kind, actor_metadata,
            "link_removed",
            {
                "from_work_item_id": str(from_work_item_id),
                "to_work_item_id": str(to_work_item_id),
                "link_type": link_type,
            },
        )

        self._links = [
            ln for ln in self._links
            if not (
                ln["from_id"] == from_work_item_id
                and ln["to_id"] == to_work_item_id
                and ln["link_type"] == link_type
            )
        ]

    def replay(self, *, continue_on_revoked: bool = False) -> ReplayReport:
        ok = 0
        drift = 0
        halted = 0
        warnings = 0
        for wi_id, wi in self._work_items.items():
            evts = self._events.get(wi_id, [])
            if not evts:
                continue
            derived_state = None
            derived_fields: dict = {}
            derived_needs_review = False
            derived_not_before = None
            derived_last_seq = 0
            derived_attempt_number = 0
            derived_claimed_by = None
            for evt in sorted(evts, key=lambda e: e.event_seq):
                if self._key_set is not None:
                    key_entry = None
                    try:
                        key_entry = self._key_set.verify_key_status(evt.key_id)
                    except SubstrateError as e:
                        if e.code == ErrorCode.REVOKED_KEY_ID and continue_on_revoked:
                            key_entry = self._key_set.get_key(evt.key_id)
                            warnings += 1
                        elif e.code == ErrorCode.UNKNOWN_KEY_ID and continue_on_revoked:
                            warnings += 1
                        else:
                            raise
                    if key_entry is not None:
                        if not _verify_event(
                            event_id=evt.event_id,
                            work_item_id=evt.work_item_id,
                            actor_id=evt.actor_id,
                            transition=evt.transition,
                            payload=evt.payload,
                            signature=evt.signature,
                            canonical_hash=evt.payload_canonical_hash,
                            key=key_entry.secret,
                            stored_envelope=evt.canonical_envelope,
                        ):
                            raise SubstrateError(
                                ErrorCode.REPLAY_HALTED,
                                f"Signature verification failed for event {evt.event_id} "
                                f"at seq {evt.event_seq}",
                            )
                derived_last_seq = evt.event_seq
                if evt.transition == "created":
                    p = evt.payload or {}
                    derived_state = p.get("initial_state")
                    derived_fields = p.get("custom_fields", {})
                    nb = p.get("not_before")
                    if nb:
                        derived_not_before = (
                            datetime.fromisoformat(nb)
                            if isinstance(nb, str) else nb
                        )
                elif evt.transition in ("claim_acquired", "claim_released", "claim_expired",
                                        "claim_stolen", "link_created", "link_removed",
                                        "hook_dead_lettered"):
                    if evt.transition in ("claim_acquired", "claim_stolen"):
                        derived_attempt_number += 1
                    if evt.transition == "claim_acquired":
                        p = evt.payload or {}
                        derived_claimed_by = p.get("actor_id")
                    elif evt.transition == "claim_stolen":
                        p = evt.payload or {}
                        derived_claimed_by = p.get("new_actor_id")
                    elif evt.transition in ("claim_released", "claim_expired"):
                        derived_claimed_by = None
                elif evt.transition == "escalated":
                    derived_needs_review = True
                elif evt.transition == "not_before_set":
                    p = evt.payload or {}
                    nb = p.get("not_before")
                    if nb:
                        derived_not_before = (
                            datetime.fromisoformat(nb)
                            if isinstance(nb, str) else nb
                        )
                    else:
                        derived_not_before = None
                else:
                    wf_data = self._workflows.get((wi["workflow_name"], wi["workflow_version"]))
                    found = False
                    if wf_data:
                        for t in wf_data.get("transitions", []):
                            if t["name"] == evt.transition and t["from_state"] == derived_state:
                                derived_state = t["to_state"]
                                found = True
                                break
                    if found:
                        p = evt.payload or {}
                        if "custom_fields_update" in p:
                            derived_fields = {**derived_fields, **p["custom_fields_update"]}
                        derived_claimed_by = None

            if derived_state is not None:
                if (
                    derived_state != wi["current_state"]
                    or derived_fields != (wi["custom_fields"] or {})
                    or derived_needs_review != wi.get("needs_review", False)
                    or derived_not_before != wi.get("not_before")
                    or derived_last_seq != wi.get("last_event_seq", 0)
                    or derived_attempt_number != wi.get("attempt_number", 0)
                    or derived_claimed_by != wi.get("claimed_by")
                ):
                    drift += 1
                else:
                    ok += 1

        return ReplayReport(
            table_name="in_memory_replay",
            replayed_ok=ok,
            replayed_drift=drift,
            halted=halted,
            warnings=warnings,
        )

    def requeue_dead_lettered_hook(self, dead_letter_id: int) -> None:
        entry = self._dead_letter.pop(dead_letter_id, None)
        if entry is None:
            raise SubstrateError(
                ErrorCode.HOOK_NOT_FOUND,
                f"Dead letter entry {dead_letter_id} not found",
            )
        payload = entry.get("payload") or {}
        self._hook_queue.append({
            "id": entry["original_hook_queue_id"] or len(self._hook_queue) + 1,
            "event_id": entry["event_id"],
            "work_item_id": entry.get("work_item_id"),
            "hook_name": entry["hook_name"],
            "hook_type": entry["hook_type"],
            "transition": payload.get("transition"),
            "payload": payload.get("event_payload"),
            "retry_count": 0,
            "max_retries": 3,
            "status": "pending",
            "updated_at": datetime.now(UTC),
        })

    def list_dead_lettered_hooks(self) -> list[DeadLetterEntry]:
        return [
            DeadLetterEntry(
                id=e["id"],
                event_id=e["event_id"],
                hook_name=e["hook_name"],
                hook_type=e["hook_type"],
                payload=e.get("payload"),
                retry_count=e["retry_count"],
                error_message=e.get("error_message"),
                dead_lettered_at=e["dead_lettered_at"],
                original_hook_queue_id=e.get("original_hook_queue_id"),
            )
            for e in sorted(
                self._dead_letter.values(),
                key=lambda x: x["dead_lettered_at"],
                reverse=True,
            )
        ]

    def update_not_before(
        self,
        work_item_id: uuid.UUID,
        not_before: datetime | None,
        actor_id: str,
        actor_kind: str = "agent",
        actor_metadata: dict | None = None,
        *,
        event_id: uuid.UUID | None = None,
    ) -> Event:
        _validate_actor_kind(actor_kind)
        if event_id is None:
            event_id = uuid.uuid4()

        wi = self._work_items.get(work_item_id)
        validate_work_item_exists(wi, work_item_id)

        existing = check_idempotency(
            self._event_id_index.get(event_id),
            actor_id,
            "not_before_set",
            work_item_id,
        )
        if existing is not None:
            return existing

        wi["not_before"] = not_before
        now = datetime.now(UTC)
        evt = _make_event(
            event_id=event_id,
            work_item_id=work_item_id,
            event_seq=wi["next_event_seq"],
            actor_id=actor_id,
            actor_kind=actor_kind,
            actor_metadata=actor_metadata,
            workflow_name=wi["workflow_name"],
            workflow_version=wi["workflow_version"],
            transition="not_before_set",
            payload={"not_before": not_before.isoformat() if not_before else None},
            timestamp=now,
            key_set=self._key_set,
        )
        self._events.setdefault(work_item_id, []).append(evt)
        self._event_id_index[event_id] = evt
        wi["last_event_seq"] = wi["next_event_seq"]
        wi["last_event_at"] = now
        wi["next_event_seq"] += 1
        return evt

    def register_actor_role(self, actor_id: str, role: str) -> None:
        key = (actor_id, role)
        if key in self._actor_roles:
            return
        self._actor_roles.add(key)
        self._actor_role_created[key] = datetime.now(UTC)

    def unregister_actor_role(self, actor_id: str, role: str) -> None:
        key = (actor_id, role)
        if key not in self._actor_roles:
            raise SubstrateError(
                ErrorCode.ACTOR_ROLE_NOT_REGISTERED,
                f"Role {role!r} not registered for actor {actor_id!r}",
            )
        self._actor_roles.discard(key)
        del self._actor_role_created[key]

    def list_actor_roles(self, actor_id: str | None = None) -> list[ActorRole]:
        result = []
        for (aid, role), created_at in self._actor_role_created.items():
            if actor_id is None or aid == actor_id:
                result.append(ActorRole(actor_id=aid, role=role, created_at=created_at))
        return sorted(result, key=lambda r: (r.actor_id, r.role))

    @staticmethod
    def validate_actor_metadata(
        event: Event,
        expected_schema: dict | None = None,
    ) -> list[str]:
        from ._lint import validate_actor_metadata as _validate
        return _validate(event, expected_schema)

    @staticmethod
    def actor_metadata_complete(
        events: list[Event],
        expected_keys: list[str],
    ) -> list[Event]:
        from ._lint import actor_metadata_complete as _complete
        return _complete(events, expected_keys)

    def _resolve_workflow(self, workflow_name: str) -> tuple[dict, int]:
        versions = [(k, v) for k, v in self._workflows.items() if k[0] == workflow_name]
        if not versions:
            raise SubstrateError(
                ErrorCode.WORKFLOW_NOT_REGISTERED,
                f"Workflow {workflow_name!r} is not registered",
            )
        versions.sort(key=lambda x: x[0][1], reverse=True)
        key, data = versions[0]
        return data, key[1]

    def _resolve_wf_def(self, workflow_name: str) -> tuple[dict, WorkflowDefinition, int]:
        versions = [(k, v) for k, v in self._workflows.items() if k[0] == workflow_name]
        if not versions:
            raise SubstrateError(
                ErrorCode.WORKFLOW_NOT_REGISTERED,
                f"Workflow {workflow_name!r} is not registered",
            )
        versions.sort(key=lambda x: x[0][1], reverse=True)
        key, data = versions[0]
        wf_def = self._workflow_defs[key]
        return data, wf_def, key[1]

    def _validate_refs_in_memory(self, wf_data: dict, work_item_type: str, values: dict) -> None:
        wits = wf_data.get("work_item_types", [])
        wit = next((t for t in wits if t["name"] == work_item_type), None)
        if wit is None:
            return
        for field_def in wit.get("custom_fields", []):
            if field_def["type"] != "work_item_ref":
                continue
            value = values.get(field_def["name"])
            if value is None:
                continue
            ref_uuid = uuid.UUID(value)
            target_type = field_def.get("target_work_item_type")
            ref_wi = self._work_items.get(ref_uuid)
            if ref_wi is None:
                raise SubstrateError(
                    ErrorCode.CUSTOM_FIELD_VIOLATION,
                    f"Field {field_def['name']!r} references nonexistent work item {value}",
                    detail={"field": field_def["name"], "value": value},
                )
            if target_type and ref_wi["work_item_type"] != target_type:
                raise SubstrateError(
                    ErrorCode.CUSTOM_FIELD_VIOLATION,
                    f"Field {field_def['name']!r} references work item of type "
                    f"{ref_wi['work_item_type']!r}, expected {target_type!r}",
                    detail={
                        "field": field_def["name"],
                        "value": value,
                        "actual_type": ref_wi["work_item_type"],
                        "expected_type": target_type,
                    },
                )

    def _check_escalation(self, wi: dict, attempt_number: int) -> bool:
        wf_data = self._workflows.get((wi["workflow_name"], wi["workflow_version"]))
        if wf_data is None:
            return False
        threshold = wf_data.get("attempt_threshold")
        has_escalated = any(
            e.transition == "escalated"
            for e in self._events.get(wi["work_item_id"], [])
        )
        if not should_escalate(threshold, has_escalated, attempt_number):
            return False
        wi["needs_review"] = True
        self._append_claim_event(
            wi, uuid.uuid4(), "escalated",
            {"attempt_number": attempt_number, "threshold": threshold},
        )
        return True

    def _append_claim_event(
        self, wi: dict, event_id: uuid.UUID, transition: str, payload: dict,
        *, actor_id: str = "system", actor_kind: str = "system",
    ) -> None:
        now = datetime.now(UTC)
        evt = _make_event(
            event_id=event_id,
            work_item_id=wi["work_item_id"],
            event_seq=wi["next_event_seq"],
            actor_id=actor_id,
            actor_kind=actor_kind,
            actor_metadata=None,
            workflow_name=wi["workflow_name"],
            workflow_version=wi["workflow_version"],
            transition=transition,
            payload=payload,
            timestamp=now,
            key_set=self._key_set,
        )
        self._events.setdefault(wi["work_item_id"], []).append(evt)
        self._event_id_index[event_id] = evt
        wi["last_event_seq"] = wi["next_event_seq"]
        wi["last_event_at"] = now
        wi["next_event_seq"] += 1

    def _append_simple_event(
        self, wi: dict, event_id: uuid.UUID,
        actor_id: str, actor_kind: str, actor_metadata: dict | None,
        transition: str, payload: dict,
    ) -> None:
        now = datetime.now(UTC)
        evt = _make_event(
            event_id=event_id,
            work_item_id=wi["work_item_id"],
            event_seq=wi["next_event_seq"],
            actor_id=actor_id,
            actor_kind=actor_kind,
            actor_metadata=actor_metadata,
            workflow_name=wi["workflow_name"],
            workflow_version=wi["workflow_version"],
            transition=transition,
            payload=payload,
            timestamp=now,
            key_set=self._key_set,
        )
        self._events.setdefault(wi["work_item_id"], []).append(evt)
        self._event_id_index[event_id] = evt
        wi["last_event_seq"] = wi["next_event_seq"]
        wi["last_event_at"] = now
        wi["next_event_seq"] += 1

    def _active_link_set(self, link_type: str) -> set[uuid.UUID]:
        result = set()
        for ln in self._links:
            if ln["link_type"] == link_type:
                result.add(ln["from_id"])
        return result

    @staticmethod
    def _wi_to_work_item(wi: dict) -> WorkItem:
        return WorkItem(
            work_item_id=wi["work_item_id"],
            workflow_name=wi["workflow_name"],
            workflow_version=wi["workflow_version"],
            work_item_type=wi["work_item_type"],
            current_state=wi["current_state"],
            custom_fields=wi["custom_fields"] or {},
            needs_review=wi.get("needs_review", False),
            not_before=wi.get("not_before"),
            last_event_seq=wi["last_event_seq"],
            last_event_at=wi["last_event_at"],
            next_event_seq=wi["next_event_seq"],
            claimed_by=wi.get("claimed_by"),
            claim_expires_at=wi.get("claim_expires_at"),
            attempt_number=wi.get("attempt_number", 0),
        )
