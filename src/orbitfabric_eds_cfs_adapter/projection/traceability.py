from __future__ import annotations

import hashlib
import json
from importlib.resources import files
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from orbitfabric_eds_cfs_adapter.projection.model import (
    COMMAND_INTERFACE_TYPE,
    FUNCTION_CODE_ENTRY,
    TELEMETRY_INTERFACE_TYPE,
    EdsContainerType,
    EdsEntry,
    EdsInterface,
    EdsProjectionModel,
    EdsVariable,
    eds_name_v1,
)
from orbitfabric_eds_cfs_adapter.projection.resolution import ResolvedProfile

TRACEABILITY_KIND = "orbitfabric.eds_cfs.traceability"
TRACEABILITY_VERSION = "0.1-candidate"
INTEGRATION_ID = "orbitfabric-eds-cfs"
INTEGRATION_SCHEMA_VERSION = "0.1-candidate"
TARGET_NAMESPACE = "cfs-eds"
EDS_ARTIFACT_ID = "eds.package"
EDS_ARTIFACT_KIND = "ccsds.sois.eds.xml"
EDS_MEDIA_TYPE = "application/xml"


class TraceabilityError(ValueError):
    """Raised when accepted staged outputs cannot form complete B7 traceability."""


def _schema() -> dict[str, Any]:
    path = files("orbitfabric_eds_cfs_adapter").joinpath(
        "schemas/traceability-0.1.schema.json"
    )
    return json.loads(path.read_text(encoding="utf-8"))


def validate_traceability(payload: dict[str, Any]) -> None:
    Draft202012Validator(_schema()).validate(payload)


def _single(items: list[Any], description: str) -> Any:
    if len(items) != 1:
        raise TraceabilityError(f"{description} must resolve exactly once; got {len(items)}")
    return items[0]


def _datatype(model: EdsProjectionModel, name: str) -> EdsContainerType:
    return _single(
        [item for item in model.datatypes if item.name == name],
        f"B5 datatype {name}",
    )


def _entry(datatype: EdsContainerType, name: str) -> EdsEntry:
    return _single(
        [item for item in datatype.entries if item.name == name],
        f"B5 entry {datatype.name}/{name}",
    )


def _interface(model: EdsProjectionModel, name: str) -> EdsInterface:
    return _single(
        [item for item in model.interfaces if item.name == name],
        f"B5 interface {name}",
    )


def _variable(model: EdsProjectionModel, name: str) -> EdsVariable:
    return _single(
        [item for item in model.variables if item.name == name],
        f"B5 variable {name}",
    )


def _target(kind: str, target_id: str) -> dict[str, str]:
    return {
        "namespace": TARGET_NAMESPACE,
        "kind": kind,
        "id": target_id,
    }


def _package_target(model: EdsProjectionModel) -> dict[str, str]:
    return _target("package", model.package_name)


def _component_target(model: EdsProjectionModel) -> dict[str, str]:
    return _target("component", f"{model.package_name}/{model.component_name}")


def _datatype_target(model: EdsProjectionModel, name: str) -> dict[str, str]:
    _datatype(model, name)
    return _target("container_type", f"{model.package_name}/{name}")


def _entry_target(
    model: EdsProjectionModel,
    datatype_name: str,
    entry_name: str,
) -> dict[str, str]:
    datatype = _datatype(model, datatype_name)
    _entry(datatype, entry_name)
    return _target("entry", f"{model.package_name}/{datatype_name}/{entry_name}")


def _interface_target(model: EdsProjectionModel, name: str) -> dict[str, str]:
    _interface(model, name)
    return _target(
        "interface",
        f"{model.package_name}/{model.component_name}/{name}",
    )


def _variable_target(model: EdsProjectionModel, name: str) -> dict[str, str]:
    _variable(model, name)
    return _target(
        "variable",
        f"{model.package_name}/{model.component_name}/{name}",
    )


def _source(domain: str, source_id: str) -> dict[str, str]:
    return {"domain": domain, "id": source_id}


def _mapping(
    mapping_id: str,
    source: dict[str, str],
    binding_id: str,
    targets: list[dict[str, str]],
) -> dict[str, Any]:
    return {
        "id": mapping_id,
        "sources": [source],
        "profile_bindings": [binding_id],
        "targets": sorted(
            targets,
            key=lambda item: (item["namespace"], item["kind"], item["id"]),
        ),
    }


def _resolution(
    resolution_id: str,
    mapping_id: str,
    binding_id: str,
    source: dict[str, str],
    property_name: str,
    value: Any,
    origin: str,
) -> dict[str, Any]:
    return {
        "id": resolution_id,
        "mapping": mapping_id,
        "binding": binding_id,
        "sources": [source],
        "property": property_name,
        "value": value,
        "origin": origin,
    }


