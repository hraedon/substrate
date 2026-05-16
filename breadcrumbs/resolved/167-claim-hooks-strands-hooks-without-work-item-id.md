---
number: "167"
title: "`claim_hooks` marks all rows `in_progress` before filtering — hooks with missing `work_item_id` stranded"
severity: high
status: resolved
kind: bug
author: glm-5.1
date: "2026-05-16"
tags: [hooks, plan-005, sidecar]
related: []
---

## Problem

`_hooks.py:claim_hooks` marked ALL claimed rows as `in_progress` via `UPDATE ... WHERE id = ANY(ids)` before iterating and filtering out rows where `payload.work_item_id` is missing. Filtered-out rows were never returned to the caller, so they could never be completed or failed. They sat in `in_progress` until lease expiry, then sweep requeued them, creating an infinite cycle.

## Fix

Reordered: first build the `valid_ids` list from rows with a present `work_item_id`, then only mark those valid rows as `in_progress`. Rows without `work_item_id` remain `pending` and are eventually dead-lettered by the normal hook processing path.
