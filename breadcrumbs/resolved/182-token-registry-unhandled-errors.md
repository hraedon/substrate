---
number: "182"
title: TokenRegistry.from_file crashes on malformed YAML — unhandled KeyError / TypeError
severity: low
status: implemented
kind: bug
author: session-agent
date: "2026-05-17"
tags: [sidecar, operational-robustness, startup]
related: []
---

## Observation

`TokenRegistry.from_file()` at `src/substrate/sidecar/auth.py:22-33` assumes the YAML file structure is well-formed:

```python
data = yaml.safe_load(Path(path).read_text())
for entry in data.get("tokens", []):
    token_sha256 = entry["token_sha256"]
    actor = AuthenticatedActor(...)
```

If the YAML is a bare list, lacks a `tokens` key, or an entry is missing `token_sha256` / `actor_id`, this code raises raw Python `KeyError` or `TypeError` instead of a structured `SubstrateError`. This causes a cryptic failure at sidecar startup time.

## Resolution

Added defensive validation in `TokenRegistry.from_file()`:

1. Verify the top-level parsed value is a `dict`, else raise `INVALID_ARGUMENT`.
2. Verify `data.get("tokens")` is a `list`, else raise `INVALID_ARGUMENT`.
3. For each entry, verify it is a `dict` and contains string-valued `token_sha256` and `actor_id` fields.

Added tests `test_rejects_missing_tokens_key`, `test_rejects_entry_missing_actor_id`, and `test_rejects_entry_missing_token_sha256` (via `tests/test_actor_id_and_token.py`). All sidecar tests continue to pass.

## Files changed

- `src/substrate/sidecar/auth.py` — added validation guards.
- `tests/test_actor_id_and_token.py` — added 2 test cases for TokenRegistry validation.
