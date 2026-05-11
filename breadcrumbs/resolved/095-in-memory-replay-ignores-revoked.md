---
number: "095"
title: InMemorySubstrate replay ignores continue_on_revoked and never verifies signatures
severity: high
status: open
kind: bug
author: adversarial-reviewer
date: "2026-05-11"
tags: [in-memory, replay, parity, signing]
related: [090]
---

## Observation

The Postgres `replay()` verifies every event signature and uses `continue_on_revoked` to skip revoked-key events with warnings. The in-memory `replay()` accepts the parameter but never verifies signatures and never checks key status. It is impossible to test revoked-key replay behavior against the in-memory backend. Given RFC-062 conformance testing between backends, this is a parity gap.

## Impact

- Conformance tests cannot catch signature/replay bugs in the in-memory backend.
- Revoked-key edge cases are untestable without a live Postgres instance.
- Backend divergence grows.

## Proposed Fix

Make in-memory replay verify dummy signatures, check key status, and respect `continue_on_revoked`. Alternatively, at minimum check key status and warn on revoked.

## Acceptance Criteria

- [ ] `InMemorySubstrate.replay(continue_on_revoked=True)` skips events with revoked keys and increments `warnings`.
- [ ] `InMemorySubstrate.replay(continue_on_revoked=False)` halts on revoked-key events.
- [ ] Conformance test covers both backends for revoked-key replay.
