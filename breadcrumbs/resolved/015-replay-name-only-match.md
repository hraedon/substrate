---
number: "015"
title: Replay matches transitions by name only, not (name, from_state)
severity: medium
status: implemented
kind: bug
author: claude-opus
date: "2026-05-05"
tags: [replay, fr-16, fr-11]
---

## Problem

`_replay.py:_replay_work_item` matches transitions by name only:

```python
for t in defn.get("transitions", []):
    if t["name"] == transition:
        state = t["to_state"]
        ...
```

A workflow with two transitions sharing a name from different source states (e.g., `cancel` from `in_progress` and `cancel` from `review`) replays incorrectly: the first match wins regardless of `from_state`. The live transition path in `__init__.py:transition()` correctly matches on both name and `from_state` (line 315), so the live and replay paths can diverge silently.

When the divergence occurs, BC-003's drift detection would catch it — but only if BC-003 is fixed to compare more than `current_state`, and only if the divergence happens to land on a different terminal state.

## Spec reference

- FR-11 (validate state transitions against the work-item's pinned workflow version)
- FR-16 ("Each historical transition validates against the workflow version recorded on its event")

## Location

`src/substrate/_replay.py` — `_replay_work_item()` lines 154-160

## Suggested fix

Match on `(name, from_state)` where `from_state` is the replayed state immediately before the event:

```python
for t in defn.get("transitions", []):
    if t["name"] == transition and t["from_state"] == state:
        state = t["to_state"]
        found = True
        break
```

Same shape as `__init__.py:transition()`. If no match, halt the work-item with `unrecognized_transition` (per FR-16's enumerated halt reasons).
