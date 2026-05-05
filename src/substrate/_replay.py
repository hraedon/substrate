from __future__ import annotations

from datetime import datetime

import psycopg
from psycopg.sql import SQL, Identifier

from ._keys import KeySet
from ._signing import verify_event
from ._types import ReplayReport

_EVENT_FIELDS = (
    "event_id, work_item_id, event_seq, actor_id, actor_kind, "
    "actor_metadata, key_id, workflow_name, workflow_version, "
    "timestamp, transition, payload, payload_canonical_hash, signature, canonical_envelope"
)


def replay(
    conn: psycopg.Connection,
    schema: str,
    project: str,
    key_set: KeySet,
) -> ReplayReport:
    import uuid as _uuid

    tag = _uuid.uuid4().hex[:8]
    replay_table = f"work_items_current_replay_{tag}"
    report_table = f"replay_report_{tag}"

    old_tables = conn.execute(
        SQL(
            "SELECT tablename FROM pg_tables WHERE schemaname = %s "
            "AND (tablename LIKE 'work_items_current_replay_%%' "
            "OR tablename LIKE 'replay_report_%%')"
        ),
        [schema],
    ).fetchall()
    for tbl in old_tables:
        conn.execute(SQL("DROP TABLE IF EXISTS {}").format(Identifier(tbl["tablename"])))

    conn.execute(
        SQL(
            "CREATE TABLE {} AS SELECT * FROM work_items_current WHERE 1=0"
        ).format(Identifier(replay_table))
    )
    conn.execute(
        SQL(
            "CREATE TABLE {} ("
            "work_item_id UUID PRIMARY KEY, "
            "category TEXT NOT NULL, "
            "detail TEXT)"
        ).format(Identifier(report_table))
    )

    wi_rows = conn.execute(
        SQL("SELECT work_item_id FROM work_items_current ORDER BY work_item_id")
    ).fetchall()

    ok_count = 0
    drift_count = 0
    halted_count = 0

    for row in wi_rows:
        wi_id = row["work_item_id"]
        events = conn.execute(
            SQL(
                f"SELECT {_EVENT_FIELDS} FROM events "
                "WHERE work_item_id = %s ORDER BY event_seq"
            ),
            [wi_id],
        ).fetchall()

        if not events:
            continue

        try:
            replayed_state = _replay_work_item(conn, wi_id, events, key_set)
        except Exception as e:
            halted_count += 1
            conn.execute(
                SQL(
                    "INSERT INTO {} (work_item_id, category, detail) VALUES (%s, %s, %s)"
                ).format(Identifier(report_table)),
                [wi_id, "halted", str(e)],
            )
            continue

        live_row = conn.execute(
            SQL(
                "SELECT work_item_id, workflow_name, workflow_version, work_item_type, "
                "current_state, custom_fields, needs_review, not_before, "
                "last_event_seq, last_event_at, next_event_seq, "
                "claimed_by, claim_expires_at "
                "FROM work_items_current WHERE work_item_id = %s"
            ),
            [wi_id],
        ).fetchone()

        if _states_match(replayed_state, live_row):
            ok_count += 1
            conn.execute(
                SQL(
                    "INSERT INTO {} (work_item_id, category) VALUES (%s, %s)"
                ).format(Identifier(report_table)),
                [wi_id, "replayed_ok"],
            )
        else:
            drift_count += 1
            diff_fields = _diff_fields(replayed_state, live_row)
            detail = (
                f"drift in: {', '.join(diff_fields)}. "
                f"live state={live_row['current_state']!r} "
                f"seq={live_row['last_event_seq']}, "
                f"replayed state={replayed_state['current_state']!r} "
                f"seq={replayed_state['last_event_seq']}"
            )
            conn.execute(
                SQL(
                    "INSERT INTO {} (work_item_id, category, detail) VALUES (%s, %s, %s)"
                ).format(Identifier(report_table)),
                [wi_id, "replayed_drift", detail],
            )

        conn.execute(
            SQL(
                "INSERT INTO {} (work_item_id, workflow_name, workflow_version, "
                "work_item_type, current_state, custom_fields, needs_review, "
                "not_before, last_event_seq, last_event_at, next_event_seq, "
                "claimed_by, claim_expires_at) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
            ).format(Identifier(replay_table)),
            [
                wi_id,
                live_row["workflow_name"],
                live_row["workflow_version"],
                live_row["work_item_type"],
                replayed_state["current_state"],
                psycopg.types.json.Jsonb(replayed_state["custom_fields"]),
                replayed_state["needs_review"],
                replayed_state["not_before"],
                replayed_state["last_event_seq"],
                live_row["last_event_at"],
                replayed_state["last_event_seq"] + 1,
                live_row["claimed_by"],
                live_row["claim_expires_at"],
            ],
        )

    return ReplayReport(
        table_name=replay_table,
        replayed_ok=ok_count,
        replayed_drift=drift_count,
        halted=halted_count,
    )


