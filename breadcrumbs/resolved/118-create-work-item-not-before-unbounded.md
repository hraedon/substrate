---
number: "118"
title: create_work_item does not bound not_before delta
severity: high
status: implemented
kind: bug
author: adversarial-review
---

## Problem

`update_not_before` enforces `validate_not_before_delta` (365-day max). `create_work_item` does not perform the same validation on its `not_before` parameter.

## Impact

An actor can create a work item gated 1000 years in the future. The work item can never be claimed (acquire_claim rejects with `NOT_BEFORE_FUTURE`), and `update_not_before` cannot rescue it because the 365-day bound prevents setting it to anything reasonable. This creates a permanent DOS with no recovery path.

## Fix

Add `_validate_not_before_delta(not_before, datetime.now(UTC))` in the public API `create_work_item` before calling the backend, matching the validation already present in `update_not_before`.

## Related

- `__init__.py` `create_work_item`
- `__init__.py` `update_not_before`
- `_contract.py` `validate_not_before_delta`
- BC-106 (resolved: unbounded not_before DOS on update_not_before)
