---
number: "008"
title: Signing scheme does not deliver jsonb-drift survival promised by FR-15
severity: high
status: resolved
kind: design
author: claude-opus
date: "2026-05-05"
tags: [signing, fr-15, ac-26, spec-ambiguity]
related: ["001", "009"]
---

## Problem

FR-15 promises: "Re-verification at replay time uses this hash, not jsonb re-serialization, so signature stability survives Postgres version upgrades that change jsonb canonicalization."

Current implementation (`_signing.py:verify_event`):
1. Rebuilds the canonical envelope from raw fields (jsonb-deserialized).
2. Computes HMAC over the rebuilt envelope, compares to stored `signature`.
3. Computes SHA-256 of the rebuilt envelope, compares to stored `payload_canonical_hash`.

If jsonb canonicalization ever drifts across Postgres versions — exactly the failure mode the stored hash was supposed to defend against — both checks fail simultaneously. The promised property does not materialize.

## Spec reference

- FR-15 (canonical signing envelope, storage of canonical bytes)
- AC-26 ("A simulated jsonb-formatting change ... does NOT invalidate previously verified events")

## Location

- `src/substrate/_signing.py` — `verify_event()`
- The spec itself — FR-15 as written is ambiguous; resolution requires a spec amendment

## Suggested fix

Two design options; **spec must choose** before implementation changes:

**Option A — Store canonical envelope bytes.** Add a `canonical_envelope BYTEA NOT NULL` column to `events`. Re-verify uses the stored bytes for both HMAC and hash checks. Larger storage footprint (envelope is typically 100s of bytes per event), but survives any jsonb drift.

**Option B — HMAC over canonical_hash.** Sign the SHA-256 of the canonical envelope, not the envelope itself. Re-verify uses only the stored hash. Smaller storage; loses the property that HMAC commits to envelope content (any preimage colliding under SHA-256 would verify, which is computationally infeasible for SHA-256 but a notable cryptographic step away from "HMAC commits to plaintext").

Recommendation: Option A. It's honest about what's stored, costs ~100B per event (cheap at substrate scale), and survives canonicalization changes by design. Option B is cryptographically defensible but a less standard construction.

Either way: spec amendment required before code change. Raise to operator.
