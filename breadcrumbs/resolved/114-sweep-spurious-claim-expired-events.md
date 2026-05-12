---
number: "114"
title: Sweep emits spurious claim_expired events causing replay drift
severity: critical
status: implemented
kind: bug
author: adversarial-review
---

## Problem

`src/substrate/_claims.py::sweep_expired_claims` performs:

1. `DELETE FROM claims WHERE expires_at < now() RETURNING ...`
2. For each deleted row, locks the work item, updates `work_items_current` with a guarded `WHERE claimed_by = %s`, then unconditionally appends a `claim_expired` event.

If a concurrent actor stole the claim between steps 1 and 2, the `UPDATE` affects **zero rows** (the projection correctly keeps the new claim), but the function still emits the `claim_expired` event.

## Impact

The event log now contains a `claim_expired` event for a work item that has an active claim. Replay processes that event and unconditionally sets `claimed_by = None`, producing drift against the live projection. This corrupts the audit trail and undermines the core guarantee that the projection is fully derivable from events.

## Fix

Check the rowcount of the `UPDATE` and only emit the event when it actually cleared the claim.

## Related

- `_replay.py` `_replay_work_item` (claim state tracking)
- `_claims.py` `sweep_expired_claims`
- `_in_memory.py` sweep logic for InMemory parity
