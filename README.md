# OrbitFabric EDS-cFS Adapter

Private experimental adapter workspace for bridging OrbitFabric mission contracts through a CCSDS EDS realization into the NASA cFS / EdsLib integration lane.

## Status

```text
maturity         experimental / PoC
current gate     C0 bootstrap conformity
next gate        P0 projection proof
public release   none
```

This repository is intentionally bootstrapped clean rather than created from `orbitfabric-adapter-template`.

That bootstrap choice does **not** define a different adapter contract. The repository is required to remain conformant with OrbitFabric Core contracts and with the responsibility/readiness model defined by the OrbitFabric Adapter Developer Template.

## Integration topology

```text
OrbitFabric Mission Model
    -> Core Integration Input Set
    -> EDS-cFS Projection Profile
    -> OrbitFabric EDS-cFS Adapter
    -> CCSDS EDS
    -> NASA EdsLib
    -> NASA cFS native EDS-enabled build/runtime
```

The EDS artifact is an explicit interoperability boundary. It must not be bypassed by hidden direct cFS inference.

## Architecture authority

Cross-repository architecture, hypotheses, evidence, falsification and sequencing are owned by the private `OrbitFabric-Architecture-Lab` repository.

This repository owns only the adapter implementation, local product tests, PoC harnesses and generated artifacts.

If implementation evidence suggests a Core contract change, an ownership change, a different integration topology or a broader public interoperability claim, work stops here and the finding returns to Architecture Lab first.

## Frozen upstream PoC baseline

```text
NASA cFS v7.0.1
    088b2fa828db9ff7e00733f1908e0eeb59f66ce3

NASA EdsLib v7.0.1
    2acc963b34f77692c6396555dcfb10ef43eb1046
```

The initial work does not vendor either upstream repository.

## Scope now

C0 establishes a clean, installable, Core-conformant adapter skeleton before substantive EDS projection code is written.

P0 will then prove:

```text
Core Integration Input Set
    -> explicit Projection Profile
    -> deterministic EDS XML
    -> machine-readable traceability
```

No generic CCSDS EDS support claim is made at this stage.
