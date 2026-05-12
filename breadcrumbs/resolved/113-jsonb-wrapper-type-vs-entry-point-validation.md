---
number: "113"
title: "Jsonb() wrapper type would replace fragile per-entry-point validation"
severity: low
status: proposed
kind: design
author: opus-review
date: "2026-05-11"
tags: [contract, jsonb, validation, api-ergonomics]
related: ["064", "076", "092", "096"]
---

## Observation

Recent sessions (19–22) closed a string of bugs in the same shape:
JSONB-bound data (`actor_metadata`, `payload`, `custom_fields`) reached
the backend without going through `validate_json_safe_value`. Each fix
was the same mechanical step — add a `_vjs(...)` call at one more entry
point:

- BC-064: null bytes in string custom fields (added validation in `_workflow._coerce_field`)
- BC-076: `actor_metadata`/`payload` divergence between backends (added at 4 entry points in `_events.py` and `_in_memory.py`)
- BC-092: NaN/Inf floats (added to `validate_json_safe_value`)
- BC-096-class: incomplete dict-walk coverage (deepened the recursive validator)

The validator is correct and recursive. What's fragile is the contract
that **every new JSONB-bound parameter must remember to call it**. Today
that's roughly 6 call sites across `_events.py`, `_in_memory.py`,
`_workflow.py`. Any new public method that accepts a JSONB-shaped
argument needs a new explicit call — and forgetting is silent until a
backend divergence is found by property tests (or, worse, by a user).

## Proposal

Introduce a `Jsonb` wrapper type (e.g. `@dataclass(frozen=True) class
Jsonb: value: object`) that:

1. Runs `validate_json_safe_value` in `__post_init__`, so construction
   is the validation gate.
2. Is the declared parameter type for `actor_metadata`, `payload`, and
   custom-field values at the public API boundary.
3. Backends unwrap `.value` after construction; they never see a raw
   dict at a JSONB entry point.

The win: validation is enforced by the type system (mypy) at the
function-signature level instead of by reviewer discipline at each call
site. Adding a new JSONB-bound method then can't compile without going
through `Jsonb(...)`.

## Trade-offs

- **API churn.** Public callers currently pass dicts; switching to
  `Jsonb(...)` is a breaking change. A staged path is possible:
  accept `dict | Jsonb` for one release, deprecate dict, then require
  `Jsonb`. Worth weighing against substrate's stability commitments.
- **Ergonomic cost.** `append_event(payload={"k": "v"})` becomes
  `append_event(payload=Jsonb({"k": "v"}))`. Mitigatable with a module-
  level helper or by accepting `dict` and auto-wrapping internally —
  but auto-wrapping reintroduces the "remember to call it" problem we're
  trying to eliminate, just one layer in.
- **`custom_fields` is per-field, not per-blob.** `_coerce_field` runs
  per individual field value, not on the whole `custom_fields` dict.
  The wrapper either has to support per-leaf use or `custom_fields` has
  to stay validated the current way. Probably the latter, narrowing the
  wrapper's scope to `actor_metadata` and `payload`.

## Why this is `low` severity

The current per-entry-point validation works. Every known divergence
has been closed. The property-based conformance tests will catch a
future missed call site if one is added. This is an *ergonomic and
maintainability* improvement, not a correctness gap.

The reason to file rather than ignore: substrate is otherwise close to
"done." The next dozen API additions are the right moment to settle
this shape, not after another null-byte-class bug.

## Suggested next step

Sketch the API in a small RFC: which parameters take `Jsonb`, the
migration story for callers, whether `custom_fields` is in or out of
scope. If the migration cost is judged too high, accept and close —
the current discipline is workable.
