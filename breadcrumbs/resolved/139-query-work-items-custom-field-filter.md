---
number: "139"
title: "query_work_items lacks custom_field filtering — completes the custom_fields surface"
severity: medium
status: resolved
kind: improvement
author: opus-4-7
date: "2026-05-13"
tags: [api, query, custom_fields, ergonomics]
related: ["128"]
---

## Problem

Substrate's `custom_fields` API is asymmetric. Consumers can:

- **Declare** typed custom fields per `work_item_type` via `CustomFieldDef`
- **Validate** values against the declared schema (`validate_field_values`)
- **Store** values at registration (`register_work_item`) and update them (`update_custom_fields`)
- **Retrieve** per-item (`get_work_item`, `query_work_items` returns the full dict)

But there is no way to **filter** a query by custom field value. `query_work_items` (`src/substrate/_work_items.py:231`) accepts filters on workflow, type, state, claim, link presence — but not on custom_fields. Any caller that wants "all items where `custom_fields['priority'] = 'high'`" must page through every work item and filter client-side.

This is a generic capability gap, not specific to any one consumer. Any substrate user that stores meaningful structured per-item attributes will eventually want to query by them — that is the *point* of typed custom fields. The current surface effectively treats them as opaque payload rather than queryable structured data.

The immediate prompt is software-factory-2's RFC-022 (initiative bundling), which proposes carrying an `initiative_id` as a custom field and needs efficient queries by it for telemetry rollups and a stall-detection watchdog. RFC-022's Phase A can work around the gap with client-side filtering, but the workaround is wasteful at scale and the same pattern will recur for any future custom-field-keyed query.

## Proposed change

Extend `query_work_items` with a `custom_field_filters` parameter:

```python
def query_work_items(
    self,
    *,
    workflow_name: str | None = None,
    ...
    custom_field_filters: dict[str, object] | None = None,
    cursor: uuid.UUID | None = None,
    page_size: int = 100,
) -> QueryPage[WorkItem]:
    """...
    custom_field_filters: Equality filters on custom field values. All entries
        must match (AND). Keys not declared on the queried work_item_type(s)
        match no rows.
    """
```

Postgres implementation: JSONB containment (`custom_fields @> %s::jsonb`) for the whole dict, or per-key `custom_fields->>'key' = %s` building. Containment is one parameter and one operator; per-key is more flexible if range/comparison filters are later added. Recommend starting with containment for equality-only semantics — it's the simplest correct implementation.

InMemory implementation: equivalent dict comparison in `_in_memory.py`'s `query_work_items`. Must match Postgres semantics exactly to maintain the conformance contract (RFC-062 / BC-128 trajectory).

## Design considerations

1. **Filter-key validation.** Should substrate validate that filter keys are declared custom fields on the queried `work_item_types`? Two options:
   - **Strict:** raise `InvalidQueryError` if a filter key isn't declared on any of the queried types. Catches typos at query time.
   - **Lenient:** unknown keys simply match no rows. Easier composition with multi-type queries.

   Recommend lenient. Strict requires resolving `work_item_types` filter before validating, which couples the two parameters in an unintuitive way, and "unknown key matches nothing" is a sensible empty-result semantics. Document the choice.

2. **Equality only, for now.** No `>`, `<`, `IN`, `LIKE`, or JSONB-path queries in this breadcrumb. Equality on top-level keys covers the dominant case (categorical/identifier-typed fields) and keeps the API surface small. Range/set/path queries can be filed as a separate breadcrumb if a real need emerges.

3. **Type coercion.** Custom fields are stored as JSONB. The filter value should be JSON-serialized the same way the stored value was. Strings, ints, bools, lists of those — all straightforward. Document that complex nested values must match structurally (which JSONB containment already enforces).

4. **Index strategy.** A GIN index on `work_items_current.custom_fields` would make containment queries fast across all keys without per-key index maintenance. Add as part of this change or defer until a query plan demonstrates the need. Recommend adding it now — GIN on JSONB is cheap to maintain at substrate's expected write volumes and avoids a follow-up performance breadcrumb.

5. **Cursor pagination.** The existing `cursor` parameter (work_item_id-ordered) composes naturally with the new filter — no special handling needed.

## Out of scope

- **Bulk update by custom field.** A separate, semantically heavier change (multi-event emission, replay implications). RFC-022 Phase B contemplates it as a substrate ask but only if Phase A's per-item loop proves too slow. File separately if/when.
- **Promoting any specific custom field to a first-class column.** That is a per-consumer decision and not a general substrate concern.
- **JSONB path expressions or operator support beyond equality.** Out of scope here; file separately if needed.

## Acceptance criteria

1. `query_work_items` accepts `custom_field_filters: dict | None = None`.
2. Postgres implementation uses JSONB containment (`@>`) with a GIN index on `work_items_current.custom_fields`.
3. InMemory implementation matches semantics exactly (verified by the existing property-based conformance test, extended to cover the new filter).
4. Unknown filter keys produce empty results, not errors. Documented in docstring.
5. Migration adds the GIN index (new migration file, follows existing migration conventions).
6. Tests: at least one unit test per backend for (a) single-key match, (b) multi-key AND, (c) unknown key empty result, (d) cursor pagination with filter, (e) conformance parity.

## Rationale for severity (medium)

Not critical — workaround exists (client-side filtering). Not high — no correctness risk; the existing API is honest about what it does. Medium because it's a load-bearing ergonomic gap that every meaningful custom_fields consumer will hit, and substrate is in a "complete the surface" phase post-BC-128 where these gaps are cheap to close before they accumulate consumers paying the workaround cost.
