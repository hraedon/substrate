---
number: "013"
title: has_link_type filter does not account for link_removed events
severity: medium
status: implemented
kind: bug
author: claude-opus
date: "2026-05-05"
tags: [query, fr-05b, links]
---

## Problem

`_work_items.py:query_work_items` `has_link_type` filter (lines 277-283):

```sql
EXISTS (SELECT 1 FROM events e
 WHERE e.work_item_id = work_items_current.work_item_id
   AND e.transition = 'link_created'
   AND e.payload->>'link_type' = $X)
```

This matches any work-item that has *ever had* a `link_created` event of that type, even if that link was subsequently removed. Stale link state leaks into query results.

§18.2 explicitly leaves `current_links` derived-on-demand rather than projected, but the filter as written derives wrong: it ignores `link_removed` events.

## Spec reference

- FR-05b (structured query with `has_link_type` filter)
- §18.2 ("Links are derived on demand from `link_created` / `link_removed` events")

## Location

`src/substrate/_work_items.py` — `query_work_items()` lines 277-283

## Suggested fix

Use a NOT EXISTS to subtract subsequent removals on the same `(from, to, type)` triple. Sketch:

```sql
EXISTS (
  SELECT 1 FROM events e_c
  WHERE e_c.work_item_id = work_items_current.work_item_id
    AND e_c.transition = 'link_created'
    AND e_c.payload->>'link_type' = $X
    AND NOT EXISTS (
      SELECT 1 FROM events e_r
      WHERE e_r.work_item_id = e_c.work_item_id
        AND e_r.transition = 'link_removed'
        AND e_r.payload->>'link_type' = e_c.payload->>'link_type'
        AND e_r.payload->>'to_work_item_id' = e_c.payload->>'to_work_item_id'
        AND e_r.event_seq > e_c.event_seq
    )
)
```

Watch the index story: `payload->>` queries are slower than typed columns. If this filter ends up hot, consider a `links` projection table (still BR-04-compatible — derived from events). Defer until query latency justifies.
