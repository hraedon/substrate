---
number: "145"
title: "Missing orphan-check in replay after dropping work_item_id FK"
severity: medium
status: proposed
kind: bug
author: agent
date: "2026-05-15"
tags: [replay, partition]
related: []
---

## Problem
Plan 001 (Events Month Partitioning) dropped the foreign key from `events` to `work_items_current` because partitioned tables cannot reliably maintain global foreign keys without including the partition key. To compensate, a replay-time orphan check was supposed to be added, but it was left out of the implementation.

## Impact
If an event is appended for a work item that does not exist (or was corrupted), the database no longer prevents it at write time. During replay, `substrate` might silently process or crash when encountering these orphaned events.

## Fix
Add an orphan-check inside `Substrate.replay()` (in `_replay.py`). During projection rebuild, if an event refers to an unknown `work_item_id` and is not a `created` event, raise a clear error (e.g., `REPLAY_HALTED` due to orphaned event) or log a severe warning depending on the desired fault-tolerance policy.