from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from orbitfabric_eds_cfs_adapter.coverage import (
    build_coverage,
    build_failed_coverage,
    unavailable_coverage,
)
from orbitfabric_eds_cfs_adapter.input_set import LoadedInputSet
from orbitfabric_eds_cfs_adapter.io import sha256_file
from orbitfabric_eds_cfs_adapter.profile import LoadedProfile
from orbitfabric_eds_cfs_adapter.projection.resolution import ResolvedProfile
from orbitfabric_eds_cfs_adapter.projection.traceability import serialize_traceability

RESULT_KIND = "orbitfabric.integration_result"
RESULT_VERSION = "0.2-candidate"
RESULT_STATE = "succeeded"
FAILED_RESULT_STATE = "failed"
INTEGRATION_ID = "orbitfabric-eds-cfs"
ADAPTER_ID = "orbitfabric-eds-cfs"
ADAPTER_VERSION = "0.1.0.dev0"
OPERATION_ID = "eds_cfs_projection"
EDS_RELATIVE_PATH = Path("eds/mission.xml")
TRACEABILITY_RELATIVE_PATH = Path("traceability.json")
RESULT_RELATIVE_PATH = Path("integration_result.json")
DIAGNOSTIC_ID = "diag-001"
CAPABILITIES = (
    "artifact_generation",
    "profile_validation",
    "projection",
    "traceability",
)


class ResultError(ValueError):
    """Raised when accepted staged outputs cannot form a coherent B8/B9 Result."""


@dataclass(frozen=True)
class FailureSpec:
    phase: str
    code: str
    message: str
    capabilities: tuple[str, ...]


INPUT_FAILURE = FailureSpec(
    phase="input_compatibility",
    code="EDS-CFS-INPUT-001",
    message="Core Integration Input Set is not compatible with this operation",
    capabilities=(),
)
PROFILE_FAILURE = FailureSpec(
    phase="profile_schema",
    code="EDS-CFS-PROFILE-001",
    message="Projection Profile validation failed",
    capabilities=("profile_validation",),
)
RESOLUTION_FAILURE = FailureSpec(
    phase="source_resolution",
    code="EDS-CFS-RESOLVE-001",
    message="Projection Profile could not be resolved against the Core input",
    capabilities=("profile_validation", "projection"),
)
PROJECTION_FAILURE = FailureSpec(
    phase="projection_validation",
    code="EDS-CFS-PROJECT-001",
    message=(
        "Resolved mission semantics cannot be represented by the P0 EDS-cFS projection"
    ),
    capabilities=("profile_validation", "projection"),
)
ARTIFACT_FAILURE = FailureSpec(
    phase="artifact_generation",
    code="EDS-CFS-ARTIFACT-001",
    message="Required integration artifact generation failed",
    capabilities=("profile_validation", "projection", "artifact_generation"),
)


def _require_non_empty_string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value:
        raise ResultError(f"{label} must be a non-empty string")
    return value


def _require_sha256(value: Any, label: str) -> str:
    digest = _require_non_empty_string(value, label)
    if len(digest) != 64 or any(
        character not in "0123456789abcdef" for character in digest
    ):
        raise ResultError(f"{label} must be a lowercase SHA-256 hex digest")
    return digest


def _mapping_ids(traceability: dict[str, Any]) -> list[str]:
    mappings = traceability.get("mappings")
    if not isinstance(mappings, list) or not mappings:
        raise ResultError("B7 traceability mappings must be a non-empty array")
    ids: list[str] = []
    for mapping in mappings:
        if not isinstance(mapping, dict):
            raise ResultError("B7 traceability mapping must be an object")
        mapping_id = _require_non_empty_string(mapping.get("id"), "B7 mapping id")
        ids.append(mapping_id)
    if len(ids) != len(set(ids)):
        raise ResultError("B7 traceability mapping ids must be unique")
    return sorted(ids)


