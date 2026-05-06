---
number: "029"
title: "Hook-miss recovery: documented event-since-cursor primitive"
severity: medium
status: proposed
kind: design
author: claude-opus-4-7
via: dep-software-factory-2-runner-fallback
date: "2026-05-06"
tags: [hooks, recovery, runner, sf2-readiness]
related: ["021"]
---

## Problem

BC-021 fixed hook consumer reconnection. But if the SF2 runner is disconnected past the configured backoff window (operator pauses the runner, network partition lasts longer than max retries, etc.), some hook deliveries are missed entirely. The runner's polling fallback (per SF2 BC-002 §"Hook notification mode") needs a primitive to catch up:

> "Give me all events for work-items in roles {R} since cursor X."

Polling for `new` work-items is not sufficient. Critical transitions like `gate_pass` (which triggers the next stage in SF2's pipeline) happen on items already past `new`, and a missed `gate_pass` notification means the downstream stage never starts. Without a documented catch-up API, the runner has to reach into substrate internals or duplicate substrate's event-query logic.

## What needs deciding

1. **Does this primitive already exist as a public API?** Substrate has internal event queries (`_events.py`), and `replay()` walks events in `event_seq` order. If `query_events_since(workflow_name, since_event_seq, role_filter=None)` is already reachable through the public API, the work is documenting it.
2. **If not, promote it.** Add a public method on the substrate manager: `events_since(workflow_name, cursor: int, roles: list[str] | None = None) -> Iterator[Event]`. Cursor is `event_seq`. Caller persists the cursor.
3. **Pagination semantics.** BC-016 fixed pagination by stable `work_item_id` cursor. The recovery API needs `event_seq`-ordered pagination — different shape, different stability requirements. Reuse the BC-016 pattern or document the new one.

## Why medium severity

Not blocking SF2 Phase 1 (one role, one runner, restart story is "wait for heartbeat sweep + re-claim"). Becomes load-bearing in SF2 Phase 2 when multiple stages chain via hooks. A missed `gate_pass` in Phase 2 stalls the pipeline silently.

## Acceptance criteria

- [ ] Public `events_since(workflow_name, cursor, roles=None)` API exists and is documented.
- [ ] Cursor semantics documented: monotonic on `event_seq`, stable under concurrent appends (per BC-032's pagination concern).
- [ ] Test exercises the recovery scenario: producer appends N events, consumer with cursor C < N drains and receives all events with `event_seq > C` in order.
- [ ] Test exercises the role-filter: events for unrelated roles are not returned.
- [ ] AGENTS.md "Patterns" section documents the runner recovery flow.

## Related

- BC-021 (hook consumer reconnect)
- BC-016 (pagination over moving target)
- SF2 BC-002 §"Hook notification mode"
