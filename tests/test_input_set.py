from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import pytest

from orbitfabric_eds_cfs_adapter.input_set import (
    InputSetError,
    compute_input_set_sha256,
    load_input_set,
)


def _write_json(path: Path, payload: dict[str, Any]) -> str:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _fixture(tmp_path: Path) -> Path:
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
                        {"name": "period_ms", "type": "uint32", "min": 100, "max": 60000}
                    ],
                },
            ],
            "telemetry": [
                {"id": "payload.enabled", "type": "bool"},
                {"id": "payload.sample_count", "type": "uint32"},
            ],
        },
    }
    relationship_manifest = {
        "kind": "orbitfabric.relationship_manifest",
        "manifest_version": "0.1-candidate",
        "relationships": [
            {
                "relationship_id": (
                    "packets:payload_status->packet_includes_telemetry:telemetry:payload.enabled"
                ),
                "relationship_type": "packet_includes_telemetry",
                "from": {"domain": "packets", "id": "payload_status"},
                "to": {"domain": "telemetry", "id": "payload.enabled"},
                "derived_from": {"model_field": "packets[].telemetry"},
            },
            {
                "relationship_id": (
                    "packets:payload_status->packet_includes_telemetry:telemetry:payload.sample_count"
                ),
                "relationship_type": "packet_includes_telemetry",
                "from": {"domain": "packets", "id": "payload_status"},
                "to": {"domain": "telemetry", "id": "payload.sample_count"},
                "derived_from": {"model_field": "packets[].telemetry"},
            },
            {
                "relationship_id": (
                    "commands:payload.enable->command_targets_subsystem:subsystems:payload"
                ),
                "relationship_type": "command_targets_subsystem",
                "from": {"domain": "commands", "id": "payload.enable"},
                "to": {"domain": "subsystems", "id": "payload"},
                "derived_from": {"model_field": "commands[].target"},
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
            relationship_manifest,
        ),
    }

    surfaces = []
    for role, (kind, format_version, filename, payload) in surface_payloads.items():
        digest = _write_json(tmp_path / filename, payload)
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

    manifest_path = tmp_path / "integration_input_manifest.json"
    _write_json(manifest_path, manifest)
    return manifest_path


def test_minimal_b2_input_set_loads(tmp_path: Path) -> None:
    loaded = load_input_set(_fixture(tmp_path))

    assert loaded.resolve_entity("commands", "payload.enable")["id"] == "payload.enable"
    assert loaded.resolve_entity("telemetry", "payload.sample_count")["domain"] == "telemetry"
    assert loaded.packet_telemetry_ids("payload_status") == (
        "payload.enabled",
        "payload.sample_count",
    )
    assert len(loaded.lint_warnings) == 6


def test_model_summary_is_not_required_by_b2_contract(tmp_path: Path) -> None:
    manifest_path = _fixture(tmp_path)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    assert {surface["role"] for surface in manifest["surfaces"]} == {
        "entity_index",
        "lint_report",
        "mission_snapshot",
        "relationship_manifest",
    }
    load_input_set(manifest_path)


def test_unknown_additive_relationship_family_is_ignored(tmp_path: Path) -> None:
    manifest_path = _fixture(tmp_path)
    relationship_path = tmp_path / "relationship_manifest.json"
    relationships = json.loads(relationship_path.read_text(encoding="utf-8"))
    relationships["relationships"].append(
        {
            "relationship_id": "future:relation",
            "relationship_type": "future_additive_family",
            "from": {"domain": "commands", "id": "payload.enable"},
            "to": {"domain": "telemetry", "id": "payload.enabled"},
            "derived_from": {"model_field": "future.field"},
        }
    )
    new_digest = _write_json(relationship_path, relationships)

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    relationship_record = next(
        item for item in manifest["surfaces"] if item["role"] == "relationship_manifest"
    )
    relationship_record["sha256"] = new_digest
    manifest["input_set_sha256"] = compute_input_set_sha256(manifest)
    _write_json(manifest_path, manifest)

    loaded = load_input_set(manifest_path)
    assert loaded.packet_telemetry_ids("payload_status") == (
        "payload.enabled",
        "payload.sample_count",
    )


def test_required_surface_hash_mismatch_fails_closed(tmp_path: Path) -> None:
    manifest_path = _fixture(tmp_path)
    path = tmp_path / "entity_index.json"
    path.write_text(path.read_text(encoding="utf-8") + "\n", encoding="utf-8")

    with pytest.raises(InputSetError, match="entity_index: SHA-256 mismatch"):
        load_input_set(manifest_path)


def test_failed_lint_state_is_rejected_even_with_valid_manifest_digest(tmp_path: Path) -> None:
    manifest_path = _fixture(tmp_path)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["lint_result"] = "failed"
    manifest["input_set_sha256"] = compute_input_set_sha256(manifest)
    _write_json(manifest_path, manifest)

    with pytest.raises(InputSetError, match="semantic lint blocks projection"):
        load_input_set(manifest_path)


def test_unknown_core_identity_fails_closed(tmp_path: Path) -> None:
    loaded = load_input_set(_fixture(tmp_path))

    with pytest.raises(InputSetError, match="must resolve exactly once"):
        loaded.resolve_entity("commands", "payload.unknown")
