---
number: "011"
title: Event dataclass missing workflow_name field
severity: low
status: implemented
kind: bug
author: claude-opus
date: "2026-05-05"
tags: [api-surface, types]
---

## Problem

The `events` table has a `workflow_name` column (set on every insert), but the `Event` frozen dataclass (`_types.py`) only carries `workflow_version`. `_row_to_event` in `_events.py:21-36` drops the field on the read path.

Consumers that need to know which workflow a historical event belongs to (e.g., a federated UI showing events across multiple workflows in a project, or any cross-workflow audit query) cannot get it from the API type. They'd have to read `events` directly, defeating §19's "no Postgres leaks" boundary.

## Spec reference

- §19.5 ("Domain types: ... `Event` ... value objects with documented JSON serialization")
- FR-03 (event field list — `workflow_version` is named; `workflow_name` is implicit because each event references a registered workflow)

## Location

- `src/substrate/_types.py` — `Event` dataclass
- `src/substrate/_events.py` — `_row_to_event` and the `_EVENT_FIELDS` SELECT list

## Suggested fix

Add `workflow_name: str` to the `Event` dataclass and to `_row_to_event`. Update `to_dict` / `from_dict` accordingly. Schema already has the column.
