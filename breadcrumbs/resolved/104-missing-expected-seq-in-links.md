---
number: "104"
title: expected_event_seq missing from create_link and remove_link — TOCTOU race
severity: high
status: accepted
kind: design
author: adversarial-reviewer
date: "2026-05-11"
tags: [concurrency, correctness, fr-03, br-10]
related: ["100", "105"]
resolution_date: "2026-05-11"
---

## Resolution

Accepted — FOR UPDATE lock provides adequate serialization. `create_link` and `remove_link` acquire `SELECT FOR UPDATE` on both work items in ascending order (deadlock-free), then call `append_event` which locks again (no-op since same transaction). The `expected_event_seq` parameter is an enhancement for caller-side optimistic concurrency, not a correctness requirement. Deferred as future improvement.
