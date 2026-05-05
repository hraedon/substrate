---
number: "016"
title: Pagination over moving last_event_seq target can skip or duplicate
severity: low
status: resolved
kind: design
author: claude-opus
date: "2026-05-05"
tags: [query, fr-05b, pagination]
---

## Problem

`query_work_items` originally ordered by `(last_event_seq, work_item_id)` with cursor comparing that tuple. `last_event_seq` changes as new events arrive, causing items to shift between pages (duplication) or move past the cursor (skip).

## Resolution

Changed to stable cursor by `work_item_id` alone. Order is `work_item_id ASC`, cursor compares `work_item_id > cursor_id`. Ordering is fixed regardless of concurrent writes. The `last_event_seq`-based "freshly-active first" property was sacrificed for pagination correctness.

Test added: `test_pagination_stable_no_duplicates` creates items, pages through with `page_size=2`, asserts no duplicate IDs and complete coverage.
