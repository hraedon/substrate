from __future__ import annotations

import uuid
from pathlib import Path

import pytest

from substrate._errors import ErrorCode, SubstrateError
from substrate.testing import drop_project_schema

TESTS_DIR = Path(__file__).parent
DSN = "postgresql://substrate_test:substrate_test@localhost:5432/substrate_test"
KEY_PATH = str(TESTS_DIR / "test_keys.json")

REF_WORKFLOW_YAML = """\
name: ref_test
version: 1
substrate_version: "0.1.0"

states:
  - name: new
    initial: true
  - name: done
    terminal: true

transitions:
  - name: start
    from: new
    to: done
    allowed_roles: [agent]

roles:
  - name: agent

work_item_types:
  - name: source
    custom_fields:
      - name: name
        type: string
        required: true
  - name: consumer
    custom_fields:
      - name: source_ref
        type: work_item_ref
        target_work_item_type: source
        required: true
      - name: optional_ref
        type: work_item_ref
        target_work_item_type: source
  - name: untyped_ref_holder
    custom_fields:
      - name: any_ref
        type: work_item_ref

link_types: []

attempt_threshold: 3
"""


@pytest.fixture(scope="function")
def substrate():
    from substrate import Substrate

    project = f"test_wir_{uuid.uuid4().hex[:8]}"
    sub = Substrate.create_project(DSN, project, KEY_PATH)
    sub.register_workflow(REF_WORKFLOW_YAML)
    yield sub
    sub.close()
    drop_project_schema(DSN, project)


class TestWorkItemRefCreateValidation:
    def test_nonexistent_uuid_rejected(self, substrate):
        fake_uuid = str(uuid.uuid4())
        with pytest.raises(SubstrateError) as exc_info:
            substrate.create_work_item(
                workflow_name="ref_test",
                work_item_type="consumer",
                actor_id="a1",
                custom_fields={"source_ref": fake_uuid},
            )
        assert exc_info.value.code == ErrorCode.CUSTOM_FIELD_VIOLATION
        assert "nonexistent" in str(exc_info.value)

    def test_wrong_type_rejected(self, substrate):
        src, _ = substrate.create_work_item(
            workflow_name="ref_test",
            work_item_type="source",
            actor_id="a1",
            custom_fields={"name": "src-1"},
        )
        consumer, _ = substrate.create_work_item(
            workflow_name="ref_test",
            work_item_type="consumer",
            actor_id="a1",
            custom_fields={"source_ref": str(src.work_item_id)},
        )
        with pytest.raises(SubstrateError) as exc_info:
            substrate.create_work_item(
                workflow_name="ref_test",
                work_item_type="consumer",
                actor_id="a1",
                custom_fields={"source_ref": str(consumer.work_item_id)},
            )
        assert exc_info.value.code == ErrorCode.CUSTOM_FIELD_VIOLATION
        assert "expected 'source'" in str(exc_info.value)

    def test_correct_type_accepted(self, substrate):
        src, _ = substrate.create_work_item(
            workflow_name="ref_test",
            work_item_type="source",
            actor_id="a1",
            custom_fields={"name": "src-1"},
        )
        consumer, _ = substrate.create_work_item(
            workflow_name="ref_test",
            work_item_type="consumer",
            actor_id="a1",
            custom_fields={"source_ref": str(src.work_item_id)},
        )
        assert consumer.custom_fields["source_ref"] == str(src.work_item_id)

    def test_invalid_uuid_format_rejected(self, substrate):
        with pytest.raises(SubstrateError) as exc_info:
            substrate.create_work_item(
                workflow_name="ref_test",
                work_item_type="consumer",
                actor_id="a1",
                custom_fields={"source_ref": "not-a-uuid"},
            )
        assert exc_info.value.code == ErrorCode.CUSTOM_FIELD_VIOLATION
        assert "invalid UUID" in str(exc_info.value)

    def test_optional_ref_with_none_accepted(self, substrate):
        src, _ = substrate.create_work_item(
            workflow_name="ref_test",
            work_item_type="source",
            actor_id="a1",
            custom_fields={"name": "src-1"},
        )
        consumer, _ = substrate.create_work_item(
            workflow_name="ref_test",
            work_item_type="consumer",
            actor_id="a1",
            custom_fields={
                "source_ref": str(src.work_item_id),
                "optional_ref": None,
            },
        )
        assert consumer.custom_fields.get("optional_ref") is None

    def test_untyped_ref_accepts_any_existing_uuid(self, substrate):
        src, _ = substrate.create_work_item(
            workflow_name="ref_test",
            work_item_type="source",
            actor_id="a1",
            custom_fields={"name": "src-1"},
        )
        holder, _ = substrate.create_work_item(
            workflow_name="ref_test",
            work_item_type="untyped_ref_holder",
            actor_id="a1",
            custom_fields={"any_ref": str(src.work_item_id)},
        )
        assert holder.custom_fields["any_ref"] == str(src.work_item_id)

    def test_untyped_ref_rejects_nonexistent(self, substrate):
        with pytest.raises(SubstrateError) as exc_info:
            substrate.create_work_item(
                workflow_name="ref_test",
                work_item_type="untyped_ref_holder",
                actor_id="a1",
                custom_fields={"any_ref": str(uuid.uuid4())},
            )
        assert exc_info.value.code == ErrorCode.CUSTOM_FIELD_VIOLATION