def _parse_not_before(value: str | datetime | None) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    return datetime.fromisoformat(value)


def _replay_work_item(
    conn: psycopg.Connection,
    wi_id,
    events: list[dict],
    key_set: KeySet,
) -> dict:
    state = None
    custom_fields: dict = {}
    needs_review = False
    not_before: datetime | None = None
    last_seq = 0

    for evt in events:
        transition = evt["transition"]
        last_seq = evt["event_seq"]

        key_entry = key_set.verify_key_status(evt["key_id"])

        if not verify_event(
            event_id=evt["event_id"],
            work_item_id=evt["work_item_id"],
            actor_id=evt["actor_id"],
            transition=evt["transition"],
            payload=evt["payload"],
            signature=bytes(evt["signature"]),
            canonical_hash=bytes(evt["payload_canonical_hash"]),
            key=key_entry.secret,
            stored_envelope=(
                bytes(evt["canonical_envelope"]) if evt["canonical_envelope"] else None
            ),
        ):
            raise RuntimeError(
                f"Signature verification failed for event {evt['event_id']} "
                f"at seq {evt['event_seq']}"
            )

        if transition == "created":
            payload = evt["payload"] or {}
            state = payload.get("initial_state")
            custom_fields = payload.get("custom_fields", {})
            not_before = _parse_not_before(payload.get("not_before"))
        elif transition in (
            "link_created",
            "link_removed",
            "claim_acquired",
            "claim_stolen",
            "claim_released",
            "claim_expired",
            "hook_dead_lettered",
        ):
            pass
        elif transition == "escalated":
            needs_review = True
        elif transition == "not_before_set":
            payload = evt["payload"] or {}
            not_before = _parse_not_before(payload.get("not_before"))
        else:
            wf_row = conn.execute(
                SQL(
                    "SELECT definition FROM workflow_registry "
                    "WHERE workflow_name = %s AND version = %s"
                ),
                [evt["workflow_name"], evt["workflow_version"]],
            ).fetchone()
            if wf_row is None:
                raise RuntimeError(
                    f"Missing workflow {evt['workflow_name']!r} v{evt['workflow_version']}"
                )

            defn = wf_row["definition"]
            found = False
            for t in defn.get("transitions", []):
                if t["name"] == transition and t["from_state"] == state:
                    state = t["to_state"]
                    found = True
                    break
            if not found:
                name_matches = any(
                    t["name"] == transition for t in defn.get("transitions", [])
                )
                if name_matches:
                    raise RuntimeError(
                        f"Transition {transition!r} exists but not valid from state {state!r}"
                    )

            payload = evt["payload"] or {}
            if payload.get("custom_fields"):
                custom_fields = {**custom_fields, **payload["custom_fields"]}

    return {
        "current_state": state,
        "custom_fields": custom_fields,
        "needs_review": needs_review,
        "not_before": not_before,
        "last_event_seq": last_seq,
    }


def _states_match(replayed: dict, live: dict) -> bool:
    if replayed["current_state"] != live["current_state"]:
        return False
    if replayed["last_event_seq"] != live["last_event_seq"]:
        return False
    if replayed["custom_fields"] != live["custom_fields"]:
        return False
    if replayed["needs_review"] != live["needs_review"]:
        return False
    if replayed["not_before"] != live["not_before"]:
        return False
    return True


def _diff_fields(replayed: dict, live: dict) -> list[str]:
    diffs: list[str] = []
    if replayed["current_state"] != live["current_state"]:
        diffs.append("current_state")
    if replayed["last_event_seq"] != live["last_event_seq"]:
        diffs.append("last_event_seq")
    if replayed["custom_fields"] != live["custom_fields"]:
        diffs.append("custom_fields")
    if replayed["needs_review"] != live["needs_review"]:
        diffs.append("needs_review")
    if replayed["not_before"] != live["not_before"]:
        diffs.append("not_before")
    return diffs
