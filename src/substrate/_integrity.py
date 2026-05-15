from __future__ import annotations

from ._connection import ConnectionManager
from ._errors import ErrorCode, SubstrateError
from ._migrations import check_migrations_current

SUBSTRATE_VERSION = "0.1.0"


def _parse_semver(s: str) -> tuple[int, int, int]:
    try:
        core = s.split("-", 1)[0].split("+", 1)[0]
        parts = core.split(".")
        if len(parts) != 3:
            raise ValueError(f"Expected 3 version components, got {len(parts)}")
        return (int(parts[0]), int(parts[1]), int(parts[2]))
    except (ValueError, IndexError) as e:
        raise SubstrateError(
            ErrorCode.WORKFLOW_VERSION_INCOMPATIBLE,
            f"Invalid semantic version {s!r}: {e}",
        ) from e


def check_integrity(mgr: ConnectionManager) -> list[str]:
    issues: list[str] = []

    check_migrations_current(mgr)

    with mgr.transaction() as conn:
        rows = conn.execute(
            "SELECT workflow_name, version, substrate_version FROM workflow_registry"
        ).fetchall()

    lib_ver = _parse_semver(SUBSTRATE_VERSION)

    for row in rows:
        wf_name = row["workflow_name"]
        wf_ver = row["version"]
        wf_sub_str = row["substrate_version"]

        wf_sub = _parse_semver(wf_sub_str)

        if lib_ver[0] != wf_sub[0]:
            issues.append(
                f"Workflow {wf_name!r} v{wf_ver}: substrate_version major mismatch "
                f"(workflow={wf_sub[0]}, library={lib_ver[0]})"
            )
        elif lib_ver < wf_sub:
            issues.append(
                f"Workflow {wf_name!r} v{wf_ver}: requires substrate "
                f"{wf_sub_str}, library is {SUBSTRATE_VERSION}"
            )

    if issues:
        raise SubstrateError(
            ErrorCode.WORKFLOW_VERSION_INCOMPATIBLE,
            "Workflow version incompatibilities: " + "; ".join(issues),
            detail={"issues": issues},
        )

    return issues
