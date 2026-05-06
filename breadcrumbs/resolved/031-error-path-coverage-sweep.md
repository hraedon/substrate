# Substrate Error-Path Coverage Sweep

**Date:** 2026-05-06
**Scope:** All ErrorCode enum members in `_errors.py`
**Method:** Each error code traced to raise sites in source, then grep'd for exercise in test files.

## Summary

| Category | Count |
|----------|-------|
| Total error codes defined | 38 |
| Tested (error code asserted in test) | 10 |
| Untested (raised in code, no test exercises) | 22 |
| Weakly tested (error occurs but code not asserted) | ~6 |
| Dead code (defined, never raised) | 4 |

## Tested error codes (10)

| Error Code | Raise Sites | Test |
|-----------|-------------|------|
| `CLAIM_CONTESTED` | `_claims.py:75` | `test_smoke.py:185` |
| `CONCURRENT_MODIFICATION` | `_events.py:93` | `test_idempotency.py:111,144` |
| `IDEMPOTENCY_COLLISION_WITH_DIFFERENT_PAYLOAD` | `_events.py:74,80` | `test_idempotency.py:45,69` |
| `WORKFLOW_VERSION_CONFLICT` | `__init__.py:201` | `test_smoke.py:44` |
| `VALIDATOR_TIMEOUT` | `_hooks.py:34` | `test_phase2.py:213` |
| `VALIDATOR_FAILED` | `_hooks.py:41` | `test_phase2.py:186` |
| `HOOK_NOT_FOUND` | `_hooks.py:252` | `test_phase2.py:469` |
| `ACTOR_ROLE_NOT_AUTHORIZED` | `_actor_roles.py:89` | `test_phase3.py:73` |
| `ACTOR_ROLE_ALREADY_REGISTERED` | `_actor_roles.py:22` | `test_phase3.py:42` |
| `ACTOR_ROLE_NOT_REGISTERED` | `_actor_roles.py:46` | `test_phase3.py:53` |

## Untested error codes by priority

### Critical (security / correctness gates)

| Error Code | Raise Sites | Why it matters |
|-----------|-------------|----------------|
| `UNKNOWN_KEY_ID` | `_keys.py:37,45,51,106,115` | Authentication rejection — untested |
| `REVOKED_KEY_ID` | `_keys.py:121,130` | Key revocation enforcement — untested |
| `MIGRATION_REQUIRED` | `_migrations.py:86` | Startup fail-fast — untested |
| `WORKFLOW_VERSION_INCOMPATIBLE` | `_integrity.py:53` | Startup fail-fast — untested |
| `CLAIM_LOST` | `_claims.py:242,251,299` | Stale claim protection — untested |

### High (core API correctness)

| Error Code | Raise Sites | Why it matters |
|-----------|-------------|----------------|
| `CUSTOM_FIELD_VIOLATION` | `_workflow.py` (9 sites) | Most raise sites of any error — completely untested |
| `WORKFLOW_SEMANTIC_ERROR` | `_workflow.py` (10 sites) | Workflow validation rejection — untested |
| `WORK_ITEM_NOT_FOUND` | `__init__.py`, `_claims.py`, `_events.py` (6 sites) | Core lookup failure — untested |
| `INVALID_TRANSITION` | `__init__.py:405` | State machine enforcement — untested by error code |
| `ROLE_NOT_PERMITTED` | `__init__.py:415` | Role gating — untested by error code |
| `TRANSITION_VIA_APPEND_BLOCKED` | `__init__.py:323` | API surface enforcement — untested |

### Medium (links, workflow, misc)

| Error Code | Raise Sites |
|-----------|-------------|
| `WORKFLOW_NOT_REGISTERED` | `_work_items.py:65`, `_links.py:31`, `__init__.py:391` |
| `WORK_ITEM_TYPE_NOT_DECLARED` | `_workflow.py:225`, `_work_items.py:96` |
| `WORKFLOW_VALIDATION_FAILED` | `_workflow.py:41,54` |
| `DB_NOT_FOUND` | `_connection.py:104` |
| `LINK_TYPE_NOT_ALLOWED` | `_links.py:47` |
| `LINK_TARGET_NOT_FOUND` | `_links.py:79,159` |
| `LINK_CROSS_PROJECT` | `_links.py:89` |
| `LINK_NOT_FOUND` | `_links.py:187` |
| `CLAIM_NOT_FOUND` | `_claims.py:236,293` |
| `NOT_BEFORE_FUTURE` | `_claims.py:44` |
| `INVALID_FILTER` | `__init__.py:520,525` |

### Note on "weakly tested"

Several error paths ARE exercised by tests but the tests only catch `SubstrateError` or match a broad substring, without asserting the specific error code. Examples:
- `INVALID_TRANSITION`: `test_smoke.py:110-118` catches SubstrateError but doesn't check the code
- `ROLE_NOT_PERMITTED`: `test_smoke.py:120-134` catches SubstrateError but doesn't check the code
- `WORKFLOW_NOT_REGISTERED`: `test_smoke.py:67-81` catches error broadly

These are *functionally* tested but *regression-weak* — a refactor that changes the error code would not be caught.

## Dead code (defined, never raised)

| Error Code | Notes |
|-----------|-------|
| `CLAIM_NOT_EXPIRED` | Defined but no code raises it |
| `IDEMPOTENCY_COLLISION` | Only `IDEMPOTENCY_COLLISION_WITH_DIFFERENT_PAYLOAD` is actually raised |
| `LIBRARY_IS_SOLE_SIGNER` | AC-33 is tested via a different mechanism (`test_api_surface.py`) |
| `DEPRECATED_KEY_ID` | `_keys.py:134` logs a warning but does not raise |
| `REPLAY_HALTED` | Defined but replay uses RuntimeError internally |
| `HOOK_NOT_DEAD_LETTERED` | Defined but no code raises it |

Action: remove dead codes or implement the raises (for `DEPRECATED_KEY_ID` and `LIBRARY_IS_SOLE_SIGNER`, the spec says they should raise).

## Recommendations

1. **Add error code assertions to existing tests.** Tests at `test_smoke.py:110-134` already trigger `INVALID_TRANSITION` and `ROLE_NOT_PERMITTED` — add `assert err.code == ErrorCode.INVALID_TRANSITION`. Low effort, high regression value.

2. **Write dedicated tests for the 5 critical untested codes.** Each is a small deterministic test. `UNKNOWN_KEY_ID` and `REVOKED_KEY_ID` are the most important (authentication surface).

3. **Decide on dead codes.** `DEPRECATED_KEY_ID` should probably raise (spec says "deprecated key_id: accept; emit structured warning" — accept, not reject — so maybe NOT raising is correct). `LIBRARY_IS_SOLE_SIGNER` is tested via API surface test but the error code itself is dead — the check is structural (no `signature` param on public methods), not runtime.

4. **Link subsystem has 0 error-path tests.** Four link-related error codes are untested. Write one test fixture that exercises each: `LINK_TYPE_NOT_ALLOWED`, `LINK_TARGET_NOT_FOUND`, `LINK_CROSS_PROJECT`, `LINK_NOT_FOUND`.
