---
number: "125"
title: InMemory missing input validation on several paths
severity: medium
status: implemented
kind: bug
author: adversarial-review
---

## Problem

The InMemory backend is missing several input validations that the Postgres backend enforces at the API boundary:

- `acquire_claim` / `release_claim` / `create_link` / `remove_link`: no `validate_event_id` on explicit `event_id`
- `update_not_before`: no `validate_not_before_delta`
- `create_work_item`: no `validate_not_before_delta`

## Impact

InMemory tests can pass with invalid inputs that Postgres would reject. This reduces confidence in InMemory as a conformance reference and can lead to false-positives in test suites.

## Fix

Add the same boundary validation calls in InMemory that exist in the Postgres `Substrate` class, or extract shared validation into `_contract.py` and call it from both backends.

## Related

- `_in_memory.py` (multiple methods)
- `__init__.py` `Substrate` public API methods
