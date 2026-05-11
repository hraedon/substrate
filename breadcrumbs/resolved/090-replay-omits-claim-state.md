---
number: "090"
title: Replay does not reconstruct claim state — projection not fully derivable from events
severity: critical
status: open
kind: bug
author: adversarial-reviewer
date: "2026-05-11"
tags: [replay, projection, claims, invariant]
related: []
---

## Observation

The spec (§18) states: *“Projection is fully derivable from event log via replay.”* However, `_replay_work_item` tracks:

- `current_state`
- `custom_fields`
- `needs_review`
- `not_before`
- `last_event_seq`
- `attempt_number`

It **does not** replay `claimed_by` or `claim_expires_at`. `_states_match` and `_diff_fields` omit these columns. A live `work_items_current` row with a stale `claimed_by` (e.g., pointing to a claim swept hours ago) will pass replay as `replayed_ok`.

## Impact

The core invariant that “projection is fully derivable” is violated. Replay cannot detect claim-projection corruption.

## Proposed Fix

Replay claim events to reconstruct `claimed_by` / `claim_expires_at`, and include them in drift detection.

## Acceptance Criteria

- [ ] `_replay_work_item` tracks `claimed_by` and `claim_expires_at` from claim events.
- [ ] `_states_match` and `_diff_fields` compare these fields.
- [ ] In-memory backend parity.
- [ ] Regression test: manually corrupt `claimed_by` in projection, replay reports drift.
