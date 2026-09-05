from __future__ import annotations

import hashlib
from dataclasses import replace
from pathlib import Path

import pytest

from orbitfabric_eds_cfs_adapter.projection.eds_xml import serialize_eds_xml
from orbitfabric_eds_cfs_adapter.projection.model import (
    EdsEntry,
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
EXPECTED_SHA256 = "d537a2b80658aa71e8f69af9fa0517318b009bf319db41653e406ff7d8a68c2e"
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


def _replace_datatype(model, name: str, replacement):
    datatypes = list(model.datatypes)
    index = next(index for index, item in enumerate(datatypes) if item.name == name)
    datatypes[index] = replacement(datatypes[index])
    return replace(model, datatypes=tuple(datatypes))


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


def test_command_mapping_and_resolution_provenance_are_explicit() -> None:
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

    function_code = _resolution(
        payload,
        "resolution.commands.payload.set_period.function_code",
    )
    assert (function_code["value"], function_code["origin"]) == (1, "profile")

    topic_id = _resolution(
        payload,
        "resolution.commands.payload.set_period.command_topic_id",
    )
    assert (topic_id["value"], topic_id["origin"]) == (160, "profile")

    type_ref = _resolution(
        payload,
        "resolution.commands.payload.set_period.argument.period_ms.type_ref",
    )
    assert (type_ref["value"], type_ref["origin"]) == (
        "BASE_TYPES/uint32",
        "adapter_default",
    )

    minimum = _resolution(
        payload,
        "resolution.commands.payload.set_period.argument.period_ms.minimum",
    )
    maximum = _resolution(
        payload,
        "resolution.commands.payload.set_period.argument.period_ms.maximum",
    )
    range_type = _resolution(
        payload,
        "resolution.commands.payload.set_period.argument.period_ms.range_type",
    )
    assert (minimum["value"], minimum["origin"]) == (100, "core")
    assert (maximum["value"], maximum["origin"]) == (60000, "core")
    assert (range_type["value"], range_type["origin"]) == (
        "inclusiveMinInclusiveMax",
        "adapter_default",
    )


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
    enabled_type = _resolution(
        payload,
        "resolution.telemetry.payload.enabled.type_ref",
    )
    assert (enabled_type["value"], enabled_type["origin"]) == (
        "BASE_TYPES/StatusBit",
        "adapter_default",
    )


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
    model = _replace_datatype(
        model,
        "PayloadEnableCmd",
        lambda item: replace(
            item,
            constraints=(EdsValueConstraint(entry="Sec.FunctionCode", value=7),),
        ),
    )

    with pytest.raises(TraceabilityError, match="Function Code mismatch"):
        build_traceability(resolved, model, xml)


def test_topic_id_mismatch_fails_closed() -> None:
    resolved, model, xml = _stages()
    interfaces = list(model.interfaces)
    interfaces[0] = replace(interfaces[0], topic_id=999)

    with pytest.raises(TraceabilityError, match="Topic ID mismatch"):
        build_traceability(resolved, replace(model, interfaces=tuple(interfaces)), xml)


def test_command_payload_link_mismatch_fails_closed() -> None:
    resolved, model, xml = _stages()
    model = _replace_datatype(
        model,
        "PayloadSetPeriodCmd",
        lambda item: replace(
            item,
            entries=(EdsEntry(name="Payload", type_ref="WrongPayload"),),
        ),
    )

    with pytest.raises(TraceabilityError, match="Payload type mismatch"):
        build_traceability(resolved, model, xml)


def test_command_type_realization_mismatch_fails_closed() -> None:
    resolved, model, xml = _stages()

    def replace_period(payload):
        period = payload.entries[0]
        return replace(
            payload,
            entries=(replace(period, type_ref="BASE_TYPES/StatusBit"),),
        )

    model = _replace_datatype(model, "PayloadSetPeriod_Payload", replace_period)

    with pytest.raises(TraceabilityError, match="type realization mismatch"):
        build_traceability(resolved, model, xml)


def test_missing_telemetry_entry_fails_closed() -> None:
    resolved, model, xml = _stages()

    def remove_enabled(payload):
        return replace(
            payload,
            entries=tuple(
                item for item in payload.entries if item.name != "PayloadEnabled"
            ),
        )

    model = _replace_datatype(model, "PayloadStatusTlm_Payload", remove_enabled)

    with pytest.raises(TraceabilityError, match="PayloadEnabled"):
        build_traceability(resolved, model, xml)


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
