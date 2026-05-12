---
number: "124"
title: InMemory register_validator/register_hook_handler mutate in-place
severity: medium
status: implemented
kind: bug
author: adversarial-review
---

## Problem

Postgres `Substrate` uses copy-on-write for `_validators` and `_hook_handlers` (`updated = dict(self._validators); self._validators = updated`). InMemory does `self._validators[name] = handler` in-place. If a test spawns a thread that registers a validator while another thread is iterating the dict, it can crash with `RuntimeError: dictionary changed size during iteration`.

## Impact

Thread-safety gap between backends. The InMemory backend is used for testing but is not safe under concurrent mutation, while the Postgres backend is.

## Fix

Use the same copy-on-write pattern in InMemory.

## Related

- `_in_memory.py` `register_validator`, `register_hook_handler`
- `__init__.py` `register_validator`, `register_hook_handler`
