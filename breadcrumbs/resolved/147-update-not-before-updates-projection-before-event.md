---
number: "147"
title: "update_not_before updates projection BEFORE event insert, violating spec ordering"
severity: high
status: implemented
resolution: "Moved projection UPDATE to after `_append_event` call in both Postgres and InMemory backends, inside the same transaction and lock."
kind: bug
author: agent
date: "2026-05-15"
tags: [spec-divergence, fr-26, projection]
related: []
---

## Problem

`update_not_before` in `src/substrate/__init__.py` (~1391-1409) executes:

```python
conn.execute(SQL("UPDATE work_items_current SET not_before = %s ..."))
evt = _append_event(conn, ...)
```

Spec section 18.3 states: *"Substrate updates `work_items_current` only inside the same
transaction as the corresponding event append, after the event row has been inserted,
before commit, while the canonical lock is held."* The code updates the projection
before calling `_append_event`, which is a normative ordering divergence.

## Impact

Any future trigger, assertion, or foreign key that expects the event row to exist before
projection mutation will fail. It also weakens the event log as single source of truth.

## Files / Lines

- `src/substrate/__init__.py` (~1391-1409)

## Fix

Move the `UPDATE work_items_current` to after the `_append_event` call succeeds, inside
the same transaction and under the same lock.
