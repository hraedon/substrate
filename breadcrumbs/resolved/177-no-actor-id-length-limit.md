---
number: "177"
title: No actor_id length limit — Postgres TEXT column permits ~1GB values
severity: low
status: implemented
kind: improvement
author: security-audit
date: "2026-05-17"
tags: [validation, input-sanitization, api-boundary]
related: []
---

## Resolution

Added `MAX_ACTOR_ID_LENGTH = 255` constant and `validate_actor_id(actor_id: str)` function to `src/substrate/_contract.py`. `validate_mutation_params()` now accepts an optional `actor_id` parameter and validates length at the public API boundary.

All `Substrate` and `InMemorySubstrate` mutation entry points (`create_work_item`, `append_event`, `transition`, `acquire_claim`, `heartbeat_claim`, `release_claim`, `create_link`, `remove_link`, `update_not_before`) were updated to pass `actor_id` into `validate_mutation_params()`.

Sidecar models do not yet enforce `max_length=255` via Pydantic (leaving for a future pass) — the server-side boundary validation is now present in both backends.

New unit tests in `tests/test_contract.py` cover:
- short actor_id passes
- exact 255 boundary passes
- 256 raises `INVALID_ARGUMENT`
- detail payload includes `actor_id_length`

## Files changed

- `src/substrate/_contract.py` — added `MAX_ACTOR_ID_LENGTH`, `validate_actor_id`, wired into `validate_mutation_params`.
- `src/substrate/__init__.py` — pass `actor_id` to `_validate_mutation_params` in all mutation methods.
- `src/substrate/_transition.py` — pass `actor_id` to `_validate_mutation_params`.
- `src/substrate/_in_memory.py` — pass `actor_id` to `validate_mutation_params` in all mutation methods.
- `tests/test_contract.py` — added `TestValidateActorId` with 4 cases.
