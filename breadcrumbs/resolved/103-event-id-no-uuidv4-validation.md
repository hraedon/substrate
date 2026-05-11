---
number: "103"
title: Client-supplied event_id not validated as UUIDv4; no entropy guarantees
severity: critical
status: implemented
kind: bug
author: adversarial-reviewer
date: "2026-05-11"
tags: [security, idempotency, fr-03]
related: ["102"]
resolution_date: "2026-05-11"
---

## Resolution

Fixed. Added `validate_event_id()` in `_contract.py` that checks `event_id.version == 4`. Wired into all public API methods that accept `event_id`: `append_event`, `transition`, `create_work_item`, `acquire_claim`, `release_claim`, `create_link`, `remove_link`, `update_not_before`. Non-v4 UUIDs now raise `SubstrateError(INVALID_ARGUMENT)`.
