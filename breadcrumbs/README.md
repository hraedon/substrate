# Breadcrumbs

Defects, design questions, and improvements for substrate. One file per item, numbered for reference. Numbers do not imply priority order — see `severity` in each file's frontmatter.

## Schema

```yaml
---
number: "001"
title: Short descriptive title
severity: critical | high | medium | low
status: proposed | in_progress | implemented | obsolete
kind: bug | design | improvement
author: who-raised-it
date: "YYYY-MM-DD"
tags: [topic, fr-XX, ac-NN]
related: ["002", "003"]
---
```

## Severity

- **critical** — blocks correct operation; substrate cannot be trusted for stated guarantees
- **high** — load-bearing spec property unfulfilled; silent-correctness risk
- **medium** — defect with workaround or limited blast radius
- **low** — edge case, polish, or minor API ergonomics

## Open

| # | Title | Severity | Tags |
|---|---|---|---|
| 007 | [idempotency_key parameter accepted but ignored on several mutations](007-unwired-idempotency-keys.md) | medium | idempotency, br-12 |
| 008 | [Signing scheme does not deliver jsonb-drift survival promised by FR-15](008-signing-scheme-jsonb-drift.md) | high | signing, fr-15, ac-26, spec-ambiguity |
| 009 | [JCS implementation has edge-case correctness gaps](009-jcs-edge-cases.md) | medium | signing, jcs, audit |
| 016 | [Pagination over moving last_event_seq target can skip or duplicate](016-pagination-moving-target.md) | low | query, fr-05b |
| 017 | [Test coverage missing for load-bearing ACs](017-test-coverage-load-bearing-acs.md) | high | testing, ac-17, ac-24, ac-26, ac-28, ac-29, ac-33, ac-34 |

## Resolved

| # | Title | Severity | Resolution |
|---|---|---|---|
| 001 | Replay does not verify signatures or check key status | high | [resolved/001](resolved/001-replay-no-signature-verification.md) |
| 002 | Replay output table contains live snapshot, not derived state | medium | [resolved/002](resolved/002-replay-table-live-snapshot.md) |
| 003 | Drift detection compares only current_state and last_event_seq | high | [resolved/003](resolved/003-drift-detection-incomplete.md) |
| 004 | Idempotency silently accepts different payloads under same event_id | medium | [resolved/004](resolved/004-idempotency-silent-mismatch.md) |
| 005 | Claim mutations do not emit events | high | [resolved/005](resolved/005-claims-emit-no-events.md) |
| 006 | Heartbeat does not check attempt_number for stolen-by-self | medium | [resolved/006](resolved/006-heartbeat-attempt-number.md) |
| 010 | append_event allows arbitrary transition strings, bypassing FR-11/FR-12 | high | [resolved/010](resolved/010-append-event-bypasses-validation.md) |
| 011 | Event dataclass missing workflow_name field | low | [resolved/011](resolved/011-event-missing-workflow-name.md) |
| 012 | Event.timestamp returned to caller differs from server-side stored value | low | [resolved/012](resolved/012-event-timestamp-mismatch.md) |
| 013 | has_link_type filter does not account for link_removed events | medium | [resolved/013](resolved/013-has-link-type-ignores-removal.md) |
| 014 | remove_link does not validate that the link exists | low | [resolved/014](resolved/014-remove-link-no-existence-check.md) |
| 015 | Replay matches transitions by name only, not (name, from_state) | medium | [resolved/015](resolved/015-replay-name-only-match.md) |
