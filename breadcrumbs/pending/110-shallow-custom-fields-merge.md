---
number: "110"
title: custom_fields merge in append_transition_event is shallow, not deep
severity: medium
status: proposed
kind: design
author: adversarial-reviewer
date: "2026-05-11"
tags: [correctness, custom-fields, fr-27]
related: []
---

## Description

In `_events.py:279-283`:
```python
merged_fields = wi_row["custom_fields"]
if custom_fields_update:
    if merged_fields is None:
        merged_fields = {}
    merged_fields = {**merged_fields, **custom_fields_update}
```

This is a shallow merge. If `custom_fields` contains nested structures like:
```json
{"metadata": {"version": 1, "tags": ["a", "b"]}}
```

And `custom_fields_update` contains:
```json
{"metadata": {"version": 2}}
```

The result would be:
```json
{"metadata": {"version": 2}}
```

The `tags` field would be lost entirely.

## Evidence

- `_events.py:279-283`: Shallow dict merge
- No recursive or deep merge logic
- No documentation clarifying this behavior

## Impact

- Silent data loss if consumers use nested custom fields
- If the pattern is documented as shallow merge, consumers can work around it by including full nested structures in updates
- If the intent is deep merge but implementation is shallow, this is a correctness bug

## Fix

1. Document that custom_fields merge is shallow (explicit API contract)
2. Or implement deep merge (recursive) if that's the intended behavior
3. Add a test that verifies the merge behavior

## Notes

This may be intentional for simplicity. The spec says custom fields are "validated against the type schema" but doesn't specify merge semantics. If shallow is intentional, it should be documented. If deep is needed, this is a bug.