from __future__ import annotations

import uuid
from collections.abc import Callable
from datetime import datetime
from pathlib import Path

import psycopg.types.json
import structlog

from ._connection import ConnectionManager
from ._contract import (
    Jsonb as _Jsonb,
)
from ._contract import (
    check_append_blocked as _check_append_blocked,
)
from ._contract import (
    check_reserved_transition as _check_reserved_transition,
)
from ._contract import (
    check_role_gating as _check_role_gating,
)
from ._contract import (
    resolve_transition as _resolve_transition,
)
from ._contract import (
    validate_mutation_params as _validate_mutation_params,
)
from ._contract import (
    validate_read_events_filters as _validate_read_events_filters,
)
from ._errors import ErrorCode, SubstrateError
from ._event_store import PostgresEventStore as _PostgresEventStore
from ._event_store import append_event as _store_append_event
from ._events import (
    append_transition_event as _append_transition_event,
)
from ._integrity import SUBSTRATE_VERSION, check_integrity
from ._keys import KeySet
from ._migrations import run_migrations
from ._observability import Metrics, OpTimer
from ._types import (
    ActorKind as ActorKind,
)
from ._types import (
    ActorMetadata as ActorMetadata,
)
from ._types import (
    ActorRole,
    Claim,
    ConnectionInfo,
    DeadLetterEntry,
    Event,
    Link,
    QueryPage,
    ReplayReport,
    ValidatorContext,
    WorkflowVersion,
    WorkItem,
)
from ._types import (
    HookContext as HookContext,
)
from ._types import (
    ReplayReportEntry as ReplayReportEntry,
)
from ._types import (
    ValidationError as ValidationError,
)
from ._types import (
    ValidationResult as ValidationResult,
)
from ._types import (
    WorkflowDefinition as WorkflowDefinition,
)
from ._workflow import parse_and_validate
from ._workflow import parse_file as parse_file
from ._workflow import validate_yaml as validate_yaml

log = structlog.get_logger()