def _validate_traceability_identity(
    traceability: dict[str, Any],
    loaded_profile: LoadedProfile,
    resolved: ResolvedProfile,
) -> None:
    if traceability.get("kind") != "orbitfabric.eds_cfs.traceability":
        raise ResultError("unexpected B7 traceability kind")
    if traceability.get("traceability_version") != "0.1-candidate":
        raise ResultError("unexpected B7 traceability version")

    integration = traceability.get("integration")
    if not isinstance(integration, dict) or integration.get("id") != INTEGRATION_ID:
        raise ResultError("B7 integration identity mismatch")

    profile = loaded_profile.document
    profile_integration = profile.get("integration")
    if not isinstance(profile_integration, dict):
        raise ResultError("Projection Profile integration identity is unavailable")
    schema_version = _require_non_empty_string(
        profile_integration.get("schema_version"),
        "Projection Profile integration.schema_version",
    )
    if integration.get("schema_version") != schema_version:
        raise ResultError("B7/Profile integration schema version mismatch")

    trace_profile = traceability.get("profile")
    if not isinstance(trace_profile, dict):
        raise ResultError("B7 Profile identity is unavailable")
    if trace_profile.get("id") != resolved.profile_id:
        raise ResultError("B7/B4 Profile id mismatch")
    if trace_profile.get("version") != resolved.profile_version:
        raise ResultError("B7/B4 Profile version mismatch")

    authored_profile = profile.get("profile")
    if not isinstance(authored_profile, dict):
        raise ResultError("Projection Profile instance identity is unavailable")
    if authored_profile.get("id") != resolved.profile_id:
        raise ResultError("B3/B4 Profile id mismatch")
    if authored_profile.get("version") != resolved.profile_version:
        raise ResultError("B3/B4 Profile version mismatch")


def _artifact_record(
    *,
    artifact_id: str,
    kind: str,
    media_type: str,
    relative_path: Path,
    output_dir: Path,
    mapping_ids: list[str],
) -> dict[str, Any]:
    path = output_dir / relative_path
    if not path.is_file():
        raise ResultError(f"required B8 artifact is missing: {relative_path.as_posix()}")
    return {
        "id": artifact_id,
        "kind": kind,
        "requirement": "required",
        "status": "generated",
        "path": relative_path.as_posix(),
        "media_type": media_type,
        "sha256": sha256_file(path),
        "reason": None,
        "retained_partial": False,
        "derived_from_mappings": mapping_ids,
    }


def _failed_artifact_record(
    *,
    artifact_id: str,
    kind: str,
    media_type: str,
    status: str,
    reason: str,
) -> dict[str, Any]:
    if status not in {"not_generated", "failed"}:
        raise ResultError(f"invalid failed artifact status: {status}")
    return {
        "id": artifact_id,
        "kind": kind,
        "requirement": "required",
        "status": status,
        "path": None,
        "media_type": media_type,
        "sha256": None,
        "reason": reason,
        "retained_partial": False,
        "derived_from_mappings": [],
    }


def _available_core(core: LoadedInputSet) -> dict[str, Any]:
    manifest = core.manifest
    return {
        "status": "available",
        "kind": _require_non_empty_string(manifest.get("kind"), "Core input kind"),
        "version": _require_non_empty_string(
            manifest.get("input_set_version"),
            "Core input-set version",
        ),
        "sha256": _require_sha256(
            manifest.get("input_set_sha256"),
            "Core input-set SHA-256",
        ),
        "reason": None,
    }


def _available_mission(core: LoadedInputSet) -> dict[str, Any]:
    mission = core.manifest.get("mission")
    if not isinstance(mission, dict):
        raise ResultError("Core input mission identity is unavailable")
    return {
        "status": "available",
        "id": _require_non_empty_string(mission.get("id"), "Mission id"),
        "model_version": _require_non_empty_string(
            mission.get("model_version"),
            "Mission model version",
        ),
        "reason": None,
    }


def _available_profile(loaded_profile: LoadedProfile) -> dict[str, Any]:
    profile = loaded_profile.document
    identity = profile.get("profile")
    if not isinstance(identity, dict):
        raise ResultError("Profile instance identity is unavailable")
    return {
        "status": "available",
        "kind": _require_non_empty_string(profile.get("kind"), "Profile kind"),
        "profile_version": _require_non_empty_string(
            profile.get("profile_version"),
            "Profile envelope version",
        ),
        "id": _require_non_empty_string(identity.get("id"), "Profile id"),
        "version": _require_non_empty_string(
            identity.get("version"),
            "Profile instance version",
        ),
        "sha256": _require_sha256(
            loaded_profile.sha256,
            "Profile byte SHA-256",
        ),
        "reason": None,
    }


