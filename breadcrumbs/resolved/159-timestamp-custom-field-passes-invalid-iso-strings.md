---
number: "159"
title: "timestamp custom field validation only checks isinstance(str), accepts invalid date strings"
severity: low
status: implemented
resolution: "Added `datetime.fromisoformat(value)` validation in `_coerce_field` for timestamp type, raises CUSTOM_FIELD_VIOLATION on invalid ISO strings."
kind: bug
author: agent
date: "2026-05-15"
tags: [workflow, validation, replay]
related: []
---

## Problem

In `src/substrate/_workflow.py` (~417-424), the `timestamp` custom field type does:

```python
elif ftype == "timestamp":
    if not isinstance(value, str):
        raise ...
```

It does not attempt `datetime.fromisoformat(value)`. A string like `"not-a-date"` passes
validation, then crashes during replay or downstream parsing.

## Impact

Silent acceptance of invalid data creates a time-bomb that only surfaces during replay
drift detection or downstream consumer parsing, making root-cause analysis expensive.

## Files / Lines

- `src/substrate/_workflow.py` (~417-424)

## Fix

Parse the string with `datetime.fromisoformat` inside `_coerce_field` and raise
`CUSTOM_FIELD_VIOLATION` on failure.
