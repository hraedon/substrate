---
number: "003"
title: Drift detection compares only current_state and last_event_seq
severity: high
status: implemented
kind: bug
author: claude-opus
date: "2026-05-05"
tags: [replay, projection, br-11, fr-16]
related: ["001", "002"]
---

## Problem

`_replay.py:_states_match` compares only `current_state` and `last_event_seq` between the replayed projection and live `work_items_current`. §18.2 lists `custom_fields`, `needs_review`, and `not_before` as fields fully derivable from events. A projection bug that corrupts any of those silently passes replay as `replayed_ok`.

This is the actionable defect signal for BR-11 (projection invariant). If drift detection misses three of the five derived fields, the invariant is essentially unenforced.

## Spec reference

- BR-11 (projection invariant — `work_items_current` fully derivable from `events`; drift detected via FR-16)
- §18.2 (substrate-managed fields list)
- FR-16 ("`replayed_drift` — replayed final state differs from live. This is the actionable signal")

## Location

`src/substrate/_replay.py` — `_states_match()` lines 175-179, plus the `_replay_work_item` return shape

## Suggested fix

`_states_match` should compare:
- `current_state`
- `custom_fields` (jsonb deep-equal)
- `needs_review`
- `not_before`
- `last_event_seq`

Drift detail string should name which field(s) differ to make operator triage actionable. `_replay_work_item` already tracks `needs_review` and `not_before` (though FR-10 escalation is deferred); ensure `custom_fields` is folded correctly across all transition events with `payload.custom_fields`.