class TestWorkItemRefTransitionValidation:
    def test_transition_rejects_nonexistent_ref(self, substrate):
        src, _ = substrate.create_work_item(
            workflow_name="ref_test",
            work_item_type="source",
            actor_id="a1",
            custom_fields={"name": "src-1"},
        )
        consumer, _ = substrate.create_work_item(
            workflow_name="ref_test",
            work_item_type="consumer",
            actor_id="a1",
            custom_fields={"source_ref": str(src.work_item_id)},
        )
        with pytest.raises(SubstrateError) as exc_info:
            substrate.transition(
                consumer.work_item_id, "start", "a1",
                actor_metadata={"role": "agent"},
                custom_fields={"optional_ref": str(uuid.uuid4())},
            )
        assert exc_info.value.code == ErrorCode.CUSTOM_FIELD_VIOLATION

    def test_transition_rejects_wrong_type_ref(self, substrate):
        src, _ = substrate.create_work_item(
            workflow_name="ref_test",
            work_item_type="source",
            actor_id="a1",
            custom_fields={"name": "src-1"},
        )
        consumer, _ = substrate.create_work_item(
            workflow_name="ref_test",
            work_item_type="consumer",
            actor_id="a1",
            custom_fields={"source_ref": str(src.work_item_id)},
        )
        other_consumer, _ = substrate.create_work_item(
            workflow_name="ref_test",
            work_item_type="consumer",
            actor_id="a1",
            custom_fields={"source_ref": str(src.work_item_id)},
        )
        with pytest.raises(SubstrateError) as exc_info:
            substrate.transition(
                consumer.work_item_id, "start", "a1",
                actor_metadata={"role": "agent"},
                custom_fields={"optional_ref": str(other_consumer.work_item_id)},
            )
        assert exc_info.value.code == ErrorCode.CUSTOM_FIELD_VIOLATION
        assert "expected 'source'" in str(exc_info.value)

    def test_transition_accepts_correct_type_ref(self, substrate):
        src, _ = substrate.create_work_item(
            workflow_name="ref_test",
            work_item_type="source",
            actor_id="a1",
            custom_fields={"name": "src-1"},
        )
        src2, _ = substrate.create_work_item(
            workflow_name="ref_test",
            work_item_type="source",
            actor_id="a1",
            custom_fields={"name": "src-2"},
        )
        consumer, _ = substrate.create_work_item(
            workflow_name="ref_test",
            work_item_type="consumer",
            actor_id="a1",
            custom_fields={"source_ref": str(src.work_item_id)},
        )
        substrate.transition(
            consumer.work_item_id, "start", "a1",
            actor_metadata={"role": "agent"},
            custom_fields={"optional_ref": str(src2.work_item_id)},
        )
        updated = substrate.get_work_item(consumer.work_item_id)
        assert updated.custom_fields["optional_ref"] == str(src2.work_item_id)
