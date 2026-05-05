# Substrate Worklog

Structured log of development sessions and milestones.

---

## 2026-05-05 — Session 5: BC-022 content-based idempotency, BC-023/024/025 feature work, BC-009/016/017 final closeout

**Focus:** Implement 6 breadcrumbs, resolve all remaining open items

**Context:** Session 4 left 6 open breadcrumbs (009, 016, 017 held open; 022, 023, 024, 025 newly filed by Opus). User asked to implement BC-022 (content-based idempotency) first, then BC-023/024/025, then close out BC-009/016/017.

**Delivered:**

BC-022 — Content-based workflow registration idempotency:
- `migrations/004_workflow_content_hash.sql`: adds `content_hash BYTEA` to `workflow_registry`
- `src/substrate/_errors.py`: renamed `WORKFLOW_VERSION_ALREADY_REGISTERED` → `WORKFLOW_VERSION_CONFLICT`
- `src/substrate/_workflow.py`: added `compute_content_hash()` and `compute_content_hash_from_dict()` using JCS + SHA-256
- `src/substrate/__init__.py`: `register_workflow()` computes hash, compares on collision — idempotent if same, raises if different; lazy-backfills legacy NULL hashes
- `spec.md` §8: amended registry uniqueness and error table with BC-022 rationale
- `tests/test_smoke.py`: `test_register_version_conflict` added

BC-023 — Optional payload on links:
- `src/substrate/_types.py`: `Link` dataclass gains `payload: dict | None`
- `src/substrate/_links.py`: `create_link()` accepts optional `payload`, stores in `link_created` event JSONB
- `src/substrate/__init__.py`: public `create_link()` passes `payload` through
- `tests/test_smoke.py`: `test_create_link_with_payload`

BC-024 — Telemetry-via-hooks pattern documentation:
- `AGENTS.md`: added "Patterns > Telemetry via hooks" section

BC-025 — Scale benchmarks:
- `tests/test_scale.py`: 3 benchmarks (replay, link queries, hook drain) marked `@pytest.mark.slow`
- `pyproject.toml`: registered `slow` marker
- Baselines: ~0.46ms/event replay, ~3ms link query, ~914 hooks/sec drain

BC-009 — JCS edge-case tests:
- `tests/test_jcs.py`: 16 tests covering float boundaries, integer domain (2^53), UTF-16 key ordering, determinism, NFC caveat

BC-016 — Pagination stability:
- Fix already in place (stable `work_item_id` cursor)
- `tests/test_smoke.py`: `test_pagination_stable_no_duplicates`

BC-017 — Test coverage closeout:
- All 8 load-bearing ACs + Phase 2 ACs verified covered

**Breadcrumbs resolved:** BC-009, BC-016, BC-017, BC-022, BC-023, BC-024, BC-025

**Test/lint results:** 81 passed + 3 slow benchmarks (excluded), ruff clean. Zero open breadcrumbs.

---

## 2026-05-05 — Session 4: Audit sweep — critical bug fix, replay correctness, robustness hardening

**Focus:** Comprehensive codebase audit and fix of 14 issues across correctness, robustness, concurrency, and style

**Context:** Phase 2 was complete with 61 tests passing. Two open breadcrumbs (BC-020, BC-021) from the prior session remained. User asked for a critical audit of the whole repo beyond existing breadcrumbs.

**Delivered:**

Critical bugs (1–3):
- **sweep_expired_claims crash** — `_claims.py:339`: `row[0]`/`row[1]` on `dict_row` results raised `KeyError`; fixed to `row["work_item_id"]`/`row["actor_id"]`
- **custom_fields lost in replay** — `_events.py:append_transition_event`: `custom_fields_update` now persisted in event payload under `custom_fields_update` key; `_replay.py` reads it back correctly
- **not_before lost in replay** — `_work_items.py:create_work_item`: `not_before` now included in `created` event payload as ISO string
- **acquire_claim return type** — `_claims.py`: return annotation corrected to `tuple[Claim, bool]` after BC-020 fix
