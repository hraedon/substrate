---
number: "074"
title: "continue_on_revoked=True skips signature verification entirely"
severity: high
status: implemented
kind: design
author: glm-5.1-adversarial
date: "2026-05-11"
tags: [adversarial-review]
related: []
resolution_date: "2026-05-11"
---

## Resolution

Fixed. Separated key lookup from status check in `_replay.py:_replay_work_item`. When `continue_on_revoked=True`:

- **Revoked keys**: `get_key()` retrieves the key material, signature is verified cryptographically, warning is logged. If the signature is invalid, replay still halts.
- **Unknown keys** (no material available): signature verification is skipped, warning is logged. This is the only case where verification is truly impossible.

Added 2 tests: `test_replay_revoked_key_with_wrong_secret_halts` proves a revoked key with wrong material now halts (was silently skipped), and `test_replay_unknown_key_with_continue_on_revoked_skips` confirms unknown keys still skip gracefully.
