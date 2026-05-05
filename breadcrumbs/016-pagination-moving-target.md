---
number: "016"
title: Pagination over moving last_event_seq target can skip or duplicate
severity: low
status: proposed
kind: design
author: claude-opus
date: "2026-05-05"
tags: [query, fr-05b, pagination]
---

## Problem

`_work_items.py:query_work_items` orders by `(last_event_seq, work_item_id)` with cursor `(last_event_seq, work_item_id) > (cursor_seq, cursor_id)`. `last_event_seq` is per-work-item and changes as new events arrive. A work-item that was on page 1 can be touched between pages and reappear on page 2 (duplication), or move past the cursor and never appear (skip).

This is a typical live-pagination caveat, not a bug per se. It's worth either fixing or documenting because consumers (federated UI, agent claim-discovery loops) will hit it.

## Spec reference

- FR-05b ("Pagination via `(last_event_seq, work_item_id)` cursor; default page size 100, max 1000")

## Location

`src/substrate/_work_items.py` — `query_work_items()` lines 253-305

## Suggested fix

Two options:

1. **Stable cursor by `work_item_id` alone.** Order by `work_item_id`, cursor compares `work_item_id > cursor_id`. Ordering is fixed regardless of new events. Loses the "freshly-active first" property but pagination is correctness-stable.

2. **Snapshot semantics.** Set transaction isolation to `REPEATABLE READ` for the query, document that pagination reflects a snapshot at first-page time. Adds a small isolation-mode wrinkle (substrate is otherwise READ COMMITTED per §17.1).

Option (1) is simpler and matches the way most agent claim-discovery loops actually want to consume the data ("scan all of state X in one pass"). Document the change to FR-05b's cursor shape if adopted — currently the spec says `(last_event_seq, work_item_id)`.

Either option, document the trade-off in the API.
