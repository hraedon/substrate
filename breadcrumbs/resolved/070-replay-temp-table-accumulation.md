---
number: "070"
title: "Replay temp tables accumulate between replay() calls"
severity: low
status: accepted
kind: improvement
author: deepseek-v4-pro
date: "2026-05-11"
tags: [replay, cleanup, postgres]
related: []
resolution_date: "2026-05-11"
---

## Resolution

Accepted — orphaned tables are cleaned at the start of the next `replay()` call. The caller may want to query the output table after replay, so dropping it automatically would change the API contract. Using session-scoped TEMP tables would break if the connection is returned to the pool between replays. Current behavior is correct and pragmatic.
