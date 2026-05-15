---
number: "149"
title: "fire_recurrence returns None work-item on idempotent retry"
severity: critical
status: implemented
resolution: "On early-exit (next_fire_at > now), queries events table by JSONB containment on recurrence_rule_id to find and return the existing work item instead of None."
kind: bug
author: agent
date: "2026-05-15"
tags: [recurrence, fr-28, idempotency]
related: []
---

## Problem

`fire_recurrence` generates a deterministic `event_id` via `uuid5` and calls `create_work_item`.
On success, it updates `next_fire_at` in `recurrence_rules`. On a retry with the same
scheduled fire time, `create_work_item` is idempotent and returns the existing work item.

However, `_recurrence.py` has an early-exit guard:

```python
if rule["next_fire_at"] > now:
    return rule, None
```

If the first call committed successfully (updating `next_fire_at`), a second call sees
`next_fire_at > now` and returns `None` for the work-item instead of the existing work item.

## Impact

Callers who retry `fire_recurrence` (e.g., after a network blip) cannot reliably map
the returned rule state to the work item that was actually created. This breaks idempotency
at the API level and makes error recovery unreliable.

## Files / Lines

- `src/substrate/_recurrence.py` (~206-298)
- `src/substrate/__init__.py` (~1530-1537)

## Fix

When the early-exit triggers, query for the existing work item by its deterministic
event_id (or by recurrence metadata on `work_items_current`) and return it instead of `None`.
