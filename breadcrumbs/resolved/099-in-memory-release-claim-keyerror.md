---
number: "099"
title: InMemorySubstrate.release_claim can raise KeyError on concurrent sweep
severity: medium
status: open
kind: bug
author: adversarial-reviewer
date: "2026-05-11"
tags: [in-memory, claims, parity, concurrency]
related: []
---

## Observation

`InMemorySubstrate.release_claim` does `del self._claims[work_item_id]`. If `sweep_expired_claims` deletes the claim between `validate_release` and `del`, this raises `KeyError`.

## Impact

In-memory backend crashes instead of raising a clean `SubstrateError`. While test-only, it breaks parity with the Postgres backend which handles this gracefully via row locking.

## Proposed Fix

Use `self._claims.pop(work_item_id, None)`.

## Acceptance Criteria

- [ ] `release_claim` uses `pop()`.
- [ ] Test covers the race path.
