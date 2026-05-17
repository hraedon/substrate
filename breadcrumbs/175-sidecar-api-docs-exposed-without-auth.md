---
number: "175"
title: Sidecar API docs (Swagger UI, OpenAPI schema) publicly accessible without authentication
severity: low
status: proposed
kind: improvement
author: security-audit
date: "2026-05-17"
tags: [sidecar, security, information-disclosure]
related: []
---

## Observation

The sidecar's `auth_middleware` at `sidecar/routes.py:57-76` bypasses authentication for `/docs` (Swagger UI) and `/openapi.json`:

```python
if not request.url.path.startswith("/v1") and request.url.path not in (
    "/docs", "/openapi.json",
):
    return await call_next(request)
```

This allows anyone with network access to discover the full API surface, all request/response models, parameter names, expected types, and error codes. In a homelab context this is negligible. In a multi-tenant deployment, this aids reconnaissance.

## Proposed

- Add a configuration option to disable `/docs` and `/openapi.json` (e.g., `docs_url=None` in `create_app()`).
- Alternatively: apply authentication middleware to these routes as well. FastAPI supports custom documentation authentication via `docs_url` and `openapi_url` configuration or `app.add_middleware()` ordering.
- Default could remain open for development ergonomics, with a warning in production documentation.
