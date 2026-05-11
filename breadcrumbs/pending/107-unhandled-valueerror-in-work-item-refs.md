---
number: "107"
title: validate_work_item_refs propagates unhandled ValueError from uuid.UUID()
severity: medium
status: proposed
kind: bug
author: adversarial-reviewer
date: "2026-05-11"
tags: [correctness, custom-fields, fr-27]
---

## Description

In `_workflow.py:325`, the code:
```python
ref_uuid = uuid.UUID(value)
```

If `value` is not a valid UUID string, `uuid.UUID(value)` raises `ValueError`. This exception propagates up the call stack as an unhandled exception, leaking implementation details (Python's UUID parsing) to the caller.

It should be caught and converted to a `SubstrateError` with `ErrorCode.CUSTOM_FIELD_VIOLATION`.

## Evidence

- `_workflow.py:325`: `uuid.UUID(value)` not in try/except
- `_workflow.py:408`: Same call is wrapped in try/except with proper `SubstrateError` in `_coerce_field` for `work_item_ref` type (this is the correct pattern)
- Inconsistent handling: `validate_work_item_refs` doesn't handle the error, while `_coerce_field` does

## Impact

- Implementation detail leak (Python exception exposure)
- Could reveal information about UUID format expectations to an attacker
- Inconsistent behavior: some `work_item_ref` validation handles errors gracefully, some doesn't

## Fix

Wrap `uuid.UUID(value)` in try/except and raise `SubstrateError(ErrorCode.CUSTOM_FIELD_VIOLATION, ...)` with detail about the invalid UUID.

## Notes

`_coerce_field` at line 407-414 has the correct pattern. `validate_work_item_refs` should follow the same pattern.