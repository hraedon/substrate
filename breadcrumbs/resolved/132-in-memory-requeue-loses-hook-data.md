---
number: "132"
title: InMemory requeue_dead_lettered_hook loses transition and payload data
severity: high
status: resolved
kind: bug
author: glm-5.1
date: "2026-05-12"
resolved_date: "2026-05-12"
tags: [in-memory, hooks, conformance]
related: ["126"]
---

## Problem

`_move_to_dead_letter` stored `entry.get("payload")` (the event payload) but did not preserve `entry.get("transition")` as a top-level key. `requeue_dead_lettered_hook` then tried to extract `transition` and `event_payload` from inside the payload dict via `payload.get("transition")` and `payload.get("event_payload")`, which returned None for both.

## Resolution

Added `"transition": entry.get("transition")` to the dead-letter dict in `_move_to_dead_letter`. Fixed `requeue_dead_lettered_hook` to read `"transition": entry.get("transition")` and `"payload": entry.get("payload")` directly from the dead-letter entry instead of trying to extract them from inside the payload dict.
