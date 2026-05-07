---
number: "038"
title: Ship first-class test fixtures / in-memory backend for downstream consumers
severity: high
status: implemented
kind: improvement
author: claude-opus-4-7
date: "2026-05-07"
tags: [testing, ergonomics, downstream-consumer, sf2-phase2]
---

## Observation

Software-factory-2, substrate's first major external consumer, hand-rolled a `MockSubstrate` test double (~290 lines, branching). It silently diverged from real substrate behavior (SF2 BC-018: `query_work_items` filtering, `read_events` signature, `state_map` fallback). The 2026-05-07 SF2 reflection explicitly flags it as a liability requiring re-audit on every substrate version bump. The same pattern will appear in every consumer that wants CI-portable unit tests without docker-compose.

## Proposed

Ship `substrate.testing.InMemorySubstrate` (or equivalent) as part of substrate's public surface. Goals:

- Same public API as `Substrate`. Drop-in for unit tests.
- Implements the workflow/transition/event-log/claim semantics in-process.
- Maintained alongside the real backend so it cannot diverge silently — ideally driven by the same conformance test suite.
- Optional: a `pytest` fixture (`substrate.testing.fixture`) for the common case.

## Why this matters now

SF2 plans a Phase 2 audit of MockSubstrate (2026-05-07 reflection, "On what remains"). Doing that audit on substrate's side once, instead of in every consumer forever, is the high-leverage move. Phase 2 also adds new transitions and hooks; MockSubstrate will need another extension cycle without this.

## Open questions

- Schema-per-project: does the in-memory backend need to model that, or is a single flat namespace acceptable for tests?
- HMAC signing: real or stubbed? SF2's tests load a real key file even against the mock.
