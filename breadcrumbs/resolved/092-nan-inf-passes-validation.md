---
number: "092"
title: validate_json_safe_value allows NaN and Infinity, which Postgres JSONB rejects
severity: high
status: open
kind: bug
author: adversarial-reviewer
date: "2026-05-11"
tags: [validation, jsonb, postgres, error-leak]
related: []
---

## Observation

`validate_json_safe_value` accepts any `float`, but `json.dumps` serializes `float('nan')` as `NaN` and `float('inf')` as `Infinity`. Postgres JSONB columns reject these as invalid JSON per RFC 8259. A payload or `actor_metadata` containing `NaN` will pass library validation and then blow up at the DB boundary with a raw psycopg error, leaking the SQL statement.

## Impact

- Unexpected raw DB errors instead of clean `SubstrateError`.
- Potential information disclosure in error messages.
- Broken idempotency / retry: the event may partially succeed on some backends.

## Proposed Fix

Explicitly reject `math.isnan(x)` and `math.isinf(x)` in the float branch of `validate_json_safe_value`.

## Acceptance Criteria

- [ ] `validate_json_safe_value(float('nan'), "x")` raises `INVALID_ARGUMENT`.
- [ ] Same for `float('inf')` and `float('-inf')`.
- [ ] In-memory backend parity.
