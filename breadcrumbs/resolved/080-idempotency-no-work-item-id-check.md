---
number: "080"
title: "Idempotency check does not verify work_item_id"
severity: medium
status: proposed
kind: bug
author: glm-5.1-adversarial
date: "2026-05-11"
tags: [adversarial-review]
related: []
---

## Context

`_events.py:58-72`, `_contract.py:107-126` — Queries by `event_id` only. If a
caller reuses an `event_id` across work items, the second call returns the first
work item's event and the second work item never gets its event.

## Fix

Add `work_item_id` parameter to `check_idempotency` and verify match.
