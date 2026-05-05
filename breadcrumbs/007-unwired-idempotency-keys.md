---
number: "007"
title: idempotency_key parameter accepted but ignored on several mutations
severity: medium
status: proposed
kind: bug
author: claude-opus
date: "2026-05-05"
tags: [idempotency, br-12, api-surface]
related: ["004"]
---

## Problem

BR-12 promises "all mutation operations ... accept a client-supplied idempotency key (UUIDv4). Duplicate keys return the original result deterministically."

Currently:
- `Substrate.register_workflow` accepts `idempotency_key`, ignores it. Natural idempotency comes from the `(workflow_name, version)` uniqueness check, but that's a different shape — the key is silent decoration.
- `Substrate.acquire_claim` accepts `idempotency_key`, passes it to `_claims.acquire_claim`, which ignores it.
- `Substrate.create_link` and `remove_link` accept it; only `_links` uses it as the `event_id` fallback. Functional, but the explicit `idempotency_key` semantics (idempotent across distinct event_ids on the same logical operation) aren't honored.
- `release_claim` and `heartbeat_claim` don't accept idempotency keys at all.

The shape of the public API promises BR-12 across the board; only `event_id` doubling as the event-append key is genuinely wired.

## Spec reference

- BR-12 (API-layer idempotency on every mutation)
- §19.3 ("Honor BR-12 idempotency: same key, same response, regardless of network retry topology")

## Location

- `src/substrate/__init__.py` — every mutation method that accepts `idempotency_key`
- `src/substrate/_claims.py` — `acquire_claim` parameter unused

## Suggested fix

Two-part decision:

1. **Storage:** add an `idempotency_keys` table (`(operation, idempotency_key)` PK, `result_blob jsonb`, `created_at`) with a TTL-based sweep. Or piggyback on event_id by deriving event_id from idempotency_key for operations that always emit an event.

2. **Wiring:** every mutation method either uses the key or stops accepting it. Removing the parameter is acceptable where natural idempotency exists (e.g., `register_workflow` on `(name, version)`), but should be documented in the docstring as "no idempotency key needed — natural idempotency on (name, version)."

The cleaner pattern is option (1) with a lookup-then-execute pattern guarded by the canonical lock. This matches BR-12's promise without per-operation special cases.

Pairs with BC-005 (claim mutations should emit events) — once claims are events, the `event_id`-as-idempotency-key path applies uniformly.
