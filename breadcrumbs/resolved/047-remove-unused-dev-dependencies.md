---
number: "047"
title: Remove unused pytest-postgresql and testcontainers dev dependencies
severity: low
status: proposed
kind: improvement
author: assistant
date: "2026-05-07"
tags: [dependencies, cleanup]
related: []
---

## Observation

`pytest-postgresql` and `testcontainers[postgres]` are listed in `[project.optional-dependencies].dev` in `pyproject.toml`. Every test in the suite uses the hardcoded localhost DSN (`postgresql://substrate_test:substrate_test@localhost:5432/substrate_test`). Neither package is imported or used anywhere in the test tree.

These packages add install time and potential version-conflict surface without providing value.

## Proposed

Audit whether any test file or fixture references either package. If confirmed unused, remove both from `dev` dependencies. If they are reserved for a planned future fixture strategy (e.g. per-test ephemeral Postgres), document that plan and keep them; otherwise drop them to keep the dependency tree minimal.
