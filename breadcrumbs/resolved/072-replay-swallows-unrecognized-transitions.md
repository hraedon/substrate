---
number: "072"
title: "Replay silently swallows unrecognized transitions"
severity: critical
status: proposed
kind: bug
author: glm-5.1-adversarial
date: "2026-05-11"
tags: [adversarial-review]
related: []
---

## Context

`_replay.py:296-307` — When a transition name doesn't match any definition entry
AND `name_matches` is False, execution falls through without error. The state is
unchanged but `custom_fields_update` at lines 306-307 is still applied,
corrupting the replayed state with a false negative.

## Fix

Add unconditional `else: raise _ReplayHaltError(...)` when transition not found
in workflow definition.
