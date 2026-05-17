---
number: "175"
title: Sidecar API docs (Swagger UI, OpenAPI schema) publicly accessible without authentication
severity: low
status: implemented
kind: improvement
author: security-audit
date: "2026-05-17"
tags: [sidecar, security, information-disclosure]
related: []
---

## Resolution

Added optional `docs_url` and `openapi_url` keyword arguments to `create_app()` in `src/substrate/sidecar/app.py`. Callers (and the CLI entry point in `__main__.py`) can set these to `None` to disable the docs endpoints. The CLI now reads a `SUBSTRATE_DISABLE_DOCS` environment variable; when set to `1`, `true`, or `yes`, both `/docs` and `/openapi.json` are removed from the app.

## Files changed

- `src/substrate/sidecar/app.py` — added `docs_url`/`openapi_url` parameters to `create_app()`.
- `src/substrate/sidecar/__main__.py` — reads `SUBSTRATE_DISABLE_DOCS` env var and passes `None` when enabled.
