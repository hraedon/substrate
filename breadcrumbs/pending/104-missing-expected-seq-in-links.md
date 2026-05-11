---
number: "104"
title: expected_event_seq missing from create_link and remove_link — TOCTOU race
severity: high
status: proposed
kind: bug
author: adversarial-reviewer
date: "2026-05-11"
tags: [concurrency, correctness, fr-03, br-10]
related: ["100", "105"]
---

## Description

`append_event` and `append_transition_event` accept an optional `expected_event_seq` parameter for optimistic concurrency control. However, `create_link` and `remove_link` in `_links.py` emit events but do not accept `expected_event_seq`.

Per BR-10: "Every event-producing operation on a work-item acquires a row lock on the canonical lock target (the work-item's row in `work_items_current`) via `SELECT FOR UPDATE`."

While `create_link` does acquire `FOR UPDATE` locks on both work items (in ascending order to prevent deadlock), there is no `expected_event_seq` to detect whether the work item's state has changed between when the caller fetched it and when the link event is committed.

## Evidence

- `_links.py:44-122`: `create_link` acquires locks but has no `expected_event_seq`
- `_links.py:125-199`: `remove_link` acquires locks but has no `expected_event_seq`
- `append_event` in `_events.py:99`: has `expected_event_seq` parameter
- `append_transition_event` in `_events.py:204`: has `expected_event_seq` parameter

## Impact

- **TOCTOU race**: A link operation could proceed based on a stale read of the work item's state, then commit an event even if the work item was concurrently modified
- This is partially mitigated by the `FOR UPDATE` lock, but the lock only serializes concurrent operations on the same work item — it doesn't prevent the caller from making decisions based on stale state before acquiring the lock
- If the work item's `current_state` or `custom_fields` changed after the caller read them but before the link event is committed, the link could be created based on incorrect assumptions

## Fix

1. Add `expected_event_seq` parameter to `create_link` and `remove_link`
2. Add `expected_event_seq` validation after acquiring the `FOR UPDATE` lock, similar to how `append_event` does it
3. Or document that link operations are not covered by the `expected_event_seq` concurrency mechanism and should not be used for operations that require strict serializability

## Notes

This is a deviation from the spec's stated guarantee that "Every event-producing operation" uses optimistic concurrency. The spec should either be amended to exclude links, or this bug should be fixed.