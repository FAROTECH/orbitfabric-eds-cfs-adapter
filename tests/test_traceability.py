from __future__ import annotations

import hashlib
from dataclasses import replace
from pathlib import Path

import pytest

from orbitfabric_eds_cfs_adapter.projection.eds_xml import serialize_eds_xml
from orbitfabric_eds_cfs_adapter.projection.model import (
    EdsValueConstraint,
    build_projection_model,
)
from orbitfabric_eds_cfs_adapter.projection.resolution import (
    ResolvedCommandArgument,
    ResolvedCommandBinding,
    ResolvedInterface,
    ResolvedPacketBinding,
    ResolvedProfile,
    ResolvedTelemetryField,
)
from orbitfabric_eds_cfs_adapter.projection.traceability import (
    TraceabilityError,
    build_traceability,
    serialize_traceability,
    validate_traceability,
    write_traceability,
)

ROOT = Path(__file__).resolve().parents[1]
GOLDEN = ROOT / "tests" / "fixtures" / "p0_b7" / "expected.json"
EXPECTED_SHA256 = "43d490ca64458f6166f1307e56dad77a0032941168463bcef78beea153e729d2"
EXPECTED_B6_SHA256 = "4708a4e3c61d6d89cf0273e575855de8590fc1e6e3032846725a3c180f71b240"


def _resolved() -> ResolvedProfile:
    return ResolvedProfile(
        profile_id="eds-cfs-p0",
        profile_version="0.1.0",
        package_name="OF_DEMO",
        component_name="Application",
        command_interface=ResolvedInterface(name="CMD", topic_id=160),
        telemetry_interface=ResolvedInterface(name="STATUS_TLM", topic_id=161),
        commands=(
            ResolvedCommandBinding(
                binding_id="cmd.payload-enable",
                source_id="payload.enable",
                function_code=0,
                arguments=(),
            ),
            ResolvedCommandBinding(
                binding_id="cmd.payload-set-period",
                source_id="payload.set_period",
                function_code=1,
                arguments=(
                    ResolvedCommandArgument(
                        name="period_ms",
                        semantic_type="uint32",
                        minimum=100,
                        maximum=60000,
                        enum=None,
                        default=None,
                    ),
                ),
            ),
        ),
        packets=(
            ResolvedPacketBinding(
                binding_id="packet.payload-status",
                source_id="payload_status",
                fields=(
                    ResolvedTelemetryField(
                        source_id="payload.enabled",
                        semantic_type="bool",
                    ),
                    ResolvedTelemetryField(
                        source_id="payload.sample_count",
                        semantic_type="uint32",
                    ),
                ),
            ),
        ),
        excluded=(),
        lint_warnings=(),
    )


def _stages():
    resolved = _resolved()
    model = build_projection_model(resolved)
    xml = serialize_eds_xml(model)
    return resolved, model, xml


def _mapping(payload, mapping_id: str):
    return next(item for item in payload["mappings"] if item["id"] == mapping_id)


def _resolution(payload, resolution_id: str):
    return next(item for item in payload["resolutions"] if item["id"] == resolution_id)


def test_traceability_matches_retained_golden_bytes() -> None:
    resolved, model, xml = _stages()
    payload = build_traceability(resolved, model, xml)
    actual = serialize_traceability(payload)

    assert actual == GOLDEN.read_bytes()
    assert hashlib.sha256(actual).hexdigest() == EXPECTED_SHA256
    assert payload["artifact"]["sha256"] == EXPECTED_B6_SHA256


def test_repeated_build_and_serialization_are_deterministic() -> None:
    resolved, model, xml = _stages()

    first = build_traceability(resolved, model, xml)
    second = build_traceability(resolved, model, xml)

    assert first == second
    assert serialize_traceability(first) == serialize_traceability(second)


def test_schema_validates_frozen_traceability_document() -> None:
    resolved, model, xml = _stages()
    payload = build_traceability(resolved, model, xml)

    validate_traceability(payload)


def test_all_frozen_core_sources_have_explicit_mappings() -> None:
    resolved, model, xml = _stages()
    payload = build_traceability(resolved, model, xml)

    actual = {
        (source["domain"], source["id"])
        for mapping in payload["mappings"]
        for source in mapping["sources"]
    }
    assert actual == {
        ("commands", "payload.enable"),
        ("commands", "payload.set_period"),
        ("packets", "payload_status"),
        ("telemetry", "payload.enabled"),
        ("telemetry", "payload.sample_count"),
    }
    assert [item["id"] for item in payload["mappings"]] == sorted(
        item["id"] for item in payload["mappings"]
    )


