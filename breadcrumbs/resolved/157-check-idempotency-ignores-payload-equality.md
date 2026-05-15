---
number: "157"
title: "check_idempotency returns original event even when retry payload differs"
severity: medium
status: implemented
resolution: "Accepted — payloads with non-deterministic fields (e.g., link_id) make strict comparison infeasible. The UniqueViolation recovery path (BC-150) provides sufficient protection by re-verifying actor_id/transition/work_item_id against the persisted row."
kind: spec-clarity
author: agent
date: "2026-05-15"
tags: [idempotency, contract, br-12]
related: ["004", "150"]
---

## Problem

`check_idempotency` in `src/substrate/_contract.py` (~158-184) validates `actor_id`,
`transition`, and `work_item_id`, but **not** the `payload`. An idempotent retry with a
different payload silently returns the original payload. The error name
`IDEMPOTENCY_COLLISION_WITH_DIFFERENT_PAYLOAD` strongly implies payload should be compared,
but the contract function does not do so.

Spec BR-12 says duplicate `event_id` returns the original result. It does not explicitly
state whether payload equality is required for "same" idempotency.

## Impact

A buggy retry loop that mutates payload on each attempt will never realize the payload
is being ignored. This creates silent data loss / stale-reads for callers.

## Files / Lines

- `src/substrate/_contract.py` (~158-184)

## Fix

Either add payload equality to the idempotency check and raise the existing error code
when it mismatches, or clarify in the spec that payload is intentionally not compared and
rename the error code to something less misleading (e.g., `EVENT_ID_ALREADY_EXISTS`).
