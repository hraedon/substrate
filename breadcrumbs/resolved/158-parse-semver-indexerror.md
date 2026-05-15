---
number: "158"
title: "_parse_semver crashes with IndexError on non-3-part version strings"
severity: medium
status: implemented
resolution: "_parse_semver now validates exactly 3 dot-separated components, raises SubstrateError(WORKFLOW_VERSION_INCOMPATIBLE) on malformed input with descriptive message. Removed redundant try/except from caller."
kind: bug
author: agent
date: "2026-05-15"
tags: [integrity, startup]
related: []
---

## Problem

`_parse_semver` in `src/substrate/_integrity.py` (~10-38) likely does something like:

```python
major, minor, patch =version.split(".")
```

If the version string is malformed (e.g., "1.0" or "1.0.0-beta+build123" or non-numeric),
the code can raise `IndexError` or `ValueError`. The error is swallowed by the caller,
but the startup message is poor and the agent gets no useful diagnostics.

## Impact

A bad version string in the library or a migration causes a confusing startup failure.
Operators cannot tell whether the problem is a version mismatch or a crash.

## Files / Lines

- `src/substrate/_integrity.py` (~10-38)

## Fix

Validate that the split produces exactly 3 integer components and raise a clear
`SubstrateError` with a descriptive message on malformed input.
