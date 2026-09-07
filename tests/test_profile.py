from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import pytest
import yaml
from jsonschema import ValidationError

from orbitfabric_eds_cfs_adapter.profile import load_profile

ROOT = Path(__file__).resolve().parents[1]
VALID_PROFILE = ROOT / "tests" / "fixtures" / "p0_b3" / "profile.yaml"


def _load_valid() -> dict:
    value = yaml.safe_load(VALID_PROFILE.read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def _write(tmp_path: Path, profile: dict) -> Path:
    path = tmp_path / "profile.yaml"
    path.write_text(yaml.safe_dump(profile, sort_keys=False), encoding="utf-8")
    return path


def test_real_p0_profile_is_valid() -> None:
    profile = load_profile(VALID_PROFILE)

    assert profile["settings"]["eds"] == {
        "package_name": "OF_DEMO",
        "component_name": "Application",
    }
    assert profile["settings"]["interfaces"]["command"]["topic_ref"] == (
        "CFE_MISSION/OF_DEMO_CMD_TOPICID"
    )
    assert profile["settings"]["interfaces"]["telemetry"]["topic_ref"] == (
        "CFE_MISSION/OF_DEMO_STATUS_TLM_TOPICID"
    )
    assert profile["bindings"][0]["config"]["function_code"] == 0
    assert profile["bindings"][2]["config"]["fields"][0]["source"] == {
        "domain": "telemetry",
        "id": "payload.enabled",
    }


def test_unknown_target_setting_fails_closed(tmp_path: Path) -> None:
    profile = _load_valid()
    profile["settings"]["cfs_app"] = "OF_DEMO"

    with pytest.raises(ValidationError):
        load_profile(_write(tmp_path, profile))


def test_header_override_is_not_part_of_b3(tmp_path: Path) -> None:
    profile = _load_valid()
    profile["settings"]["eds"]["command_header"] = "CFE_HDR/CommandHeader"

    with pytest.raises(ValidationError):
        load_profile(_write(tmp_path, profile))


def test_invalid_target_name_is_rejected(tmp_path: Path) -> None:
    profile = _load_valid()
    profile["settings"]["eds"]["package_name"] = "OF-DEMO"

    with pytest.raises(ValidationError):
        load_profile(_write(tmp_path, profile))


def test_topic_ref_requires_cfe_mission_namespace(tmp_path: Path) -> None:
    profile = _load_valid()
    profile["settings"]["interfaces"]["telemetry"]["topic_ref"] = (
        "OTHER_MISSION/OF_DEMO_STATUS_TLM_TOPICID"
    )

    with pytest.raises(ValidationError):
        load_profile(_write(tmp_path, profile))


def test_topic_ref_symbol_must_be_target_safe(tmp_path: Path) -> None:
    profile = _load_valid()
    profile["settings"]["interfaces"]["telemetry"]["topic_ref"] = (
        "CFE_MISSION/OF-DEMO-STATUS-TLM"
    )

    with pytest.raises(ValidationError):
        load_profile(_write(tmp_path, profile))


def test_numeric_topic_id_is_not_supported_in_pre_v01_contract(tmp_path: Path) -> None:
    profile = _load_valid()
    command = profile["settings"]["interfaces"]["command"]
    command.pop("topic_ref")
    command["topic_id"] = 160

    with pytest.raises(ValidationError):
        load_profile(_write(tmp_path, profile))


def test_projected_command_requires_function_code(tmp_path: Path) -> None:
    profile = _load_valid()
    profile["bindings"][0]["config"] = {}

    with pytest.raises(ValidationError):
        load_profile(_write(tmp_path, profile))


def test_projected_command_cannot_copy_core_arguments(tmp_path: Path) -> None:
    profile = _load_valid()
    profile["bindings"][1]["config"]["arguments"] = [
        {"name": "period_ms", "type": "uint32"}
    ]

    with pytest.raises(ValidationError):
        load_profile(_write(tmp_path, profile))


def test_projected_packet_requires_ordered_fields(tmp_path: Path) -> None:
    profile = _load_valid()
    profile["bindings"][2]["config"] = {}

    with pytest.raises(ValidationError):
        load_profile(_write(tmp_path, profile))


def test_packet_field_source_must_be_telemetry(tmp_path: Path) -> None:
    profile = _load_valid()
    profile["bindings"][2]["config"]["fields"][0]["source"]["domain"] = "commands"

    with pytest.raises(ValidationError):
        load_profile(_write(tmp_path, profile))


def test_project_binding_domain_is_limited_to_b3_classes(tmp_path: Path) -> None:
    profile = _load_valid()
    profile["bindings"][0]["sources"][0]["domain"] = "telemetry"

    with pytest.raises(ValidationError):
        load_profile(_write(tmp_path, profile))


def test_do_not_project_requires_reason_and_empty_config(tmp_path: Path) -> None:
    profile = _load_valid()
    binding = profile["bindings"][0]
    binding["intent"] = "do_not_project"
    binding["config"] = {}
    binding.pop("reason", None)

    with pytest.raises(ValidationError):
        load_profile(_write(tmp_path, profile))

    binding["reason"] = "Not part of this target realization"
    binding["config"] = {"function_code": 0}

    with pytest.raises(ValidationError):
        load_profile(_write(tmp_path, profile))

    binding["config"] = {}
    loaded = load_profile(_write(tmp_path, profile))
    assert loaded["bindings"][0]["intent"] == "do_not_project"


def test_binding_class_is_not_inferred_from_binding_id(tmp_path: Path) -> None:
    profile = deepcopy(_load_valid())
    profile["bindings"][0]["id"] = "packet.deliberately-misleading-local-id"

    loaded = load_profile(_write(tmp_path, profile))
    assert loaded["bindings"][0]["sources"][0]["domain"] == "commands"
    assert loaded["bindings"][0]["config"]["function_code"] == 0
