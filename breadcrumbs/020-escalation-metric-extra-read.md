---
number: "020"
title: Escalation metric placement requires extra DB read
severity: low
status: proposed
kind: improvement
author: glm-5.1
date: "2026-05-05"
tags: [fr-10, observability, performance]
related: []
---

## Problem

The escalation metric (`substrate_escalations_total`) is incremented in `Substrate.acquire_claim()` by reading back the work item after the transaction commits to check `needs_review`. This is an extra `SELECT` on `work_items_current` per claim acquisition, even when no escalation occurs (the common path).

## Spec reference

FR-21: "Counters: events appended, claims acquired/expired/stolen, ... escalations." The spec says to count escalations, not to query-after-commit to detect them.

## Location

`src/substrate/__init__.py` `acquire_claim()` — lines after the `_acquire()` call that do `self.get_work_item(work_item_id)`.

## Suggested fix

Have `_check_escalation()` in `_claims.py` return a boolean indicating whether escalation occurred. Thread it back through `acquire_claim()` to `Substrate.acquire_claim()` and increment the counter conditionally, avoiding the extra read. Alternatively, emit the counter inside the transaction from `_claims.py` (but that leaks observability concerns into the data layer).

---

## Problem (minor)

The NOTIFY statement for hooks uses `psycopg.sql.Literal` for the payload string. This works but is an unusual pattern — most of the codebase uses parameterized `%s` queries. The Literal approach is necessary because Postgres NOTIFY doesn't support bind parameters for the payload. Document this in a code comment for the next implementer.
