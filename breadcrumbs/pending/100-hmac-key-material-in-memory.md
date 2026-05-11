---
number: "100"
title: HMAC key material held in plaintext Python memory
severity: critical
status: proposed
kind: bug
author: adversarial-reviewer
date: "2026-05-11"
tags: [security, signing, fr-15]
related: ["101", "104"]
---

## Description

`_signing.py` and `_keys.py` hold HMAC secrets as Python `bytes` objects in memory. If an attacker can read the Python process memory (via another vulnerability, core dump, debug interface, or row hammer attacks), they recover the signing key and can forge events for any work item.

Python's garbage collector does not guarantee timely zeroing of byte strings. There is no `mlock()` or secure memory allocation.

## Evidence

- `_keys.py:18`: `KeyEntry.secret: bytes` — raw secret stored
- `_signing.py:47`: `key: bytes` passed directly to `hmac.new()`
- No key zeroization on `KeySet` close or process exit
- No use of `tracemalloc` or memory hardening

## Impact

- Complete auth bypass: attacker can sign arbitrary events as any `actor_id`
- Impersonation of any actor (agent, human, system)
- Event log integrity completely compromised

## Fix

Options (in order of preference):
1. Use a hardware security module (HSM) or key management service (KMS) — secrets never in Python heap
2. Use `secrets.token_bytes` with `mlock()` via ctypes — OS-level memory locking
3. Store only key ID in Python; secret fetched from a sidecar process via IPC on each sign operation
4. Document as an environmental trust assumption (process isolation required)

## Notes

Spec §17.9 trust tiers say actor_id and key_id are "authenticated" — but the secret itself being in Python memory is the root trust anchor. If that anchor is compromised, nothing else matters.