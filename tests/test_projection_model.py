from __future__ import annotations

from dataclasses import replace

import pytest

from orbitfabric_eds_cfs_adapter.projection.model import (
    EdsValidRange,
    ProjectionModelError,
    build_projection_model,
    eds_name_v1,
)
from orbitfabric_eds_cfs_adapter.projection.resolution import (
    ResolvedCommandArgument,
    ResolvedCommandBinding,
    ResolvedInterface,
    ResolvedPacketBinding,
    ResolvedProfile,
    ResolvedTelemetryField,
)


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


def _datatype(model, name: str):
    return next(item for item in model.datatypes if item.name == name)


def test_eds_name_v1_is_frozen() -> None:
    assert eds_name_v1("payload.enable") == "PayloadEnable"
    assert eds_name_v1("payload.set_period") == "PayloadSetPeriod"
    assert eds_name_v1("payload_status") == "PayloadStatus"
    assert eds_name_v1("period_ms") == "PeriodMs"
    assert eds_name_v1("payload.sample_count") == "PayloadSampleCount"
    assert eds_name_v1("STATUS_TLM") == "STATUSTLM"
    assert eds_name_v1("123_mode") == "N123Mode"


def test_frozen_slice_builds_expected_b5_model() -> None:
    model = build_projection_model(_resolved())

    assert (model.package_name, model.component_name) == ("OF_DEMO", "Application")
    assert [item.name for item in model.datatypes] == [
        "CommandBase",
        "PayloadEnableCmd",
        "PayloadSetPeriod_Payload",
        "PayloadSetPeriodCmd",
        "PayloadStatusTlm_Payload",
        "PayloadStatusTlm",
    ]

    command_base = _datatype(model, "CommandBase")
    assert command_base.base_type == "CFE_HDR/CommandHeader"
    assert command_base.entries == ()

    enable = _datatype(model, "PayloadEnableCmd")
    assert enable.base_type == "CommandBase"
    assert enable.entries == ()
    assert [(item.entry, item.value) for item in enable.constraints] == [
        ("Sec.FunctionCode", 0)
    ]

    period_payload = _datatype(model, "PayloadSetPeriod_Payload")
    assert [(item.name, item.type_ref) for item in period_payload.entries] == [
        ("PeriodMs", "BASE_TYPES/uint32")
    ]
    assert period_payload.entries[0].valid_range == EdsValidRange(
        minimum=100,
        maximum=60000,
        range_type="inclusiveMinInclusiveMax",
    )

    set_period = _datatype(model, "PayloadSetPeriodCmd")
    assert [(item.name, item.type_ref) for item in set_period.entries] == [
        ("Payload", "PayloadSetPeriod_Payload")
    ]
    assert [(item.entry, item.value) for item in set_period.constraints] == [
        ("Sec.FunctionCode", 1)
    ]

    telemetry_payload = _datatype(model, "PayloadStatusTlm_Payload")
    assert [(item.name, item.type_ref) for item in telemetry_payload.entries] == [
        ("PayloadEnabled", "BASE_TYPES/StatusBit"),
        ("PayloadSampleCount", "BASE_TYPES/uint32"),
    ]

    telemetry_message = _datatype(model, "PayloadStatusTlm")
    assert telemetry_message.base_type == "CFE_HDR/TelemetryHeader"
    assert [(item.name, item.type_ref) for item in telemetry_message.entries] == [
        ("Payload", "PayloadStatusTlm_Payload")
    ]

    assert [
        (
            item.name,
            item.interface_type,
            item.generic_type_name,
            item.generic_type_ref,
            item.topic_id,
            item.topic_variable,
        )
        for item in model.interfaces
    ] == [
        (
            "CMD",
            "CFE_SB/Telecommand",
            "TelecommandDataType",
            "CommandBase",
            160,
            "CMDTopicId",
        ),
        (
            "STATUS_TLM",
            "CFE_SB/Telemetry",
            "TelemetryDataType",
            "PayloadStatusTlm",
            161,
            "STATUSTLMTopicId",
        ),
    ]

    assert [
        (item.name, item.type_ref, item.read_only, item.initial_value)
        for item in model.variables
    ] == [
        ("CMDTopicId", "BASE_TYPES/uint16", True, 160),
        ("STATUSTLMTopicId", "BASE_TYPES/uint16", True, 161),
    ]
    assert [
        (item.interface, item.parameter, item.variable_ref)
        for item in model.parameter_maps
    ] == [
        ("CMD", "TopicId", "CMDTopicId"),
        ("STATUS_TLM", "TopicId", "STATUSTLMTopicId"),
    ]


def test_same_resolved_profile_builds_equal_model() -> None:
    resolved = _resolved()
    assert build_projection_model(resolved) == build_projection_model(resolved)


