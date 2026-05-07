---
number: "048"
title: InMemorySubstrate poll_hooks does not track hook status or retry stuck hooks
severity: low
status: proposed
kind: improvement
author: glm-5.1
date: "2026-05-07"
tags: [in-memory, hooks, test-fidelity]
related: []
---

## Observation

The real backend's `poll_and_process_hooks` first resets stuck `in_progress` entries older than 5 minutes to `pending`. InMemorySubstrate's `poll_hooks` simply clears and reprocesses the entire queue. Since the in-memory backend has no real `status` tracking, hooks from prior partial runs that failed are retried (rather than being identified as stuck), which means the behavior diverges from the real backend.

## Proposed

Add status tracking to in-memory hook queue entries (`pending`, `in_progress`, `completed`) and implement the same stuck-entry recovery logic. Alternatively, document the divergence and accept that the in-memory backend's simpler model is sufficient for unit tests.
