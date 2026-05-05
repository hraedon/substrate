from __future__ import annotations

from datetime import UTC, datetime

import psycopg
from psycopg.sql import SQL, Identifier

from ._types import ReplayReport

_EVENT_FIELDS = (
    "event_id, work_item_id, event_seq, actor_id, actor_kind, "
    "actor_metadata, key_id, workflow_name, workflow_version, "
    "timestamp, transition, payload, payload_canonical_hash, signature"
)


def replay(conn: psycopg.Connection, schema: str, project: str) -> ReplayReport:
    ts = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    replay_table = f"work_items_current_replay_{ts}"
    report_table = f"replay_report_{ts}"

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
            replayed_state = _replay_work_item(conn, wi_id, events)
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
                "SELECT current_state, custom_fields, needs_review, not_before, "
                "last_event_seq FROM work_items_current WHERE work_item_id = %s"
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
            detail = (
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
                "INSERT INTO {} SELECT * FROM work_items_current WHERE work_item_id = %s"
            ).format(Identifier(replay_table)),
            [wi_id],
        )

    return ReplayReport(
        table_name=replay_table,
        replayed_ok=ok_count,
        replayed_drift=drift_count,
        halted=halted_count,
    )


def _replay_work_item(
    conn: psycopg.Connection,
    wi_id,
    events: list[dict],
) -> dict:
    state = None
    custom_fields = {}
    needs_review = False
    not_before = None
    last_seq = 0

    for evt in events:
        transition = evt["transition"]
        last_seq = evt["event_seq"]

        if transition == "created":
            payload = evt["payload"] or {}
            state = payload.get("initial_state")
            custom_fields = payload.get("custom_fields", {})
        elif transition in ("link_created", "link_removed"):
            pass
        elif transition == "not_before_set":
            payload = evt["payload"] or {}
            not_before = payload.get("not_before")
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
                if t["name"] == transition:
                    state = t["to_state"]
                    found = True
                    break
            if not found:
                pass

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
    return (
        replayed["current_state"] == live["current_state"]
        and replayed["last_event_seq"] == live["last_event_seq"]
    )
