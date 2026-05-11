---
number: "112"
title: "Sync validator row-lock DoS — operational hardening against buggy validators"
severity: medium
status: implemented
kind: improvement
author: opus-gemini-review
date: "2026-05-11"
tags: [validators, hooks, operational-robustness, fr-13]
related: [096]
---

## Observation

Sync validators (registered via `register_validator`) execute inside the
`transition()` transaction which holds a `FOR UPDATE` row lock on
`work_items_current`.  The 5-second Python-level timeout in
`run_validator` (`_hooks.py:23-44`) bounds the wait from the caller's
perspective, but:

1.  The Postgres connection itself has no `statement_timeout`.  If a
    future code path were to issue SQL on the same connection during
    validator execution, the DB would have no enforcement boundary.
2.  There is no registration-time check for I/O usage.  A validator
    that accidentally imports `requests` or `psycopg` can block
    indefinitely in I/O, leaking the thread-pool thread and holding the
    row lock for the full 5-second Python timeout on every call.
3.  There is no observability for near-miss executions.  A validator
    that takes 4.5s (90 % of the timeout) degrades throughput but is
    invisible to operators until it actually times out.

The threat model is **operational robustness against the operator's own
buggy validators**, not a security exploit.  Substrate is single-tenant;
hooks and validators are code the operator wrote.

## Proposed Fix

1.  `SET LOCAL statement_timeout = '5s'` on the transaction connection
    before invoking the validator — one config line, Postgres-native
    enforcement, resets at transaction end.
2.  AST-level I/O detection at `register_validator` time — parse the
    handler source, cross-reference `Name` nodes with `__globals__` to
    detect references to I/O modules.  Best-effort; silently allows
    uninspectable handlers with a warning log.
3.  Watchdog in `run_validator` — measure elapsed time, emit structured
    log event (`validators.near_timeout`) and increment metric when
    execution exceeds 80 % of the timeout threshold.

## Acceptance Criteria

- [ ] `SET LOCAL statement_timeout` applied before validator execution.
- [ ] `register_validator` rejects handlers that reference I/O modules
      in their source (best-effort; no false rejection for uninspectable
      handlers).
- [ ] Structured log emitted on near-timeout (≥ 80 % of threshold).
- [ ] `validators_near_timeout` Prometheus counter added.
- [ ] `VALIDATOR_IO_UNSAFE` error code added to `ErrorCode` enum.
- [ ] Tests for all three mitigations.
