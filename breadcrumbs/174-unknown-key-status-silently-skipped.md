---
number: "174"
title: Unknown key status silently skipped — typo in status field drops keys from rotation
severity: low
status: proposed
kind: bug
author: security-audit
date: "2026-05-17"
tags: [keys, signing, operational, observability]
related: ["066"]
---

## Observation

`KeySet._load()` at `_keys.py:59-61` silently skips keys with unrecognized `status` values:

```python
status = entry.get("status", "active")
if status not in ("active", "deprecated", "revoked"):
    continue
```

If an operator accidentally uses a misspelled status (e.g., `"actve"`), the key entry is silently ignored. No structured log warning is emitted, no metric is incremented. The only signal is the key count in the `keys.loaded` log line at line 77-82, which would show fewer keys than expected.

## Proposed

- Emit a `log.warning("keys.unknown_status", key_id=key_id, status=status)` before the `continue`.
- Increment a `keys_unknown_status` metric counter.
- Optionally: reject entirely (raise `SubstrateError`) for unknown status values rather than silently skipping, making misconfiguration fail fast.
