# substrate

Coordination + state plane for agent pipelines over Postgres.

[![Tests](https://img.shields.io/badge/tests-293%20passing-brightgreen)]()
[![License](https://img.shields.io/badge/license-MIT-blue)]()
[![Status](https://img.shields.io/badge/status-MVP%20%2B%20Phase%202%20%2B%20Phase%203%20complete-brightgreen)]()

Substrate is a Python library that provides durable claims, event-sourced state, validated state transitions, and typed links for multi-role agent pipelines. Each project deploys substrate as its own isolated instance using schema-per-project isolation within a single Postgres database.

## Quick Start

```bash
# Install
pip install -e .

# Start test Postgres
docker compose -f docker-compose.test.yml up -d

# Run tests
pytest tests/ -v
```

## Usage

```python
from substrate import Substrate

# Initialize a project (one-time)
sub = Substrate.create_project(
    dsn="postgresql://user:pass@host:5432/mydb",
    project="factory",
    hmac_key_path="/secrets/substrate-keys.json",
)

# Register a workflow
sub.register_workflow_file("workflows/spec-pipeline.yaml")

# Create work
wi, event = sub.create_work_item(
    workflow_name="spec_pipeline",
    work_item_type="feature",
    actor_id="agent-1",
    actor_metadata={"role": "agent", "model": "gpt-4"},
    custom_fields={"title": "Add authentication"},
)

# Claim and transition
claim = sub.acquire_claim(wi.work_item_id, "agent-1", ttl_seconds=300)
sub.transition(wi.work_item_id, "start", "agent-1", actor_metadata={"role": "agent"})

# Query available work
page = sub.query_work_items(
    workflow_name="spec_pipeline",
    claimable_now=True,
    current_states=["new"],
)

# Replay for integrity check
report = sub.replay()
assert report.replayed_drift == 0
```

## Workflow Definitions

Workflows are YAML files validated against a JSON Schema:

```yaml
name: my_workflow
version: 1
substrate_version: "0.1.0"

states:
  - name: new
    initial: true
  - name: done
    terminal: true

transitions:
  - name: complete
    from: new
    to: done
    allowed_roles: [agent]

roles:
  - name: agent

work_item_types:
  - name: task
    custom_fields:
      - name: title
        type: string
        required: true
        ui_visible: true
```

## HMAC Key Format

```json
{
  "keys": [
    {
      "key_id": "key-001",
      "secret": "base64-encoded-secret",
      "status": "active"
    }
  ]
}
```

Key statuses: `active`, `deprecated` (accepted with warning), `revoked` (rejected).

## Architecture

- **Event-sourced**: events are the authoritative log; `work_items_current` is a transactionally-consistent projection
- **Schema-per-project**: one Postgres database, one schema per project, engine-enforced isolation
- **Library mode**: runs in-process, no HTTP server, exposes `prometheus_client.CollectorRegistry`
- **Library is sole signer**: HMAC-SHA256 over RFC 8785 canonical JSON, computed internally

## Spec

Authoritative spec: `spec.md`. Machine-readable sidecar: `spec.yaml`.

## Status

MVP + Phase 2 + Phase 3 complete. All FRs implemented and tested. See `AGENTS.md` for current status.

## License

MIT. See [LICENSE](LICENSE).
