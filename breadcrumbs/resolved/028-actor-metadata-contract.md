---
number: "028"
title: "Document and type the actor_metadata contract"
severity: medium
status: proposed
kind: design
author: claude-opus-4-7
via: dep-software-factory-2-telemetry
date: "2026-05-06"
tags: [telemetry, observability, actor-metadata, sf2-readiness]
related: ["024"]
---

## Problem

`actor_metadata` is stored as opaque JSONB on every event (`_types.py:22`, `_events.py:142-154`). Substrate enforces no schema on its keys.

SF2's per-(role, channel) pass-rate telemetry (SF2 spec §7) depends on every event consistently carrying `{role, channel, model, family, attempt_n, context_hash}`. If a runner ever writes an event missing one of those keys — for instance, a transition wrapper that forgets to populate `family` — the nightly pass-rate query silently produces wrong numbers. The drift is invisible until the data is consumed, which may be weeks later.

This is the "discipline that drifts" failure mode SF2 BC-002 already flagged for runner-side telemetry. Substrate is the right place to close it because every event flows through one of substrate's mutation methods.

## Options

1. **Typed contract.** Ship a `TypedDict` or `@dataclass` `ActorMetadata` in `substrate._types` with the canonical SF2-shaped keys. Document that runners are expected to construct it and pass it in. Keep the underlying JSONB column open for non-SF2 uses (substrate is a library; not every consumer is SF2).
2. **Documented expected keys + lint helper.** Add a `Patterns` section to `AGENTS.md` describing the canonical actor_metadata shape, plus a `_lint.actor_metadata_complete(events)` helper that asserts every event in a window has all expected keys. Runners and CI invoke the helper; substrate enforces nothing at write time.
3. **Schema-validated keys at write time.** Optionally, runners register a `RegisteredActorMetadataSchema` on init; substrate validates against it on every event write. Highest cost; highest assurance.

## Recommendation

Option 1 + Option 2. Ship the `ActorMetadata` dataclass as the canonical SF2 shape, document the expected keys, and provide the lint helper for CI / nightly checks. Defer Option 3 until telemetry drift is observed in practice.

The dataclass should not be required by substrate's mutation APIs (which still accept `dict | None`), but using it gives runners a single import that documents the contract. This matches the BC-024 telemetry-via-hooks pattern: substrate offers shape, runners opt in.

## Why medium severity

Not blocking SF2 Phase 1 (single role, single channel — drift is unlikely with one runner). Becomes load-bearing in SF2 Phase 3 when fleet integration multiplies the number of code paths populating `actor_metadata`. Closing now prevents the drift from accumulating before it's noticed.

## Acceptance criteria

- [ ] `substrate._types.ActorMetadata` (TypedDict or frozen dataclass) with documented keys: `role`, `channel`, `model`, `family`, `attempt_n`, `context_hash`. All optional at the type level so non-SF2 consumers are not broken.
- [ ] `AGENTS.md` "Patterns" section documents the canonical shape and the lint helper.
- [ ] `substrate._lint.actor_metadata_complete(work_item_id, expected_keys)` returns a list of events missing any expected key.
- [ ] Test asserts the lint helper catches a synthetic event missing `family`.

## Related

- BC-024 (telemetry-via-hooks pattern)
- SF2 spec §7 (per-role per-channel telemetry)
- SF2 BC-002 §"Critical changes #3" (telemetry as transition-wrapper discipline)
