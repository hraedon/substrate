---
number: "046"
title: Hook dispatch silently falls back to nil UUID when work_item_id missing from payload
severity: medium
status: resolved
kind: bug
author: glm-5.1
date: "2026-05-07"
tags: [hooks, data-integrity]
related: []
---

## Problem

`poll_and_process_hooks` in `_hooks.py` constructed `HookContext` with `uuid.UUID(payload.get("work_item_id", str(uuid.UUID(int=0))))` — a nil UUID fallback when `work_item_id` was missing from the stored hook payload. This silently masked data integrity issues in the hook queue, producing a `HookContext` that pointed at a nonexistent work item.

## Resolution

Changed to check for missing `work_item_id` before constructing the context. If missing, the hook is dead-lettered with an appropriate error message instead of being dispatched to a nil UUID target.
