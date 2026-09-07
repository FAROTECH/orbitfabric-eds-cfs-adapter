from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from pathlib import Path
from typing import Any

import yaml

from orbitfabric_eds_cfs_adapter.cli import main
from orbitfabric_eds_cfs_adapter.input_set import compute_input_set_sha256

ROOT = Path(__file__).resolve().parents[1]
VALID_PROFILE = ROOT / "tests" / "fixtures" / "p0_b3" / "profile.yaml"
B8_GOLDEN = ROOT / "tests" / "fixtures" / "p0_b8" / "expected.json"


def _write_json(path: Path, payload: dict[str, Any]) -> str:
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _input_set(root: Path) -> Path:
    root.mkdir(parents=True)
    entity_index = {
        "kind": "orbitfabric.entity_index",
        "index_version": "0.1",
        "entities": [
            {"domain": "commands", "id": "payload.enable"},
            {"domain": "commands", "id": "payload.set_period"},
            {"domain": "telemetry", "id": "payload.enabled"},
            {"domain": "telemetry", "id": "payload.sample_count"},
            {"domain": "packets", "id": "payload_status"},
        ],
    }
    snapshot = {
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
    }
    relationships = {
        "kind": "orbitfabric.relationship_manifest",
        "manifest_version": "0.1-candidate",
        "relationships": [
            {
                "relationship_id": (
                    "packets:payload_status->packet_includes_telemetry:"
                    "telemetry:payload.enabled"
                ),
                "relationship_type": "packet_includes_telemetry",
                "from": {"domain": "packets", "id": "payload_status"},
                "to": {"domain": "telemetry", "id": "payload.enabled"},
                "derived_from": {"model_field": "packets[].telemetry"},
            },
            {
                "relationship_id": (
                    "packets:payload_status->packet_includes_telemetry:"
                    "telemetry:payload.sample_count"
                ),
                "relationship_type": "packet_includes_telemetry",
                "from": {"domain": "packets", "id": "payload_status"},
                "to": {"domain": "telemetry", "id": "payload.sample_count"},
                "derived_from": {"model_field": "packets[].telemetry"},
            },
        ],
    }
    lint_report = {
        "tool": "orbitfabric-lint",
        "version": "1.3.0",
        "result": "passed_with_warnings",
        "findings": [
            {"severity": "WARNING", "code": f"TEST-{index}"} for index in range(6)
        ],
    }

    surface_payloads = {
        "entity_index": (
            "orbitfabric.entity_index",
            "0.1",
            "entity_index.json",
            entity_index,
        ),
        "lint_report": ("orbitfabric-lint", "v1", "lint_report.json", lint_report),
        "mission_snapshot": (
            "orbitfabric.mission_snapshot",
            "0.1-candidate",
            "mission_snapshot.json",
            snapshot,
        ),
        "relationship_manifest": (
            "orbitfabric.relationship_manifest",
            "0.1-candidate",
            "relationship_manifest.json",
            relationships,
        ),
    }

    surfaces = []
    for role, (kind, format_version, filename, payload) in surface_payloads.items():
        digest = _write_json(root / filename, payload)
        surfaces.append(
            {
                "role": role,
                "requirement": "required",
                "status": "available",
                "kind": kind,
                "format_version": format_version,
                "path": filename,
                "sha256": digest,
                "unavailable_reason": None,
            }
        )

    manifest = {
        "kind": "orbitfabric.integration_input_set",
        "input_set_version": "0.1-candidate",
        "orbitfabric_version": "1.3.0",
        "mission": {"id": "eds-cfs-p0", "model_version": "0.1.0"},
        "load_result": "loaded",
        "lint_result": "passed_with_warnings",
        "surfaces": surfaces,
    }
    manifest["input_set_sha256"] = compute_input_set_sha256(manifest)
    manifest_path = root / "integration_input_manifest.json"
    _write_json(manifest_path, manifest)
    return manifest_path


