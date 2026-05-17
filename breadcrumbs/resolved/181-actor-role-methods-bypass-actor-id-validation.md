---
number: "181"
title: register_actor_role / unregister_actor_role bypass actor_id validation
severity: low
status: implemented
kind: bug
author: session-agent
date: "2026-05-17"
tags: [validation, api-boundary, actor-roles]
related: ["177", "174"]
---

## Observation

Both the Postgres `Substrate` and `InMemorySubstrate` backends expose `register_actor_role(actor_id, role)` and `unregister_actor_role(actor_id, role)` as state-mutating public API methods. Despite every other mutation entry point (`create_work_item`, `append_event`, `transition`, `acquire_claim`, etc.) now passing `actor_id` through `validate_mutation_params()` (as of BC-177), these two methods were overlooked and never called any validation on `actor_id`.

This means an operator with a misconfigured token file (or any programmatic caller) could supply an arbitrarily long `actor_id` to the role registry, bypassing the 255-character boundary established by `MAX_ACTOR_ID_LENGTH` and `validate_actor_id()`.

## Resolution

- Wired `_validate_actor_id(actor_id)` at the top of both `Substrate.register_actor_role` and `Substrate.unregister_actor_role`.
- Wired `validate_actor_id(actor_id)` at the top of both `InMemorySubstrate.register_actor_role` and `InMemorySubstrate.unregister_actor_role`.
- Added tests `test_register_actor_role_rejects_overlong_actor_id` and `test_unregister_actor_role_rejects_overlong_actor_id` to `tests/test_phase3.py` for the Postgres path.

All 285 targeted tests pass after the fix.

## Files changed

- `src/substrate/__init__.py` — add `_validate_actor_id` calls in role registration/unregistration.
- `src/substrate/_in_memory.py` — add `validate_actor_id` calls in role registration/unregistration.
- `tests/test_phase3.py` — added 2 new test cases.
