# Architecture and Ownership

## Integration topology

```text
OrbitFabric Core Integration Input Set
    -> EDS-cFS Projection Profile
    -> adapter deterministic projection
    -> CCSDS EDS artifact
    -> NASA EdsLib
    -> NASA cFS
```

The product is an OrbitFabric adapter. Its integration role is a standards-backed bridge.

## Ownership

### OrbitFabric Core owns

- mission semantic identity and intent;
- command signatures, including argument names, types and semantic min/max constraints;
- the Integration Input Set contract;
- the generic Projection Profile envelope;
- Integration Package Manifest and Integration Result semantics;
- Adapter Manager lifecycle semantics.

### The EDS-cFS adapter owns

- its target-specific Projection Profile schema;
- explicit OrbitFabric identity to EDS realization bindings;
- deterministic EDS artifact generation;
- faithful projection of supported Core command constraints into EDS;
- adapter-side validation and traceability;
- declared target compatibility and Integration Coverage;
- evidence-backed statements about what the pinned target runtime does and does not enforce automatically.

### The target realization owns

- EDS package/component naming;
- cFS application/interface bindings;
- Topic / Message ID realization;
- Function Codes;
- header references and other target-only wire choices;
- executable command acceptance/rejection policy in the target application/runtime realization.

### EdsLib owns

EDS processing, generated/runtime representations and native materialization support.

For the pinned P2-B proof path, an entry-level EDS `ValidRange` is retained in the generated contract but no automatic range rejection was observed before typed application delivery. This repository therefore does not claim that EdsLib automatically enforces every projected `ValidRange` at runtime.

### cFS owns

Executable flight-software runtime behavior and native acceptance.

The adapter does not inject a duplicate hard-coded flight policy merely because the selected runtime path does not automatically enforce a projected semantic constraint.

## Constraint boundary

For the current `payload.set_period` proof:

```text
OrbitFabric Core
    period_ms semantic range = 100..60000

EDS-cFS adapter
    projects that range as EDS ValidRange

pinned EdsLib/cFS path
    delivers 99 and 60001 to the generated typed handler

target application
    remains the executable command-policy boundary unless a target-native generic validator is separately selected and proven
```

Therefore:

```text
constraint projection
    !=
automatic runtime enforcement
```

This distinction is part of the Target Applicable Surface and must remain explicit in coverage claims.

## Identity boundary

```text
OrbitFabric command ID != cFS Function Code
OrbitFabric entity ID  != cFS Topic / Message ID
```

No target identifier is inferred into Core.

## Architecture authority

Cross-repository architecture decisions and falsification evidence live in OrbitFabric Architecture Lab. This repository must not become an alternate architecture authority.
