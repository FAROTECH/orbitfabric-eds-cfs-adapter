# OrbitFabric EDS-cFS Adapter

OrbitFabric adapter bridging mission contracts through a CCSDS EDS realization into the NASA cFS / EdsLib integration lane.

## Status

```text
maturity         experimental / pre-release
P0               complete: deterministic OF -> EDS projection + traceability + native EdsLib validation
P1               complete: pinned native_eds build/install with fixed cFS consumer
P2               active: runtime command/telemetry proof
public release   none yet
```

This repository is intentionally clean-bootstrapped rather than created from `orbitfabric-adapter-template`. That choice does not define a different adapter contract: the implementation remains conformant with OrbitFabric Core contracts and with the responsibility/readiness model defined by the OrbitFabric Adapter Developer Template.

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

## Proven scope

The current retained proof slice covers:

```text
commands
telemetry
packet membership
command_sequence / expected_outputs traceability
```

P0 proves deterministic EDS XML, machine-readable traceability, Core-conformant Integration Results, deterministic failure semantics and native EdsLib processing against exact pinned upstream refs.

P1 proves that a fixed product-owned cFS application can consume interfaces generated from the retained OF_DEMO EDS and be compiled, linked, installed and staged through the pinned `native_eds` mission build.

P2 is the active gate. Its first runtime slice is intentionally narrow:

```text
payload.enable
    -> EDS-enabled cmd_send
    -> cFS / ci_lab
    -> generated OF_DEMO dispatcher
    -> fixed application handler
    -> PayloadStatusTlm
    -> to_lab
    -> EDS-enabled tlm_recv
    -> PayloadEnabled=true
```

No generic/full CCSDS EDS interoperability claim, generic OrbitFabric ACK realization, or complete cFS integration coverage is made yet.

## Architecture authority

Cross-repository architecture, hypotheses, evidence, falsification and sequencing are maintained in the private OrbitFabric Architecture Lab.

This repository owns only the adapter implementation, local product tests, proof harnesses and product evidence. If implementation evidence suggests a Core contract change, ownership change, different integration topology or broader interoperability claim, the finding returns to Architecture Lab before product scope is changed.

## Frozen upstream baseline

```text
NASA cFS
    088b2fa828db9ff7e00733f1908e0eeb59f66ce3

NASA EdsLib
    2acc963b34f77692c6396555dcfb10ef43eb1046

NASA cFE
    c5fb2b4d540bd55eb6c3707da7dd13eee679d4dd
```

Additional cFS sample applications and command-line tools used by native proofs are also pinned by exact commit in the corresponding CI harnesses.

NASA sources are not vendored into this repository.

## Development

See [docs/development.md](docs/development.md) for local checks and native-proof notes, [docs/architecture-and-ownership.md](docs/architecture-and-ownership.md) for ownership boundaries, and [coverage/integration-coverage.md](coverage/integration-coverage.md) for the evidence-backed coverage disposition.
