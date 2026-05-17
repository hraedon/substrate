---
number: "176"
title: Sidecar sole-signer middleware only checks POST — non-POST mutation routes would bypass
severity: low
status: proposed
kind: bug
author: security-audit
date: "2026-05-17"
tags: [sidecar, security, fr-15]
related: []
---

## Observation

The `sole_signer_middleware` at `sidecar/app.py:26` only inspects POST requests:

```python
if request.method == "POST" and request.url.path.startswith("/v1"):
```

If a `PUT` or `PATCH` route were ever added to `/v1` for mutations, the signing field check would be skipped, allowing pre-signed events to pass through. While no such routes exist today, this is a fragile guard — it relies on route convention rather than intent.

## Proposed

- Change the condition to check `request.method in ("POST", "PUT", "PATCH")` for defense-in-depth against future route additions.
- Alternatively: tie to the route handler rather than the middleware by applying a FastAPI dependency check.