def _profile() -> dict[str, Any]:
    value = yaml.safe_load(VALID_PROFILE.read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def _write_profile(root: Path, payload: dict[str, Any]) -> Path:
    path = root / "profile.yaml"
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    return path


def _run(
    manifest: Path,
    profile: Path,
    output_dir: Path,
    operation: str = "eds_cfs_projection",
) -> int:
    return main(
        [
            "run",
            "--operation",
            operation,
            "--input-set-manifest",
            str(manifest),
            "--profile",
            str(profile),
            "--output-dir",
            str(output_dir),
        ]
    )


def _result(output_dir: Path) -> dict[str, Any]:
    return json.loads((output_dir / "integration_result.json").read_text(encoding="utf-8"))


def _assert_failed_bundle(
    output_dir: Path,
    *,
    phase: str,
    code: str,
    core_status: str,
    mission_status: str,
    profile_status: str,
    schema_version: str | None,
    coverage_status: str,
) -> dict[str, Any]:
    result = _result(output_dir)
    assert result["result"] == "failed"
    assert result["integration"]["schema_version"] == schema_version
    assert result["inputs"]["core_input_set"]["status"] == core_status
    assert result["mission"]["status"] == mission_status
    assert result["inputs"]["profile"]["status"] == profile_status
    assert result["inputs"]["operation_inputs"] == []
    assert result["mappings"] == []
    assert result["resolutions"] == []
    assert result["evidence"] == []
    assert result["external_tools"] == []
    assert result["coverage"]["status"] == coverage_status
    assert result["diagnostics"] == [
        {
            "id": "diag-001",
            "owner": "integration",
            "producer": "orbitfabric-eds-cfs",
            "phase": phase,
            "severity": "ERROR",
            "code": code,
            "message": result["diagnostics"][0]["message"],
            "sources": [],
            "profile_bindings": [],
            "targets": [],
        }
    ]
    assert [item["id"] for item in result["artifacts"]] == [
        "eds.package",
        "traceability",
    ]
    assert all(item["path"] is None for item in result["artifacts"])
    assert all(item["sha256"] is None for item in result["artifacts"])
    assert all(item["retained_partial"] is False for item in result["artifacts"])
    assert not (output_dir / "eds" / "mission.xml").exists()
    assert not (output_dir / "traceability.json").exists()
    return result


def test_unknown_operation_returns_2_without_mutating_existing_bundle(tmp_path: Path) -> None:
    manifest = _input_set(tmp_path / "input")
    output = tmp_path / "out"
    (output / "eds").mkdir(parents=True)
    files = {
        output / "integration_result.json": B8_GOLDEN.read_bytes(),
        output / "traceability.json": b"old trace\n",
        output / "eds" / "mission.xml": b"old xml\n",
        output / "keep.txt": b"caller owned\n",
    }
    for path, content in files.items():
        path.write_bytes(content)

    assert _run(manifest, VALID_PROFILE, output, operation="unknown") == 2
    assert {path: path.read_bytes() for path in files} == files


def test_b2_tampered_core_fails_with_unavailable_provenance(tmp_path: Path) -> None:
    manifest = _input_set(tmp_path / "input")
    entity_index = manifest.parent / "entity_index.json"
    entity_index.write_bytes(entity_index.read_bytes() + b"\n")
    output = tmp_path / "out"

    assert _run(manifest, VALID_PROFILE, output) == 1
    result = _assert_failed_bundle(
        output,
        phase="input_compatibility",
        code="EDS-CFS-INPUT-001",
        core_status="unavailable",
        mission_status="unavailable",
        profile_status="unavailable",
        schema_version=None,
        coverage_status="unavailable",
    )
    assert result["capabilities"] == []


def test_b3_negative_matrix_fails_at_profile_schema(tmp_path: Path) -> None:
    manifest = _input_set(tmp_path / "input")
    base = _profile()
    cases: list[tuple[str, dict[str, Any]]] = []

    missing_function_code = deepcopy(base)
    missing_function_code["bindings"][0]["config"] = {}
    cases.append(("missing-function-code", missing_function_code))

    missing_topic = deepcopy(base)
    missing_topic["settings"]["interfaces"]["command"].pop("topic_ref")
    cases.append(("missing-topic-ref", missing_topic))

    invalid_name = deepcopy(base)
    invalid_name["settings"]["eds"]["package_name"] = "OF-DEMO"
    cases.append(("invalid-target-name", invalid_name))

    for name, payload in cases:
        case_root = tmp_path / name
        case_root.mkdir()
        profile = _write_profile(case_root, payload)
        output = case_root / "out"
        assert _run(manifest, profile, output) == 1
        result = _assert_failed_bundle(
            output,
            phase="profile_schema",
            code="EDS-CFS-PROFILE-001",
            core_status="available",
            mission_status="available",
            profile_status="unavailable",
            schema_version=None,
            coverage_status="unavailable",
        )
        assert result["capabilities"] == ["profile_validation"]


def test_b4_negative_matrix_fails_at_source_resolution(tmp_path: Path) -> None:
    manifest = _input_set(tmp_path / "input")
    base = _profile()
    cases: list[tuple[str, dict[str, Any]]] = []

    function_collision = deepcopy(base)
    function_collision["bindings"][1]["config"]["function_code"] = 0
    cases.append(("function-code-collision", function_collision))

    topic_collision = deepcopy(base)
    topic_collision["settings"]["interfaces"]["telemetry"]["topic_ref"] = (
        base["settings"]["interfaces"]["command"]["topic_ref"]
    )
    cases.append(("topic-ref-collision", topic_collision))

    unknown_source = deepcopy(base)
    unknown_source["bindings"][0]["sources"][0]["id"] = "payload.unknown"
    cases.append(("unknown-core-source", unknown_source))

    membership_mismatch = deepcopy(base)
    membership_mismatch["bindings"][2]["config"]["fields"] = membership_mismatch[
        "bindings"
    ][2]["config"]["fields"][:1]
    cases.append(("packet-membership-mismatch", membership_mismatch))

    for name, payload in cases:
        case_root = tmp_path / name
        case_root.mkdir()
        profile = _write_profile(case_root, payload)
        output = case_root / "out"
        assert _run(manifest, profile, output) == 1
        result = _assert_failed_bundle(
            output,
            phase="source_resolution",
            code="EDS-CFS-RESOLVE-001",
            core_status="available",
            mission_status="available",
            profile_status="available",
            schema_version="0.1-candidate",
            coverage_status="unavailable",
        )
        assert result["capabilities"] == ["profile_validation", "projection"]


def test_b5_function_code_128_is_projection_validation_with_blocked_coverage(
    tmp_path: Path,
) -> None:
    manifest = _input_set(tmp_path / "input")
    profile_payload = _profile()
    profile_payload["bindings"][0]["config"]["function_code"] = 128
    profile = _write_profile(tmp_path, profile_payload)
    output = tmp_path / "out"

    assert _run(manifest, profile, output) == 1
    result = _assert_failed_bundle(
        output,
        phase="projection_validation",
        code="EDS-CFS-PROJECT-001",
        core_status="available",
        mission_status="available",
        profile_status="available",
        schema_version="0.1-candidate",
        coverage_status="complete",
    )
    assert result["capabilities"] == ["profile_validation", "projection"]
    assert result["coverage"]["summary"] == {"blocked": 5}
    assert len(result["coverage"]["records"]) == 5
    assert all(
        record["state"] == "blocked" for record in result["coverage"]["records"]
    )
    assert all(
        record["diagnostics"] == ["diag-001"]
        for record in result["coverage"]["records"]
    )


def test_declared_failure_rolls_back_owned_outputs_but_preserves_unrelated_files(
    tmp_path: Path,
) -> None:
    manifest = _input_set(tmp_path / "input")
    profile_payload = _profile()
    profile_payload["bindings"][0]["config"]["function_code"] = 128
    profile = _write_profile(tmp_path, profile_payload)
    output = tmp_path / "out"
    (output / "eds").mkdir(parents=True)
    (output / "integration_result.json").write_bytes(B8_GOLDEN.read_bytes())
    (output / "traceability.json").write_text("stale trace\n", encoding="utf-8")
    (output / "eds" / "mission.xml").write_text("stale xml\n", encoding="utf-8")
    (output / "keep.txt").write_text("caller owned\n", encoding="utf-8")
    (output / "eds" / "keep-too.txt").write_text("caller owned\n", encoding="utf-8")

    assert _run(manifest, profile, output) == 1
    assert (output / "integration_result.json").is_file()
    assert not (output / "traceability.json").exists()
    assert not (output / "eds" / "mission.xml").exists()
    assert (output / "keep.txt").read_text(encoding="utf-8") == "caller owned\n"
    assert (output / "eds" / "keep-too.txt").read_text(encoding="utf-8") == "caller owned\n"


def test_failed_result_bytes_are_deterministic(tmp_path: Path) -> None:
    manifest = _input_set(tmp_path / "input")
    profile_payload = _profile()
    profile_payload["bindings"][0]["config"]["function_code"] = 128
    profile = _write_profile(tmp_path, profile_payload)

    outputs = [tmp_path / "out-a", tmp_path / "out-b"]
    for output in outputs:
        assert _run(manifest, profile, output) == 1

    first = (outputs[0] / "integration_result.json").read_bytes()
    second = (outputs[1] / "integration_result.json").read_bytes()
    assert first == second
    assert first.endswith(b"\n")
    assert b"\r\n" not in first
