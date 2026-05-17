---
number: "178"
title: Sidecar sole-signer middleware reassembles body from stream() with no size limit
severity: low
status: proposed
kind: improvement
author: security-audit
date: "2026-05-17"
tags: [sidecar, security, denial-of-service, memory]
related: ["162"]
---

## Observation

The `sole_signer_middleware` at `sidecar/app.py:27-30` reassembles the request body from `request.stream()` without any size limit:

```python
body_bytes = b""
async for chunk in request.stream():
    body_bytes += chunk
```

A client could send a POST request with a multi-gigabyte body, exhausting server memory before FastAPI's Pydantic model validation or any size limit kicks in. BC-162 addressed the explicit streaming/caching pattern, but did not add a size guard.

## Proposed

- Add a maximum body size check within the stream loop (e.g., 10MB hard limit, configurable). Break and reject with 413 Payload Too Large if exceeded.
- Alternatively: move the sole-signer check to a FastAPI dependency attached to each route handler, running after Pydantic model parsing (which applies field-level constraints) rather than before.
