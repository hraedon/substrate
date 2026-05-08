---
number: "057"
title: Replay output table mixes replayed state with live-projection columns
severity: low
status: implemented
kind: bug
author: adversarial-reviewer
date: "2026-05-08"
tags: [fr-16, §18.5, replay, projection]
---

## Resolution

Set `last_event_at`, `claimed_by`, and `claim_expires_at` to NULL in the replay output table INSERT. Replay does not derive claim state or event timestamps, so these columns were semantically misleading live-snapshot values. Making them NULL makes the table self-documenting: only columns with values are genuinely replayed.