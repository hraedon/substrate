---
number: "130"
title: Replay does not derive claim_expires_at, latent drift risk
severity: medium
status: proposed
kind: design
author: claude-opus
date: "2026-05-12"
tags: [replay, claims]
related: ["090"]
---

## Problem

`_replay.py:_replay_work_item` derives `claimed_by` from claim events (claim_acquired → set, claim_stolen → set, claim_released/claim_expired → clear) but never derives `claim_expires_at`. The replay output table always stores `NULL` for `claim_expires_at` (line 178). The `_states_match` function checks `claimed_by` but not `claim_expires_at`.

Currently latent: any work item with an active claim will have a non-NULL `claim_expires_at` in the live projection but `NULL` in the replayed row, but since `_states_match` doesn't check it, no drift is reported. If `_states_match` were ever extended to check `claim_expires_at`, every replay with an active claim would falsely report drift.

## Impact

Replay completeness gap. Claim timing information is lost in replay, making `claim_expires_at` unverifiable. The `_states_match` function is incomplete by omission.

## Fix

Either:
1. Derive `claim_expires_at` from claim_acquired/claim_stolen/claim_heartbeat events in `_replay_work_item` and include it in `_states_match`, or
2. Document the omission as intentional (claim expiry is a runtime concern, not an audit concern) and add `claim_expires_at` to the diff fields explicitly excluded from replay comparison.