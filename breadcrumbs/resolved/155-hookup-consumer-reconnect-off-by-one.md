---
number: "155"
title: "Hook consumer reconnect max-attempts is off-by-one (allows 11 instead of 10)"
severity: medium
status: implemented
resolution: "Changed `>` to `>=` in both initial-connect and mid-flight reconnect attempt checks so max_reconnect_attempts=10 means exactly 10 attempts."
kind: bug
author: agent
date: "2026-05-15"
tags: [hooks, fr-13]
related: []
---

## Problem

In `src/substrate/_hooks.py` (~496-509):

```python
reconnect_attempts += 1
if reconnect_attempts > max_reconnect_attempts:
    break
```

With `max_reconnect_attempts = 10`, the code fails after the 11th attempt (value 11),
not the 10th.

## Impact

Operational expectations about retry behavior are violated. Ten attempts are explicitly
configured; eleven are performed.

## Files / Lines

- `src/substrate/_hooks.py` (~496-509)

## Fix

Change `>` to `>=`.
