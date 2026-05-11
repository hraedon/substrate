---
number: "074"
title: "continue_on_revoked=True skips signature verification entirely"
severity: high
status: deferred
kind: design
author: glm-5.1-adversarial
date: "2026-05-11"
tags: [adversarial-review]
related: []
---

## Context

`_replay.py:219-253` — When `verify_key_status` raises, `key_entry` stays None
and the `if key_entry is not None` block is skipped. This means a completely
unknown key (not just revoked) passes without any cryptographic check.

## Options

- Separate key lookup from status check; always verify signature when key
  material is available, only skip revocation status
- Accept current behavior (documented limitation)
