from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any

from orbitfabric_eds_cfs_adapter.input_set import LoadedInputSet
from orbitfabric_eds_cfs_adapter.projection.resolution import ResolvedProfile


class CoverageError(ValueError):
    """Raised when complete integration coverage cannot be established reliably."""


def _source_key(source: dict[str, Any]) -> tuple[str, str]:
    domain = source.get("domain")
    source_id = source.get("id")
    if not isinstance(domain, str) or not domain:
        raise CoverageError("coverage source domain must be a non-empty string")
    if not isinstance(source_id, str) or not source_id:
        raise CoverageError("coverage source id must be a non-empty string")
    return domain, source_id


def _projected_bindings(resolved: ResolvedProfile) -> dict[tuple[str, str], set[str]]:
    projected: dict[tuple[str, str], set[str]] = defaultdict(set)
    for command in resolved.commands:
        projected[("commands", command.source_id)].add(command.binding_id)
    for packet in resolved.packets:
        projected[("packets", packet.source_id)].add(packet.binding_id)
        for field in packet.fields:
            projected[("telemetry", field.source_id)].add(packet.binding_id)
    return dict(projected)


def _excluded_bindings(resolved: ResolvedProfile) -> dict[tuple[str, str], tuple[str, str]]:
    excluded: dict[tuple[str, str], tuple[str, str]] = {}
    for item in resolved.excluded:
        key = (item.source_domain, item.source_id)
        if key in excluded:
            raise CoverageError(f"duplicate excluded source: {key[0]}/{key[1]}")
        excluded[key] = (item.binding_id, item.reason)
    return excluded


def _mapping_index(traceability: dict[str, Any]) -> dict[tuple[str, str], list[str]]:
    records = traceability.get("mappings")
    if not isinstance(records, list):
        raise CoverageError("traceability.mappings must be an array")

    by_source: dict[tuple[str, str], list[str]] = defaultdict(list)
    seen_ids: set[str] = set()
    for mapping in records:
        if not isinstance(mapping, dict):
            raise CoverageError("traceability mapping must be an object")
        mapping_id = mapping.get("id")
        if not isinstance(mapping_id, str) or not mapping_id:
            raise CoverageError("traceability mapping id must be a non-empty string")
        if mapping_id in seen_ids:
            raise CoverageError(f"duplicate traceability mapping id: {mapping_id}")
        seen_ids.add(mapping_id)

        sources = mapping.get("sources")
        if not isinstance(sources, list) or not sources:
            raise CoverageError(f"traceability mapping {mapping_id} has no sources")
        for source in sources:
            if not isinstance(source, dict):
                raise CoverageError(
                    f"traceability mapping {mapping_id} has an invalid source"
                )
            by_source[_source_key(source)].append(mapping_id)

    return {key: sorted(value) for key, value in by_source.items()}


def _core_sources(core: LoadedInputSet) -> dict[tuple[str, str], dict[str, Any]]:
    entities = core.entity_index.get("entities")
    if not isinstance(entities, list):
        raise CoverageError("entity_index.entities must be an array")

    core_sources: dict[tuple[str, str], dict[str, Any]] = {}
    for entity in entities:
        if not isinstance(entity, dict):
            raise CoverageError("Core Entity Index record must be an object")
        key = _source_key(entity)
        if key in core_sources:
            raise CoverageError(f"duplicate Core entity: {key[0]}/{key[1]}")
        core_sources[key] = entity
    return core_sources


def _scope(
    projected: dict[tuple[str, str], set[str]],
    excluded: dict[tuple[str, str], tuple[str, str]],
) -> list[str]:
    overlap = sorted(set(projected) & set(excluded))
    if overlap:
        domain, source_id = overlap[0]
        raise CoverageError(
            f"source is both projected and excluded: {domain}/{source_id}"
        )

    scoped_domains = sorted(
        {domain for domain, _ in projected} | {domain for domain, _ in excluded}
    )
    if not scoped_domains:
        raise CoverageError("projection coverage has no declared Core domains")
    return scoped_domains