def test_command_binding_collection_order_is_canonicalized() -> None:
    resolved = _resolved()
    reordered = replace(resolved, commands=tuple(reversed(resolved.commands)))

    assert build_projection_model(reordered) == build_projection_model(resolved)


def test_packet_field_order_changes_ordered_telemetry_model() -> None:
    resolved = _resolved()
    packet = resolved.packets[0]
    reordered_packet = replace(packet, fields=tuple(reversed(packet.fields)))
    reordered = replace(resolved, packets=(reordered_packet,))

    original_model = build_projection_model(resolved)
    reordered_model = build_projection_model(reordered)

    original_payload = _datatype(original_model, "PayloadStatusTlm_Payload")
    reordered_payload = _datatype(reordered_model, "PayloadStatusTlm_Payload")
    assert [item.name for item in original_payload.entries] == [
        "PayloadEnabled",
        "PayloadSampleCount",
    ]
    assert [item.name for item in reordered_payload.entries] == [
        "PayloadSampleCount",
        "PayloadEnabled",
    ]
    assert original_model != reordered_model


def test_function_code_above_cfe_range_fails_closed() -> None:
    resolved = _resolved()
    commands = list(resolved.commands)
    commands[0] = replace(commands[0], function_code=128)

    with pytest.raises(ProjectionModelError, match=r"outside 0\.\.127"):
        build_projection_model(replace(resolved, commands=tuple(commands)))


def test_unsupported_core_semantic_type_fails_closed() -> None:
    resolved = _resolved()
    packet = resolved.packets[0]
    fields = list(packet.fields)
    fields[0] = replace(fields[0], semantic_type="float32")

    with pytest.raises(ProjectionModelError, match="unsupported Core semantic type"):
        build_projection_model(
            replace(resolved, packets=(replace(packet, fields=tuple(fields)),))
        )


def test_non_empty_enum_fails_closed() -> None:
    resolved = _resolved()
    commands = list(resolved.commands)
    argument = commands[1].arguments[0]
    commands[1] = replace(
        commands[1],
        arguments=(replace(argument, enum=("A", "B")),),
    )

    with pytest.raises(ProjectionModelError, match="enum realization is not supported"):
        build_projection_model(replace(resolved, commands=tuple(commands)))


def test_non_null_default_fails_closed() -> None:
    resolved = _resolved()
    commands = list(resolved.commands)
    argument = commands[1].arguments[0]
    commands[1] = replace(
        commands[1],
        arguments=(replace(argument, default=1000),),
    )

    with pytest.raises(ProjectionModelError, match="default realization is not supported"):
        build_projection_model(replace(resolved, commands=tuple(commands)))


def test_generated_datatype_collision_fails_closed() -> None:
    resolved = _resolved()
    duplicate_stem = ResolvedCommandBinding(
        binding_id="cmd.payload-enable-alias",
        source_id="payload_enable",
        function_code=2,
        arguments=(),
    )

    with pytest.raises(ProjectionModelError, match="datatype name collision"):
        build_projection_model(
            replace(resolved, commands=resolved.commands + (duplicate_stem,))
        )


def test_command_entry_collision_fails_closed() -> None:
    resolved = _resolved()
    commands = list(resolved.commands)
    base_argument = commands[1].arguments[0]
    commands[1] = replace(
        commands[1],
        arguments=(
            base_argument,
            replace(base_argument, name="period-ms"),
        ),
    )

    with pytest.raises(ProjectionModelError, match="command entry"):
        build_projection_model(replace(resolved, commands=tuple(commands)))


def test_topic_variable_collision_fails_closed() -> None:
    resolved = _resolved()
    collided = replace(
        resolved,
        command_interface=ResolvedInterface(name="A_B", topic_id=160),
        telemetry_interface=ResolvedInterface(name="AB", topic_id=161),
    )

    with pytest.raises(ProjectionModelError, match="TopicId variable name collision"):
        build_projection_model(collided)


def test_multiple_projected_packets_fail_closed() -> None:
    resolved = _resolved()

    with pytest.raises(ProjectionModelError, match="exactly one projected telemetry packet"):
        build_projection_model(replace(resolved, packets=resolved.packets * 2))


def test_invalid_uint32_range_fails_closed() -> None:
    resolved = _resolved()
    commands = list(resolved.commands)
    argument = commands[1].arguments[0]
    commands[1] = replace(
        commands[1],
        arguments=(replace(argument, minimum=70000, maximum=60000),),
    )

    with pytest.raises(ProjectionModelError, match="minimum 70000 exceeds maximum 60000"):
        build_projection_model(replace(resolved, commands=tuple(commands)))
