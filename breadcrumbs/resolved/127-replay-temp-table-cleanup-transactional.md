---
number: "127"
title: Replay temp-table cleanup is transactional
severity: medium
status: implemented
kind: bug
author: adversarial-review
---

## Problem

`replay()` drops old replay tables at the start of its transaction. If the replay then fails and rolls back, the `DROP TABLE` is undone, leaving zombie tables on disk. This contradicts the cleanup intent.

## Impact

Temporary table accumulation across failed replays. Over time this can clutter the schema and slow catalog queries.

## Fix

Either:
1. Drop old tables in a separate transaction before starting the replay transaction, or
2. Use `ON COMMIT DROP` temporary tables instead of permanent replay tables.

## Related

- `_replay.py` `replay` (old table cleanup)
- BC-070 (resolved: accepted — temp tables accumulate between replay calls)
