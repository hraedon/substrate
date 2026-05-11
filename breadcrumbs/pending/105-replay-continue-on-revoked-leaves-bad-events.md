---
number: "105"
title: Replay skip of revoked-key events with continue_on_revoked=True leaves bad events in log
severity: high
status: proposed
kind: design
author: adversarial-reviewer
date: "2026-05-11"
tags: [security, replay, fr-25]
related: ["074"]
---

## Description

When `continue_on_revoked=True` is passed to `replay()`, events signed with revoked or unknown keys are skipped with a warning logged. The events remain in the authoritative `events` table.

This means a revoked key that was used to sign a fraudulent event could result in:
1. `replay()` skips the event (logs warning)
2. The fraudulent event remains in `events` table
3. The live `work_items_current` projection may reflect the fraud
4. An operator running `continue_on_revoked=True` for "audit completeness" sees only a warning, not a blocked replay

## Evidence

- `_replay.py:220-235`: When `continue_on_revoked=True`, revoked-key events are skipped with `warnings += 1` but no halt
- The events are not removed or flagged in any special way
- `replay()` returns a `ReplayReport` with a `warnings` count, but the report doesn't identify which events were skipped

## Impact

- **Silent integrity compromise**: A revoked-key event representing fraud or error remains in the log with no automatic remediation path
- **False audit confidence**: Operator runs replay with `continue_on_revoked=True`, sees `warnings=5, drift=0, halted=0`, and concludes the system is consistent — but 5 malicious events remain
- The spec says FR-25 is for "operator wants a complete replay report for audit despite having rotated keys" — but it doesn't address what to do when those keys signed malicious events

## Fix

1. When `continue_on_revoked=True` skips an event, write a `replay_skipped_revoked_event` record to the report table with `event_id`, `key_id`, `event_seq` for auditability
2. Provide a separate API to list all revoked-key events in the event log
3. Document clearly that `continue_on_revoked=True` is only safe when the operator has independently verified no revoked-key events are malicious
4. Consider requiring a confirmation flag or a separate audit mode that flags skipped events rather than silently counting them

## Notes

This is related to deferred item #074 ("continue_on_revoked=True skips signature verification entirely") which is about skipping the actual verification step, not just halting. The implications of skipping are more severe than just the halted replay path.