# OrbitFabric EDS-cFS Adapter

OrbitFabric adapter bridging mission contracts through a CCSDS EDS realization into the NASA cFS / EdsLib integration lane.

## Status

```text
maturity         experimental / pre-release
P0               complete: deterministic OF -> EDS projection + traceability + native EdsLib validation
P1               complete: pinned native_eds build/install with fixed cFS consumer
P2               complete: generated runtime command/telemetry proof + constraint characterization
P3               complete: negative/conformance runtime behavior characterized on frozen lane
target allocation complete: Profile binds mission-owned symbolic CFE_MISSION TopicId allocations
C1 readiness      installed lifecycle proof present; full final-head acceptance required before promotion
public release    none yet
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

## Target allocation ownership

The public pre-v0.1 Profile does not own absolute cFS TopicId numbers.

Instead it binds OrbitFabric-facing interfaces to mission-owned symbolic allocation identities, for example:

```text
CFE_MISSION/OF_DEMO_CMD_TOPICID
CFE_MISSION/OF_DEMO_STATUS_TLM_TOPICID
```

The selected cFS mission owns the concrete TopicId allocation and MissionLib/cFE mission realization owns the target-specific TopicId-to-MsgId mapping.

The pinned SampleMission proof still resolves the accepted reference values:

```text
OF_DEMO_CMD_TOPICID        -> 160
OF_DEMO_STATUS_TLM_TOPICID -> 416
```

Those numbers are reference-mission evidence, not generic adapter policy. Native selected-mission processing remains the final target validity authority, and missing required mission symbols fail the native acceptance proof.

## Proven scope

The current retained proof slice covers:

```text
commands
telemetry
packet membership
command_sequence / expected_outputs traceability
native build/install dependency
runtime command/telemetry closed loop
runtime conformance characterization
mission-owned symbolic target allocation binding
```

P0 proves deterministic EDS XML, machine-readable traceability, Core-conformant Integration Results, deterministic failure semantics and native EdsLib processing against exact pinned upstream refs.

P1 proves that a fixed product-owned cFS application can consume interfaces generated from the retained OF_DEMO EDS and be compiled, linked, installed and staged through the pinned `native_eds` mission build.

P2 proves the retained EDS-backed runtime lane:

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

P2 also characterizes projected `ValidRange` metadata versus runtime behavior: the pinned lane delivers both in-range and out-of-range `PeriodMs` values to the typed handler, so this adapter does not claim automatic runtime enforcement of every projected range constraint.

P3 pressure-tests the same frozen runtime lane with a structurally valid OF_DEMO command carrying undefined Function Code 127. The observed lane dispatches that command to the valid generated `payload.enable` typed handler. A dedicated evidence-only EdsLib intervention preserves known derived commands and a genuinely non-derived NASA SAMPLE_APP command while making the unmatched-derived case fail closed.

P3 therefore closes as a characterization, not as a claim of automatic unknown-command rejection. No adapter-local Function Code guard, Core change or Projection Profile workaround is introduced.

C1 adds an installed-product lifecycle proof through OrbitFabric Adapter Manager. The proof installs the built wheel into a managed environment, removes the checkout package source and acquisition material, verifies the installed state, executes `eds_cfs_projection` through the installed adapter, and requires the resulting B6/B7/B8 bytes to match the retained accepted golden artifacts exactly.

See [coverage/integration-coverage.md](coverage/integration-coverage.md) for the exact claim boundaries.

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

See [docs/development.md](docs/development.md) for local checks and native-proof notes, [docs/architecture-and-ownership.md](docs/architecture-and-ownership.md) for ownership boundaries, [docs/repository-conformance.md](docs/repository-conformance.md) for readiness checkpoints, and [coverage/integration-coverage.md](coverage/integration-coverage.md) for the evidence-backed coverage disposition.
