from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import pytest

from orbitfabric_eds_cfs_adapter.input_set import LoadedInputSet
from orbitfabric_eds_cfs_adapter.profile import load_profile
from orbitfabric_eds_cfs_adapter.projection.resolution import ResolutionError, resolve_profile

ROOT = Path(__file__).resolve().parents[1]
PROFILE = ROOT / "tests" / "fixtures" / "p0_b3" / "profile.yaml"


def _core() -> LoadedInputSet:
    entities = [
        {"domain": "commands", "id": "payload.enable"},
        {"domain": "commands", "id": "payload.set_period"},
        {"domain": "telemetry", "id": "payload.enabled"},
        {"domain": "telemetry", "id": "payload.sample_count"},
        {"domain": "telemetry", "id": "payload.temperature"},
        {"domain": "packets", "id": "payload_status"},
    ]
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
                            "description": "Must not leak into the B4 resolved contract",
                        }
                    ],
                },
            ],
            "telemetry": [
                {
                    "id": "payload.enabled",
                    "type": "bool",
                    "description": "Must not leak into the B4 resolved contract",
                },
                {"id": "payload.sample_count", "type": "uint32"},
                {"id": "payload.temperature", "type": "float32"},
            ],
        },
    }
    relationships = {
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
    }
    lint = {
        "tool": "orbitfabric-lint",
        "result": "passed_with_warnings",
        "findings": [
            {"severity": "WARNING", "code": f"TEST-{index}"} for index in range(6)
        ],
    }
    return LoadedInputSet(
        root=Path("."),
        manifest={"lint_result": "passed_with_warnings"},
        snapshot=snapshot,
        entity_index={
            "kind": "orbitfabric.entity_index",
            "index_version": "0.1",
            "entities": entities,
        },
        relationship_manifest=relationships,
        lint_report=lint,
    )


def _profile() -> dict:
    return deepcopy(load_profile(PROFILE))


def test_canonical_profile_resolves_against_core() -> None:
    resolved = resolve_profile(_profile(), _core())

    assert resolved.profile_id == "eds-cfs-p0"
    assert resolved.package_name == "OF_DEMO"
    assert resolved.command_interface.topic_id == 160
    assert resolved.telemetry_interface.topic_id == 416
    assert [(item.source_id, item.function_code) for item in resolved.commands] == [
        ("payload.enable", 0),
        ("payload.set_period", 1),
    ]
    assert resolved.commands[1].arguments[0].name == "period_ms"
    assert resolved.commands[1].arguments[0].semantic_type == "uint32"
    assert resolved.commands[1].arguments[0].minimum == 100
    assert resolved.commands[1].arguments[0].maximum == 60000
    assert [field.source_id for field in resolved.packets[0].fields] == [
        "payload.enabled",
        "payload.sample_count",
    ]
    assert [field.semantic_type for field in resolved.packets[0].fields] == [
        "bool",
        "uint32",
    ]
    assert len(resolved.lint_warnings) == 6


def test_resolved_boundary_does_not_leak_unfrozen_snapshot_fields() -> None:
    resolved = resolve_profile(_profile(), _core())

    argument = resolved.commands[1].arguments[0]
    field = resolved.packets[0].fields[0]
    assert not hasattr(argument, "description")
    assert not hasattr(field, "description")


def test_packet_field_order_is_profile_owned_not_relationship_order() -> None:
    profile = _profile()
    profile["bindings"][2]["config"]["fields"].reverse()

    resolved = resolve_profile(profile, _core())

    assert [field.source_id for field in resolved.packets[0].fields] == [
        "payload.sample_count",
        "payload.enabled",
    ]


def test_binding_collection_order_is_canonicalized() -> None:
    profile = _profile()
    profile["bindings"].reverse()

    resolved = resolve_profile(profile, _core())

    assert [item.binding_id for item in resolved.commands] == [
        "cmd.payload-enable",
        "cmd.payload-set-period",
    ]
    assert [item.binding_id for item in resolved.packets] == ["packet.payload-status"]


def test_unknown_command_identity_fails_closed() -> None:
    profile = _profile()
    profile["bindings"][0]["sources"][0]["id"] = "payload.unknown"

    with pytest.raises(ResolutionError, match="Core identity must resolve exactly once"):
        resolve_profile(profile, _core())


def test_unknown_packet_identity_fails_closed() -> None:
    profile = _profile()
    profile["bindings"][2]["sources"][0]["id"] = "unknown_status"

    with pytest.raises(ResolutionError, match="Core identity must resolve exactly once"):
        resolve_profile(profile, _core())


def test_unknown_telemetry_field_identity_fails_closed() -> None:
    profile = _profile()
    profile["bindings"][2]["config"]["fields"][0]["source"]["id"] = "payload.unknown"

    with pytest.raises(ResolutionError, match="Core identity must resolve exactly once"):
        resolve_profile(profile, _core())


def test_duplicate_function_code_fails_closed() -> None:
    profile = _profile()
    profile["bindings"][1]["config"]["function_code"] = 0

    with pytest.raises(ResolutionError, match="Function Code collision"):
        resolve_profile(profile, _core())


def test_topic_id_collision_fails_closed() -> None:
    profile = _profile()
    profile["settings"]["interfaces"]["telemetry"]["topic_id"] = 160

    with pytest.raises(ResolutionError, match="Topic ID collision"):
        resolve_profile(profile, _core())


def test_missing_packet_member_fails_closed() -> None:
    profile = _profile()
    profile["bindings"][2]["config"]["fields"].pop()

    with pytest.raises(ResolutionError, match=r"missing=payload\.sample_count"):
        resolve_profile(profile, _core())


def test_extra_packet_member_fails_closed() -> None:
    profile = _profile()
    profile["bindings"][2]["config"]["fields"].append(
        {"source": {"domain": "telemetry", "id": "payload.temperature"}}
    )

    with pytest.raises(ResolutionError, match=r"extra=payload\.temperature"):
        resolve_profile(profile, _core())


def test_duplicate_packet_member_fails_closed() -> None:
    profile = _profile()
    profile["bindings"][2]["config"]["fields"].append(
        {"source": {"domain": "telemetry", "id": "payload.enabled"}}
    )

    with pytest.raises(ResolutionError, match="duplicate packet field source"):
        resolve_profile(profile, _core())


def test_duplicate_binding_id_fails_closed() -> None:
    profile = _profile()
    profile["bindings"][1]["id"] = profile["bindings"][0]["id"]

    with pytest.raises(ResolutionError, match="duplicate binding id"):
        resolve_profile(profile, _core())


def test_do_not_project_source_still_resolves_and_is_recorded() -> None:
    profile = _profile()
    binding = profile["bindings"][0]
    binding["intent"] = "do_not_project"
    binding["reason"] = "Intentionally excluded from this target realization"
    binding["config"] = {}

    resolved = resolve_profile(profile, _core())

    assert [(item.source_domain, item.source_id) for item in resolved.excluded] == [
        ("commands", "payload.enable")
    ]
    assert [item.source_id for item in resolved.commands] == ["payload.set_period"]
