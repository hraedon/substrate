from __future__ import annotations

import hashlib
import json
import os
import sys
import tempfile
import uuid

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("uvicorn")

from fastapi.testclient import TestClient

from substrate import Substrate

DSN = os.environ.get(
    "TEST_DSN",
    "postgresql://substrate_test:substrate_test@localhost:5432/substrate_test",
)
TEST_KEYS = os.environ.get("TEST_KEYS", "tests/test_keys.json")
TEST_WORKFLOW = os.environ.get("TEST_WORKFLOW", "tests/test_workflow.yaml")


def _make_token_file():
    raw_token = "test-secret-token-12345"
    token_sha256 = hashlib.sha256(raw_token.encode()).hexdigest()
    data = {
        "tokens": [
            {
                "token_sha256": token_sha256,
                "actor_id": "test-agent",
                "actor_kind": "agent",
                "allowed_roles": ["agent", "coder", "reviewer"],
            }
        ]
    }
    f = tempfile.NamedTemporaryFile(
        mode="w", suffix=".yaml", delete=False,
    )
    json.dump(data, f)
    f.close()
    return f.name, raw_token


@pytest.fixture(scope="module")
def token_file():
    path, raw = _make_token_file()
    yield path, raw
    os.unlink(path)


@pytest.fixture(scope="module")
def substrate_instance():
    project = f"sidecar_test_{uuid.uuid4().hex[:8]}"
    sub = Substrate.create_project(DSN, project, TEST_KEYS)
    yield sub
    sub.close()
    from substrate._testing import drop_project_schema
    drop_project_schema(DSN, project)


@pytest.fixture(scope="module")
def client(substrate_instance, token_file):
    token_path, _ = token_file
    from substrate.sidecar.app import create_app
    from substrate.sidecar.auth import TokenRegistry

    tokens = TokenRegistry.from_file(token_path)
    app = create_app(substrate_instance, tokens)
    return TestClient(app)


@pytest.fixture(scope="module")
def auth_headers(token_file):
    _, raw = token_file
    return {"Authorization": f"Bearer {raw}"}


@pytest.fixture(scope="module")
def workflow_id(substrate_instance):
    yaml_content = open(TEST_WORKFLOW).read()
    substrate_instance.register_workflow(yaml_content)
    return yaml_content


class TestAuth:
    def test_auth_required(self, client):
        resp = client.post("/v1/create_work_item", json={
            "workflow_name": "nonexistent",
            "work_item_type": "task",
        })
        assert resp.status_code == 401

    def test_invalid_token(self, client):
        resp = client.post(
            "/v1/create_work_item",
            json={"workflow_name": "nonexistent", "work_item_type": "task"},
            headers={"Authorization": "Bearer wrong-token"},
        )
        assert resp.status_code == 401


class TestSoleSigner:
    def test_signature_rejected(self, client, auth_headers, workflow_id):
        resp = client.post(
            "/v1/create_work_item",
            json={
                "workflow_name": "test_workflow",
                "work_item_type": "feature",
                "signature": "deadbeef",
            },
            headers=auth_headers,
        )
        assert resp.status_code == 400
        assert resp.json()["error"]["code"] == "LIBRARY_IS_SOLE_SIGNER"

    def test_payload_canonical_hash_rejected(self, client, auth_headers, workflow_id):
        resp = client.post(
            "/v1/create_work_item",
            json={
                "workflow_name": "test_workflow",
                "work_item_type": "feature",
                "payload_canonical_hash": "abc",
            },
            headers=auth_headers,
        )
        assert resp.status_code == 400
        assert resp.json()["error"]["code"] == "LIBRARY_IS_SOLE_SIGNER"


