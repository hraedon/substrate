---
number: "106"
title: Unbounded not_before allows permanent work-item DOS
severity: high
status: implemented
kind: bug
author: adversarial-reviewer
date: "2026-05-11"
tags: [security, denial-of-service, fr-26]
related: ["102"]
resolution_date: "2026-05-11"
---

## Resolution

Fixed. Added `validate_not_before_delta()` in `_contract.py` with a 365-day max delta. Wired into `update_not_before` in `__init__.py`. Setting `not_before` more than 1 year in the future now raises `SubstrateError(INVALID_ARGUMENT)`.
