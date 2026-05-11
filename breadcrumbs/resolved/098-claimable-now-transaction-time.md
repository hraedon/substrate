---
number: "098"
title: claimable_now filter uses transaction-time now() instead of statement-time
severity: medium
status: open
kind: design
author: adversarial-reviewer
date: "2026-05-11"
tags: [claims, query, timing, postgres]
related: []
---

## Observation

`query_work_items` `claimable_now` evaluates `now()` inside the SQL query. In Postgres, `now()` returns the transaction start timestamp. A long-running transaction will see stale claim-expiry times, potentially returning work items whose claims expired mid-transaction as “claimable” (or vice versa).

## Impact

Snapshot inconsistency for claim freshness within long transactions.

## Proposed Fix

Document the behavior explicitly, or switch to `clock_timestamp()` with a spec note.

## Acceptance Criteria

- [ ] Spec or docstring documents `now()` semantics for `claimable_now`.
- [ ] Optional: switch to `clock_timestamp()`.
