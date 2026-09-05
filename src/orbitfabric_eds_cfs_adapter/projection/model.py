from __future__ import annotations

import re
from dataclasses import dataclass

from orbitfabric_eds_cfs_adapter.projection.resolution import (
    ResolvedCommandArgument,
    ResolvedProfile,
)

COMMAND_BASE_NAME = "CommandBase"
COMMAND_HEADER_TYPE = "CFE_HDR/CommandHeader"
TELEMETRY_HEADER_TYPE = "CFE_HDR/TelemetryHeader"
COMMAND_INTERFACE_TYPE = "CFE_SB/Telecommand"
TELEMETRY_INTERFACE_TYPE = "CFE_SB/Telemetry"
COMMAND_GENERIC_TYPE = "TelecommandDataType"
TELEMETRY_GENERIC_TYPE = "TelemetryDataType"
FUNCTION_CODE_ENTRY = "Sec.FunctionCode"
TOPIC_ID_PARAMETER = "TopicId"
TOPIC_ID_TYPE = "BASE_TYPES/uint16"
FUNCTION_CODE_MAX = 127
UINT32_MAX = 4294967295

TYPE_REFS = {
    "bool": "BASE_TYPES/StatusBit",
    "uint32": "BASE_TYPES/uint32",
}

_NAME_TOKEN = re.compile(r"[A-Za-z0-9]+")


class ProjectionModelError(ValueError):
    """Raised when a resolved B4 boundary cannot be represented safely in B5."""


@dataclass(frozen=True)
class EdsValidRange:
    minimum: int | None
    maximum: int | None
    range_type: str


@dataclass(frozen=True)
class EdsEntry:
    name: str
    type_ref: str
    valid_range: EdsValidRange | None = None


@dataclass(frozen=True)
class EdsValueConstraint:
    entry: str
    value: int


@dataclass(frozen=True)
class EdsContainerType:
    name: str
    base_type: str | None = None
    entries: tuple[EdsEntry, ...] = ()
    constraints: tuple[EdsValueConstraint, ...] = ()


@dataclass(frozen=True)
class EdsInterface:
    name: str
    interface_type: str
    generic_type_name: str
    generic_type_ref: str
    topic_id: int
    topic_variable: str


@dataclass(frozen=True)
class EdsVariable:
    name: str
    type_ref: str
    read_only: bool
    initial_value: int


@dataclass(frozen=True)
class EdsParameterMap:
    interface: str
    parameter: str
    variable_ref: str


@dataclass(frozen=True)
class EdsProjectionModel:
    package_name: str
    component_name: str
    datatypes: tuple[EdsContainerType, ...]
    interfaces: tuple[EdsInterface, ...]
    variables: tuple[EdsVariable, ...]
    parameter_maps: tuple[EdsParameterMap, ...]


def eds_name_v1(value: str) -> str:
    """Apply the frozen orbitfabric-eds-name-v1 generated-name policy."""

    tokens = _NAME_TOKEN.findall(value)
    if not tokens:
        raise ProjectionModelError(f"cannot derive EDS name from {value!r}")

    name = "".join(token[0].upper() + token[1:] for token in tokens)
    if name[0].isdigit():
        name = "N" + name
    return name


def _type_ref(semantic_type: str) -> str:
    try:
        return TYPE_REFS[semantic_type]
    except KeyError as exc:
        raise ProjectionModelError(
            f"unsupported Core semantic type for P0: {semantic_type}"
        ) from exc


def _integer_bound(value: object, label: str, argument: ResolvedCommandArgument) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int):
        raise ProjectionModelError(
            f"{argument.name}: {label} must be an integer for {argument.semantic_type}"
        )
    if not 0 <= value <= UINT32_MAX:
        raise ProjectionModelError(
            f"{argument.name}: {label} is outside uint32 range: {value}"
        )
    return value


def _argument_range(argument: ResolvedCommandArgument) -> EdsValidRange | None:
    if argument.enum:
        raise ProjectionModelError(
            f"{argument.name}: enum realization is not supported in P0"
        )
    if argument.default is not None:
        raise ProjectionModelError(
            f"{argument.name}: default realization is not supported in P0"
        )

    if argument.semantic_type == "bool":
        if argument.minimum is not None or argument.maximum is not None:
            raise ProjectionModelError(
                f"{argument.name}: bool range realization is not supported in P0"
            )
        return None

    if argument.semantic_type != "uint32":
        _type_ref(argument.semantic_type)
        return None

    minimum = _integer_bound(argument.minimum, "minimum", argument)
    maximum = _integer_bound(argument.maximum, "maximum", argument)
    if minimum is not None and maximum is not None and minimum > maximum:
        raise ProjectionModelError(
            f"{argument.name}: minimum {minimum} exceeds maximum {maximum}"
        )

    if minimum is None and maximum is None:
        return None
    if minimum is not None and maximum is not None:
        range_type = "inclusiveMinInclusiveMax"
    elif minimum is not None:
        range_type = "atLeast"
    else:
        range_type = "atMost"

    return EdsValidRange(
        minimum=minimum,
        maximum=maximum,
        range_type=range_type,
    )


def _register_name(name: str, used: set[str], namespace: str) -> None:
    if name in used:
        raise ProjectionModelError(f"{namespace} name collision: {name}")
    used.add(name)


