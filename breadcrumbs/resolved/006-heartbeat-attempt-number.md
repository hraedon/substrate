---
number: "006"
title: Heartbeat does not check attempt_number for stolen-by-self
severity: medium
status: implemented
kind: bug
author: claude-opus
date: "2026-05-05"
tags: [claims, fr-07, ac-07]
related: ["005"]
---

## Problem

`_claims.py:heartbeat_claim` checks `claim_row["actor_id"] != actor_id` only. AC-07 explicitly requires rejection if `attempt_number` has advanced — defending against the edge case where the same actor stole the claim back from itself after expiry.

Sequence: actor A acquires (attempt 1) → TTL expires while A is offline → A re-acquires (attempt 2, same actor_id) → original session resumes and heartbeats. Currently the heartbeat succeeds because actor_id matches, but the original work was lost when the claim expired.

## Spec reference

- FR-07 ("Stale-heartbeat protection: if `claims.actor_id != heartbeat.actor_id` OR `attempt_number` has advanced since the claim was acquired, the heartbeat is rejected with a 'claim lost' signal")
- AC-07 (same — explicit edge case)

## Location

`src/substrate/_claims.py` — `heartbeat_claim()` lines 121-164

## Suggested fix

Caller passes back the `attempt_number` they were issued at acquire time. The `Claim` dataclass already carries it, so the API gains an `expected_attempt_number: int` parameter (or `attempt_number` directly) on `heartbeat_claim`. Reject with `CLAIM_LOST` if `claim_row["attempt_number"] != expected_attempt_number`.

Public API change: `Substrate.heartbeat_claim` gains the parameter. Existing callers must thread `claim.attempt_number` through.
