---
number: "150"
title: "UniqueViolation catch raises false-positive IDEMPOTENCY_COLLISION_WITH_DIFFERENT_PAYLOAD on identical-payload races"
severity: high
status: implemented
resolution: "On UniqueViolation in both `append_event` and `append_transition_event`, re-runs `check_idempotency` against the persisted row. If actor_id/transition/work_item_id match, returns existing event (idempotent retry). Only raises error on true collision."
kind: bug
author: agent
date: "2026-05-15"
tags: [idempotency, events, br-12]
related: ["004"]
---

## Problem

In `src/substrate/_events.py` (~136-166), event INSERT is wrapped in:

```python
except psycopg.errors.UniqueViolation:
    raise SubstrateError(
        ErrorCode.IDEMPOTENCY_COLLISION_WITH_DIFFERENT_PAYLOAD,
        f"event_id {event_id} already exists",
    )
```

If two concurrent requests append the same `event_id` with the **identical** payload, the
loser hits `UniqueViolation` and raises `IDEMPOTENCY_COLLISION_WITH_DIFFERENT_PAYLOAD`
even though the payload is the same. Retries should be silent per BR-12.

## Impact

Caller retries across transient failures are not safe. A spurious "collision" error forces
callers to handle an edge case that should be silently idempotent. This undermines the
idempotency guarantee.

## Files / Lines

- `src/substrate/_events.py` (~136-166)

## Fix

On `UniqueViolation`, re-run `check_idempotency` against the persisted row. If the payload
matches, return the existing event deterministically. Only raise
`IDEMPOTENCY_COLLISION_WITH_DIFFERENT_PAYLOAD` if the payload actually differs.
