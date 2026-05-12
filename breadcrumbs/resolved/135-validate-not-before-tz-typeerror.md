---
number: "135"
title: validate_not_before raises TypeError on naive/aware datetime mismatch
severity: medium
status: resolved
kind: bug
author: glm-5.1
date: "2026-05-12"
resolved_date: "2026-05-12"
tags: [contract, validation]
related: []
---

## Problem

`_contract.py::validate_not_before()` compared `not_before > now` directly. If one is timezone-aware (UTC) and the other naive, Python 3 raises `TypeError: can't compare offset-naive and offset-aware datetimes`. The sibling function `validate_not_before_delta` already normalizes with `.replace(tzinfo=UTC)`.

## Resolution

Added the same timezone normalization pattern: `nb_utc = not_before if not_before.tzinfo else not_before.replace(tzinfo=UTC)` before comparison.
