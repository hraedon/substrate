---
number: "012"
title: Event.timestamp returned to caller differs from server-side stored value
severity: low
status: implemented
kind: bug
author: claude-opus
date: "2026-05-05"
tags: [api-surface, br-08, time]
---

## Problem

`_events.py:append_event` and `append_transition_event` build the returned `Event` dataclass with `timestamp=datetime.now(UTC)` (Python-side, computed in the application process). The actual database row uses `now()` (server-stamped, transaction-stable). These differ by milliseconds, and on a busy system can differ by more.

BR-08 designates Postgres `now()` as the time authority. The caller receives an Event whose `timestamp` is not the authoritative one. Tests that read back the event will see a different timestamp than the one returned by the write call.

## Spec reference

- BR-08 ("Postgres `now()` (transaction-stable) is the time authority")
- FR-03 ("`timestamp` — Postgres `now()`, server-stamped (BR-08)")

## Location

- `src/substrate/_events.py:154-168` (return value of `append_event`)
- `src/substrate/_events.py:273-287` (return value of `append_transition_event`)

## Suggested fix

Use `RETURNING timestamp` on the INSERT and bind the returned value to the dataclass:

```python
row = conn.execute(
    SQL("INSERT INTO events (...) VALUES (...) RETURNING timestamp"),
    [...],
).fetchone()
return Event(..., timestamp=row["timestamp"], ...)
```

Removes the divergence and matches BR-08.
