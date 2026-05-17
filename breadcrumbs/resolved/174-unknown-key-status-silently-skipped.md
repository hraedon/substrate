---
number: "174"
title: Unknown key status silently skipped — typo in status field drops keys from rotation
severity: low
status: implemented
kind: bug
author: security-audit
date: "2026-05-17"
tags: [keys, signing, operational, observability]
related: ["066"]
---

## Resolution

Added a `log.warning("keys.unknown_status", key_id=..., status=...)` before the `continue` in `KeySet._load()` (`src/substrate/_keys.py:61`). The existing suite of tests continues to pass; no behavioural change for valid status values.

## Files changed

- `src/substrate/_keys.py` — emit structured log warning for unrecognized key statuses.
