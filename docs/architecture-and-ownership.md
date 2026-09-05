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
- the Integration Input Set contract;
- the generic Projection Profile envelope;
- Integration Package Manifest and Integration Result semantics;
- Adapter Manager lifecycle semantics.

### The EDS-cFS adapter owns

- its target-specific Projection Profile schema;
- explicit OrbitFabric identity to EDS realization bindings;
- deterministic EDS artifact generation;
- adapter-side validation and traceability;
- declared target compatibility and Integration Coverage.

### The target realization owns

- EDS package/component naming;
- cFS application/interface bindings;
- Topic / Message ID realization;
- Function Codes;
- header references and other target-only wire choices.

### EdsLib owns

EDS processing, generated/runtime representations and native materialization support.

### cFS owns

Executable flight-software runtime behavior and native acceptance.

## Identity boundary

```text
OrbitFabric command ID != cFS Function Code
OrbitFabric entity ID  != cFS Topic / Message ID
```

No target identifier is inferred into Core.

## Architecture authority

Cross-repository architecture decisions and falsification evidence live in OrbitFabric Architecture Lab. This repository must not become an alternate architecture authority.
