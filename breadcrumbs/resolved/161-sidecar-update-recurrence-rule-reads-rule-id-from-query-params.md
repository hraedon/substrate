---
number: "161"
title: "Sidecar `update_recurrence_rule` reads `rule_id` from query_params instead of body — KeyError at runtime"
severity: high
status: resolved
kind: bug
author: opus-4-7
date: "2026-05-16"
tags: [sidecar, plan-005, recurrence, http]
related: []
---

## Problem

`src/substrate/sidecar/routes.py:344-353` defines:

```python
@router.post("/update_recurrence_rule")
async def update_recurrence_rule(body: UpdateRecurrenceRuleRequest, request: Request):
    _get_actor(request)
    result = substrate.update_recurrence_rule(
        rule_id=_parse_uuid(request.query_params.get("rule_id", "")),
        status=body.status,
        schedule_expr=body.schedule_expr,
        template=body.template,
    )
```

The route is a `POST` with no path parameter for `rule_id`. The `UpdateRecurrenceRuleRequest` Pydantic model (`models.py:190-194`) does not declare a `rule_id` field — only `status`, `schedule_expr`, `template`. So `request.query_params.get("rule_id", "")` returns `""`, which `_parse_uuid("")` will reject with a parse error (or, depending on `_parse_uuid` semantics, raise on an empty string).

Sibling routes read `rule_id` from `body["rule_id"]` (e.g., `fire_recurrence` at line 335, `cancel_recurrence_rule` at line 341), so the call convention is "body field" everywhere else.

## Impact

- Every call to the sidecar `/v1/update_recurrence_rule` endpoint fails at runtime, regardless of payload.
- Plan 005 hook lifecycle tests don't currently exercise this path, so CI doesn't catch it (see related BC-163 on stubbed hook tests).
- Live operators who try to update a recurrence rule via the sidecar will hit this on first call.

## Files / Lines

- `src/substrate/sidecar/routes.py:344-353`
- `src/substrate/sidecar/models.py:190-194` (UpdateRecurrenceRuleRequest)
- `tests/sidecar/test_sidecar.py` — no test exercises this route end-to-end

## Fix

Two coordinated edits:

1. Add `rule_id: str` to `UpdateRecurrenceRuleRequest`.
2. Change the handler to read `_parse_uuid(body.rule_id)`.

Then add a sidecar test that POSTs a valid body and asserts the rule mutates.

## Lesson

When a set of sibling routes share a parameter convention ("rule_id in body"), a code review checklist or a shared helper would prevent one route from diverging silently. Pydantic `extra="forbid"` on the body would have surfaced this earlier if the caller had tried to send `rule_id` in the body — the request would 422 with "extra field not permitted", making the divergence visible.
