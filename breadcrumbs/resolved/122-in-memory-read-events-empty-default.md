---
number: "122"
title: InMemory read_events returns empty list with no filters
severity: high
status: implemented
kind: bug
author: adversarial-review
---

## Problem

When `read_events()` is called with no filters (bare call), InMemory returns `[]`. Postgres returns the most recent events across all work items ordered by `(timestamp, event_seq)` DESC.

## Impact

Conformance gap between backends. Tests or downstream code that relies on the "give me everything" default will behave differently on InMemory vs Postgres.

## Fix

Add a default path in InMemory `read_events()` that returns all events sorted by `(timestamp, event_seq)` DESC, matching Postgres.

## Related

- `_in_memory.py` `read_events`
- `_events.py` `read_events_composite` (Postgres)
