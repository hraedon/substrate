---
number: "141"
title: "_dict_contains diverges from Postgres @> on nested JSON custom fields"
severity: medium
status: proposed
kind: bug
author: glm-5.1
date: "2026-05-13"
tags: [conformance, custom_fields, in_memory]
related: ["139"]
---

## Problem

BC-139 added `custom_field_filters` with JSONB containment (`@>`) on Postgres and `_dict_contains()` on InMemory. The semantics diverge on nested dict values:

- **Postgres `@>`**: deep containment. `{"a": {"b": 1, "c": 2}} @> {"a": {"b": 1}}` → `true`.
- **InMemory `_dict_contains`**: exact equality per key. `haystack["a"] == needle["a"]` → `{"b": 1, "c": 2} == {"b": 1}` → `False`.

This does not manifest today because the test workflow only uses flat string/enum/int fields. But any consumer with a `json`-typed custom field containing nested dicts will see different query results between Postgres and InMemory — a conformance contract violation (RFC-062).

## Proposed fix

Replace `_dict_contains` with a recursive containment check that matches Postgres `@>` semantics:

```python
def _dict_contains(haystack, needle):
    for k, v in needle.items():
        if k not in haystack:
            return False
        h = haystack[k]
        if isinstance(v, dict) and isinstance(h, dict):
            if not _dict_contains(h, v):
                return False
        elif h != v:
            return False
    return True
```

## Acceptance criteria

1. `_dict_contains` matches Postgres `@>` for nested dicts, lists (deep containment), and scalars.
2. New conformance test: create a work item with a `json` field containing a nested dict, filter by a partial nested dict, assert both backends return the same result.
3. Existing 419 tests still pass.
