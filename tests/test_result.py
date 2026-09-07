from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from orbitfabric_eds_cfs_adapter.input_set import LoadedInputSet
from orbitfabric_eds_cfs_adapter.profile import load_profile_with_provenance
from orbitfabric_eds_cfs_adapter.projection.eds_xml import serialize_eds_xml
from orbitfabric_eds_cfs_adapter.projection.model import build_projection_model
from orbitfabric_eds_cfs_adapter.projection.resolution import resolve_profile
from orbitfabric_eds_cfs_adapter.projection.traceability import (
    build_traceability,
    serialize_traceability,
)
from orbitfabric_eds_cfs_adapter.result import (
    CAPABILITIES,
    EDS_RELATIVE_PATH,
    TRACEABILITY_RELATIVE_PATH,
    ResultError,
    build_success_result,
    serialize_result,
    write_result,
)

ROOT = Path(__file__).resolve().parents[1]
PROFILE = ROOT / "tests" / "fixtures" / "p0_b3" / "profile.yaml"
GOLDEN = ROOT / "tests" / "fixtures" / "p0_b8" / "expected.json"
CORE_DIGEST = "e8b70eebbda845a91546f40121ee6d927f96a2a39de2776437930e009b20bc98"
PROFILE_DIGEST = "bf5e5d4f85636c3f389da091a71a30b785125aaa559145cf899d90431738ed18"
B6_DIGEST = "afac1000713f6fdb0b15cdf71641b40c346c29fcf63ab074a934b6b7dfb969bb"
B7_DIGEST = "3480f57f0461839ec66b62ded192be2aac71f2446b5baa869e82f410256a20f8"


def _core() -> LoadedInputSet:
    return LoadedInputSet(
        root=Path("/fixture"),
        manifest={
            "kind": "orbitfabric.integration_input_set",
            "input_set_version": "0.1-candidate",
            "orbitfabric_version": "1.3.0",
            "mission": {"id": "eds-cfs-p0", "model_version": "0.1.0"},
            "load_result": "loaded",
            "lint_result": "passed_with_warnings",
            "input_set_sha256": CORE_DIGEST,
        },
        snapshot={
            "kind": "orbitfabric.mission_snapshot",
            "snapshot_version": "0.1-candidate",
            "result": "loaded",
            "model": {
                "commands": [
                    {"id": "payload.enable", "arguments": []},
                    {
                        "id": "payload.set_period",
                        "arguments": [
                            {
                                "name": "period_ms",
                                "type": "uint32",
                                "min": 100,
                                "max": 60000,
                            }
                        ],
                    },
                ],
                "telemetry": [
                    {"id": "payload.enabled", "type": "bool"},
                    {"id": "payload.sample_count", "type": "uint32"},
                ],
            },
        },
        entity_index={
            "kind": "orbitfabric.entity_index",
            "index_version": "0.1",
            "entities": [
                {"domain": "commands", "id": "payload.enable"},
                {"domain": "commands", "id": "payload.set_period"},
                {"domain": "telemetry", "id": "payload.enabled"},
                {"domain": "telemetry", "id": "payload.sample_count"},
                {"domain": "packets", "id": "payload_status"},
                {"domain": "subsystems", "id": "payload"},
            ],
        },
        relationship_manifest={
            "kind": "orbitfabric.relationship_manifest",
            "manifest_version": "0.1-candidate",
            "relationships": [
                {
                    "relationship_type": "packet_includes_telemetry",
                    "from": {"domain": "packets", "id": "payload_status"},
                    "to": {"domain": "telemetry", "id": "payload.enabled"},
                },
                {
                    "relationship_type": "packet_includes_telemetry",
                    "from": {"domain": "packets", "id": "payload_status"},
                    "to": {"domain": "telemetry", "id": "payload.sample_count"},
                },
            ],
        },
        lint_report={
            "tool": "orbitfabric-lint",
            "result": "passed_with_warnings",
            "findings": [
                {"severity": "WARNING", "code": f"TEST-{index}"} for index in range(6)
            ],
        },
    )


def _bundle(tmp_path: Path):
    core = _core()
    loaded_profile = load_profile_with_provenance(PROFILE)
    resolved = resolve_profile(loaded_profile.document, core)
    model = build_projection_model(resolved)
    xml_bytes = serialize_eds_xml(model)
    traceability = build_traceability(resolved, model, xml_bytes)

    output_dir = tmp_path / "out"
    eds_path = output_dir / EDS_RELATIVE_PATH
    eds_path.parent.mkdir(parents=True)
    eds_path.write_bytes(xml_bytes)
    traceability_path = output_dir / TRACEABILITY_RELATIVE_PATH
    traceability_path.write_bytes(serialize_traceability(traceability))

    result = build_success_result(
        core,
        loaded_profile,
        resolved,
        traceability,
        output_dir,
    )
    return core, loaded_profile, resolved, traceability, output_dir, result


def test_profile_provenance_uses_exact_consumed_bytes() -> None:
    loaded = load_profile_with_provenance(PROFILE)

    assert loaded.sha256 == PROFILE_DIGEST
    assert loaded.sha256 == hashlib.sha256(PROFILE.read_bytes()).hexdigest()
    assert loaded.document["profile"]["id"] == "eds-cfs-p0"


