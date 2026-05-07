---
number: "043"
title: read_events composite filter ordering semantics are undocumented
severity: low
status: resolved
kind: design
author: assistant
date: "2026-05-07"
tags: [api-ergonomics, documentation]
related: []
---

## Observation

The `read_events` composite filter support added in session 14 allows multiple filter dimensions (e.g. `work_item_id + transition`, `actor_id + transition`, `start/end + transition`). The ordering of returned events depends on an implicit priority rule:

- If `work_item_id` is present → ASC by `event_seq`
- Else if `start`/`end` is present → ASC by `timestamp`
- Else → DESC by `(timestamp, event_seq)`

This is consistent between real and in-memory backends today, but it is not stated in the docstring or spec. A consumer doing `read_events(actor_id=X, start=..., end=...)` may be surprised that the sort order switches from DESC to ASC depending on whether the time range is provided.

## Proposed

Document the ordering rule explicitly in `Substrate.read_events` docstring and, if stable, in `spec.md` §19. Consider whether the rule should be simplified (e.g. always ASC by `timestamp`, `event_seq`) to reduce consumer surprise.

## Resolution

Documented ordering semantics in `Substrate.read_events` and `InMemorySubstrate.read_events` docstrings. Three-case rule is now explicit: work_item_id → ASC by event_seq; time range → ASC by (timestamp, event_seq); otherwise → DESC by (timestamp, event_seq).
