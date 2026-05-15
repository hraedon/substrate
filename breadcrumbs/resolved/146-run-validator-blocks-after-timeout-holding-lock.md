---
number: "146"
title: "run_validator ThreadPoolExecutor blocks after timeout while holding canonical row lock"
severity: critical
status: implemented
resolution: "Replaced `with ThreadPoolExecutor` with manual lifecycle: `shutdown(wait=False, cancel_futures=True)` on timeout, `shutdown(wait=True)` on success. No longer blocks on slow validators after timeout."
kind: bug
author: agent
date: "2026-05-15"
tags: [hooks, validators, locking, fr-13]
related: ["112"]
---

## Problem

`run_validator` in `src/substrate/_hooks.py` uses `ThreadPoolExecutor(max_workers=1)` with a
5-second `future.result(timeout=5)`. When the timeout fires, the context manager's
`shutdown(wait=True)` blocks until the validator thread actually finishes (potentially minutes).
Meanwhile, the caller (`Substrate.transition`) is inside a transaction holding `SELECT FOR UPDATE`
on the work item. A single slow validator can hold the row lock for its entire runtime,
starving all other agents on that work item.

Per FR-13, validators are synchronous, 5-second-timeout, and block transitions on failure.
The 5-second timeout is an API contract. The current implementation violates that contract
by waiting for thread completion.

## Impact

A misbehaving validator (e.g., an accidental blocking HTTP call) can monopolize a work item
for minutes, breaking the operational expectation that validators are bounded. This is a
row-lock DoS vector.

## Files / Lines

- `src/substrate/_hooks.py` (~44-59)
- `src/substrate/__init__.py` (~766-771)

## Fix

Replace the per-call `ThreadPoolExecutor` with a long-lived executor so `shutdown(wait=True)`
is never invoked on the hot path, or run validators in a separate OS-level process with a
hard `SIGKILL` after the timeout. Short-term: create the executor once per `Substrate`
instance or use `concurrent.futures.ProcessPoolExecutor` with a timeout that actually
terminates.
