---
number: "010"
title: append_event allows arbitrary transition strings, bypassing FR-11/FR-12
severity: high
status: implemented
kind: bug
author: claude-opus
date: "2026-05-05"
tags: [api-surface, fr-11, fr-12, security, br-09]
---

## Problem

`Substrate.append_event` accepts a free-form `transition: str | None` parameter and writes the event without consulting the workflow definition. A caller can do:

```python
sub.append_event(work_item_id=wi, actor_id="evil", transition="approve",
                 actor_metadata={"role": "agent"}, payload={...})
```

This produces an event with `transition="approve"` that bypasses:
- FR-11 transition validation (is "approve" a valid transition from current state?)
- FR-12 role-gating (is "agent" allowed to do "approve"?)
- Implicit claim release (the dedicated `transition` method releases claims; `append_event` does not)

The current `transition` property in events is what consumers and replay use to reconstruct state. A bypass-shaped event will replay as a valid state transition (per BC-015 replay matches by name only — it would even pick up the to_state). This is a correctness AND a security issue.

## Spec reference

- FR-03 (event append) — does not specify whether `transition` field is constrained
- FR-11, FR-12 (transition + role-gating validation)
- BR-09 (authorization is audit, not enforcement — but the "audit" trail is what's polluted here)

## Location

`src/substrate/__init__.py` — `Substrate.append_event()` lines 217-268

## Suggested fix

Two layers of defense:

1. **Reject any `transition` string that matches a defined transition in the pinned workflow.** If you want to record state transitions, use `Substrate.transition()`. `append_event` is for non-transition events (annotations, system notes).

2. **Define a curated set of permitted `append_event` transition labels.** Suggested vocabulary: `null` (no-op annotation), `"annotation"`, `"system_note"`, `"not_before_set"`. Reject anything else. This makes the API self-documenting about what `append_event` is for.

Alternative: rename `append_event` to `append_annotation` (or split into `append_annotation` and a private internal append). Self-documenting names are better than docstrings.
