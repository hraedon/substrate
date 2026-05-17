---
number: "176"
title: Sidecar sole-signer middleware only checks POST — non-POST mutation routes would bypass
severity: low
status: implemented
kind: bug
author: security-audit
date: "2026-05-17"
tags: [sidecar, security, fr-15]
related: []
---

## Resolution

Changed the guard from `request.method == "POST"` to `request.method in ("POST", "PUT", "PATCH")` in `sole_signer_middleware` (`src/substrate/sidecar/app.py:28`). This defends against future route additions that use PUT/PATCH for mutations.

## Files changed

- `src/substrate/sidecar/app.py` — include PUT and PATCH in the sole-signer method check.
