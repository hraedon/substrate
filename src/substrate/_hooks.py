from __future__ import annotations

import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FuturesTimeout
from datetime import UTC, datetime, timedelta

import psycopg
import structlog
from psycopg.sql import SQL, Identifier, Literal

from ._errors import ErrorCode, SubstrateError
from ._events import append_event
from ._keys import KeySet
from ._observability import Metrics
from ._types import HookContext, ValidatorContext

log = structlog.get_logger()


def run_validator(
    validator_name: str,
    handler,
    ctx: ValidatorContext,
    timeout: float = 5.0,
) -> None:
    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(handler, ctx)
        try:
            future.result(timeout=timeout)
        except FuturesTimeout:
            raise SubstrateError(
                ErrorCode.VALIDATOR_TIMEOUT,
                f"Validator {validator_name!r} timed out after {timeout}s",
            )
        except SubstrateError:
            raise
        except Exception as e:
            raise SubstrateError(
                ErrorCode.VALIDATOR_FAILED,
                f"Validator {validator_name!r} failed: {e}",
            )


def enqueue_hooks(
    conn: psycopg.Connection,
    event_id: uuid.UUID,
    work_item_id: uuid.UUID,
    hook_names: list[str],
    transition: str | None,
    event_payload: dict | None,
    channel: str,
    max_retries: int = 3,
) -> None:
    import psycopg.types.json

    for hook_name in hook_names:
        conn.execute(
            SQL(
                "INSERT INTO hook_queue (event_id, hook_name, hook_type, payload, max_retries) "
                "VALUES (%s, %s, 'async', %s, %s)"
            ),
            [
                event_id,
                hook_name,
                psycopg.types.json.Jsonb({
                    "work_item_id": str(work_item_id),
                    "transition": transition,
                    "event_payload": event_payload,
                }),
                max_retries,
            ],
        )

    if hook_names:
        # NOTIFY payload does not support bind parameters; Literal produces
        # a properly-escaped SQL string literal for the event_id.
        conn.execute(
            SQL("NOTIFY {}, {}").format(Identifier(channel), Literal(str(event_id))),
        )


def poll_and_process_hooks(
    conn: psycopg.Connection,
    handlers: dict,
    key_set: KeySet,
    metrics: Metrics | None,
    project: str,
) -> int:
    conn.execute(
        SQL(
            "UPDATE hook_queue SET status = 'pending', updated_at = now() "
            "WHERE status = 'in_progress' AND updated_at < now() - interval '5 minutes'"
        ),
    )

    rows = conn.execute(
        SQL(
            "SELECT id, event_id, hook_name, payload, retry_count, max_retries "
            "FROM hook_queue "
            "WHERE status = 'pending' "
            "AND (next_retry_at IS NULL OR next_retry_at <= now()) "
            "ORDER BY id LIMIT 100"
        ),
    ).fetchall()

    processed = 0
    for row in rows:
        hook_id = row["id"]
        hook_name = row["hook_name"]
        handler = handlers.get(hook_name)

        if handler is None:
            log.warning("hooks.handler_not_registered", hook_name=hook_name)
            _move_to_dead_letter(conn, row, f"Handler {hook_name!r} not registered", key_set)
            if metrics:
                metrics.inc("hooks_dead_lettered", project)
            continue

        payload = row["payload"] or {}
        raw_wi_id = payload.get("work_item_id")
        if raw_wi_id is None:
            log.error("hooks.missing_work_item_id", hook_id=hook_id, hook_name=hook_name)
            _move_to_dead_letter(conn, row, "work_item_id missing from payload", key_set)
            if metrics:
                metrics.inc("hooks_dead_lettered", project)
            continue
        ctx = HookContext(
            hook_queue_id=hook_id,
            event_id=row["event_id"],
            work_item_id=uuid.UUID(raw_wi_id),
            hook_name=hook_name,
            transition=payload.get("transition"),
            payload=payload.get("event_payload"),
        )

        conn.execute(
            SQL("UPDATE hook_queue SET status = 'in_progress', updated_at = now() WHERE id = %s"),
            [hook_id],
        )

        try:
            with conn.transaction():
                handler(ctx)
                conn.execute(
                    SQL(
                        "UPDATE hook_queue SET status = 'completed', updated_at = now() "
                        "WHERE id = %s"
                    ),
                    [hook_id],
                )
                if metrics:
                    metrics.inc("hooks_succeeded", project)
            processed += 1
        except Exception as e:
            retry_count = row["retry_count"] + 1
            max_retries = row["max_retries"]

            if retry_count >= max_retries:
                _move_to_dead_letter(conn, row, str(e), key_set)
                if metrics:
                    metrics.inc("hooks_dead_lettered", project)
            else:
                backoff = timedelta(seconds=min(2 ** retry_count, 60))
                next_retry = datetime.now(UTC) + backoff
                conn.execute(
                    SQL(
                        "UPDATE hook_queue SET status = 'pending', retry_count = %s, "
                        "next_retry_at = %s, updated_at = now() WHERE id = %s"
                    ),
                    [retry_count, next_retry, hook_id],
                )
                if metrics:
                    metrics.inc("hooks_failed", project)
            log.warning("hooks.handler_failed", hook_name=hook_name, error=str(e))

    return processed


