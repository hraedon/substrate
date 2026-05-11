---
number: "096"
title: run_validator loses original exception chain
severity: medium
status: open
kind: bug
author: adversarial-reviewer
date: "2026-05-11"
tags: [hooks, observability, exceptions]
related: []
---

## Observation

`run_validator` in `_hooks.py:23-44` catches `Exception` and wraps it in `SubstrateError` without chaining:

```python
except Exception as e:
    raise SubstrateError(
        ErrorCode.VALIDATOR_FAILED,
        f"Validator {validator_name!r} failed: {e}",
    )
```

The original traceback is truncated to the `run_validator` frame.

## Impact

Root-cause analysis is painful for consumers debugging validators.

## Proposed Fix

Add `from e` to preserve the exception chain.

## Acceptance Criteria

- [ ] `run_validator` raises with `from e`.
- [ ] Test asserts `__cause__` is set on the resulting `SubstrateError`.
