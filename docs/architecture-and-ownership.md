# Architecture and Ownership

## Integration topology

```text
OrbitFabric Core Integration Input Set
    -> EDS-cFS Projection Profile
    -> adapter deterministic projection
    -> CCSDS EDS artifact
    -> selected cFS mission allocation identities
    -> NASA EdsLib / MissionLib realization
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

### The EDS-cFS adapter and Projection Profile own

- the target-specific Projection Profile schema;
- explicit OrbitFabric identity to EDS realization bindings;
- binding cFS interfaces to mission-owned `CFE_MISSION` topic allocation identities;
- deterministic EDS artifact generation;
- faithful projection of supported Core command constraints into EDS;
- adapter-side validation and traceability;
- declared target compatibility and Integration Coverage;
- evidence-backed statements about what the pinned target runtime does and does not enforce automatically.

The reusable Profile does not own concrete TopicId values.

### The selected cFS mission owns

- concrete TopicId allocations for the allocation identities required by the Profile;
- mission-specific topic-space policy and registry definitions.

The retained SampleMission values `160` and `416` are reference-mission evidence, not universal cFS rules.

### MissionLib / cFE own

- mission-specific TopicId / MsgId realization;
- any custom target mapping policy selected by the mission.

The adapter does not reimplement MissionLib mapping rules.

### The remaining target realization owns

- cFS application/interface realization;
- Function Codes;
- header references and other target-only wire choices;
- executable command acceptance/rejection policy in the target application/runtime realization.

### EdsLib owns

EDS processing, generated/runtime representations and native materialization support.

For the pinned P2-B proof path, an entry-level EDS `ValidRange` is retained in the generated contract but no automatic range rejection was observed before typed application delivery. This repository therefore does not claim that EdsLib automatically enforces every projected `ValidRange` at runtime.

### cFS owns

Executable flight-software runtime behavior and native acceptance.

The adapter does not inject a duplicate hard-coded flight policy merely because the selected runtime path does not automatically enforce a projected semantic constraint.

## Target allocation boundary

```text
OrbitFabric semantic interface
    -> Profile topic_ref
    -> CFE_MISSION allocation identity
    -> selected mission concrete TopicId
    -> MissionLib / cFE realization
```

A missing required allocation must fail the selected native target proof. No fallback TopicId is invented by the adapter.

See [target-allocation.md](target-allocation.md) for the concrete pre-v0.1 contract.

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
OrbitFabric entity ID  != cFS topic allocation identity
cFS topic allocation identity != universal numeric TopicId
```

No target identifier or allocation policy is inferred into Core.

## Architecture authority

Cross-repository architecture decisions and falsification evidence live in OrbitFabric Architecture Lab. This repository must not become an alternate architecture authority.
