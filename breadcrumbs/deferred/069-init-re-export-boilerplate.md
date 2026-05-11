---
number: "069"
title: __init__.py has excessive _types re-export boilerplate
severity: low
status: deferred
kind: improvement
author: deepseek-v4-pro
date: "2026-05-11"
tags: [public-api, refactoring, polish]
related: []
---

## Context

`__init__.py` at 1340 lines has ~20 individual `from ._types import (X as X,)`
blocks (lines 41-86) for re-exporting domain types. These are all defined in
`_types.py:739` as the canonical file.

## Options

- Collapse into a single `from ._types import (A, B, C, ...)` block
- Use `from . import _types` and reference `_types.X` (would break existing
  public API compatibility)
- Accept current style
