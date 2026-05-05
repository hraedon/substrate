---
number: "001"
title: Replay does not verify signatures or check key status
severity: high
status: implemented
kind: bug
author: claude-opus
date: "2026-05-05"
tags: [replay, signing, audit, fr-15, fr-16, ac-17, ac-26]
related: ["002", "008"]
---

## Problem

`_replay.py:_replay_work_item` iterates events and re-derives state but never calls `verify_event` and never consults `KeySet.verify_key_status`. A revoked-key event replays normally and the work-item is reported as `replayed_ok`. The `halted` category in `replay_report_<ts>` is effectively unreachable except on raw exceptions.

The whole audit-grade replay promise depends on this check existing. Without it, replay confirms the projection logic is consistent with the event log, but cannot detect tampering or revoked-key compromise.

## Spec reference

- FR-15 (re-verification at replay)
- FR-16 ("Encountering a revoked-key event halts replay on that work-item with operator alert")
- AC-17 (revoked-key event halts replay; live projection untouched)
- AC-26 (re-verification uses stored canonical hash, not jsonb re-serialization)

## Location

`src/substrate/_replay.py` — `_replay_work_item()`, the per-event loop starting around line 126

## Suggested fix

Inside the per-event loop:
1. Call `KeySet.verify_key_status(evt["key_id"])` — raises on revoked, logs on deprecated.
2. Call `verify_event(...)` against stored signature using the resolved key's secret.
3. On either failure, raise to outer try/except so the work-item is recorded as `halted` with reason (`revoked_key`, `signature_verification_failed`, `unknown_key_id`).

Pairs with BC-002 (replay table population) and BC-008 (signing scheme ambiguity). Address as one cohesive replay fix.
