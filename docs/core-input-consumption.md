# Core Input Consumption

P0 consumes the stable Core Integration Input Set boundary frozen in OrbitFabric Architecture Lab Decision 003.

## Declared surfaces

```text
entity_index              orbitfabric.entity_index / 0.1
lint_report               orbitfabric-lint / v1
mission_snapshot          orbitfabric.mission_snapshot / 0.1-candidate
relationship_manifest     orbitfabric.relationship_manifest / 0.1-candidate
```

The only relationship family whose semantics this adapter declares understanding in P0 is:

```text
packet_includes_telemetry
```

## Ownership rules

`mission_snapshot` supplies mission semantic values such as command argument types/constraints and telemetry types.

`entity_index` supplies canonical Core identity/domain resolution for Profile source references.

`relationship_manifest` supplies packet-to-telemetry membership. The adapter does not reconstruct that relationship from `mission_snapshot.packets[].telemetry` or naming conventions.

`lint_report` gates projection. `passed` and `passed_with_warnings` are accepted; warnings remain evidence. Failed or unknown lint states are rejected.

`model_summary` may exist in a Core-produced Input Set but is not a semantic dependency of this adapter.

## Fail-closed behavior

The loader rejects missing required surfaces, incompatible kind/version declarations, digest mismatches, unsafe paths, unacceptable Core load/lint states and unresolved canonical identities.

Unknown additive relationship families are not interpreted. Target-specific cFS/EDS identifiers remain Projection Profile facts, not Core facts.
