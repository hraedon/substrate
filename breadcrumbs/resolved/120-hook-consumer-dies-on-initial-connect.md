---
number: "120"
title: HookConsumer dies silently on initial connection failure
severity: high
status: implemented
kind: bug
author: adversarial-review
---

## Problem

`HookConsumer._run` attempts an initial connection. If it fails, the method logs and returns immediately. The background thread exits. `start()` has already returned to the caller, which has no signal that the consumer is dead until it notices `is_running == False` or hooks stop draining.

## Impact

Operational silent failure. Hooks accumulate in the queue with no consumer. A transient network blip at startup (e.g., Postgres restarting) permanently disables hook processing for the process lifetime unless a human intervenes.

## Fix

Retry the initial connection inside the main loop with the same backoff policy used for mid-flight reconnections. Alternatively, raise an exception from `start()` if the first connect fails.

## Related

- `_hooks.py` `HookConsumer._run`
- `_hooks.py` `HookConsumer.start`
