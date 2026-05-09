---
number: "063"
title: Add optional prompt_template_hash field to ActorMetadata
severity: low
status: implemented
kind: improvement
author: claude-opus-4-7
date: "2026-05-09"
tags: [actor-metadata, telemetry, sf2-coordination]
related: []
---

## Context

`ActorMetadata` (`src/substrate/_types.py`) currently exposes the fields every consumer is expected to need: `role`, `channel`, `model`, `family`, `gate_name`, `attempt_n`, `context_hash`. Anything sf2-specific beyond that is supposed to flow through `payload` or `custom_fields`.

sf2 is about to bundle a telemetry refactor (`plans/phase2-close-and-phase3-prep.md` §1.1, items A1–A4) that adds prompt-template versioning to its telemetry pipeline. The request is to surface the prompt template's content hash as a first-class telemetry dimension so per-(role, channel, family, gate_name, prompt_template_hash) groupings can detect "channel comparison was confounded by an untracked prompt change between runs."

sf2 has two paths:

1. Thread `prompt_template_hash` through `payload` and let sf2's telemetry consumer extract it. No substrate change needed.
2. Add `prompt_template_hash: str | None = None` to `ActorMetadata` directly, alongside `context_hash`. One sf2 line per `ActorMetadata(...)` construction; no payload plumbing.

## Why this is a substrate-level question, not a consumer-level one

`context_hash` is already on `ActorMetadata` and is conceptually identical: a content hash that lets a consumer correlate outcomes across attempts. `prompt_template_hash` is the same shape (optional `str`, opaque to substrate) and serves the same purpose at a different granularity (template alone vs full rendered context). Putting it next to `context_hash` is the principle-of-least-surprise location.

The counter-argument (raised by sf2's own Debate 009 review) is that putting sf2-specific fields on a substrate dataclass couples the spine to one consumer. That argument applies if `prompt_template_hash` is genuinely sf2-specific. It is not — any consumer that uses prompt-driven workers will want the same field for the same reason. It generalizes the same way `context_hash` already does.

## Proposed change

Add to `ActorMetadata`:

```python
prompt_template_hash: str | None = None
```

Add the obvious lines to `to_dict()` (only emit when not None) and `from_dict()`. Bump no version; the field is additive and backward-compatible — existing events without the field deserialize cleanly with `prompt_template_hash=None`, and consumers that don't read it are unaffected.

## Cost

~6 lines in `_types.py`, ~6 lines in tests asserting round-trip. Half an hour.

## Why this is filed as low severity

- Strictly additive; no migration, no compatibility break.
- sf2 has a clean fallback (option 1 above) if substrate declines the change.
- Not blocking sf2's plan — the fallback is uglier, not impossible.

## Risks

| Risk | Mitigation |
|---|---|
| Adding the field invites future "just one more sf2-specific field" requests | Treat each on its merits; the bar is "would any prompt-driven-worker consumer want this?" `prompt_template_hash` clears that bar; e.g. `gr006a_request_id` would not |
| sf2 ships the fallback and substrate later adds the field anyway → double work | Decide before sf2 Window A starts (target: 2026-05-10). Decision either way unblocks sf2 |

## Decision needed

Substrate maintainer: accept the change, or instruct sf2 to use `payload`. Either is fine; sf2 needs the answer before the bundled telemetry refactor in `plans/phase2-close-and-phase3-prep.md` §1.1 begins.

## References

- sf2 plan: `/projects/software-factory-2/plans/phase2-close-and-phase3-prep.md` §1.1 A2 + §5 risk row 1
- sf2 debate items that surfaced the requirement: `debate/resolved/011-prompt-versioning-in-telemetry.md` (glm-5.1) and `debate/resolved/NEW-001-prompt-version-in-actor-metadata.md` (deepseek-v4-pro) — independent convergence from two reviewers
