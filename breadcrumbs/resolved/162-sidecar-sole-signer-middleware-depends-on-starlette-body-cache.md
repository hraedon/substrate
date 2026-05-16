---
number: "162"
title: "Sidecar sole-signer middleware reads request body before Pydantic — depends on Starlette body caching"
severity: medium
status: resolved
kind: bug
author: opus-4-7
date: "2026-05-16"
tags: [sidecar, plan-005, middleware, fragility]
related: []
---

## Problem

`src/substrate/sidecar/app.py:24-49` defines `sole_signer_middleware`, which calls `await request.body()` and parses JSON to check for `signature` / `payload_canonical_hash` fields. The downstream Pydantic route handler then re-reads the body to validate the request.

This only works because Starlette caches the read body on the `Request` object. The contract is **implicit** — not documented in Starlette's public API as a stability guarantee for middleware. If a future Starlette release changes the caching behavior (e.g., stream-only requests, or async-iter consumption), the middleware will break silently: either the middleware sees an empty body, or the Pydantic handler sees an empty body. Either way the failure mode is a confusing 422 or auth bypass, not an obvious crash.

## Impact

- Latent fragility against a Starlette upgrade. Substrate pins FastAPI/Starlette versions, so this is a future risk, not a current bug.
- The 400-vs-422 sole-signer rejection (the original motivation for the middleware, per Session 28 reflection) is correct; the implementation is what's fragile.

## Files / Lines

- `src/substrate/sidecar/app.py:24-49` — sole_signer_middleware

## Fix

Options, in order of preference:

1. **Move sole-signer validation into a Pydantic validator** on each request model that needs it (a shared mixin). Pydantic owns body parsing; the validator runs after parsing and can reject with a structured 400 via a custom exception handler.
2. **Use Starlette's `Request.stream()` once + cache explicitly** on `request.state.raw_body`, and have route handlers consume from there. Makes the contract explicit.
3. **Pin Starlette major version** and add a regression test that hits the middleware with a non-sole-signer body, then asserts the handler still receives the body. Cheapest mitigation, doesn't fix the design.

## Lesson

Middleware that consumes the request body is one of the FastAPI/Starlette sharp edges. Where possible, validation logic that depends on body content belongs in Pydantic, where the parsing contract is owned end-to-end.
