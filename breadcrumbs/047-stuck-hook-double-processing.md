---
number: "047"
title: Stuck hook recovery could cause double-processing
severity: low
status: proposed
kind: design
author: glm-5.1
date: "2026-05-07"
tags: [hooks, correctness]
related: []
---

## Observation

`poll_and_process_hooks` at `_hooks.py:91-96` resets `in_progress` hooks older than 5 minutes to `pending`, then immediately fetches pending hooks. If a handler is genuinely still running (slow but not stuck), it could be dispatched again. The nested savepoint (line 137) mitigates corruption but the handler's side effects may execute twice.

## Proposed

Increase the recovery threshold, or add a check that the `in_progress` entry's connection PID is no longer alive before resetting it. Alternatively, use an advisory lock per hook_queue ID to prevent concurrent dispatch.
