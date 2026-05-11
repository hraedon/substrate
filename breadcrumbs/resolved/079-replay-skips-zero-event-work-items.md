---
number: "079"
title: "Replay skips work items with zero events silently"
severity: medium
status: accepted
kind: design
author: glm-5.1-adversarial
date: "2026-05-11"
tags: [adversarial-review]
related: []
resolution_date: "2026-05-11"
---

## Resolution

Accepted — work items always have at least a `created` event. A work item with zero events in `work_items_current` is already corrupt beyond what replay can validate. Replay validates event-derived state; a zero-event item has no event-derived state to compare. Treating it as halted would add noise without actionable signal.