def build_coverage(
    core: LoadedInputSet,
    resolved: ResolvedProfile,
    traceability: dict[str, Any],
) -> dict[str, Any]:
    """Build complete B8 projection coverage from accepted B2, B4 and B7 outputs."""

    projected = _projected_bindings(resolved)
    excluded = _excluded_bindings(resolved)
    scoped_domains = _scope(projected, excluded)

    mapping_index = _mapping_index(traceability)
    unexpected_mapped = sorted(set(mapping_index) - set(projected))
    if unexpected_mapped:
        domain, source_id = unexpected_mapped[0]
        raise CoverageError(
            f"B7 mapping source is not a B4 projected source: {domain}/{source_id}"
        )

    core_sources = _core_sources(core)
    for key in sorted(set(projected) | set(excluded)):
        if key not in core_sources:
            raise CoverageError(
                f"resolved source missing from Core Entity Index: {key[0]}/{key[1]}"
            )

    records: list[dict[str, Any]] = []
    for key in sorted(core_sources):
        domain, source_id = key
        if domain not in scoped_domains:
            continue

        source = {"domain": domain, "id": source_id}
        if key in projected:
            mapping_ids = mapping_index.get(key, [])
            if not mapping_ids:
                raise CoverageError(
                    f"projected source has no B7 mapping: {domain}/{source_id}"
                )
            records.append(
                {
                    "source": source,
                    "state": "projected",
                    "mappings": mapping_ids,
                    "profile_bindings": sorted(projected[key]),
                    "diagnostics": [],
                    "reason": None,
                }
            )
            continue

        if key in excluded:
            binding_id, reason = excluded[key]
            records.append(
                {
                    "source": source,
                    "state": "intentionally_not_projected",
                    "mappings": [],
                    "profile_bindings": [binding_id],
                    "diagnostics": [],
                    "reason": reason,
                }
            )
            continue

        records.append(
            {
                "source": source,
                "state": "not_projected",
                "mappings": [],
                "profile_bindings": [],
                "diagnostics": [],
                "reason": (
                    "No Projection Profile binding for this source in the "
                    "declared EDS-cFS scope"
                ),
            }
        )

    if not records:
        raise CoverageError("successful projection coverage has no entity records")

    counts = Counter(record["state"] for record in records)
    summary = {state: counts[state] for state in sorted(counts) if counts[state]}
    return {
        "status": "complete",
        "scope": {"domains": scoped_domains},
        "reason": None,
        "summary": summary,
        "records": records,
    }


def build_failed_coverage(
    core: LoadedInputSet,
    resolved: ResolvedProfile,
    diagnostic_id: str,
) -> dict[str, Any]:
    """Account for a failed operation after B4 established a coherent scope."""

    projected = _projected_bindings(resolved)
    excluded = _excluded_bindings(resolved)
    scoped_domains = _scope(projected, excluded)
    core_sources = _core_sources(core)

    for key in sorted(set(projected) | set(excluded)):
        if key not in core_sources:
            raise CoverageError(
                f"resolved source missing from Core Entity Index: {key[0]}/{key[1]}"
            )

    records: list[dict[str, Any]] = []
    for key in sorted(core_sources):
        domain, source_id = key
        if domain not in scoped_domains:
            continue

        source = {"domain": domain, "id": source_id}
        if key in projected:
            records.append(
                {
                    "source": source,
                    "state": "blocked",
                    "mappings": [],
                    "profile_bindings": sorted(projected[key]),
                    "diagnostics": [diagnostic_id],
                    "reason": (
                        "Projection was blocked because the integration operation "
                        "failed"
                    ),
                }
            )
            continue

        if key in excluded:
            binding_id, reason = excluded[key]
            records.append(
                {
                    "source": source,
                    "state": "intentionally_not_projected",
                    "mappings": [],
                    "profile_bindings": [binding_id],
                    "diagnostics": [],
                    "reason": reason,
                }
            )
            continue

        records.append(
            {
                "source": source,
                "state": "not_projected",
                "mappings": [],
                "profile_bindings": [],
                "diagnostics": [],
                "reason": (
                    "No Projection Profile binding for this source in the "
                    "declared EDS-cFS scope"
                ),
            }
        )

    if not records:
        raise CoverageError("failed projection coverage has no entity records")

    counts = Counter(record["state"] for record in records)
    summary = {state: counts[state] for state in sorted(counts) if counts[state]}
    return {
        "status": "complete",
        "scope": {"domains": scoped_domains},
        "reason": None,
        "summary": summary,
        "records": records,
    }


def unavailable_coverage(reason: str) -> dict[str, Any]:
    """Return deterministic unavailable coverage before B4 completion."""

    if not reason:
        raise CoverageError("unavailable coverage requires a reason")
    return {
        "status": "unavailable",
        "scope": {"domains": []},
        "reason": reason,
        "summary": {},
        "records": [],
    }