def _move_to_dead_letter(
    conn: psycopg.Connection,
    hook_row: dict,
    error_message: str,
    key_set: KeySet,
) -> None:
    import psycopg.types.json

    conn.execute(
        SQL(
            "INSERT INTO hook_dead_letter "
            "(event_id, hook_name, hook_type, payload, retry_count, error_message, "
            "original_hook_queue_id) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s)"
        ),
        [
            hook_row["event_id"],
            hook_row["hook_name"],
            "async",
            (
                psycopg.types.json.Jsonb(hook_row["payload"])
                if hook_row["payload"]
                else None
            ),
            hook_row["retry_count"],
            error_message,
            hook_row["id"],
        ],
    )

    conn.execute(
        SQL("DELETE FROM hook_queue WHERE id = %s"),
        [hook_row["id"]],
    )

    evt_row = conn.execute(
        SQL(
            "SELECT work_item_id, workflow_name, workflow_version "
            "FROM events WHERE event_id = %s"
        ),
        [hook_row["event_id"]],
    ).fetchone()

    if evt_row is not None:
        append_event(
            conn=conn,
            work_item_id=evt_row["work_item_id"],
            actor_id="system",
            actor_kind="system",
            actor_metadata=None,
            key_set=key_set,
            workflow_name=evt_row["workflow_name"],
            workflow_version=evt_row["workflow_version"],
            transition="hook_dead_lettered",
            payload={
                "hook_name": hook_row["hook_name"],
                "hook_queue_id": hook_row["id"],
                "error_message": error_message,
            },
            event_id=uuid.uuid4(),
        )


def requeue_dead_lettered_hook(
    conn: psycopg.Connection,
    dead_letter_id: int,
    channel: str,
    key_set: KeySet,
) -> None:
    import psycopg.types.json

    row = conn.execute(
        SQL("SELECT * FROM hook_dead_letter WHERE id = %s"),
        [dead_letter_id],
    ).fetchone()

    if row is None:
        raise SubstrateError(
            ErrorCode.HOOK_NOT_FOUND,
            f"Dead-lettered hook {dead_letter_id} not found",
        )

    conn.execute(
        SQL(
            "INSERT INTO hook_queue "
            "(event_id, hook_name, hook_type, payload, retry_count, max_retries) "
            "VALUES (%s, %s, 'async', %s, 0, 3)"
        ),
        [
            row["event_id"],
            row["hook_name"],
            psycopg.types.json.Jsonb(row["payload"]) if row["payload"] else None,
        ],
    )

    conn.execute(
        SQL("DELETE FROM hook_dead_letter WHERE id = %s"),
        [dead_letter_id],
    )

    conn.execute(
        SQL("NOTIFY {}, {}").format(Identifier(channel), Literal(str(row["event_id"]))),
    )


class HookConsumer:
    def __init__(
        self,
        dsn: str,
        schema: str,
        project: str,
        handlers: dict,
        key_set: KeySet,
        metrics: Metrics | None,
        poll_interval: float = 30.0,
    ) -> None:
        self._dsn = dsn
        self._schema = schema
        self._project = project
        self._handlers = handlers
        self._key_set = key_set
        self._metrics = metrics
        self._poll_interval = poll_interval
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._channel = f"substrate_hooks_{schema}"

    def start(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        log.info("hooks.consumer_started", project=self._project)

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=5)
            self._thread = None
        log.info("hooks.consumer_stopped", project=self._project)

    @property
    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def _connect(self):
        from psycopg.rows import dict_row

        conn = psycopg.connect(
            self._dsn,
            row_factory=dict_row,
            autocommit=True,
        )
        conn.execute(
            SQL("SET search_path TO {}").format(Identifier(self._schema))
        )
        conn.execute(SQL("LISTEN {}").format(Identifier(self._channel)))
        return conn

    def _run(self) -> None:
        max_reconnect_attempts = 10
        reconnect_backoff_base = 2.0
        reconnect_attempts = 0

        try:
            conn = self._connect()
        except Exception as e:
            log.error("hooks.initial_connect_failed", error=str(e))
            return

        try:
            while not self._stop.is_set():
                try:
                    for _notify in conn.notifies(timeout=self._poll_interval):
                        if self._stop.is_set():
                            break
                except psycopg.OperationalError as e:
                    if self._stop.is_set():
                        break
                    reconnect_attempts += 1
                    if reconnect_attempts > max_reconnect_attempts:
                        log.error(
                            "hooks.reconnect_exhausted",
                            attempts=reconnect_attempts,
                            error=str(e),
                        )
                        break
                    backoff = min(
                        reconnect_backoff_base * (2 ** (reconnect_attempts - 1)),
                        60.0,
                    )
                    log.warning(
                        "hooks.connection_lost",
                        attempt=reconnect_attempts,
                        backoff=backoff,
                        error=str(e),
                    )
                    try:
                        conn.close()
                    except Exception:
                        pass
                    time.sleep(backoff)
                    try:
                        conn = self._connect()
                        successful_attempt = reconnect_attempts
                        reconnect_attempts = 0
                        log.info("hooks.reconnected", attempt=successful_attempt)
                    except Exception as ce:
                        log.error("hooks.reconnect_failed", error=str(ce))
                    continue

                if self._stop.is_set():
                    break

                reconnect_attempts = 0

                try:
                    with conn.transaction():
                        poll_and_process_hooks(
                            conn,
                            self._handlers,
                            self._key_set,
                            self._metrics,
                            self._project,
                        )
                except psycopg.OperationalError as e:
                    log.error("hooks.poll_connection_error", error=str(e))
                except Exception as e:
                    log.error("hooks.poll_error", error=str(e))
        finally:
            try:
                conn.close()
            except Exception:
                pass
