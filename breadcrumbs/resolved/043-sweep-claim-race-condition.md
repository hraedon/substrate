---
number: "043"
title: sweep_expired_claims can clobber newly-acquired claims under concurrency
severity: high
status: resolved
kind: bug
author: glm-5.1
date: "2026-05-07"
tags: [claims, concurrency, projection-correctness]
related: []
---

## Problem

`sweep_expired_claims` deletes expired claims first, then locks the `work_items_current` row. Between the DELETE and the FOR UPDATE lock, a concurrent `acquire_claim` can insert a new claim and set `claimed_by` on the projection. When sweep then executes `UPDATE SET claimed_by = NULL WHERE claimed_by IS NOT NULL`, it clobbers the new claimer's projection state, making `claimed_by` inconsistent with the `claims` table.

## Resolution

Changed the WHERE clause from `AND claimed_by IS NOT NULL` to `AND claimed_by = %s` using the expired `prior_actor_id`. If a new actor has claimed the item, the UPDATE matches zero rows and the projection is preserved. Regression test in `tests/test_session13_regression.py::TestSweepRaceCondition`.
