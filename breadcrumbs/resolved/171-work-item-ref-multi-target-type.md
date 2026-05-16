---
number: "171"
title: "work_item_ref fields cannot declare multiple allowed target_work_item_types"
severity: low
status: resolved
kind: improvement
author: plm (via sf2/GR-035 forensics)
date: "2026-05-16"
tags: [workflow, custom-fields, work-item-ref, validation]
related: ["037", "107"]
---

## Context

`work_item_ref` custom fields take an optional `target_work_item_type` (single
string). At runtime, `validate_work_item_refs` (`_workflow.py:334-391`) enforces
that the referenced work item's type equals that target. At registration,
`_workflow.py:162-169` rejects unknown targets.

Both call sites treat `target_work_item_type` as a single scalar
(`_types.py:281`). There is no way to declare "this ref may point to a work
item of type A OR type B."

## Motivating case (sf2 GR-035 / BC-145)

sf2's `ensure_upstream_revision` (`scheduler.py:223`) stores the source
work-item ID in a custom field `upstream_revision_of` on the newly-created
revision. The source may be either a `review` or a `jury` work item depending
on which stage failed. There is no single `target_work_item_type` that fits.

sf2's first attempt declared the field with `target_work_item_type:
implementation` (the *new* item's type, by analogy with `interface_ref`).
Substrate correctly rejected this with `CUSTOM_FIELD_VIOLATION` whenever the
source was a `review`.

The workaround sf2 ended up with is to declare `upstream_revision_of` as
plain `string` (commit `555f85d` in sf2). This compiles and runs, but trades
away the UUID-format and existence validation that `work_item_ref` provides
even without `target_work_item_type` (the type check at `_workflow.py:380`
is the only thing gated on `target_type` being truthy; UUID parsing and
existence lookup at lines 358-378 always run).

So there are actually two distinct improvements available:

1. **(Already supported, but easy to miss.)** Document that omitting
   `target_work_item_type` is a legitimate way to opt into UUID + existence
   validation without type enforcement. This is enough for consumers like sf2
   to recover one tier of validation without any substrate change.

2. **(The actual enhancement.)** Accept a list form, e.g.
   `target_work_item_types: [review, jury]`, that constrains the referent to
   *one of* an enumerated set. This is the right shape for routing/lineage
   fields whose source type varies but is still bounded.

## Proposed shape

```yaml
custom_fields:
  - name: upstream_revision_of
    type: work_item_ref
    target_work_item_types: [review, jury]   # plural, list of allowed types
    required: false
```

Semantics:

- If `target_work_item_type` (singular) is present → behaves as today.
- If `target_work_item_types` (plural) is present → referent must match one of
  the listed types; each must exist in the workflow at registration.
- Specifying both is a `WORKFLOW_SEMANTIC_ERROR` at registration.
- Specifying neither → existence-only validation (as today).

Backward compatible: existing workflows use the singular form and behave
unchanged.

## Touched surface

- `_types.py:CustomFieldDef` — add `target_work_item_types: list[str] | None`.
- `_workflow.py` registration validation (~line 162) — accept the plural form;
  reject the both-present case; verify each target is a known type.
- `_workflow.py:validate_work_item_refs` (~line 366) — when plural form is
  set, check `row["work_item_type"] in target_types` instead of `== target_type`.
- `to_dict`/`from_dict` round-trips in `_types.py` (~line 291, 303).

## Severity rationale

Low. Consumers can already get UUID + existence validation today by omitting
`target_work_item_type`, and they can layer additional type checks in their
own code if needed. The plural form is mainly an ergonomics/safety win:
substrate becomes the single point that enforces the bounded-set invariant
instead of every consumer reinventing it.

## Notes / open questions

- BC-037 (resolved) introduced the runtime existence + type check. This
  breadcrumb extends that with multi-target support.
- BC-107 (resolved) hardened the `uuid.UUID(value)` parsing path.
- Worth considering whether to also support `target_work_item_type: "*"` or
  similar sentinel for "any existing work item." Today, omitting the field
  achieves the same thing, so probably not needed.

## Resolution

Implemented `target_work_item_types: list[str]` as the plural complement to the existing singular `target_work_item_type`.

**Files changed:**

- `src/substrate/_types.py:281-296` — added `target_work_item_types: list[str] | None` field; `to_dict` is now fully conditional for both singular and plural (no more `None` key emission); `from_dict` reads both keys.
- `src/substrate/_workflow.py:160-188` — `_validate_semantics` checks: both-present → `WORKFLOW_SEMANTIC_ERROR`; each type in plural list must exist in the workflow. Also `build_definition` (line 227), `validate_field_update` (line 345), and `validate_work_item_refs` (lines 383-420) carry the new field through.
- `src/substrate/_workflow_schema.json:196-222` — added `allOf` / `not` constraint requiring `target_work_item_type` and `target_work_item_types` not both be present; schema fires `WORKFLOW_VALIDATION_FAILED` before semantics layer can fire, providing defense-in-depth.
- `src/substrate/_in_memory.py:1494,1511-1522` — InMemory runtime validation mirrors Postgres: checks `target_types` set membership, raises `CUSTOM_FIELD_VIOLATION` with `expected_types` detail.
- `src/substrate/_work_items.py:187` — `_rebuild_wf` carries `target_work_item_types` when deserializing stored workflow data.
- `tests/test_work_item_ref_validation.py` — `multi_target_substrate` fixture parametrized across `postgres` and `in_memory` backends (doubles test coverage); added `test_schema_rejects_both_singular_and_plural` for explicit schema-layer assertion. 11 new tests (9 original + 2 added in follow-up), all running against both backends where applicable.
