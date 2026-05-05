---
number: "002"
title: Replay output table contains live snapshot, not derived state
severity: medium
status: implemented
kind: bug
author: claude-opus
date: "2026-05-05"
tags: [replay, fr-16, ac-17]
related: ["001", "003"]
---

## Problem

`_replay.py` populates `work_items_current_replay_<ts>` via `INSERT INTO replay_table SELECT FROM work_items_current` (lines 100-105). The replay table is a copy of live state, not the replay-derived projection.

Drift detection still works in-memory (`_states_match` compares the in-memory `replayed_state` against `live_row`), but the replay table itself cannot be used for the operator workflow described in FR-16: "Operator decides whether to atomically swap (rename) or diff for verification." There is nothing to swap or diff against — the table holds the same data as `work_items_current`.

## Spec reference

- FR-16: "rebuild a `work_items_current_replay_<timestamp>` projection from the event log on demand. ... Output is a fresh table"
- AC-17: "`replay()` produces `work_items_current_replay_<ts>` table; live `work_items_current` is unchanged"

## Location

`src/substrate/_replay.py` — lines 100-105, the `INSERT INTO {} SELECT FROM work_items_current` block

## Suggested fix

Insert a row built from `replayed_state` into `replay_table`, not a copy from live `work_items_current`. The row schema should mirror `work_items_current` (same columns) but values come from `_replay_work_item`'s output. This makes the table genuinely usable for atomic-swap or diff workflows.

Pairs with BC-001 and BC-003 — the replay machinery needs one cohesive pass.
