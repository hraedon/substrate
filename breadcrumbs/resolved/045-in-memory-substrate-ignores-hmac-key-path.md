---
number: "045"
title: InMemorySubstrate accepts but silently ignores hmac_key_path
severity: medium
status: resolved
kind: design
author: assistant
date: "2026-05-07"
tags: [testing, api-parity, silent-correctness-risk]
related: []
---

## Observation

`InMemorySubstrate.__init__` accepts `hmac_key_path: str` but does not use it. Events are signed with a dummy key. This creates a silent-correctness gap: a factory agent can construct an `InMemorySubstrate()` without a real key file, run tests successfully, and only discover the configuration mismatch when switching to real Postgres.

The `None`-contract inconsistency was fixed in session 14 (parameter is now `str` not `str | None`), but the no-op behavior remains.

## Proposed

Option A: Optionally validate that `hmac_key_path` exists (if non-empty) and load it, then use the loaded key for dummy signing. This keeps API parity and catches drift early.

Option B: Leave as-is, but document the limitation clearly in `AGENTS.md` under the `InMemorySubstrate` section.

## Resolution

Implemented Option A. When `hmac_key_path` is non-empty, `InMemorySubstrate` now loads a `KeySet` and uses real HMAC-SHA256 signing via `_signing.sign_event`. When `hmac_key_path` is empty (default), dummy signing is used as before. This catches configuration drift early while preserving test convenience.
