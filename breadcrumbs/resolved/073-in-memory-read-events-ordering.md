---
number: "073"
title: "InMemory read_events returns oldest events; Postgres returns newest"
severity: high
status: proposed
kind: bug
author: glm-5.1-adversarial
date: "2026-05-11"
tags: [adversarial-review]
related: []
---

## Context

`_in_memory.py:634-635` — When querying by `work_item_id` with a limit, InMemory
sorts ascending and returns `[:limit]` (oldest). Postgres sorts DESC, takes
limit, then reverses (newest). Conformance tests don't catch this because they
don't exceed the default limit.

## Fix

Match Postgres ordering: sort descending, take limit, reverse to ascending.