def test_command_mapping_and_resolutions_are_explicit() -> None:
    resolved, model, xml = _stages()
    payload = build_traceability(resolved, model, xml)

    mapping = _mapping(payload, "mapping.commands.payload.set_period")
    assert mapping["profile_bindings"] == ["cmd.payload-set-period"]
    assert {target["id"] for target in mapping["targets"]} >= {
        "OF_DEMO/PayloadSetPeriodCmd",
        "OF_DEMO/PayloadSetPeriod_Payload",
        "OF_DEMO/PayloadSetPeriod_Payload/PeriodMs",
        "OF_DEMO/Application/CMD",
        "OF_DEMO/Application/CMDTopicId",
    }

    assert _resolution(
        payload,
        "resolution.commands.payload.set_period.function_code",
    )["value"] == 1
    assert _resolution(
        payload,
        "resolution.commands.payload.set_period.command_topic_id",
    )["value"] == 160
    assert _resolution(
        payload,
        "resolution.commands.payload.set_period.argument.period_ms.type_ref",
    )["value"] == "BASE_TYPES/uint32"
    assert _resolution(
        payload,
        "resolution.commands.payload.set_period.argument.period_ms.valid_range",
    )["value"] == {
        "minimum": 100,
        "maximum": 60000,
        "range_type": "inclusiveMinInclusiveMax",
    }


def test_packet_and_telemetry_traceability_are_explicit() -> None:
    resolved, model, xml = _stages()
    payload = build_traceability(resolved, model, xml)

    packet = _mapping(payload, "mapping.packets.payload_status")
    assert packet["profile_bindings"] == ["packet.payload-status"]
    assert {target["id"] for target in packet["targets"]} >= {
        "OF_DEMO/PayloadStatusTlm_Payload",
        "OF_DEMO/PayloadStatusTlm",
        "OF_DEMO/Application/STATUS_TLM",
        "OF_DEMO/Application/STATUSTLMTopicId",
    }
    assert _resolution(
        payload,
        "resolution.packets.payload_status.telemetry_topic_id",
    )["value"] == 161

    enabled = _mapping(payload, "mapping.telemetry.payload.enabled")
    assert enabled["profile_bindings"] == ["packet.payload-status"]
    assert {target["id"] for target in enabled["targets"]} == {
        "OF_DEMO/PayloadStatusTlm_Payload",
        "OF_DEMO/PayloadStatusTlm_Payload/PayloadEnabled",
    }
    assert _resolution(
        payload,
        "resolution.telemetry.payload.enabled.type_ref",
    )["value"] == "BASE_TYPES/StatusBit"


def test_missing_b5_target_fails_closed() -> None:
    resolved, model, xml = _stages()
    model = replace(
        model,
        datatypes=tuple(
            item for item in model.datatypes if item.name != "PayloadEnableCmd"
        ),
    )

    with pytest.raises(TraceabilityError, match="B5 datatype PayloadEnableCmd"):
        build_traceability(resolved, model, xml)


def test_function_code_mismatch_fails_closed() -> None:
    resolved, model, xml = _stages()
    datatypes = list(model.datatypes)
    index = next(
        index
        for index, item in enumerate(datatypes)
        if item.name == "PayloadEnableCmd"
    )
    variant = datatypes[index]
    datatypes[index] = replace(
        variant,
        constraints=(EdsValueConstraint(entry="Sec.FunctionCode", value=7),),
    )

    with pytest.raises(TraceabilityError, match="Function Code mismatch"):
        build_traceability(resolved, replace(model, datatypes=tuple(datatypes)), xml)


def test_topic_id_mismatch_fails_closed() -> None:
    resolved, model, xml = _stages()
    interfaces = list(model.interfaces)
    interfaces[0] = replace(interfaces[0], topic_id=999)

    with pytest.raises(TraceabilityError, match="Topic ID mismatch"):
        build_traceability(resolved, replace(model, interfaces=tuple(interfaces)), xml)


def test_missing_telemetry_entry_fails_closed() -> None:
    resolved, model, xml = _stages()
    datatypes = list(model.datatypes)
    index = next(
        index
        for index, item in enumerate(datatypes)
        if item.name == "PayloadStatusTlm_Payload"
    )
    payload = datatypes[index]
    datatypes[index] = replace(
        payload,
        entries=tuple(
            item for item in payload.entries if item.name != "PayloadEnabled"
        ),
    )

    with pytest.raises(TraceabilityError, match="PayloadEnabled"):
        build_traceability(resolved, replace(model, datatypes=tuple(datatypes)), xml)


def test_empty_b6_artifact_fails_closed() -> None:
    resolved, model, _ = _stages()

    with pytest.raises(TraceabilityError, match="non-empty bytes"):
        build_traceability(resolved, model, b"")


def test_b7_does_not_mutate_b6_bytes() -> None:
    resolved, model, xml = _stages()
    before = hashlib.sha256(xml).hexdigest()

    build_traceability(resolved, model, xml)

    assert hashlib.sha256(xml).hexdigest() == before == EXPECTED_B6_SHA256


def test_file_wrapper_writes_exact_serializer_bytes(tmp_path: Path) -> None:
    resolved, model, xml = _stages()
    payload = build_traceability(resolved, model, xml)
    path = tmp_path / "traceability.json"

    write_traceability(path, payload)

    assert path.read_bytes() == serialize_traceability(payload)