def _profile_schema_version(loaded_profile: LoadedProfile | None) -> str | None:
    if loaded_profile is None:
        return None
    integration = loaded_profile.document.get("integration")
    if not isinstance(integration, dict):
        raise ResultError("Profile integration identity is unavailable")
    if integration.get("id") != INTEGRATION_ID:
        raise ResultError("Profile integration id does not match adapter integration id")
    return _require_non_empty_string(
        integration.get("schema_version"),
        "Profile integration schema version",
    )


def _unavailable_core() -> dict[str, Any]:
    return {
        "status": "unavailable",
        "kind": None,
        "version": None,
        "sha256": None,
        "reason": "Core Integration Input Set provenance was not established",
    }


def _unavailable_mission() -> dict[str, Any]:
    return {
        "status": "unavailable",
        "id": None,
        "model_version": None,
        "reason": "Mission provenance was not established from a compatible Core input",
    }


def _unavailable_profile() -> dict[str, Any]:
    return {
        "status": "unavailable",
        "kind": None,
        "profile_version": None,
        "id": None,
        "version": None,
        "sha256": None,
        "reason": "Projection Profile provenance was not established",
    }


def build_success_result(
    core: LoadedInputSet,
    loaded_profile: LoadedProfile,
    resolved: ResolvedProfile,
    traceability: dict[str, Any],
    output_dir: Path,
) -> dict[str, Any]:
    """Build the deterministic B8 success envelope from accepted staged outputs."""

    output_dir = output_dir.resolve()
    _validate_traceability_identity(traceability, loaded_profile, resolved)
    mapping_ids = _mapping_ids(traceability)

    eds_path = output_dir / EDS_RELATIVE_PATH
    traceability_path = output_dir / TRACEABILITY_RELATIVE_PATH
    if not eds_path.is_file():
        raise ResultError(f"required B6 artifact is missing: {EDS_RELATIVE_PATH.as_posix()}")
    if not traceability_path.is_file():
        raise ResultError(
            f"required B7 artifact is missing: {TRACEABILITY_RELATIVE_PATH.as_posix()}"
        )

    trace_bytes = serialize_traceability(traceability)
    if traceability_path.read_bytes() != trace_bytes:
        raise ResultError(
            "materialized B7 traceability bytes differ from the accepted serializer"
        )

    trace_artifact = traceability.get("artifact")
    if not isinstance(trace_artifact, dict):
        raise ResultError("B7 traceability artifact binding is unavailable")
    expected_eds_digest = _require_sha256(
        trace_artifact.get("sha256"),
        "B7 EDS artifact SHA-256",
    )
    if sha256_file(eds_path) != expected_eds_digest:
        raise ResultError("materialized B6 XML digest differs from the B7 artifact binding")

    manifest = core.manifest
    core_kind = _require_non_empty_string(manifest.get("kind"), "Core input kind")
    core_version = _require_non_empty_string(
        manifest.get("input_set_version"),
        "Core input-set version",
    )
    core_digest = _require_sha256(
        manifest.get("input_set_sha256"),
        "Core input-set SHA-256",
    )

    mission = manifest.get("mission")
    if not isinstance(mission, dict):
        raise ResultError("Core input mission identity is unavailable")
    mission_id = _require_non_empty_string(mission.get("id"), "Mission id")
    mission_version = _require_non_empty_string(
        mission.get("model_version"),
        "Mission model version",
    )

    profile = loaded_profile.document
    profile_kind = _require_non_empty_string(profile.get("kind"), "Profile kind")
    profile_version = _require_non_empty_string(
        profile.get("profile_version"),
        "Profile envelope version",
    )
    profile_identity = profile.get("profile")
    if not isinstance(profile_identity, dict):
        raise ResultError("Profile instance identity is unavailable")
    profile_id = _require_non_empty_string(profile_identity.get("id"), "Profile id")
    profile_revision = _require_non_empty_string(
        profile_identity.get("version"),
        "Profile instance version",
    )
    profile_digest = _require_sha256(loaded_profile.sha256, "Profile byte SHA-256")

    profile_integration = profile.get("integration")
    if not isinstance(profile_integration, dict):
        raise ResultError("Profile integration identity is unavailable")
    if profile_integration.get("id") != INTEGRATION_ID:
        raise ResultError("Profile integration id does not match the adapter integration id")
    integration_schema_version = _require_non_empty_string(
        profile_integration.get("schema_version"),
        "Profile integration schema version",
    )

    artifacts = sorted(
        [
            _artifact_record(
                artifact_id="eds.package",
                kind="ccsds.sois.eds.xml",
                media_type="application/xml",
                relative_path=EDS_RELATIVE_PATH,
                output_dir=output_dir,
                mapping_ids=mapping_ids,
            ),
            _artifact_record(
                artifact_id="traceability",
                kind="orbitfabric.eds_cfs.traceability",
                media_type="application/json",
                relative_path=TRACEABILITY_RELATIVE_PATH,
                output_dir=output_dir,
                mapping_ids=mapping_ids,
            ),
        ],
        key=lambda item: item["id"],
    )

    result: dict[str, Any] = {
        "kind": RESULT_KIND,
        "result_version": RESULT_VERSION,
        "result": RESULT_STATE,
        "integration": {
            "id": INTEGRATION_ID,
            "schema_version": integration_schema_version,
        },
        "adapter": {
            "id": ADAPTER_ID,
            "version": ADAPTER_VERSION,
        },
        "operation": {"id": OPERATION_ID},
        "mission": {
            "status": "available",
            "id": mission_id,
            "model_version": mission_version,
            "reason": None,
        },
        "inputs": {
            "core_input_set": {
                "status": "available",
                "kind": core_kind,
                "version": core_version,
                "sha256": core_digest,
                "reason": None,
            },
            "profile": {
                "status": "available",
                "kind": profile_kind,
                "profile_version": profile_version,
                "id": profile_id,
                "version": profile_revision,
                "sha256": profile_digest,
                "reason": None,
            },
            "operation_inputs": [],
        },
        "capabilities": list(CAPABILITIES),
        "artifacts": artifacts,
        "mappings": traceability["mappings"],
        "resolutions": traceability["resolutions"],
        "diagnostics": [],
        "coverage": build_coverage(core, resolved, traceability),
        "evidence": [],
        "external_tools": [],
    }
    validate_success_result(result, traceability)
    return result


