---
number: "183"
title: __init__.py and _in_memory.py still exceed 1300 lines — need further decomposition
severity: medium
status: proposed
kind: improvement
author: session-agent
date: "2026-05-17"
tags: [refactoring, maintainability, code-health]
related: []
---

## Resolution

2026-05-17 session: Delivered Phase A decomposition.

- Created `src/substrate/_in_memory_claims.py` — extracted `acquire_claim`, `heartbeat_claim`, `release_claim`, `sweep_expired_claims` bodies plus `_check_escalation` and `_append_claim_event` helpers.
- Created `src/substrate/_in_memory_links.py` — extracted `create_link` and `remove_link` bodies.
- Created `src/substrate/_in_memory_hooks.py` — extracted `poll_hooks`, `_move_to_dead_letter`, `requeue_dead_lettered_hook`, `list_dead_lettered_hooks`.
- Created `src/substrate/_in_memory_recurrence.py` — extracted `register_recurrence_rule`, `list_recurrence_rules`, `due_recurrences`, `fire_recurrence`, `cancel_recurrence_rule`, `update_recurrence_rule`.
- Created `src/substrate/_in_memory_replay.py` — extracted `replay()` body (~135 lines).
- `_in_memory.py` reduced from **1,619 → 1,129 lines** (down 490 lines).
- `__init__.py` reduced from **1,393 → 1,371 lines** (import consolidation only).
- Also fixed bare `except:` in `__init__.py` and consolidated split `_types` imports.
- Added `--strict-markers` to pytest config.
- All 561 tests pass, lint clean, property tests pass.

Remaining in `_in_memory.py` (~1,129 lines) are:
- `__init__`, `create_project`, `close` (~35 lines)
- `register_validator`, `register_hook_handler`, start/stop consumer (~10 lines)
- `register_workflow`, `register_workflow_file`, `get_workflow` (~60 lines)
- `_create_work_item`, `create_work_item` (~90 lines)
- `append_event`, `transition`, `read_events`, `read_events_since` (~150 lines)
- `query_work_items`, `get_work_item` (~80 lines)
- `update_not_before` (~35 lines)
- `register_actor_role`, `unregister_actor_role`, `list_actor_roles` (~40 lines)
- `validate_actor_metadata`, `actor_metadata_complete` (~10 lines)
- `_resolve_workflow`, `_resolve_wf_def`, `_validate_refs_in_memory`, `_append_simple_event`, `_active_link_set`, `_wi_to_work_item` (~100 lines)

Phase B (`_work_items_api.py`, `_events_api.py`) is deferred to future session.

## Status

status: implemented
