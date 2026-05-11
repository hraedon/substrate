---
number: "106"
title: Unbounded not_before allows permanent work-item DOS
severity: high
status: proposed
kind: bug
author: adversarial-reviewer
date: "2026-05-11"
tags: [security, denial-of-service, fr-26]
related: ["102"]
---

## Description

`update_not_before` allows setting `not_before` to any future datetime with no maximum bound. A malicious actor could set `not_before` to 10 years in the future, effectively locking the work item forever (since no claim can be acquired before `not_before`).

## Evidence

- `__init__.py:1175-1253`: `update_not_before` accepts `datetime | None` with no range check
- `_contract.py:51-56`: `validate_not_before` only checks that `not_before > now`, not any upper bound
- `acquire_claim` in `_claims.py:238`: `validate_not_before(wi_not_before, now)` — only rejects if in future, not if too far in future

## Impact

- **Permanent DOS**: Work item locked forever by setting `not_before` to far future
- An actor with `update_not_before` access (any actor who can cause a transition that calls this) can permanently lock work items
- No mechanism to override or clear a maliciously set `not_before` except setting it to `None` (which requires the same privilege)

## Fix

1. Add a maximum `not_before` delta: e.g., `not_before` cannot be more than 1 year from now
2. Require a special privilege to set `not_before` beyond a reasonable window (e.g., > 1 month)
3. Emit an alert when `not_before` is set to an unusually distant future
4. Allow only certain roles/actors to call `update_not_before`

## Notes

`update_not_before` is FR-26. The spec doesn't mention any bounds on the feature. This is a gap between the designed API and adversarial hardening.