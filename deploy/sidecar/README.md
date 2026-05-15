# Substrate HTTP Sidecar

Thin 1:1 HTTP pass-through of the Substrate Python API. Exposes every public
operation over JSON endpoints for non-Python consumers.

## Quick start

```bash
pip install ".[sidecar]"

export SUBSTRATE_DSN="postgresql://user:pass@host:5432/db"
export SUBSTRATE_PROJECT="my_project"
export SUBSTRATE_HMAC_KEY_PATH="/path/to/keys.json"
export SUBSTRATE_TOKENS_PATH="/path/to/tokens.yaml"

python -m substrate.sidecar
```

Or via Docker:

```bash
docker build -t substrate-sidecar -f deploy/sidecar/Dockerfile .
docker run -e SUBSTRATE_DSN=... -e SUBSTRATE_PROJECT=... \
  -e SUBSTRATE_HMAC_KEY_PATH=... -e SUBSTRATE_TOKENS_PATH=... \
  substrate-sidecar
```

## Environment variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `SUBSTRATE_DSN` | Yes | | Postgres connection string |
| `SUBSTRATE_PROJECT` | Yes | | Project (schema) name |
| `SUBSTRATE_HMAC_KEY_PATH` | Yes | | Path to HMAC key-set JSON |
| `SUBSTRATE_TOKENS_PATH` | Yes | | Path to bearer-token YAML |
| `SUBSTRATE_BIND` | No | `0.0.0.0:8080` | Listen address |
| `SUBSTRATE_POOL_MIN` | No | `1` | Min pool size |
| `SUBSTRATE_POOL_MAX` | No | `10` | Max pool size |

## Token file format

```yaml
tokens:
  - token_sha256: "<sha256-hex-of-raw-token>"
    actor_id: "agent-1"
    actor_kind: "agent"
    allowed_roles: ["coder", "reviewer"]
```

Tokens are stored as SHA-256 hashes. The raw token is sent in the
`Authorization: Bearer <token>` header.

## Architectural notes

- **Signing is server-side only.** The sidecar holds the HMAC key material.
  Request bodies must not include `signature` or `payload_canonical_hash`.
  Including either returns `400 LIBRARY_IS_SOLE_SIGNER`.

- **Synchronous validators are not exposed over HTTP.** Per spec FR-13,
  transition validators must not perform I/O and must be Python callables.
  Non-Python consumers should express invariants as async hooks and use the
  `POST /v1/hooks/claim` polling API.

- **One sidecar per project.** Multi-project routing is deferred.

- **API version is `/v1`.** Breaking changes will use `/v2`.

## Hook queue for non-Python consumers

Instead of registering Python handlers, use the HTTP hook lifecycle:

1. `POST /v1/hooks/claim` — claim a batch of pending hooks
2. Process hooks in your own runtime
3. `POST /v1/hooks/{id}/complete` — ack success
4. `POST /v1/hooks/{id}/fail` — ack failure (requeues or dead-letters)

Run `POST /v1/sweep_expired_hook_leases` on a timer to reclaim hooks from
crashed consumers.