def _verify_interface(
    resolved_name: str,
    resolved_topic_id: int,
    expected_type: str,
    model: EdsProjectionModel,
) -> tuple[EdsInterface, EdsVariable]:
    interface = _interface(model, resolved_name)
    if interface.interface_type != expected_type:
        raise TraceabilityError(
            f"B5 interface type mismatch for {resolved_name}: "
            f"{interface.interface_type!r} != {expected_type!r}"
        )
    if interface.topic_id != resolved_topic_id:
        raise TraceabilityError(
            f"B4/B5 Topic ID mismatch for {resolved_name}: "
            f"{resolved_topic_id} != {interface.topic_id}"
        )
    variable = _variable(model, interface.topic_variable)
    if variable.initial_value != resolved_topic_id:
        raise TraceabilityError(
            f"B5 TopicId variable mismatch for {resolved_name}: "
            f"{variable.initial_value} != {resolved_topic_id}"
        )
    return interface, variable


def _verify_function_code(
    datatype: EdsContainerType,
    expected: int,
    source_id: str,
) -> None:
    matches = [
        item
        for item in datatype.constraints
        if item.entry == FUNCTION_CODE_ENTRY
    ]
    constraint = _single(matches, f"B5 Function Code constraint for {source_id}")
    if constraint.value != expected:
        raise TraceabilityError(
            f"B4/B5 Function Code mismatch for {source_id}: "
            f"{expected} != {constraint.value}"
        )


def _valid_range_value(entry: EdsEntry) -> dict[str, Any] | None:
    if entry.valid_range is None:
        return None
    return {
        "minimum": entry.valid_range.minimum,
        "maximum": entry.valid_range.maximum,
        "range_type": entry.valid_range.range_type,
    }


def _check_unique(records: list[dict[str, Any]], family: str) -> None:
    ids = [record["id"] for record in records]
    duplicates = sorted({record_id for record_id in ids if ids.count(record_id) > 1})
    if duplicates:
        raise TraceabilityError(
            f"duplicate {family} id(s): " + ", ".join(duplicates)
        )