class Substrate:
    """Coordination and durable state for agent pipelines over Postgres.

    One Substrate instance owns one logical project namespace. Use
    ``create_project`` to bootstrap a new project, then connect via the
    constructor for subsequent sessions.
    """

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
        """Connect to an existing project.

        Args:
            dsn: Postgres connection string.
            project: Project (schema) name.
            hmac_key_path: Path to HMAC key-set JSON file (required).
            pool_min: Minimum connection-pool size.
            pool_max: Maximum connection-pool size.
            prometheus_registry: Optional ``prometheus_client.CollectorRegistry``.

        Raises:
            SubstrateError: If migrations are pending or workflow versions are
                incompatible.
        """
        if hmac_key_path is None:
            raise SubstrateError(
                ErrorCode.UNKNOWN_KEY_ID,
                "hmac_key_path is required",
            )
        self._mgr = ConnectionManager(dsn, project, pool_min=pool_min, pool_max=pool_max)
        try:
            self._mgr.open()
            self._mgr.ensure_schema()
            self._keys = KeySet(hmac_key_path)
            self._metrics = Metrics(registry=prometheus_registry)
            self._project = project
            self._validators: dict[str, Callable] = {}
            self._hook_handlers: dict[str, Callable] = {}
            self._hook_channel = f"substrate_hooks_{self._mgr.schema}"
            self._hook_consumer = None
            from ._hooks import HookConsumer

            self._hook_consumer = HookConsumer(
                dsn=self._mgr.dsn,
                schema=self._mgr.schema,
                project=project,
                handlers=self._hook_handlers,
                key_set=self._keys,
                metrics=self._metrics,
            )
            check_integrity(self._mgr)
        except:
            self._mgr.close()
            raise
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
        """Create a new project: schema, migrations, and return a connected handle.

        Args:
            dsn: Postgres connection string.
            project: Project (schema) name.
            hmac_key_path: Path to HMAC key-set JSON file.
            pool_min: Minimum connection-pool size.
            pool_max: Maximum connection-pool size.
            prometheus_registry: Optional ``prometheus_client.CollectorRegistry``.

        Returns:
            A connected ``Substrate`` instance.
        """
        mgr = ConnectionManager(dsn, project, pool_min=pool_min, pool_max=pool_max)
        try:
            mgr.open()
            mgr.create_schema()
            run_migrations(mgr)
        finally:
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
        """Stop hook consumer (if running) and release the connection pool."""
        if self._hook_consumer is not None and self._hook_consumer.is_running:
            self._hook_consumer.stop()
        if self._mgr is not None:
            self._mgr.close()
            self._mgr = None
        log.info("substrate.disconnected", project=self._project)

    @property
    def project(self) -> str:
        return self._project

    @property
    def connection_info(self) -> ConnectionInfo:
        """Connection details (no credentials) for downstream test infrastructure.

        Returns:
            ``ConnectionInfo`` with host, port, database, and project.
        """
        from urllib.parse import urlparse

        parsed = urlparse(self._mgr.dsn)
        return ConnectionInfo(
            host=parsed.hostname,
            port=parsed.port,
            database=parsed.path.lstrip("/") if parsed.path else None,
            project=self._project,
        )

    @property
    def substrate_version(self) -> str:
        return SUBSTRATE_VERSION

    @property
    def prometheus_registry(self):
        return self._metrics.registry

    def register_validator(self, name: str, handler: Callable) -> None:
        """Register a sync transition validator. Blocks the transaction on failure.

        Args:
            name: Must match a ``validator`` field in a workflow transition.
            handler: ``Callable[[ValidatorContext], None]``. Must complete
                within 5 seconds. Must not perform I/O (best-effort AST
                check at registration time).
        """
        from ._hooks import check_validator_io_safety

        check_validator_io_safety(handler, name)
        updated = dict(self._validators)
        updated[name] = handler
        self._validators = updated

    def register_hook_handler(self, name: str, handler: Callable) -> None:
        """Register an async hook handler dispatched via the hook queue.

        Args:
            name: Must match a hook name listed in a workflow transition's ``hooks``.
            handler: ``Callable[[HookContext], None]``.
        """
        updated = dict(self._hook_handlers)
        updated[name] = handler
        self._hook_handlers = updated
        self._hook_consumer._handlers = updated

    def start_hook_consumer(self) -> None:
        """Start a background thread that LISTENs and polls the hook queue."""
        self._hook_consumer.start()

    def stop_hook_consumer(self) -> None:
        """Stop the background hook consumer thread."""
        self._hook_consumer.stop()

    def poll_hooks(self) -> int:
        """Manually drain and process pending hooks from the queue.

        Returns:
            Number of hooks processed.
        """
        from ._hooks import poll_and_process_hooks

        with self._mgr.transaction() as conn:
            return poll_and_process_hooks(
                conn, self._hook_handlers, self._keys, self._metrics, self._project,
            )

    def register_workflow(
        self,
        yaml_content: str,
    ) -> WorkflowVersion:
        """Parse, validate, and register a workflow definition.

        Idempotent: re-registering the same name+version with identical content
        returns the existing entry. Different content raises
        ``WORKFLOW_VERSION_CONFLICT``.

        Args:
            yaml_content: Workflow YAML string.

        Returns:
            The registered ``WorkflowVersion``.

        Raises:
            SubstrateError: ``WORKFLOW_VALIDATION_FAILED``,
                ``WORKFLOW_SEMANTIC_ERROR``, ``WORKFLOW_VERSION_CONFLICT``.
        """
        timer = OpTimer(self._project, "register_workflow")
        try:
            wf = parse_and_validate(yaml_content)
            from ._workflow import compute_content_hash, compute_content_hash_from_dict

            content_hash = compute_content_hash(wf)
            with self._mgr.transaction() as conn:
                from psycopg.sql import SQL

                existing = conn.execute(
                    SQL(
                        "SELECT workflow_name, version, substrate_version, registered_at, "
                        "content_hash, definition "
                        "FROM workflow_registry WHERE workflow_name = %s AND version = %s"
                    ),
                    [wf.name, wf.version],
                ).fetchone()
                if existing is not None:
                    existing_hash = existing["content_hash"]
                    if existing_hash is None:
                        existing_hash = compute_content_hash_from_dict(existing["definition"])
                        conn.execute(
                            SQL(
                                "UPDATE workflow_registry SET content_hash = %s "
                                "WHERE workflow_name = %s AND version = %s"
                            ),
                            [existing_hash, wf.name, wf.version],
                        )
                    if existing_hash != content_hash:
                        raise SubstrateError(
                            ErrorCode.WORKFLOW_VERSION_CONFLICT,
                            f"Workflow {wf.name!r} v{wf.version} already registered "
                            f"with different content",
                            detail={"workflow_name": wf.name, "version": wf.version},
                        )
                    timer.log("ok", detail=f"idempotent:{wf.name} v{wf.version}")
                    return WorkflowVersion(
                        name=existing["workflow_name"],
                        version=existing["version"],
                        substrate_version=existing["substrate_version"],
                        registered_at=existing["registered_at"],
                    )

                row = conn.execute(
                    SQL(
                        "INSERT INTO workflow_registry "
                        "(workflow_name, version, substrate_version, definition, content_hash) "
                        "VALUES (%s, %s, %s, %s, %s) "
                        "RETURNING registered_at"
                    ),
                    [
                        wf.name, wf.version, wf.substrate_version,
                        psycopg.types.json.Jsonb(wf.to_dict()),
                        content_hash,
                    ],
                ).fetchone()

            self._metrics.inc("workflows_registered", self._project)
            timer.log("ok", detail=wf.name)
            return WorkflowVersion(
                name=wf.name,
                version=wf.version,
                substrate_version=wf.substrate_version,
                registered_at=row["registered_at"],
            )
        except SubstrateError:
            timer.log("error")
            raise

    def register_workflow_file(
        self,
        path: str | Path,
    ) -> WorkflowVersion:
        """Register a workflow from a file path. Convenience wrapper around
        ``register_workflow``.

        Args:
            path: Path to a workflow YAML file.

        Returns:
            The registered ``WorkflowVersion``.
        """
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
        """Create a new work item in the given workflow.

        Args:
            workflow_name: Name of a registered workflow.
            work_item_type: Must be declared in the workflow definition.
            actor_id: Authenticated actor identifier.
            actor_kind: ``"agent"`` | ``"human"`` | ``"system"``.
            actor_metadata: Optional JSONB metadata for audit.
            custom_fields: Initial field values validated against the type schema.
            not_before: Gate timestamp; claims before this time are rejected.
            event_id: Optional UUIDv4 for idempotency.

        Returns:
            Tuple of ``(WorkItem, Event)``.

        Raises:
            SubstrateError: ``WORKFLOW_NOT_REGISTERED``,
                ``WORK_ITEM_TYPE_NOT_DECLARED``, ``CUSTOM_FIELD_VIOLATION``.
        """
        timer = OpTimer(self._project, "create_work_item")
        try:
            _validate_mutation_params(
                actor_kind=actor_kind,
                event_id=event_id,
                not_before=not_before,
            )
            from ._work_items import create_work_item as _create

            with self._mgr.transaction() as conn:
                wi, evt = _create(
                    conn,
                    workflow_name=workflow_name,
                    work_item_type=work_item_type,
                    actor_id=actor_id,
                    actor_kind=actor_kind,
                    actor_metadata=_Jsonb(actor_metadata) if actor_metadata is not None else None,
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
        """Append a free-form event to the work-item log.

        Rejects transitions that match a workflow-defined transition name — use
        ``transition()`` for state changes.

        Args:
            work_item_id: Target work item.
            actor_id: Authenticated actor.
            actor_kind: ``"agent"`` | ``"human"`` | ``"system"``.
            actor_metadata: Optional JSONB metadata.
            transition: Free-form transition label (must not collide with workflow).
            payload: Optional JSONB payload.
            event_id: UUIDv4 idempotency key.
            expected_event_seq: Optimistic-concurrency check.

        Returns:
            The appended ``Event``.

        Raises:
            SubstrateError: ``WORK_ITEM_NOT_FOUND``,
                ``TRANSITION_VIA_APPEND_BLOCKED``,
                ``IDEMPOTENCY_COLLISION_WITH_DIFFERENT_PAYLOAD``,
                ``CONCURRENT_MODIFICATION``.
        """
        timer = OpTimer(self._project, "append_event")
        try:
            if event_id is None:
                event_id = uuid.uuid4()
            _validate_mutation_params(
                actor_kind=actor_kind,
                event_id=event_id,
            )

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
                    _check_reserved_transition(transition)
                    wf_data = conn.execute(
                        "SELECT definition FROM workflow_registry "
                        "WHERE workflow_name = %s AND version = %s",
                        [wi_row["workflow_name"], wi_row["workflow_version"]],
                    ).fetchone()
                    if wf_data is not None:
                        _check_append_blocked(
                            wf_data["definition"].get("transitions", []),
                            transition,
                            wi_row["workflow_name"],
                        )

                store = _PostgresEventStore(conn, self._keys)
                evt = _store_append_event(
                    store,
                    work_item_id=work_item_id,
                    actor_id=actor_id,
                    actor_kind=actor_kind,
                    actor_metadata=_Jsonb(actor_metadata) if actor_metadata is not None else None,
                    workflow_name=wi_row["workflow_name"],
                    workflow_version=wi_row["workflow_version"],
                    transition=transition,
                    payload=_Jsonb(payload) if payload is not None else None,
                    event_id=event_id,
                    expected_event_seq=expected_event_seq,
                    key_set=self._keys,
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
        """Execute a workflow-defined state transition.

        Validates the transition against the pinned workflow version, checks
        role gating, runs sync validators, and releases any active claim.

        Args:
            work_item_id: Target work item.
            transition_name: Must match a transition in the pinned workflow version.
            actor_id: Authenticated actor.
            actor_kind: ``"agent"`` | ``"human"`` | ``"system"``.
            actor_metadata: Must include ``"role"`` when roles are enforced.
            payload: Optional JSONB payload.
            custom_fields: Partial update to custom fields (validated against schema).
            event_id: UUIDv4 idempotency key.
            expected_event_seq: Optimistic-concurrency check.

        Returns:
            The appended ``Event``.

        Raises:
            SubstrateError: ``INVALID_TRANSITION``, ``ROLE_NOT_PERMITTED``,
                ``ACTOR_ROLE_NOT_AUTHORIZED``, ``CUSTOM_FIELD_VIOLATION``,
                ``VALIDATOR_TIMEOUT``, ``VALIDATOR_FAILED``.
        """
        timer = OpTimer(self._project, "transition")
        try:
            if event_id is None:
                event_id = uuid.uuid4()
            _validate_mutation_params(
                actor_kind=actor_kind,
                event_id=event_id,
            )

            with self._mgr.transaction() as conn:
                wi_row = conn.execute(
                    "SELECT workflow_name, workflow_version, current_state, "
                    "work_item_type, custom_fields "
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
                transition_def = _resolve_transition(
                    defn.get("transitions", []),
                    wi_row["current_state"],
                    transition_name,
                    wi_row["workflow_name"],
                    wi_row["workflow_version"],
                )

                _check_role_gating(
                    transition_def.get("allowed_roles", []),
                    actor_metadata,
                    transition_name,
                )
                if transition_def.get("allowed_roles"):
                    role = (actor_metadata or {}).get("role")
                    from ._actor_roles import check_actor_role_authorized
                    check_actor_role_authorized(conn, actor_id, role)

                if custom_fields:
                    from ._workflow import validate_field_update, validate_work_item_refs
                    validate_field_update(defn, wi_row["work_item_type"], custom_fields)
                    validate_work_item_refs(conn, defn, wi_row["work_item_type"], custom_fields)

                new_state = transition_def["to_state"]

                validator_name = transition_def.get("validator")
                if validator_name:
                    handler = self._validators.get(validator_name)
                    if handler is not None:
                        from ._hooks import run_validator

                        ctx = ValidatorContext(
                            work_item_id=work_item_id,
                            workflow_name=wi_row["workflow_name"],
                            workflow_version=wi_row["workflow_version"],
                            work_item_type=wi_row["work_item_type"],
                            current_state=wi_row["current_state"],
                            new_state=new_state,
                            transition_name=transition_name,
                            payload=payload,
                            custom_fields=wi_row["custom_fields"] or {},
                            actor_id=actor_id,
                            actor_metadata=actor_metadata,
                        )
                        try:
                            conn.execute("SET LOCAL statement_timeout = '5s'")
                            run_validator(
                                validator_name, handler, ctx,
                                metrics=self._metrics, project=self._project,
                            )
                            conn.execute("SET LOCAL statement_timeout = 0")
                            self._metrics.inc("validators_succeeded", self._project)
                        except SubstrateError as e:
                            if e.code == ErrorCode.VALIDATOR_TIMEOUT:
                                self._metrics.inc("validators_timed_out", self._project)
                            else:
                                self._metrics.inc("validators_failed", self._project)
                            raise
                    else:
                        log.warning(
                            "validator.not_registered",
                            validator=validator_name,
                            transition=transition_name,
                        )

                evt = _append_transition_event(
                    conn,
                    work_item_id=work_item_id,
                    actor_id=actor_id,
                    actor_kind=actor_kind,
                    actor_metadata=_Jsonb(actor_metadata) if actor_metadata is not None else None,
                    key_set=self._keys,
                    transition_name=transition_name,
                    new_state=new_state,
                    payload=_Jsonb(payload) if payload is not None else None,
                    event_id=event_id,
                    expected_event_seq=expected_event_seq,
                    custom_fields_update=custom_fields,
                    release_claim=True,
                )

                hook_names = transition_def.get("hooks", [])
                if hook_names:
                    from ._hooks import enqueue_hooks

                    hook_defaults = defn.get("hook_defaults") or {}
                    wf_max_retries = hook_defaults.get("max_retries", 3)

                    enqueue_hooks(
                        conn,
                        event_id=evt.event_id,
                        work_item_id=work_item_id,
                        hook_names=hook_names,
                        transition=transition_name,
                        event_payload=payload,
                        channel=self._hook_channel,
                        max_retries=wf_max_retries,
                    )
                    self._metrics.inc("hooks_dispatched", self._project, amount=len(hook_names))

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
        """Read events with structured filters. Multiple filter dimensions
        may be combined; results satisfy all provided criteria.

        Ordering depends on which filters are active:

        - ``work_item_id`` provided: ascending by ``event_seq``.
        - Time range (``start``/``end``) without ``work_item_id``:
          ascending by ``(timestamp, event_seq)``.
        - Otherwise: descending by ``(timestamp, event_seq)``.

        Args:
            work_item_id: Filter by work item (supports ``before_seq`` pagination).
            actor_id: Filter by actor.
            start: Range-start timestamp (requires ``end``).
            end: Range-end timestamp (requires ``start``).
            transition: Filter by transition name.
            limit: Maximum events to return.
            before_seq: Paginate backwards from this ``event_seq`` (requires
                ``work_item_id``).

        Returns:
            List of ``Event`` objects.

        Raises:
            SubstrateError: ``INVALID_FILTER``.
        """
        _validate_read_events_filters(before_seq, work_item_id, start, end)
        from ._events import read_events_composite

        with self._mgr.transaction() as conn:
            return read_events_composite(
                conn,
                work_item_id=work_item_id,
                actor_id=actor_id,
                start=start,
                end=end,
                transition=transition,
                limit=limit,
                before_seq=before_seq,
            )

    def read_events_since(
        self,
        work_item_id: uuid.UUID,
        after_seq: int,
        *,
        limit: int = 100,
    ) -> list[Event]:
        """Read events for a work item with event_seq strictly greater than
        the given cursor.

        This is the primitive for hook-miss recovery: a runner persists the
        highest event_seq it has processed and calls ``read_events_since``
        on startup to catch up.

        Args:
            work_item_id: Target work item.
            after_seq: Return events with ``event_seq > after_seq``.
            limit: Maximum events to return (default 100).

        Returns:
            Events in ascending ``event_seq`` order.
        """
        from ._events import read_events_by_work_item as _read

        with self._mgr.transaction() as conn:
            return _read(conn, work_item_id, limit=limit, after_seq=after_seq)

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
        custom_field_filters: dict[str, object] | None = None,
        cursor: uuid.UUID | None = None,
        page_size: int = 100,
    ) -> QueryPage[WorkItem]:
        """Structured work-item query with cursor-based pagination.

        Args:
            workflow_name: Filter by workflow.
            workflow_version: Filter by pinned version.
            work_item_types: Filter by type names.
            current_states: Filter by current state.
            claimed_by: Filter by claiming actor.
            claimable_now: True = unclaimed and ``not_before`` has passed.
            needs_review: Filter by escalation flag.
            has_link_type: Items with at least one active link of this type.
            custom_field_filters: Equality filters on custom field values.
                All entries must match (AND semantics). Keys not declared on
                the queried work_item_type(s) match no rows (empty result, not
                an error).
            cursor: Continue from a previous page's cursor.
            page_size: Items per page (default 100).

        Returns:
            ``QueryPage[WorkItem]`` with cursor for the next page.
        """
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
                custom_field_filters=custom_field_filters,
                cursor=cursor,
                page_size=page_size,
            )

    def get_work_item(self, work_item_id: uuid.UUID) -> WorkItem | None:
        """Retrieve a single work item by ID.

        Returns:
            The ``WorkItem`` or ``None`` if not found.
        """
        from ._work_items import get_work_item as _get

        with self._mgr.transaction() as conn:
            return _get(conn, work_item_id)

    def acquire_claim(
        self,
        work_item_id: uuid.UUID,
        actor_id: str,
        ttl_seconds: int = 300,
        *,
        event_id: uuid.UUID | None = None,
        actor_kind: str = "agent",
    ) -> Claim:
        """Acquire a durable claim (lease) on a work item.

        Same-actor re-acquire silently extends TTL. Cross-actor acquire on an
        expired claim auto-steals and increments attempt_number.

        Args:
            work_item_id: Target work item.
            actor_id: Claiming actor.
            ttl_seconds: Lease duration in seconds (default 300).
            event_id: UUIDv4 idempotency key.
            actor_kind: Kind of actor (default "agent").

        Returns:
            The ``Claim``.

        Raises:
            SubstrateError: ``CLAIM_CONTESTED``, ``NOT_BEFORE_FUTURE``,
                ``WORK_ITEM_NOT_FOUND``, ``INVALID_ARGUMENT``.
        """
        _validate_mutation_params(
            actor_kind=actor_kind,
            event_id=event_id,
            ttl_seconds=ttl_seconds,
        )
        from ._claims import acquire_claim as _acquire

        timer = OpTimer(self._project, "acquire_claim")
        try:
            with self._mgr.transaction() as conn:
                claim, escalated, stolen = _acquire(
                    conn, work_item_id, actor_id, ttl_seconds,
                    self._keys, event_id, actor_kind,
                )

            self._metrics.inc("claims_acquired", self._project)

            if stolen:
                self._metrics.inc("claims_stolen", self._project)

            if escalated:
                self._metrics.inc("escalations", self._project)

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
        """Renew a claim's TTL. Rejects if claim is held by a different actor.

        Args:
            work_item_id: Target work item.
            actor_id: Must match the current claim holder.
            ttl_seconds: New lease duration.
            expected_attempt_number: Detect stale sessions after claim theft.

        Returns:
            The renewed ``Claim``.

        Raises:
            SubstrateError: ``CLAIM_LOST``, ``CLAIM_NOT_FOUND``,
                ``INVALID_ARGUMENT``.
        """
        _validate_mutation_params(ttl_seconds=ttl_seconds)
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
        *,
        event_id: uuid.UUID | None = None,
        actor_kind: str = "agent",
    ) -> None:
        """Release a claim held by the given actor.

        Args:
            work_item_id: Target work item.
            actor_id: Must match the current claim holder.
            event_id: UUIDv4 idempotency key.
            actor_kind: Kind of actor (default "agent").

        Raises:
            SubstrateError: ``CLAIM_LOST``, ``CLAIM_NOT_FOUND``.
        """
        _validate_mutation_params(
            actor_kind=actor_kind,
            event_id=event_id,
        )
        from ._claims import release_claim as _release

        timer = OpTimer(self._project, "release_claim")
        try:
            with self._mgr.transaction() as conn:
                _release(conn, work_item_id, actor_id, self._keys, event_id, actor_kind)

            self._metrics.inc("claims_released", self._project)
            timer.log("ok", work_item_id=str(work_item_id))
        except SubstrateError:
            timer.log("error")
            raise

    def sweep_expired_claims(self) -> int:
        """Delete all expired claims and emit ``claim_expired`` events.

        Returns:
            Number of expired claims swept.
        """
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
        event_id: uuid.UUID | None = None,
        payload: dict | None = None,
    ) -> Link:
        """Create a typed directed link between two work items.

        Args:
            from_work_item_id: Source work item.
            to_work_item_id: Target work item.
            link_type: Must be declared in the workflow definition.
            actor_id: Authenticated actor.
            actor_kind: ``"agent"`` | ``"human"`` | ``"system"``.
            actor_metadata: Optional JSONB metadata.
            event_id: UUIDv4 idempotency key.
            payload: Optional JSONB payload on the link.

        Returns:
            The created ``Link``.

        Raises:
            SubstrateError: ``LINK_TYPE_NOT_ALLOWED``,
                ``LINK_TARGET_NOT_FOUND``, ``LINK_CROSS_PROJECT``.
        """
        from ._links import create_link as _create

        timer = OpTimer(self._project, "create_link")
        try:
            _validate_mutation_params(
                actor_kind=actor_kind,
                event_id=event_id,
            )
            with self._mgr.transaction() as conn:
                link = _create(
                    conn,
                    from_work_item_id=from_work_item_id,
                    to_work_item_id=to_work_item_id,
                    link_type=link_type,
                    actor_id=actor_id,
                    actor_kind=actor_kind,
                    actor_metadata=_Jsonb(actor_metadata) if actor_metadata is not None else None,
                    key_set=self._keys,
                    event_id=event_id,
                    payload=_Jsonb(payload) if payload is not None else None,
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
        event_id: uuid.UUID | None = None,
    ) -> None:
        """Remove a typed directed link between two work items.

        Args:
            from_work_item_id: Source work item.
            to_work_item_id: Target work item.
            link_type: The link type to remove.
            actor_id: Authenticated actor.
            actor_kind: ``"agent"`` | ``"human"`` | ``"system"``.
            actor_metadata: Optional JSONB metadata.
            event_id: UUIDv4 idempotency key.

        Raises:
            SubstrateError: ``LINK_NOT_FOUND``.
        """
        from ._links import remove_link as _remove

        timer = OpTimer(self._project, "remove_link")
        try:
            _validate_mutation_params(
                actor_kind=actor_kind,
                event_id=event_id,
            )
            with self._mgr.transaction() as conn:
                _remove(
                    conn,
                    from_work_item_id=from_work_item_id,
                    to_work_item_id=to_work_item_id,
                    link_type=link_type,
                    actor_id=actor_id,
                    actor_kind=actor_kind,
                    actor_metadata=_Jsonb(actor_metadata) if actor_metadata is not None else None,
                    key_set=self._keys,
                    event_id=event_id,
                )

            self._metrics.inc("links_removed", self._project)
            timer.log("ok")
        except SubstrateError:
            timer.log("error")
            raise

    def replay(self, *, continue_on_revoked: bool = False) -> ReplayReport:
        """Rebuild projection from the event log and compare with live state.

        Args:
            continue_on_revoked: Skip revoked-key events with warnings instead
                of halting replay.

        Returns:
            ``ReplayReport`` with counts of ok, drift, halted, and warnings.
        """
        from ._replay import (
            drop_old_replay_tables,
        )
        from ._replay import (
            replay as _replay,
        )

        with self._mgr.connect() as conn:
            drop_old_replay_tables(conn, self._mgr.schema)
            conn.commit()

        timer = OpTimer(self._project, "replay")
        try:
            with self._mgr.transaction() as conn:
                report = _replay(
                    conn, self._mgr.schema, self._project, self._keys,
                    continue_on_revoked=continue_on_revoked,
                )

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

    def requeue_dead_lettered_hook(self, dead_letter_id: int) -> None:
        """Re-queue a dead-lettered hook for retry.

        Args:
            dead_letter_id: ID from ``list_dead_lettered_hooks``.

        Raises:
            SubstrateError: ``HOOK_NOT_FOUND``.
        """
        from ._hooks import requeue_dead_lettered_hook as _requeue

        timer = OpTimer(self._project, "requeue_dead_lettered_hook")
        try:
            with self._mgr.transaction() as conn:
                _requeue(conn, dead_letter_id, self._hook_channel, self._keys)

            timer.log("ok", detail=str(dead_letter_id))
        except SubstrateError:
            timer.log("error")
            raise

    def list_dead_lettered_hooks(self) -> list[DeadLetterEntry]:
        """List all dead-lettered hooks in reverse chronological order.

        Returns:
            List of ``DeadLetterEntry`` objects.
        """
        from psycopg.sql import SQL

        with self._mgr.transaction() as conn:
            rows = conn.execute(
                SQL(
                    "SELECT id, event_id, hook_name, hook_type, payload, "
                    "retry_count, error_message, dead_lettered_at, "
                    "original_hook_queue_id "
                    "FROM hook_dead_letter ORDER BY dead_lettered_at DESC"
                ),
            ).fetchall()

        return [
            DeadLetterEntry(
                id=r["id"],
                event_id=r["event_id"],
                hook_name=r["hook_name"],
                hook_type=r["hook_type"],
                payload=r["payload"],
                retry_count=r["retry_count"],
                error_message=r["error_message"],
                dead_lettered_at=r["dead_lettered_at"],
                original_hook_queue_id=r.get("original_hook_queue_id"),
            )
            for r in rows
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
        """Set or clear the ``not_before`` gate on a work item.

        Args:
            work_item_id: Target work item.
            not_before: New gate timestamp, or ``None`` to clear.
            actor_id: Authenticated actor.
            actor_kind: ``"agent"`` | ``"human"`` | ``"system"``.
            actor_metadata: Optional JSONB metadata.
            event_id: UUIDv4 idempotency key.

        Returns:
            The ``not_before_set`` ``Event``.

        Raises:
            SubstrateError: ``WORK_ITEM_NOT_FOUND``.
        """
        from psycopg.sql import SQL

        from ._events import append_event as _append_event
        from ._events import lock_work_item as _lock

        timer = OpTimer(self._project, "update_not_before")
        try:
            if event_id is None:
                event_id = uuid.uuid4()
            _validate_mutation_params(
                actor_kind=actor_kind,
                event_id=event_id,
                not_before=not_before,
            )

            with self._mgr.transaction() as conn:
                wi = _lock(conn, work_item_id)
                if wi is None:
                    raise SubstrateError(
                        ErrorCode.WORK_ITEM_NOT_FOUND,
                        f"Work item {work_item_id} not found",
                    )

                from ._events import check_idempotency as _check_idem

                existing = _check_idem(
                    conn, event_id, actor_id=actor_id, transition="not_before_set",
                    work_item_id=work_item_id,
                )
                if existing is not None:
                    return existing

                conn.execute(
                    SQL("UPDATE work_items_current SET not_before = %s WHERE work_item_id = %s"),
                    [not_before, work_item_id],
                )

                evt = _append_event(
                    conn,
                    work_item_id=work_item_id,
                    actor_id=actor_id,
                    actor_kind=actor_kind,
                    actor_metadata=_Jsonb(actor_metadata) if actor_metadata is not None else None,
                    key_set=self._keys,
                    workflow_name=wi["workflow_name"],
                    workflow_version=wi["workflow_version"],
                    transition="not_before_set",
                    payload=_Jsonb({"not_before": not_before.isoformat() if not_before else None}),
                    event_id=event_id,
                    _prelocked_wi=wi,
                )

            self._metrics.inc("events_appended", self._project)
            timer.log("ok", work_item_id=str(work_item_id))
            return evt
        except SubstrateError:
            timer.log("error")
            raise

    def register_actor_role(self, actor_id: str, role: str) -> None:
        """Register a role for an actor. Enables role enforcement for that actor.

        Args:
            actor_id: Actor identifier.
            role: Role to register.

        Duplicate registrations are silently idempotent.
        """
        from ._actor_roles import register_actor_role as _register

        timer = OpTimer(self._project, "register_actor_role")
        try:
            with self._mgr.transaction() as conn:
                _register(conn, actor_id, role)
            timer.log("ok", detail=f"{actor_id}:{role}")
        except SubstrateError:
            timer.log("error")
            raise

    def unregister_actor_role(self, actor_id: str, role: str) -> None:
        """Remove a role from an actor's registered set.

        Args:
            actor_id: Actor identifier.
            role: Role to remove.

        Raises:
            SubstrateError: ``ACTOR_ROLE_NOT_REGISTERED``.
        """
        from ._actor_roles import unregister_actor_role as _unregister

        timer = OpTimer(self._project, "unregister_actor_role")
        try:
            with self._mgr.transaction() as conn:
                _unregister(conn, actor_id, role)
            timer.log("ok", detail=f"{actor_id}:{role}")
        except SubstrateError:
            timer.log("error")
            raise

    def list_actor_roles(self, actor_id: str | None = None) -> list[ActorRole]:
        """List registered actor roles.

        Args:
            actor_id: Filter by actor, or ``None`` for all actors.

        Returns:
            List of ``ActorRole`` objects.
        """
        from ._actor_roles import list_actor_roles as _list

        with self._mgr.transaction() as conn:
            rows = _list(conn, actor_id=actor_id)
        return [
            ActorRole(
                actor_id=r["actor_id"],
                role=r["role"],
                created_at=r["created_at"],
            )
            for r in rows
        ]

    @staticmethod
    def validate_actor_metadata(
        event: Event,
        expected_schema: dict | None = None,
    ) -> list[str]:
        """Lint helper: validate actor_metadata against recommended fields.

        Args:
            event: Event to inspect.
            expected_schema: Optional JSON Schema to validate against.

        Returns:
            List of issue descriptions (empty if clean).
        """
        from ._lint import validate_actor_metadata as _validate

        return _validate(event, expected_schema)

    @staticmethod
    def actor_metadata_complete(
        events: list[Event],
        expected_keys: list[str],
    ) -> list[Event]:
        """Lint helper: return events missing any of the expected actor_metadata keys.

        Args:
            events: Events to inspect.
            expected_keys: List of keys that must be present in actor_metadata.

        Returns:
            List of events with incomplete actor_metadata.
        """
        from ._lint import actor_metadata_complete as _complete

        return _complete(events, expected_keys)
