---
number: "194"
title: "heartbeat_claim mutates claim_expires_at without emitting an event — field is non-replayable"
severity: medium
status: proposed
kind: design
author: claude
date: "2026-05-18"
tags: [claims, replay, events, BC-189-followup]
related: ["189"]
---

# BC-194 — Heartbeat is invisible to event replay

## Problem

`heartbeat_claim` in `src/substrate/_claims.py:217-220` directly updates `work_items_current.claim_expires_at` to `now + ttl_seconds`. No event is appended. The same path in `acquire_claim` (line ~102) writes an event; `release_claim` (line ~263) writes a `claim_released` event; only heartbeat is silent.

Consequence (surfaced while implementing BC-189): the event stream cannot reconstruct the live value of `claim_expires_at` for any work item that has ever been heartbeated. Any drift-detection comparison over the field will always trip on real claims, not a bug. BC-189 added `claim_expires_at` to the replay state-equality check; this BC documents why that addition was reverted and what should land instead.

## Why it matters

- Replay drift detection is supposed to catch projection bugs. Right now it can detect them for every column *except* `claim_expires_at`, because that field has a non-event source of truth. The asymmetry is undocumented and surprising.
- Operationally, a deployment that consumes events to build a separate live view (the watchpost-style second consumer) cannot reconstruct the current `claim_expires_at` from substrate's event log alone. The downstream consumer has to do its own polling of `work_items_current` to know how long the claim has left.

## Proposed fix

Add a `claim_heartbeat` event written inside `heartbeat_claim`'s transaction, with payload `{"actor_id": ..., "expires_at": <ISO timestamp>}`. Symmetric with `claim_acquired` / `claim_released`. The replay derivation then updates `derived_claim_expires_at` on each heartbeat, and `claim_expires_at` can be re-added to the state-equality check.

Cost: heartbeats become append operations. For agents that heartbeat every 30s on long-running work items, this is a non-trivial event-stream volume increase. Worth measuring before committing.

Alternative: keep heartbeat silent, but explicitly document `claim_expires_at` as live-only (not replayable) in the spec, and consider exposing a separate "claim TTL" stream for consumers that need it.

## Acceptance criteria (if we adopt option 1)

1. Every `heartbeat_claim` call appends a `claim_heartbeat` event.
2. Replay derivation updates `derived_claim_expires_at` on `claim_heartbeat`.
3. `_states_match` / `_diff_fields` re-include `claim_expires_at`.
4. Test: a sequence acquire → heartbeat × 3 → release produces a clean replay.

## Open question

Is the volume cost (≈ N heartbeats/min × M concurrent claims) tolerable, or do we want a coalescing strategy (only emit a heartbeat event when the expires_at delta exceeds some threshold)? Watchpost's long-lived `awaiting_human` states will heartbeat for hours-to-days; sf2's seconds-to-minutes claims will heartbeat tens of times per work item. Different shapes want different answers.

## Resolution

_(pending)_
