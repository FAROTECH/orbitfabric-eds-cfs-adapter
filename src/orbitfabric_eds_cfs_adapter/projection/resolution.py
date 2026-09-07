from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from orbitfabric_eds_cfs_adapter.input_set import InputSetError, LoadedInputSet


class ResolutionError(ValueError):
    """Raised when a valid Profile cannot be resolved against the Core input set."""


@dataclass(frozen=True)
class ResolvedInterface:
    name: str
    topic_ref: str


@dataclass(frozen=True)
class ResolvedCommandArgument:
    name: str
    semantic_type: str
    minimum: float | int | None
    maximum: float | int | None
    enum: tuple[str, ...] | None
    default: Any | None


@dataclass(frozen=True)
class ResolvedTelemetryField:
    source_id: str
    semantic_type: str


@dataclass(frozen=True)
class ResolvedCommandBinding:
    binding_id: str
    source_id: str
    function_code: int
    arguments: tuple[ResolvedCommandArgument, ...]


@dataclass(frozen=True)
class ResolvedPacketBinding:
    binding_id: str
    source_id: str
    fields: tuple[ResolvedTelemetryField, ...]


@dataclass(frozen=True)
class ResolvedExcludedBinding:
    binding_id: str
    source_domain: str
    source_id: str
    reason: str


@dataclass(frozen=True)
class ResolvedProfile:
    profile_id: str
    profile_version: str
    package_name: str
    component_name: str
    command_interface: ResolvedInterface
    telemetry_interface: ResolvedInterface
    commands: tuple[ResolvedCommandBinding, ...]
    packets: tuple[ResolvedPacketBinding, ...]
    excluded: tuple[ResolvedExcludedBinding, ...]
    lint_warnings: tuple[dict[str, Any], ...]


def _model_record(core: LoadedInputSet, domain: str, entity_id: str) -> dict[str, Any]:
    records = core.model.get(domain)
    if not isinstance(records, list):
        raise ResolutionError(f"mission_snapshot.model.{domain} is not an array")

    matches = [
        record
        for record in records
        if isinstance(record, dict) and record.get("id") == entity_id
    ]
    if len(matches) != 1:
        raise ResolutionError(
            f"Core semantic record must resolve exactly once: {domain}/{entity_id}"
        )
    return matches[0]


def _resolve_core_entity(core: LoadedInputSet, domain: str, entity_id: str) -> None:
    try:
        core.resolve_entity(domain, entity_id)
    except InputSetError as exc:
        raise ResolutionError(str(exc)) from exc


def _packet_membership(core: LoadedInputSet, packet_id: str) -> set[str]:
    try:
        return set(core.packet_telemetry_ids(packet_id))
    except InputSetError as exc:
        raise ResolutionError(str(exc)) from exc


def _command_arguments(
    core: LoadedInputSet,
    command_id: str,
) -> tuple[ResolvedCommandArgument, ...]:
    command = _model_record(core, "commands", command_id)
    arguments = command.get("arguments")
    if not isinstance(arguments, list):
        raise ResolutionError(f"Core command arguments are not an array: {command_id}")

    resolved: list[ResolvedCommandArgument] = []
    for argument in arguments:
        if not isinstance(argument, dict):
            raise ResolutionError(f"Core command argument is not an object: {command_id}")
        name = argument.get("name")
        semantic_type = argument.get("type")
        if not isinstance(name, str) or not name:
            raise ResolutionError(f"Core command argument has invalid name: {command_id}")
        if not isinstance(semantic_type, str) or not semantic_type:
            raise ResolutionError(f"Core command argument has invalid type: {command_id}/{name}")
        enum = argument.get("enum")
        if enum is not None:
            if not isinstance(enum, list) or not all(isinstance(item, str) for item in enum):
                raise ResolutionError(
                    f"Core command argument has invalid enum: {command_id}/{name}"
                )
            resolved_enum: tuple[str, ...] | None = tuple(enum)
        else:
            resolved_enum = None
        resolved.append(
            ResolvedCommandArgument(
                name=name,
                semantic_type=semantic_type,
                minimum=argument.get("min"),
                maximum=argument.get("max"),
                enum=resolved_enum,
                default=argument.get("default"),
            )
        )
    return tuple(resolved)


def _telemetry_type(core: LoadedInputSet, telemetry_id: str) -> str:
    telemetry = _model_record(core, "telemetry", telemetry_id)
    semantic_type = telemetry.get("type")
    if not isinstance(semantic_type, str) or not semantic_type:
        raise ResolutionError(f"Core telemetry has invalid type: {telemetry_id}")
    return semantic_type


