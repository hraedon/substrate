---
number: "004"
title: Idempotency silently accepts different payloads under same event_id
severity: medium
status: implemented
kind: bug
author: claude-opus
date: "2026-05-05"
tags: [idempotency, br-12, ac-24, error-codes]
related: ["007"]
---

## Problem

`_events.py:check_idempotency` matches by `event_id` only and returns the original event. If a buggy caller retries with the same `event_id` but a mutated `actor_id`, `transition`, or `payload`, the first row is returned silently and the second call's intent is lost. The caller has no signal that its retry was malformed.

Spec §19.5 names the error code `idempotency_collision_with_different_payload` as part of the API contract; it is never raised.

## Spec reference

- BR-12 (API-layer idempotency)
- §19.5 (error code list — `idempotency_collision_with_different_payload` is enumerated)
- AC-24 (idempotent retry returns original result deterministically)

## Location

`src/substrate/_events.py` — `check_idempotency()` lines 56-66

## Suggested fix

Compare the stored event row to the incoming request:
- `actor_id`, `actor_kind`, `transition` should match exactly
- `payload_canonical_hash` should match the canonical hash of the incoming payload (compute envelope and hash before lookup)

On mismatch, raise `SubstrateError(ErrorCode.IDEMPOTENCY_COLLISION_WITH_DIFFERENT_PAYLOAD, ...)`. Add the error code to `_errors.py` if missing.
