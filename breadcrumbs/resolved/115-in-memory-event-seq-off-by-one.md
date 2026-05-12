---
number: "115"
title: InMemory backend event_seq off-by-one vs Postgres on create_work_item
severity: critical
status: implemented
kind: bug
author: adversarial-review
---

## Problem

`InMemorySubstrate.create_work_item` emits the `created` event with `event_seq=0` and leaves `last_event_seq=0`. Postgres emits it with `event_seq=1` and sets `last_event_seq=1`. Every subsequent sequence number differs between backends.

## Impact

Any code that depends on absolute `event_seq` values (e.g., optimistic concurrency with `expected_event_seq`, or external consumers correlating events) will see different behavior on InMemory vs Postgres. The InMemory backend is advertised as a conformance reference but is not actually conformant for sequence numbering.

## Fix

Make InMemory assign `event_seq = next_event_seq` (i.e. 1) for the `created` event, matching Postgres. The `next_event_seq` should also become 2 after creation, matching Postgres behavior where `INSERT` then `UPDATE` increments the sequence counter.

## Related

- `_in_memory.py` `create_work_item`
- `_work_items.py` `create_work_item` (Postgres)
- `tests/test_in_memory_conformance.py` (seq assertions)
