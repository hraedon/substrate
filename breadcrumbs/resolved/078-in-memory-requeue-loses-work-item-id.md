---
number: "078"
title: "InMemory requeue_dead_lettered_hook loses work_item_id"
severity: medium
status: proposed
kind: bug
author: glm-5.1-adversarial
date: "2026-05-11"
tags: [adversarial-review]
related: []
---

## Context

`_in_memory.py:1093-1097` — The dead-letter stores `entry.get("payload")` (raw
event payload). On requeue, `payload.get("work_item_id")` looks in the event
payload, yielding None. The requeued hook immediately dead-letters again.

## Fix

Store `work_item_id` at the top level of dead-letter entries, and use it
directly in requeue.