def build_traceability(
    resolved: ResolvedProfile,
    model: EdsProjectionModel,
    eds_xml: bytes,
) -> dict[str, Any]:
    """Build deterministic B7 traceability from accepted B4, B5 and B6 outputs."""

    if not isinstance(eds_xml, bytes) or not eds_xml:
        raise TraceabilityError("B6 EDS XML bytes must be non-empty bytes")

    if resolved.package_name != model.package_name:
        raise TraceabilityError(
            f"B4/B5 package mismatch: {resolved.package_name} != {model.package_name}"
        )
    if resolved.component_name != model.component_name:
        raise TraceabilityError(
            f"B4/B5 component mismatch: {resolved.component_name} != {model.component_name}"
        )
    if len(resolved.packets) != 1:
        raise TraceabilityError(
            f"P0 B7 requires exactly one projected packet; got {len(resolved.packets)}"
        )

    command_interface, command_topic_variable = _verify_interface(
        resolved.command_interface.name,
        resolved.command_interface.topic_id,
        COMMAND_INTERFACE_TYPE,
        model,
    )
    telemetry_interface, telemetry_topic_variable = _verify_interface(
        resolved.telemetry_interface.name,
        resolved.telemetry_interface.topic_id,
        TELEMETRY_INTERFACE_TYPE,
        model,
    )

    mappings: list[dict[str, Any]] = []
    resolutions: list[dict[str, Any]] = []

    for command in sorted(resolved.commands, key=lambda item: item.binding_id):
        source = _source("commands", command.source_id)
        mapping_id = f"mapping.commands.{command.source_id}"
        stem = eds_name_v1(command.source_id)
        variant_name = stem + "Cmd"
        variant = _datatype(model, variant_name)
        _verify_function_code(variant, command.function_code, command.source_id)

        targets = [
            _package_target(model),
            _component_target(model),
            _datatype_target(model, variant_name),
            _interface_target(model, command_interface.name),
            _variable_target(model, command_topic_variable.name),
        ]

        if command.arguments:
            payload_name = stem + "_Payload"
            payload = _datatype(model, payload_name)
            targets.append(_datatype_target(model, payload_name))
            for argument in command.arguments:
                entry_name = eds_name_v1(argument.name)
                entry = _entry(payload, entry_name)
                targets.append(_entry_target(model, payload_name, entry_name))

                resolutions.append(
                    _resolution(
                        f"resolution.commands.{command.source_id}.argument."
                        f"{argument.name}.type_ref",
                        mapping_id,
                        command.binding_id,
                        source,
                        f"eds.argument.{argument.name}.type_ref",
                        entry.type_ref,
                        "core",
                    )
                )

                range_value = _valid_range_value(entry)
                if argument.minimum is not None or argument.maximum is not None:
                    if range_value is None:
                        raise TraceabilityError(
                            f"B5 valid range missing for {command.source_id}/{argument.name}"
                        )
                    resolutions.append(
                        _resolution(
                            f"resolution.commands.{command.source_id}.argument."
                            f"{argument.name}.valid_range",
                            mapping_id,
                            command.binding_id,
                            source,
                            f"eds.argument.{argument.name}.valid_range",
                            range_value,
                            "core",
                        )
                    )

        mappings.append(_mapping(mapping_id, source, command.binding_id, targets))
        resolutions.extend(
            [
                _resolution(
                    f"resolution.commands.{command.source_id}.function_code",
                    mapping_id,
                    command.binding_id,
                    source,
                    "cfs.function_code",
                    command.function_code,
                    "profile",
                ),
                _resolution(
                    f"resolution.commands.{command.source_id}.command_topic_id",
                    mapping_id,
                    command.binding_id,
                    source,
                    "cfs.command_topic_id",
                    command_interface.topic_id,
                    "profile",
                ),
            ]
        )

    packet = resolved.packets[0]
    packet_source = _source("packets", packet.source_id)
    packet_mapping_id = f"mapping.packets.{packet.source_id}"
    packet_stem = eds_name_v1(packet.source_id)
    telemetry_payload_name = packet_stem + "Tlm_Payload"
    telemetry_message_name = packet_stem + "Tlm"
    telemetry_payload = _datatype(model, telemetry_payload_name)
    _datatype(model, telemetry_message_name)

    mappings.append(
        _mapping(
            packet_mapping_id,
            packet_source,
            packet.binding_id,
            [
                _package_target(model),
                _component_target(model),
                _datatype_target(model, telemetry_payload_name),
                _datatype_target(model, telemetry_message_name),
                _interface_target(model, telemetry_interface.name),
                _variable_target(model, telemetry_topic_variable.name),
            ],
        )
    )
    resolutions.append(
        _resolution(
            f"resolution.packets.{packet.source_id}.telemetry_topic_id",
            packet_mapping_id,
            packet.binding_id,
            packet_source,
            "cfs.telemetry_topic_id",
            telemetry_interface.topic_id,
            "profile",
        )
    )

    for field in packet.fields:
        source = _source("telemetry", field.source_id)
        mapping_id = f"mapping.telemetry.{field.source_id}"
        entry_name = eds_name_v1(field.source_id)
        entry = _entry(telemetry_payload, entry_name)
        mappings.append(
            _mapping(
                mapping_id,
                source,
                packet.binding_id,
                [
                    _datatype_target(model, telemetry_payload_name),
                    _entry_target(model, telemetry_payload_name, entry_name),
                ],
            )
        )
        resolutions.append(
            _resolution(
                f"resolution.telemetry.{field.source_id}.type_ref",
                mapping_id,
                packet.binding_id,
                source,
                "eds.type_ref",
                entry.type_ref,
                "core",
            )
        )

    mappings.sort(key=lambda item: item["id"])
    resolutions.sort(key=lambda item: item["id"])
    _check_unique(mappings, "mapping")
    _check_unique(resolutions, "resolution")

    mapped_sources = {
        (source["domain"], source["id"])
        for mapping in mappings
        for source in mapping["sources"]
    }
    expected_sources = {
        *(("commands", command.source_id) for command in resolved.commands),
        ("packets", packet.source_id),
        *(("telemetry", field.source_id) for field in packet.fields),
    }
    if mapped_sources != expected_sources:
        missing = sorted(expected_sources - mapped_sources)
        extra = sorted(mapped_sources - expected_sources)
        raise TraceabilityError(
            f"B7 source coverage mismatch: missing={missing}; extra={extra}"
        )

    payload: dict[str, Any] = {
        "kind": TRACEABILITY_KIND,
        "traceability_version": TRACEABILITY_VERSION,
        "integration": {
            "id": INTEGRATION_ID,
            "schema_version": INTEGRATION_SCHEMA_VERSION,
        },
        "profile": {
            "id": resolved.profile_id,
            "version": resolved.profile_version,
        },
        "artifact": {
            "id": EDS_ARTIFACT_ID,
            "kind": EDS_ARTIFACT_KIND,
            "media_type": EDS_MEDIA_TYPE,
            "sha256": hashlib.sha256(eds_xml).hexdigest(),
            "package": model.package_name,
            "component": model.component_name,
        },
        "mappings": mappings,
        "resolutions": resolutions,
    }
    validate_traceability(payload)
    return payload


def serialize_traceability(payload: dict[str, Any]) -> bytes:
    """Serialize a B7 traceability document using the frozen byte contract."""

    validate_traceability(payload)
    return (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode("utf-8")


def write_traceability(path: Path, payload: dict[str, Any]) -> Path:
    path.write_bytes(serialize_traceability(payload))
    return path
