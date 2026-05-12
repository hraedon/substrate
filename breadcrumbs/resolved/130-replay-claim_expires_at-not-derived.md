---
number: "130"
title: Replay does not derive claim_expires_at, latent drift risk
severity: medium
status: resolved
kind: design
author: claude-opus
date: "2026-05-12"
resolved_date: "2026-05-12"
tags: [replay, claims]
related: ["090"]
---

## Problem

`_replay.py:_replay_work_item` derives `claimed_by` from claim events (claim_acquired → set, claim_stolen → set, claim_released/claim_expired → clear) but never derives `claim_expires_at`. The replay output table always stores `NULL` for `claim_expires_at` (line 178). The `_states_match` function checks `claimed_by` but not `claim_expires_at`.

Currently latent: any work item with an active claim will have a non-NULL `claim_expires_at` in the live projection but `NULL` in the replayed row, but since `_states_match` doesn't check it, no drift is reported. If `_states_match` were ever extended to check `claim_expires_at`, every replay with an active claim would falsely report drift.

## Resolution

Option 1 (derive) implemented by GLM-3 in Session 24: `_replay_work_item` now derives `claim_expires_at` from claim_acquired/claim_stolen event payloads. The replay output table stores the derived value.

`_states_match` intentionally does NOT compare `claim_expires_at` because heartbeats mutate it without emitting events, so the replay-derived value may differ from the live value. This is the correct tradeoff: derivation provides completeness for the output table, while drift comparison stays limited to fields fully derivable from the event log.