def build_failed_result(
    failure: FailureSpec,
    *,
    core: LoadedInputSet | None = None,
    loaded_profile: LoadedProfile | None = None,
    resolved: ResolvedProfile | None = None,
    failed_artifacts: frozenset[str] = frozenset(),
) -> dict[str, Any]:
    """Build one deterministic B9 failed Result from facts established before failure."""

    if resolved is not None and (core is None or loaded_profile is None):
        raise ResultError("B4 failure context requires Core and Profile provenance")

    diagnostic = {
        "id": DIAGNOSTIC_ID,
        "owner": "integration",
        "producer": INTEGRATION_ID,
        "phase": failure.phase,
        "severity": "ERROR",
        "code": failure.code,
        "message": failure.message,
        "sources": [],
        "profile_bindings": [],
        "targets": [],
    }

    artifact_specs = (
        ("eds.package", "ccsds.sois.eds.xml", "application/xml"),
        (
            "traceability",
            "orbitfabric.eds_cfs.traceability",
            "application/json",
        ),
    )
    artifacts = [
        _failed_artifact_record(
            artifact_id=artifact_id,
            kind=kind,
            media_type=media_type,
            status="failed" if artifact_id in failed_artifacts else "not_generated",
            reason=failure.message,
        )
        for artifact_id, kind, media_type in artifact_specs
    ]

    if core is not None and resolved is not None:
        coverage = build_failed_coverage(core, resolved, DIAGNOSTIC_ID)
    else:
        coverage = unavailable_coverage(failure.message)

    result: dict[str, Any] = {
        "kind": RESULT_KIND,
        "result_version": RESULT_VERSION,
        "result": FAILED_RESULT_STATE,
        "integration": {
            "id": INTEGRATION_ID,
            "schema_version": _profile_schema_version(loaded_profile),
        },
        "adapter": {
            "id": ADAPTER_ID,
            "version": ADAPTER_VERSION,
        },
        "operation": {"id": OPERATION_ID},
        "mission": (
            _available_mission(core) if core is not None else _unavailable_mission()
        ),
        "inputs": {
            "core_input_set": (
                _available_core(core) if core is not None else _unavailable_core()
            ),
            "profile": (
                _available_profile(loaded_profile)
                if loaded_profile is not None
                else _unavailable_profile()
            ),
            "operation_inputs": [],
        },
        "capabilities": list(failure.capabilities),
        "artifacts": artifacts,
        "mappings": [],
        "resolutions": [],
        "diagnostics": [diagnostic],
        "coverage": coverage,
        "evidence": [],
        "external_tools": [],
    }
    validate_failed_result(result)
    return result


