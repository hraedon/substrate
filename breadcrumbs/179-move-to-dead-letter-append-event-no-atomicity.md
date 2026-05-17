---
number: "179"
title: _move_to_dead_letter's append_event has no atomicity with work-item state
severity: low
status: proposed
kind: bug
author: security-audit
date: "2026-05-17"
tags: [hooks, dead-letter, events, atomicity]
related: ["167"]
---

## Observation

`_move_to_dead_letter()` at `_hooks.py:301-369` runs the following within a `conn.transaction()` but without acquiring the canonical `SELECT FOR UPDATE` lock on the work item:

1. `INSERT INTO hook_dead_letter` (line 309-330)
2. `DELETE FROM hook_queue` (line 332-335)
3. `SELECT ... FROM events WHERE event_id = %s` (line 337-343)
4. Conditionally: `append_event(... transition="hook_dead_lettered" ...)` (line 346-368)

If `evt_row` is `None` (event was deleted or partition was dropped before the hook queue entry), the dead-letter insert succeeds but no `hook_dead_lettered` event is appended, producing an audit gap. Events are append-only by design (BR-03), but the SELECT reads across all partitions — a partition DROP between steps 1 and 3 would cause `evt_row` to become `None`.

BC-167 addressed the claim order (filter before marking in_progress) but did not address the append_event atomicity in the dead-letter path.

## Proposed

- If `evt_row` is `None`, still append the `hook_dead_lettered` event using the event_id stored in `hook_row["event_id"]` and a known work_item_id extracted from the event_id context (or use `NULL` / a sentinel).
- Alternatively: accept the audit gap as theoretical (partition DROP mid-transaction is an administrative operation, not concurrent traffic) and document the behavior.
