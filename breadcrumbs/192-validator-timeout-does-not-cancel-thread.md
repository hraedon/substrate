---
number: "192"
title: "Validator timeout leaks threads; ThreadPoolExecutor cancel_futures is misleading"
severity: medium
status: proposed
kind: bug
author: claude
date: "2026-05-18"
tags: [validators, hooks, resource-leak, concurrency]
related: []
---

# BC-192 — Validator timeout does not actually cancel the validator

## Problem

`src/substrate/_hooks.py:35-64` runs validators via `ThreadPoolExecutor` and `future.result(timeout=...)`. Python threads are not cancellable; on timeout the worker keeps running until it returns. `cancel_futures=True` only affects *unstarted* futures.

A pathological validator (infinite loop, slow computation, or hanging on a blocking call the AST safety check missed) accumulates one zombie thread per timeout. Repeated timeouts grow background threads unbounded, consuming memory and FDs.

Compounding: `check_validator_io_safety` (`src/substrate/_hooks.py:442+`) is heuristic — an AST walk of `__globals__` only catches direct top-level imports. It misses `__import__`, `importlib`, attribute-access into modules, calls through closures, and any indirect IO. The current contract therefore both *under-enforces* (heuristic) and *under-protects* (no actual cancellation when enforcement fails).

## Proposed fix

Choose one of:

1. **Run validators in a subprocess.** Real cancellation via `process.kill()` on timeout. Cost: per-call subprocess spawn (~ms) plus serialization. Acceptable if validators are rare or batched.
2. **Drop the safety theater.** Document validators as "trusted, cooperative, run in-process at your risk." Remove `check_validator_io_safety` and the timeout/executor entirely. Validator authors are responsible for not hanging. Simpler, honest, smaller code surface.
3. **Status quo + circuit breaker.** Keep the executor but track per-validator timeout counts; after N timeouts, refuse to invoke that validator until reset. Doesn't fix the leak, just bounds it.

(1) is the only option that delivers the contract the current code pretends to. (2) is the right call if no caller actually requires hard cancellation.

## Acceptance criteria

1. Decision recorded (which of 1/2/3) and reflected in the spec section on validators.
2. If (1): test that a validator running `while True: pass` is cancelled within `timeout + epsilon` and no zombie subprocess remains.
3. If (2): docs and spec updated; tests assert the old executor wrappers are gone.

## Resolution

_(pending)_