def _argument_entries(
    command_id: str,
    arguments: tuple[ResolvedCommandArgument, ...],
) -> tuple[EdsEntry, ...]:
    used: set[str] = set()
    entries: list[EdsEntry] = []
    for argument in arguments:
        name = eds_name_v1(argument.name)
        _register_name(name, used, f"command entry for {command_id}")
        entries.append(
            EdsEntry(
                name=name,
                type_ref=_type_ref(argument.semantic_type),
                valid_range=_argument_range(argument),
            )
        )
    return tuple(entries)


def build_projection_model(resolved: ResolvedProfile) -> EdsProjectionModel:
    """Build the deterministic B5 model from the accepted B4 resolved boundary."""

    if len(resolved.packets) != 1:
        raise ProjectionModelError(
            "P0 requires exactly one projected telemetry packet; "
            f"got {len(resolved.packets)}"
        )

    if resolved.command_interface.name == resolved.telemetry_interface.name:
        raise ProjectionModelError(
            f"interface name collision: {resolved.command_interface.name}"
        )

    command_topic_variable = eds_name_v1(resolved.command_interface.name) + "TopicId"
    telemetry_topic_variable = eds_name_v1(resolved.telemetry_interface.name) + "TopicId"
    if command_topic_variable == telemetry_topic_variable:
        raise ProjectionModelError(
            f"TopicId variable name collision: {command_topic_variable}"
        )

    datatype_names = {COMMAND_BASE_NAME}
    datatypes: list[EdsContainerType] = [
        EdsContainerType(
            name=COMMAND_BASE_NAME,
            base_type=COMMAND_HEADER_TYPE,
        )
    ]

    for command in sorted(resolved.commands, key=lambda item: item.binding_id):
        if not 0 <= command.function_code <= FUNCTION_CODE_MAX:
            raise ProjectionModelError(
                f"{command.source_id}: Function Code {command.function_code} is outside 0..127"
            )

        stem = eds_name_v1(command.source_id)
        variant_name = stem + "Cmd"
        _register_name(variant_name, datatype_names, "datatype")

        variant_entries: tuple[EdsEntry, ...] = ()
        if command.arguments:
            payload_name = stem + "_Payload"
            _register_name(payload_name, datatype_names, "datatype")
            datatypes.append(
                EdsContainerType(
                    name=payload_name,
                    entries=_argument_entries(command.source_id, command.arguments),
                )
            )
            variant_entries = (EdsEntry(name="Payload", type_ref=payload_name),)

        datatypes.append(
            EdsContainerType(
                name=variant_name,
                base_type=COMMAND_BASE_NAME,
                entries=variant_entries,
                constraints=(
                    EdsValueConstraint(
                        entry=FUNCTION_CODE_ENTRY,
                        value=command.function_code,
                    ),
                ),
            )
        )

    packet = resolved.packets[0]
    packet_stem = eds_name_v1(packet.source_id)
    telemetry_payload_name = packet_stem + "Tlm_Payload"
    telemetry_message_name = packet_stem + "Tlm"
    _register_name(telemetry_payload_name, datatype_names, "datatype")
    _register_name(telemetry_message_name, datatype_names, "datatype")

    field_names: set[str] = set()
    telemetry_entries: list[EdsEntry] = []
    for field in packet.fields:
        name = eds_name_v1(field.source_id)
        _register_name(name, field_names, f"telemetry entry for {packet.source_id}")
        telemetry_entries.append(
            EdsEntry(
                name=name,
                type_ref=_type_ref(field.semantic_type),
            )
        )

    datatypes.extend(
        [
            EdsContainerType(
                name=telemetry_payload_name,
                entries=tuple(telemetry_entries),
            ),
            EdsContainerType(
                name=telemetry_message_name,
                base_type=TELEMETRY_HEADER_TYPE,
                entries=(EdsEntry(name="Payload", type_ref=telemetry_payload_name),),
            ),
        ]
    )

    command_interface = EdsInterface(
        name=resolved.command_interface.name,
        interface_type=COMMAND_INTERFACE_TYPE,
        generic_type_name=COMMAND_GENERIC_TYPE,
        generic_type_ref=COMMAND_BASE_NAME,
        topic_id=resolved.command_interface.topic_id,
        topic_variable=command_topic_variable,
    )
    telemetry_interface = EdsInterface(
        name=resolved.telemetry_interface.name,
        interface_type=TELEMETRY_INTERFACE_TYPE,
        generic_type_name=TELEMETRY_GENERIC_TYPE,
        generic_type_ref=telemetry_message_name,
        topic_id=resolved.telemetry_interface.topic_id,
        topic_variable=telemetry_topic_variable,
    )

    variables = (
        EdsVariable(
            name=command_topic_variable,
            type_ref=TOPIC_ID_TYPE,
            read_only=True,
            initial_value=resolved.command_interface.topic_id,
        ),
        EdsVariable(
            name=telemetry_topic_variable,
            type_ref=TOPIC_ID_TYPE,
            read_only=True,
            initial_value=resolved.telemetry_interface.topic_id,
        ),
    )
    parameter_maps = (
        EdsParameterMap(
            interface=resolved.command_interface.name,
            parameter=TOPIC_ID_PARAMETER,
            variable_ref=command_topic_variable,
        ),
        EdsParameterMap(
            interface=resolved.telemetry_interface.name,
            parameter=TOPIC_ID_PARAMETER,
            variable_ref=telemetry_topic_variable,
        ),
    )

    return EdsProjectionModel(
        package_name=resolved.package_name,
        component_name=resolved.component_name,
        datatypes=tuple(datatypes),
        interfaces=(command_interface, telemetry_interface),
        variables=variables,
        parameter_maps=parameter_maps,
    )