def resolve_profile(profile: dict[str, Any], core: LoadedInputSet) -> ResolvedProfile:
    """Resolve a schema-valid B3 Profile against a schema-valid B2 Core input set.

    This is B4 only. It performs cross-document identity/allocation checks and
    returns a deterministic resolved boundary. It does not generate EDS XML.
    """

    settings = profile["settings"]
    eds = settings["eds"]
    interfaces = settings["interfaces"]
    command_interface = ResolvedInterface(
        name=interfaces["command"]["name"],
        topic_ref=interfaces["command"]["topic_ref"],
    )
    telemetry_interface = ResolvedInterface(
        name=interfaces["telemetry"]["name"],
        topic_ref=interfaces["telemetry"]["topic_ref"],
    )

    if command_interface.topic_ref == telemetry_interface.topic_ref:
        raise ResolutionError(
            "Topic reference collision: "
            f"{command_interface.topic_ref} is used by both interfaces"
        )

    binding_ids: set[str] = set()
    function_codes: dict[int, str] = {}
    commands: list[ResolvedCommandBinding] = []
    packets: list[ResolvedPacketBinding] = []
    excluded: list[ResolvedExcludedBinding] = []

    for binding in profile["bindings"]:
        binding_id = binding["id"]
        if binding_id in binding_ids:
            raise ResolutionError(f"duplicate binding id: {binding_id}")
        binding_ids.add(binding_id)

        source = binding["sources"][0]
        source_domain = source["domain"]
        source_id = source["id"]
        _resolve_core_entity(core, source_domain, source_id)

        if binding["intent"] == "do_not_project":
            excluded.append(
                ResolvedExcludedBinding(
                    binding_id=binding_id,
                    source_domain=source_domain,
                    source_id=source_id,
                    reason=binding["reason"],
                )
            )
            continue

        if source_domain == "commands":
            function_code = binding["config"]["function_code"]
            previous = function_codes.get(function_code)
            if previous is not None:
                raise ResolutionError(
                    f"Function Code collision: {function_code} used by {previous} and {binding_id}"
                )
            function_codes[function_code] = binding_id
            commands.append(
                ResolvedCommandBinding(
                    binding_id=binding_id,
                    source_id=source_id,
                    function_code=function_code,
                    arguments=_command_arguments(core, source_id),
                )
            )
            continue

        if source_domain == "packets":
            membership = _packet_membership(core, source_id)
            fields: list[ResolvedTelemetryField] = []
            field_ids: list[str] = []
            for field in binding["config"]["fields"]:
                telemetry_id = field["source"]["id"]
                _resolve_core_entity(core, "telemetry", telemetry_id)
                field_ids.append(telemetry_id)
                fields.append(
                    ResolvedTelemetryField(
                        source_id=telemetry_id,
                        semantic_type=_telemetry_type(core, telemetry_id),
                    )
                )

            duplicates = sorted(
                telemetry_id
                for telemetry_id in set(field_ids)
                if field_ids.count(telemetry_id) > 1
            )
            if duplicates:
                raise ResolutionError(
                    "duplicate packet field source(s): " + ", ".join(duplicates)
                )

            field_set = set(field_ids)
            if field_set != membership:
                missing = sorted(membership - field_set)
                extra = sorted(field_set - membership)
                details = []
                if missing:
                    details.append("missing=" + ",".join(missing))
                if extra:
                    details.append("extra=" + ",".join(extra))
                raise ResolutionError(
                    f"packet field set does not match Core membership for {source_id}: "
                    + "; ".join(details)
                )

            packets.append(
                ResolvedPacketBinding(
                    binding_id=binding_id,
                    source_id=source_id,
                    fields=tuple(fields),
                )
            )
            continue

        raise ResolutionError(f"unsupported projected source domain: {source_domain}")

    return ResolvedProfile(
        profile_id=profile["profile"]["id"],
        profile_version=profile["profile"]["version"],
        package_name=eds["package_name"],
        component_name=eds["component_name"],
        command_interface=command_interface,
        telemetry_interface=telemetry_interface,
        commands=tuple(sorted(commands, key=lambda item: item.binding_id)),
        packets=tuple(sorted(packets, key=lambda item: item.binding_id)),
        excluded=tuple(sorted(excluded, key=lambda item: item.binding_id)),
        lint_warnings=core.lint_warnings,
    )
