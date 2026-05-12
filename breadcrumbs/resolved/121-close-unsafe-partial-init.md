---
number: "121"
title: Substrate.close unsafe on partially-constructed instances
severity: high
status: implemented
kind: bug
author: adversarial-review
---

## Problem

If `KeySet()` or `Metrics()` raises during `__init__`, `_hook_consumer` is never assigned. A caller's `finally: sub.close()` then hits `self._hook_consumer.is_running` and raises `AttributeError`.

## Impact

Exception masking during cleanup. The original exception from `KeySet` or `Metrics` is lost behind the `AttributeError` from `close()`. Resource leaks (connection pool not closed) because cleanup aborts mid-way.

## Fix

Initialize `_hook_consumer = None` early in `__init__`, or use `getattr(self, '_hook_consumer', None)` in `close()`.

## Related

- `__init__.py` `Substrate.__init__`
- `__init__.py` `Substrate.close`
