---
number: "070"
title: Replay temp tables accumulate between replay() calls
severity: low
status: deferred
kind: improvement
author: deepseek-v4-pro
date: "2026-05-11"
tags: [replay, cleanup, postgres]
related: []
---

## Context

`_replay.py:37-65` creates two temporary tables with UUID suffixes
(`work_items_current_replay_*` and `replay_report_*`) per `replay()` call.
Orphaned tables from prior replays are cleaned up at the start of the next
replay (line 41-50), but they accumulate between replays.

## Risk

No correctness issue — just database clutter. If replay is called frequently
without cleaning, stale tables could occupy disk.

## Options

- Drop the temp tables at the end of `replay()` (the caller may want to query
  them, so this changes the API contract)
- Use actual Postgres TEMP tables (bound to session lifetime) instead of
  persistent tables
- Accept current behavior