def test_success_result_has_frozen_identity_and_provenance(tmp_path: Path) -> None:
    _core_input, loaded_profile, _resolved, _traceability, _output_dir, result = _bundle(
        tmp_path
    )

    assert result["kind"] == "orbitfabric.integration_result"
    assert result["result_version"] == "0.2-candidate"
    assert result["result"] == "succeeded"
    assert result["integration"] == {
        "id": "orbitfabric-eds-cfs",
        "schema_version": "0.1-candidate",
    }
    assert result["adapter"] == {
        "id": "orbitfabric-eds-cfs",
        "version": "0.1.0",
    }
    assert result["operation"] == {"id": "eds_cfs_projection"}
    assert result["mission"] == {
        "status": "available",
        "id": "eds-cfs-p0",
        "model_version": "0.1.0",
        "reason": None,
    }
    assert result["inputs"]["core_input_set"]["sha256"] == CORE_DIGEST
    assert result["inputs"]["profile"]["sha256"] == loaded_profile.sha256 == PROFILE_DIGEST
    assert result["inputs"]["operation_inputs"] == []


def test_success_result_claims_only_b8_capabilities(tmp_path: Path) -> None:
    *_prefix, result = _bundle(tmp_path)

    assert result["capabilities"] == list(CAPABILITIES)
    assert result["diagnostics"] == []
    assert result["evidence"] == []
    assert result["external_tools"] == []


def test_b8_reuses_b7_mapping_and_resolution_objects_exactly(tmp_path: Path) -> None:
    *_prefix, traceability, _output_dir, result = _bundle(tmp_path)

    assert result["mappings"] is traceability["mappings"]
    assert result["resolutions"] is traceability["resolutions"]


def test_artifact_records_bind_exact_materialized_bytes(tmp_path: Path) -> None:
    *_prefix, output_dir, result = _bundle(tmp_path)
    artifacts = {item["id"]: item for item in result["artifacts"]}

    assert [item["id"] for item in result["artifacts"]] == ["eds.package", "traceability"]
    assert artifacts["eds.package"]["path"] == "eds/mission.xml"
    assert artifacts["eds.package"]["sha256"] == B6_DIGEST
    assert artifacts["traceability"]["path"] == "traceability.json"
    assert artifacts["traceability"]["sha256"] == B7_DIGEST
    assert artifacts["eds.package"]["sha256"] == hashlib.sha256(
        (output_dir / EDS_RELATIVE_PATH).read_bytes()
    ).hexdigest()
    assert artifacts["traceability"]["sha256"] == hashlib.sha256(
        (output_dir / TRACEABILITY_RELATIVE_PATH).read_bytes()
    ).hexdigest()


def test_coverage_is_complete_for_the_three_frozen_domains(tmp_path: Path) -> None:
    *_prefix, result = _bundle(tmp_path)
    coverage = result["coverage"]

    assert coverage["status"] == "complete"
    assert coverage["reason"] is None
    assert coverage["scope"] == {"domains": ["commands", "packets", "telemetry"]}
    assert coverage["summary"] == {"projected": 5}
    assert [
        (record["source"]["domain"], record["source"]["id"], record["state"])
        for record in coverage["records"]
    ] == [
        ("commands", "payload.enable", "projected"),
        ("commands", "payload.set_period", "projected"),
        ("packets", "payload_status", "projected"),
        ("telemetry", "payload.enabled", "projected"),
        ("telemetry", "payload.sample_count", "projected"),
    ]


def test_b6_tamper_after_b7_binding_fails_closed(tmp_path: Path) -> None:
    core, loaded_profile, resolved, traceability, output_dir, _result = _bundle(tmp_path)
    path = output_dir / EDS_RELATIVE_PATH
    path.write_bytes(path.read_bytes() + b"\n")

    with pytest.raises(ResultError, match="B7 artifact binding"):
        build_success_result(core, loaded_profile, resolved, traceability, output_dir)


def test_b7_materialized_bytes_must_match_serializer(tmp_path: Path) -> None:
    core, loaded_profile, resolved, traceability, output_dir, _result = _bundle(tmp_path)
    path = output_dir / TRACEABILITY_RELATIVE_PATH
    path.write_bytes(path.read_bytes() + b"\n")

    with pytest.raises(ResultError, match="traceability bytes differ"):
        build_success_result(core, loaded_profile, resolved, traceability, output_dir)


def test_result_matches_retained_b8_golden_bytes(tmp_path: Path) -> None:
    *_prefix, result = _bundle(tmp_path)
    actual = serialize_result(result)

    assert actual == GOLDEN.read_bytes()


def test_result_serialization_is_deterministic_and_write_last_ready(tmp_path: Path) -> None:
    *_prefix, traceability, output_dir, result = _bundle(tmp_path)

    first = serialize_result(result)
    second = serialize_result(result)
    assert first == second
    assert first.endswith(b"\n")
    assert b"\r\n" not in first

    path = write_result(output_dir, result, traceability)
    assert path.name == "integration_result.json"
    assert path.read_bytes() == first == GOLDEN.read_bytes()
