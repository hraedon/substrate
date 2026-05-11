---
number: "105"
title: Replay skip of revoked-key events with continue_on_revoked=True leaves bad events in log
severity: high
status: accepted
kind: design
author: adversarial-reviewer
date: "2026-05-11"
tags: [security, replay, fr-25]
related: ["074"]
resolution_date: "2026-05-11"
---

## Resolution

Accepted — by design. Events are the immutable audit trail (spec: events are never edited). `continue_on_revoked=True` is for operators who accept the risk and want to proceed past key-rotation gaps. The `ReplayReport.warnings` count tells them how many events were skipped. Removing or flagging events would violate the event-sourcing model. The operator is responsible for investigating skipped events.
