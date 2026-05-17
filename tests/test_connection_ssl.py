from __future__ import annotations

import uuid
from pathlib import Path

import pytest

from substrate._errors import ErrorCode, SubstrateError
from substrate.testing import drop_project_schema

TESTS_DIR = Path(__file__).parent
DSN = "postgresql://substrate_test:substrate_test@localhost:5432/substrate_test"
KEY_PATH = str(TESTS_DIR / "test_keys.json")


class TestRequireSsl:
    def test_require_ssl_rejects_plaintext_connection(self):
        from substrate import Substrate

        project = f"test_ssl_{uuid.uuid4().hex[:8]}"
        Substrate.create_project(DSN, project, KEY_PATH)
        try:
            with pytest.raises(SubstrateError) as exc_info:
                Substrate(DSN, project, KEY_PATH, require_ssl=True)
            assert exc_info.value.code == ErrorCode.INVALID_ARGUMENT
            assert "SSL is required" in exc_info.value.message
        finally:
            drop_project_schema(DSN, project)

    def test_require_ssl_false_allows_plaintext(self):
        from substrate import Substrate

        project = f"test_ssl_off_{uuid.uuid4().hex[:8]}"
        Substrate.create_project(DSN, project, KEY_PATH)
        try:
            sub = Substrate(DSN, project, KEY_PATH, require_ssl=False)
            sub.close()
        finally:
            drop_project_schema(DSN, project)

    def test_require_ssl_passed_through_create_project(self):
        from substrate import Substrate

        project = f"test_ssl_cp_{uuid.uuid4().hex[:8]}"
        sub = Substrate.create_project(DSN, project, KEY_PATH, require_ssl=False)
        sub.close()
        drop_project_schema(DSN, project)
