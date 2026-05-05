from __future__ import annotations

import uuid
from datetime import datetime
from pathlib import Path

import psycopg.types.json
import structlog

from ._connection import ConnectionManager
from ._errors import ErrorCode, SubstrateError
from ._events import (
    append_event as _append_event,
)
from ._events import (
    append_transition_event as _append_transition_event,
)
from ._events import (
    read_events_by_actor as _read_by_actor,
)
from ._events import (
    read_events_by_time_range as _read_by_range,
)
from ._events import (
    read_events_by_transition as _read_by_transition,
)
from ._events import (
    read_events_by_work_item as _read_by_work_item,
)
from ._integrity import SUBSTRATE_VERSION, check_integrity
from ._keys import KeySet
from ._migrations import run_migrations
from ._observability import Metrics, OpTimer
from ._types import (
    ActorKind as ActorKind,
)
from ._types import (
    Claim,
    Event,
    Link,
    QueryPage,
    ReplayReport,
    WorkflowVersion,
    WorkItem,
)
from ._types import (
    ReplayReportEntry as ReplayReportEntry,
)
from ._types import (
    WorkflowDefinition as WorkflowDefinition,
)
from ._workflow import parse_and_validate
from ._workflow import parse_file as parse_file

log = structlog.get_logger()


class Substrate:
    def __init__(
        self,
        dsn: str,
        project: str,
        hmac_key_path: str | None = None,
        *,
        pool_min: int = 1,
        pool_max: int = 10,
        prometheus_registry=None,
    ) -> None:
        if hmac_key_path is None:
            raise SubstrateError(
                ErrorCode.UNKNOWN_KEY_ID,
                "hmac_key_path is required",
            )
        self._mgr = ConnectionManager(dsn, project, pool_min=pool_min, pool_max=pool_max)
        self._mgr.open()
        self._mgr.ensure_schema()
        self._keys = KeySet(hmac_key_path)
        self._metrics = Metrics(registry=prometheus_registry)
        self._project = project
        check_integrity(self._mgr)
        log.info("substrate.connected", project=project, substrate_version=SUBSTRATE_VERSION)

    @classmethod
    def create_project(
        cls,
        dsn: str,
        project: str,
        hmac_key_path: str,
        *,
        pool_min: int = 1,
        pool_max: int = 10,
        prometheus_registry=None,
    ) -> Substrate:
        mgr = ConnectionManager(dsn, project, pool_min=pool_min, pool_max=pool_max)
        mgr.open()
        mgr.create_schema()
        run_migrations(mgr)
        mgr.close()
        log.info("substrate.project_created", project=project)
        return cls(
            dsn,
            project,
            hmac_key_path,
            pool_min=pool_min,
            pool_max=pool_max,
            prometheus_registry=prometheus_registry,
        )

    def close(self) -> None:
        self._mgr.close()
        log.info("substrate.disconnected", project=self._project)

    @property
    def project(self) -> str:
        return self._project

    @property
    def substrate_version(self) -> str:
        return SUBSTRATE_VERSION

    @property
    def prometheus_registry(self):
        return self._metrics.registry

    def register_workflow(
        self,
        yaml_content: str,
        *,
        idempotency_key: uuid.UUID | None = None,
    ) -> WorkflowVersion:
        timer = OpTimer(self._project, "register_workflow")
        try:
            wf = parse_and_validate(yaml_content)
            with self._mgr.transaction() as conn:
                existing = conn.execute(
                    "SELECT workflow_name, version, substrate_version, registered_at "
                    "FROM workflow_registry WHERE workflow_name = %s AND version = %s",
                    [wf.name, wf.version],
                ).fetchone()
                if existing is not None:
                    timer.log("ok", detail=f"idempotent:{wf.name} v{wf.version}")
                    return WorkflowVersion(
                        name=existing["workflow_name"],
                        version=existing["version"],
                        substrate_version=existing["substrate_version"],
                        registered_at=existing["registered_at"],
                    )

                conn.execute(
                    "INSERT INTO workflow_registry "
                    "(workflow_name, version, substrate_version, definition) "
                    "VALUES (%s, %s, %s, %s)",
                    [
                        wf.name, wf.version, wf.substrate_version,
                        psycopg.types.json.Jsonb(wf.to_dict()),
                    ],
                )

            self._metrics.inc("workflows_registered", self._project)
            timer.log("ok", detail=wf.name)
            return WorkflowVersion(
                name=wf.name,
                version=wf.version,
                substrate_version=wf.substrate_version,
                registered_at=datetime.now(),
            )
        except SubstrateError:
            timer.log("error")
            raise

    def register_workflow_file(
        self,
        path: str | Path,
        *,
        idempotency_key: uuid.UUID | None = None,
    ) -> WorkflowVersion:
        return self.register_workflow(Path(path).read_text(), idempotency_key=idempotency_key)

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
        timer = OpTimer(self._project, "create_work_item")
        try:
            from ._work_items import create_work_item as _create

            with self._mgr.transaction() as conn:
                wi, evt = _create(
                    conn,
                    workflow_name=workflow_name,
                    work_item_type=work_item_type,
                    actor_id=actor_id,
                    actor_kind=actor_kind,
                    actor_metadata=actor_metadata,
                    key_set=self._keys,
                    custom_fields=custom_fields,
                    not_before=not_before,
                    event_id=event_id,
                )

            self._metrics.inc("work_items_created", self._project)
            self._metrics.inc("events_appended", self._project)
            timer.log("ok", work_item_id=str(wi.work_item_id))
            return wi, evt
        except SubstrateError:
            timer.log("error")
            raise

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
        timer = OpTimer(self._project, "append_event")
        try:
            if event_id is None:
                event_id = uuid.uuid4()

            with self._mgr.transaction() as conn:
                wi_row = conn.execute(
                    "SELECT workflow_name, workflow_version FROM work_items_current "
                    "WHERE work_item_id = %s",
                    [work_item_id],
                ).fetchone()
                if wi_row is None:
                    raise SubstrateError(
                        ErrorCode.WORK_ITEM_NOT_FOUND,
                        f"Work item {work_item_id} not found",
                    )

                if transition is not None:
                    wf_data = conn.execute(
                        "SELECT definition FROM workflow_registry "
                        "WHERE workflow_name = %s AND version = %s",
                        [wi_row["workflow_name"], wi_row["workflow_version"]],
                    ).fetchone()
                    if wf_data is not None:
                        for t in wf_data["definition"].get("transitions", []):
                            if t["name"] == transition:
                                raise SubstrateError(
                                    ErrorCode.TRANSITION_VIA_APPEND_BLOCKED,
                                    f"Transition {transition!r} is defined in workflow "
                                    f"{wi_row['workflow_name']!r}. "
                                    f"Use Substrate.transition() instead.",
                                )

                evt = _append_event(
                    conn,
                    work_item_id=work_item_id,
                    actor_id=actor_id,
                    actor_kind=actor_kind,
                    actor_metadata=actor_metadata,
                    key_set=self._keys,
                    workflow_name=wi_row["workflow_name"],
                    workflow_version=wi_row["workflow_version"],
                    transition=transition,
                    payload=payload,
                    event_id=event_id,
                    expected_event_seq=expected_event_seq,
                )

            self._metrics.inc("events_appended", self._project)
            timer.log("ok", work_item_id=str(work_item_id))
            return evt
        except SubstrateError as e:
            if e.code == ErrorCode.CONCURRENT_MODIFICATION:
                self._metrics.inc("expected_seq_mismatches", self._project)
            timer.log("rejected", work_item_id=str(work_item_id))
            raise

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
        timer = OpTimer(self._project, "transition")
        try:
            if event_id is None:
                event_id = uuid.uuid4()

            with self._mgr.transaction() as conn:
                wi_row = conn.execute(
                    "SELECT workflow_name, workflow_version, current_state "
                    "FROM work_items_current WHERE work_item_id = %s FOR UPDATE",
                    [work_item_id],
                ).fetchone()
                if wi_row is None:
                    raise SubstrateError(
                        ErrorCode.WORK_ITEM_NOT_FOUND,
                        f"Work item {work_item_id} not found",
                    )

                wf_data = conn.execute(
                    "SELECT definition FROM workflow_registry "
                    "WHERE workflow_name = %s AND version = %s",
                    [wi_row["workflow_name"], wi_row["workflow_version"]],
                ).fetchone()
                if wf_data is None:
                    raise SubstrateError(
                        ErrorCode.WORKFLOW_NOT_REGISTERED,
                        f"Workflow {wi_row['workflow_name']!r} "
                        f"v{wi_row['workflow_version']} not found",
                    )

                defn = wf_data["definition"]
                transition_def = None
                for t in defn.get("transitions", []):
                    if t["name"] == transition_name and t["from_state"] == wi_row["current_state"]:
                        transition_def = t
                        break

                if transition_def is None:
                    raise SubstrateError(
                        ErrorCode.INVALID_TRANSITION,
                        f"Transition {transition_name!r} not valid from state "
                        f"{wi_row['current_state']!r} in {wi_row['workflow_name']!r} "
                        f"v{wi_row['workflow_version']}",
                    )

                if transition_def.get("allowed_roles"):
                    role = (actor_metadata or {}).get("role")
                    if role not in transition_def["allowed_roles"]:
                        raise SubstrateError(
                            ErrorCode.ROLE_NOT_PERMITTED,
                            f"Role {role!r} not permitted for transition {transition_name!r}",
                        )

                new_state = transition_def["to_state"]

                evt = _append_transition_event(
                    conn,
                    work_item_id=work_item_id,
                    actor_id=actor_id,
                    actor_kind=actor_kind,
                    actor_metadata=actor_metadata,
                    key_set=self._keys,
                    transition_name=transition_name,
                    new_state=new_state,
                    payload=payload,
                    event_id=event_id,
                    expected_event_seq=expected_event_seq,
                    custom_fields_update=custom_fields,
                    release_claim=True,
                )

            self._metrics.inc("events_appended", self._project)
            self._metrics.inc("transitions_accepted", self._project)
            timer.log("ok", work_item_id=str(work_item_id), transition=transition_name)
            return evt
        except SubstrateError as e:
            if e.code in (ErrorCode.INVALID_TRANSITION, ErrorCode.ROLE_NOT_PERMITTED):
                self._metrics.inc("transitions_rejected", self._project)
            timer.log("rejected", work_item_id=str(work_item_id))
            raise

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
        with self._mgr.transaction() as conn:
            if work_item_id is not None:
                return _read_by_work_item(conn, work_item_id, limit=limit, before_seq=before_seq)
            if actor_id is not None:
                return _read_by_actor(conn, actor_id, limit=limit)
            if start is not None and end is not None:
                return _read_by_range(conn, start, end, limit=limit)
            if transition is not None:
                return _read_by_transition(conn, transition, limit=limit)
        return []

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
        cursor: tuple[int, uuid.UUID] | None = None,
        page_size: int = 100,
    ) -> QueryPage[WorkItem]:
        from ._work_items import query_work_items as _query

        with self._mgr.transaction() as conn:
            return _query(
                conn,
                workflow_name=workflow_name,
                workflow_version=workflow_version,
                work_item_types=work_item_types,
                current_states=current_states,
                claimed_by=claimed_by,
                claimable_now=claimable_now,
                needs_review=needs_review,
                has_link_type=has_link_type,
                cursor=cursor,
                page_size=page_size,
            )

    def get_work_item(self, work_item_id: uuid.UUID) -> WorkItem | None:
        from ._work_items import get_work_item as _get

        with self._mgr.transaction() as conn:
            return _get(conn, work_item_id)

    def acquire_claim(
        self,
        work_item_id: uuid.UUID,
        actor_id: str,
        ttl_seconds: int = 300,
        *,
        idempotency_key: uuid.UUID | None = None,
    ) -> Claim:
        from ._claims import acquire_claim as _acquire

        timer = OpTimer(self._project, "acquire_claim")
        try:
            with self._mgr.transaction() as conn:
                claim = _acquire(
                    conn, work_item_id, actor_id, ttl_seconds,
                    self._keys, idempotency_key,
                )

            self._metrics.inc("claims_acquired", self._project)
            timer.log("ok", work_item_id=str(work_item_id))
            return claim
        except SubstrateError as e:
            if e.code == ErrorCode.CLAIM_CONTESTED:
                timer.log("rejected", work_item_id=str(work_item_id))
            else:
                timer.log("error")
            raise

    def heartbeat_claim(
        self,
        work_item_id: uuid.UUID,
        actor_id: str,
        ttl_seconds: int = 300,
        *,
        expected_attempt_number: int | None = None,
    ) -> Claim:
        from ._claims import heartbeat_claim as _heartbeat

        timer = OpTimer(self._project, "heartbeat_claim")
        try:
            with self._mgr.transaction() as conn:
                claim = _heartbeat(
                    conn, work_item_id, actor_id, ttl_seconds,
                    expected_attempt_number=expected_attempt_number,
                )

            timer.log("ok", work_item_id=str(work_item_id))
            return claim
        except SubstrateError:
            timer.log("error")
            raise

    def release_claim(
        self,
        work_item_id: uuid.UUID,
        actor_id: str,
    ) -> None:
        from ._claims import release_claim as _release

        timer = OpTimer(self._project, "release_claim")
        try:
            with self._mgr.transaction() as conn:
                _release(conn, work_item_id, actor_id, self._keys)

            self._metrics.inc("claims_released", self._project)
            timer.log("ok", work_item_id=str(work_item_id))
        except SubstrateError:
            timer.log("error")
            raise

    def sweep_expired_claims(self) -> int:
        from ._claims import sweep_expired_claims as _sweep

        with self._mgr.transaction() as conn:
            count = _sweep(conn, self._keys)
        self._metrics.inc("claims_expired", self._project, amount=count)
        return count

    def create_link(
        self,
        from_work_item_id: uuid.UUID,
        to_work_item_id: uuid.UUID,
        link_type: str,
        actor_id: str,
        actor_kind: str = "agent",
        actor_metadata: dict | None = None,
        *,
        idempotency_key: uuid.UUID | None = None,
    ) -> Link:
        from ._links import create_link as _create

        timer = OpTimer(self._project, "create_link")
        try:
            with self._mgr.transaction() as conn:
                link = _create(
                    conn,
                    from_work_item_id=from_work_item_id,
                    to_work_item_id=to_work_item_id,
                    link_type=link_type,
                    actor_id=actor_id,
                    actor_kind=actor_kind,
                    actor_metadata=actor_metadata,
                    key_set=self._keys,
                    idempotency_key=idempotency_key,
                )

            self._metrics.inc("links_created", self._project)
            timer.log("ok")
            return link
        except SubstrateError:
            timer.log("error")
            raise

    def remove_link(
        self,
        from_work_item_id: uuid.UUID,
        to_work_item_id: uuid.UUID,
        link_type: str,
        actor_id: str,
        actor_kind: str = "agent",
        actor_metadata: dict | None = None,
        *,
        idempotency_key: uuid.UUID | None = None,
    ) -> None:
        from ._links import remove_link as _remove

        timer = OpTimer(self._project, "remove_link")
        try:
            with self._mgr.transaction() as conn:
                _remove(
                    conn,
                    from_work_item_id=from_work_item_id,
                    to_work_item_id=to_work_item_id,
                    link_type=link_type,
                    actor_id=actor_id,
                    actor_kind=actor_kind,
                    actor_metadata=actor_metadata,
                    key_set=self._keys,
                    idempotency_key=idempotency_key,
                )

            self._metrics.inc("links_removed", self._project)
            timer.log("ok")
        except SubstrateError:
            timer.log("error")
            raise

    def replay(self) -> ReplayReport:
        from ._replay import replay as _replay

        timer = OpTimer(self._project, "replay")
        try:
            with self._mgr.transaction() as conn:
                report = _replay(conn, self._mgr.schema, self._project, self._keys)

            if report.replayed_drift > 0:
                self._metrics.inc("replay_drift_count", self._project, amount=report.replayed_drift)
            timer.log(
                "ok",
                detail=(
                    f"ok={report.replayed_ok} drift={report.replayed_drift} "
                    f"halted={report.halted}"
                ),
            )
            return report
        except Exception:
            timer.log("error")
            raise
