---
number: "014"
title: remove_link does not validate that the link exists
severity: low
status: implemented
kind: bug
author: claude-opus
date: "2026-05-05"
tags: [links, fr-23]
---

## Problem

`_links.py:remove_link` writes a `link_removed` event without checking whether a corresponding `link_created` exists for the same `(from, to, type)` triple. Phantom-removal events accumulate; replay and `has_link_type` queries see them and may produce inconsistent results.

## Spec reference

- FR-23 ("Remove a link between work-items — records `link_removed` event")
- AC-23 ("Link remove emits `link_removed`. Prior link history remains in event log") — silent on whether removal of a non-existent link should error

## Location

`src/substrate/_links.py` — `remove_link()` lines 131-181

## Suggested fix

Before writing the `link_removed` event, query the event log:

```sql
SELECT 1 FROM events
WHERE work_item_id = $from
  AND transition = 'link_created'
  AND payload->>'to_work_item_id' = $to
  AND payload->>'link_type' = $type
  AND NOT EXISTS (subsequent link_removed for same triple)
LIMIT 1
```

If no live link exists, raise `ErrorCode.LINK_NOT_FOUND`. Pairs with BC-013 — both want the "links from event log" derivation to be correct.

Lower priority because the consequences (phantom removals) are detectable via replay drift once BC-003 lands.
