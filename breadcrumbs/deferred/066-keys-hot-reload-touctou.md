---
number: "066"
title: KeySet hot-reload TOCTOU between active_key_id check and access
severity: low
status: deferred
kind: design
author: deepseek-v4-pro
date: "2026-05-11"
tags: [keys, threading, hot-reload]
related: []
---

## Context

`KeySet.active_key()` (`_keys.py:112-124`) checks `self._active_key_id not in
self._keys` and then accesses `self._keys[self._active_key_id]` in two separate
operations. If hot-reload fires between the check and the access (replacing the
entire `self._keys` dict), the second access could produce a `KeyError`.

## Risk

Very low probability. Single-threaded use is unaffected. The existing check
fails gracefully (returns "No active signing key" error), but the error message
is misleading when the key was just hot-reloaded out momentarily rather than
actually missing.

## Options

- Capture `keys = self._keys` to a local before the check + access (trivially
  safe but doesn't help if the key is genuinely removed)
- Use `self._keys.get(self._active_key_id)` which is atomic with respect to
  hot-reload (the `.get()` happens on the same dict ref, but a new `self._keys`
  could be assigned between `not in` and `.get()`)
- Accept current behavior as sufficient