def validate_success_result(result: dict[str, Any], traceability: dict[str, Any]) -> None:
    if result.get("kind") != RESULT_KIND:
        raise ResultError("unexpected Integration Result kind")
    if result.get("result_version") != RESULT_VERSION:
        raise ResultError("unexpected Integration Result version")
    if result.get("result") != RESULT_STATE:
        raise ResultError("B8 success result must use the succeeded state")
    if result.get("capabilities") != list(CAPABILITIES):
        raise ResultError("B8 capabilities differ from the frozen P0 set")
    if result.get("diagnostics") != []:
        raise ResultError("B8 successful P0 result must not contain integration diagnostics")
    if result.get("evidence") != []:
        raise ResultError("B8 must not claim native/runtime evidence")
    if result.get("external_tools") != []:
        raise ResultError("B8 must not claim external-tool execution")
    if result.get("mappings") != traceability.get("mappings"):
        raise ResultError("B8 mappings are not exact B7 mappings")
    if result.get("resolutions") != traceability.get("resolutions"):
        raise ResultError("B8 resolutions are not exact B7 resolutions")
    if result.get("coverage", {}).get("status") != "complete":
        raise ResultError("successful projection Result requires complete coverage")
    if result.get("inputs", {}).get("operation_inputs") != []:
        raise ResultError("eds_cfs_projection requires zero operation inputs")


def validate_failed_result(result: dict[str, Any]) -> None:
    if result.get("kind") != RESULT_KIND:
        raise ResultError("unexpected Integration Result kind")
    if result.get("result_version") != RESULT_VERSION:
        raise ResultError("unexpected Integration Result version")
    if result.get("result") != FAILED_RESULT_STATE:
        raise ResultError("B9 failed Result must use the failed state")
    if result.get("operation") != {"id": OPERATION_ID}:
        raise ResultError("B9 failed Result operation identity mismatch")
    if result.get("inputs", {}).get("operation_inputs") != []:
        raise ResultError("eds_cfs_projection requires zero operation inputs")
    if result.get("mappings") != [] or result.get("resolutions") != []:
        raise ResultError("B9 failed Result must not retain mappings or resolutions")
    if result.get("evidence") != [] or result.get("external_tools") != []:
        raise ResultError("B9 failed Result must not claim native/runtime evidence")

    diagnostics = result.get("diagnostics")
    if not isinstance(diagnostics, list) or len(diagnostics) != 1:
        raise ResultError("B9 failed Result requires one primary diagnostic")
    diagnostic = diagnostics[0]
    if diagnostic.get("id") != DIAGNOSTIC_ID:
        raise ResultError("B9 failed diagnostic id mismatch")
    if (
        diagnostic.get("owner") != "integration"
        or diagnostic.get("severity") != "ERROR"
    ):
        raise ResultError("B9 failure must be an integration-owned ERROR")

    artifacts = result.get("artifacts")
    if not isinstance(artifacts, list) or len(artifacts) != 2:
        raise ResultError("B9 failed Result must account for two required artifacts")
    expected_ids = ["eds.package", "traceability"]
    if [item.get("id") for item in artifacts] != expected_ids:
        raise ResultError("B9 failed artifact inventory mismatch")
    for artifact in artifacts:
        if artifact.get("status") not in {"not_generated", "failed"}:
            raise ResultError("B9 failed artifact has invalid status")
        if artifact.get("path") is not None or artifact.get("sha256") is not None:
            raise ResultError("B9 failed artifact must not retain a file")
        if artifact.get("retained_partial") is not False:
            raise ResultError("B9 failed artifact must not retain partial bytes")
        if not artifact.get("reason"):
            raise ResultError("B9 failed artifact requires a reason")


def serialize_result(result: dict[str, Any]) -> bytes:
    return (json.dumps(result, indent=2, sort_keys=True) + "\n").encode("utf-8")


def write_result(
    output_dir: Path,
    result: dict[str, Any],
    traceability: dict[str, Any],
) -> Path:
    validate_success_result(result, traceability)
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / RESULT_RELATIVE_PATH
    path.write_bytes(serialize_result(result))
    return path


def write_failed_result(output_dir: Path, result: dict[str, Any]) -> Path:
    validate_failed_result(result)
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / RESULT_RELATIVE_PATH
    path.write_bytes(serialize_result(result))
    return path