class TestRoundTrip:
    def test_create_transition_read(self, client, auth_headers, workflow_id):
        resp = client.post(
            "/v1/create_work_item",
            json={
                "workflow_name": "test_workflow",
                "work_item_type": "feature",
                "custom_fields": {"title": "test feature"},
            },
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        wi_id = data["work_item"]["work_item_id"]
        assert data["event"]["signature"] is not None

        client.post(
            "/v1/register_actor_role",
            json={"role": "agent"},
            headers=auth_headers,
        )

        resp = client.post(
            "/v1/transition",
            json={
                "work_item_id": wi_id,
                "transition_name": "start",
                "actor_metadata": {"role": "agent"},
            },
            headers=auth_headers,
        )
        assert resp.status_code == 200

        resp = client.post(
            "/v1/read_events",
            json={"work_item_id": wi_id},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        events = resp.json()
        assert len(events) >= 2
        assert events[0]["event_seq"] == 1
        assert events[1]["event_seq"] == 2

    def test_get_work_item(self, client, auth_headers, workflow_id):
        resp = client.post(
            "/v1/create_work_item",
            json={
                "workflow_name": "test_workflow",
                "work_item_type": "feature",
                "custom_fields": {"title": "test feature"},
            },
            headers=auth_headers,
        )
        wi_id = resp.json()["work_item"]["work_item_id"]

        resp = client.get(f"/v1/work_items/{wi_id}", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["work_item_id"] == wi_id

    def test_query_work_items(self, client, auth_headers, workflow_id):
        resp = client.post(
            "/v1/query_work_items",
            json={"workflow_name": "test_workflow"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert "items" in resp.json()


class TestClaims:
    def test_acquire_release_claim(self, client, auth_headers, workflow_id):
        resp = client.post(
            "/v1/create_work_item",
            json={
                "workflow_name": "test_workflow",
                "work_item_type": "feature",
                "custom_fields": {"title": "test feature"},
            },
            headers=auth_headers,
        )
        wi_id = resp.json()["work_item"]["work_item_id"]

        resp = client.post(
            "/v1/acquire_claim",
            json={"work_item_id": wi_id, "ttl_seconds": 300},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["actor_id"] == "test-agent"

        resp = client.post(
            "/v1/release_claim",
            json={"work_item_id": wi_id},
            headers=auth_headers,
        )
        assert resp.status_code == 200


class TestErrorMapping:
    def test_work_item_not_found(self, client, auth_headers):
        fake_id = str(uuid.uuid4())
        resp = client.get(f"/v1/work_items/{fake_id}", headers=auth_headers)
        assert resp.status_code == 404
        assert resp.json()["error"]["code"] == "WORK_ITEM_NOT_FOUND"

    def test_workflow_not_registered(self, client, auth_headers):
        resp = client.get("/v1/workflows/nonexistent/1", headers=auth_headers)
        assert resp.status_code == 404
        assert resp.json()["error"]["code"] == "WORKFLOW_NOT_REGISTERED"


class TestIdempotency:
    def test_idempotent_append_event(self, client, auth_headers, workflow_id):
        resp = client.post(
            "/v1/create_work_item",
            json={
                "workflow_name": "test_workflow",
                "work_item_type": "feature",
                "custom_fields": {"title": "test feature"},
            },
            headers=auth_headers,
        )
        wi_id = resp.json()["work_item"]["work_item_id"]
        event_id = str(uuid.uuid4())

        resp1 = client.post(
            "/v1/append_event",
            json={
                "work_item_id": wi_id,
                "transition": "note",
                "event_id": event_id,
            },
            headers=auth_headers,
        )
        assert resp1.status_code == 200

        resp2 = client.post(
            "/v1/append_event",
            json={
                "work_item_id": wi_id,
                "transition": "note",
                "event_id": event_id,
            },
            headers=auth_headers,
        )
        assert resp2.status_code == 200
        assert resp1.json()["event_id"] == resp2.json()["event_id"]


class TestActorRoles:
    def test_register_role(self, client, auth_headers):
        resp = client.post(
            "/v1/register_actor_role",
            json={"role": "coder"},
            headers=auth_headers,
        )
        assert resp.status_code == 200

    def test_unauthorized_role(self, client, auth_headers):
        resp = client.post(
            "/v1/register_actor_role",
            json={"role": "admin"},
            headers=auth_headers,
        )
        assert resp.status_code == 403

    def test_list_roles(self, client, auth_headers):
        resp = client.get("/v1/actor_roles", headers=auth_headers)
        assert resp.status_code == 200


class TestNoValidatorOverHttp:
    def test_no_register_validator_route(self, client, auth_headers):
        resp = client.post(
            "/v1/register_validator",
            json={"name": "test"},
            headers=auth_headers,
        )
        assert resp.status_code == 404 or resp.status_code == 405


class TestHookQueue:
    def test_claim_complete_round_trip(self, client, auth_headers, workflow_id, substrate_instance):
        pass

    def test_sweep_expired_hook_leases(self, client, auth_headers):
        resp = client.post("/v1/sweep_expired_hook_leases", headers=auth_headers)
        assert resp.status_code == 200
