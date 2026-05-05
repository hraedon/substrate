from __future__ import annotations

import inspect

DSN = "postgresql://substrate_test:substrate_test@localhost:5432/substrate_test"


class TestAC33PreSignedRejection:
    def test_public_api_has_no_signature_params(self):
        from substrate import Substrate

        methods = [
            Substrate.append_event,
            Substrate.transition,
            Substrate.create_work_item,
            Substrate.register_workflow,
        ]
        for method in methods:
            sig = inspect.signature(method)
            assert "signature" not in sig.parameters, (
                f"{method.__name__} accepts a 'signature' parameter"
            )
            assert "canonical_hash" not in sig.parameters, (
                f"{method.__name__} accepts a 'canonical_hash' parameter"
            )


class TestAC34NoPostgresTypesLeak:
    PG_TYPES = {"psycopg", "Connection", "Cursor", "ConnectionPool"}

    def test_event_no_pg_types(self):
        from substrate._types import Event

        annotations = Event.__dataclass_fields__
        for field_name, field in annotations.items():
            type_str = str(field.type)
            for pg in self.PG_TYPES:
                assert pg not in type_str, (
                    f"Event.{field_name} references Postgres type: {type_str}"
                )

    def test_work_item_no_pg_types(self):
        from substrate._types import WorkItem

        annotations = WorkItem.__dataclass_fields__
        for field_name, field in annotations.items():
            type_str = str(field.type)
            for pg in self.PG_TYPES:
                assert pg not in type_str, (
                    f"WorkItem.{field_name} references Postgres type: {type_str}"
                )

    def test_claim_no_pg_types(self):
        from substrate._types import Claim

        annotations = Claim.__dataclass_fields__
        for field_name, field in annotations.items():
            type_str = str(field.type)
            for pg in self.PG_TYPES:
                assert pg not in type_str, (
                    f"Claim.{field_name} references Postgres type: {type_str}"
                )

    def test_substrate_public_api_no_pg_imports(self):
        import substrate

        public_names = [name for name in dir(substrate) if not name.startswith("_")]
        for name in public_names:
            obj = getattr(substrate, name)
            if inspect.isclass(obj):
                module = getattr(obj, "__module__", "")
                assert "psycopg" not in module, (
                    f"substrate.{name} is from psycopg module: {module}"
                )
