---
number: "129"
title: InMemory _append_claim_event and _append_simple_event bypass idempotency
severity: critical
status: proposed
kind: bug
author: claude-opus
date: "2026-05-12"
tags: [in-memory, idempotency, conformance]
related: ["116"]
---

## Problem

BC-116 identified that `acquire_claim`, `release_claim`, `create_link`, and `remove_link` bypass idempotency checks. The root cause is deeper: the internal helpers `_append_claim_event` (`_in_memory.py:1341`) and `_append_simple_event` (`_in_memory.py:1366`) unconditionally append to `self._events` and `self._event_id_index` without calling `check_idempotency`. Any future method wired through these helpers inherits the same gap.

## Impact

Any mutation path that goes through these helpers (claims, links, escalation, not_before_set) can create duplicate events with the same `event_id` but different `event_seq`, violating the "unique within project" guarantee. This is broader than just the four methods identified in BC-116.

## Fix

Add `check_idempotency(self._event_id_index.get(event_id), ...)` at the top of both `_append_claim_event` and `_append_simple_event`, returning the existing event if matched. This centralizes the guard rather than scattering it per-call-site.