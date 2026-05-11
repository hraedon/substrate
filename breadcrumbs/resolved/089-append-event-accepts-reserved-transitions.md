---
number: "089"
title: append_event accepts reserved system transition names — can spoof escalations and corrupt replay
severity: critical
status: open
kind: bug
author: adversarial-reviewer
date: "2026-05-11"
tags: [events, api-boundary, spoofing, replay, escalation]
related: []
---

## Observation

`Substrate.append_event` only blocks transition names that collide with the *workflow-defined* transition list (`_check_append_blocked`). It does **not** block reserved system transitions such as:

- `escalated`
- `created`
- `claim_acquired`, `claim_stolen`, `claim_released`, `claim_expired`
- `not_before_set`
- `hook_dead_lettered`

A caller can append a fake `escalated` event. `_check_escalation` checks whether an `escalated` event already exists; a spoofed event suppresses real escalation forever. Replay treats these transitions as authoritative, so a fake `created` event mid-history will overwrite replayed state and custom fields.

## Impact

- Suppression of real escalation (security/policy violation).
- Replay drift goes undetected because the spoofed events are themselves part of the replay.
- Audit log integrity is compromised.

## Proposed Fix

Maintain a `frozenset` of reserved system transition names in `_contract.py` and reject them in `append_event` (and `InMemorySubstrate.append_event`).

## Acceptance Criteria

- [ ] `append_event` with `transition="escalated"` raises `TRANSITION_VIA_APPEND_BLOCKED` or a new error code.
- [ ] Same protection in `InMemorySubstrate.append_event`.
- [ ] Regression tests for each reserved name.
