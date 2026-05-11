---
number: "097"
title: drop_project_schema does not validate project name before executing DROP SCHEMA
severity: medium
status: open
kind: bug
author: adversarial-reviewer
date: "2026-05-11"
tags: [testing, security, schema]
related: [091]
---

## Observation

`drop_project_schema` in `_testing.py:33-43` directly formats `Identifier(project)` without calling `validate_project_name`. If a test ever passes an empty string or a reserved name, it can damage the database.

## Impact

Potential accidental DROP of `public` or system schemas.

## Proposed Fix

Call `validate_project_name(project)` before executing `DROP SCHEMA`.

## Acceptance Criteria

- [ ] `drop_project_schema` validates the name.
- [ ] Invalid names raise `ValueError` before any SQL is executed.
