---
number: "050"
title: InMemorySubstrate poll_hooks does not dead-letter unregistered handlers
severity: low
status: proposed
kind: bug
author: assistant
date: "2026-05-07"
tags: [in-memory, hooks, test-fidelity]
related: ["048"]
---

## Observation

The real backend's `poll_and_process_hooks` dead-letters hooks whose handler name is not registered (`_hooks.py:125-129`). InMemorySubstrate's `poll_hooks` simply `continue`s, leaving the entry as `pending`. The hook will be re-fetched on every `poll_hooks` call, never dead-lettered and never completed.

This means tests that fire hooks without registering a handler will see silently-orphaned queue entries in the in-memory backend, while the real backend would move them to dead-letter.

## Proposed

Match the real backend behavior: dead-letter entries whose `hook_name` has no registered handler, including emitting the `hook_dead_lettered` event.
