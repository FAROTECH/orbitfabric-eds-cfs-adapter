# OrbitFabric EDS-cFS Adapter

`orbitfabric-eds-cfs-adapter` bridges OrbitFabric mission contracts through a CCSDS EDS realization into the NASA cFS / EdsLib integration lane.

## Release readiness

```text
P0 projection proof          DONE / NATIVE ACCEPTED
P1 native_eds build          DONE / PROMOTED / MAIN REVALIDATED
P2 runtime proof             DONE / PROMOTED / MAIN REVALIDATED
P3 conformance proof         DONE / PROMOTED / MAIN REVALIDATED
target allocation readiness  DONE / PROMOTED / MAIN REVALIDATED
C1 installed lifecycle       DONE / PROMOTED / MAIN REVALIDATED
C2 public productization     ACTIVE
public release               none yet
```

The source tree is now rebaselined for release `0.1.0`, but the adapter remains pre-release until the verified `v0.1.0` GitHub Release is actually published.

## Choose your path

### I want to use the adapter

The normal consumer path is through OrbitFabric Adapter Manager and published release assets, not an editable source checkout.

```text
OrbitFabric Core
    -> published adapter release
    -> Adapter Manager install
    -> verify
    -> execute eds_cfs_projection
    -> CCSDS EDS + traceability + Integration Result
```

Start with [Getting Started](docs/getting-started.md).

### I want to understand the integration boundary

Read [Architecture and ownership](docs/architecture-and-ownership.md), [Target allocation](docs/target-allocation.md), and [Integration Coverage](coverage/integration-coverage.md).

### I want to develop or contribute

See [Development](docs/development.md) and [CONTRIBUTING](CONTRIBUTING.md).

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

The generated EDS is an explicit interoperability boundary. The adapter does not bypass it with hidden direct OrbitFabric-to-cFS inference.

## Canonical product identity

```text
repository / distribution  orbitfabric-eds-cfs-adapter
Python package              orbitfabric_eds_cfs_adapter
console command             orbitfabric-eds-cfs
adapter / integration id    orbitfabric-eds-cfs
operation                   eds_cfs_projection
source coordinate           github.com/FAROTECH:orbitfabric/eds-cfs
release candidate           0.1.0
```

The Source Coordinate is product-owned and is carried consistently into Release Descriptor and Project Lock evidence. A release build cannot silently substitute a different source identity.

## Target allocation ownership

The public Profile does not own universal absolute cFS TopicId numbers.

Instead it binds OrbitFabric-facing interfaces to mission-owned symbolic allocation identities, for example:

```text
CFE_MISSION/OF_DEMO_CMD_TOPICID
CFE_MISSION/OF_DEMO_STATUS_TLM_TOPICID
```

The selected cFS mission owns concrete TopicId allocation and MissionLib/cFE mission realization owns target-specific TopicId-to-MsgId mapping.

The pinned SampleMission proof resolves the retained reference values:

```text
OF_DEMO_CMD_TOPICID        -> 160
OF_DEMO_STATUS_TLM_TOPICID -> 416
```

Those numbers are reference-mission evidence, not generic adapter policy. Missing required mission symbols fail the native acceptance proof.

## Proven scope

The retained proof slice covers:

```text
commands
telemetry
packet membership
command_sequence / expected_outputs traceability
native EdsLib processing
complete native_eds build/install dependency
runtime command/telemetry closed loop
typed command argument delivery
runtime conformance characterization
mission-owned symbolic target allocation binding
installed Adapter Manager execution
```

P0 proves deterministic EDS XML, machine-readable traceability, Core-conformant Integration Results, deterministic failure semantics and native EdsLib processing against exact pinned upstream refs.

P1 proves that a fixed product-owned cFS application consumes interfaces generated from the retained OF_DEMO EDS and is compiled, linked, installed and staged through the pinned `native_eds` mission build.

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

P2 also characterizes projected `ValidRange` metadata versus runtime behavior. The pinned lane delivers both in-range and out-of-range `PeriodMs` values to the typed handler, so this adapter does not claim automatic runtime enforcement of every projected range constraint.

P3 pressure-tests the same frozen runtime lane with a structurally valid OF_DEMO command carrying undefined Function Code `127`. The observed lane dispatches that command to the valid generated `payload.enable` typed handler. P3 therefore closes as target characterization, not as a claim of automatic unknown-command rejection.

No adapter-local Function Code guard, range guard, Core semantic change or Projection Profile workaround is introduced to manufacture stronger runtime behavior than the validated target provides.

C1 proves installed execution through OrbitFabric Adapter Manager after the checkout package source, built wheel and acquisition wheelhouse are removed. The resulting B6 EDS XML, B7 traceability and B8 Integration Result must remain byte-identical to retained accepted goldens.

C2 adds release construction, Project Lock lifecycle proof, publisher-only release material and published-byte verification before the GitHub Release is made public.

## Validated target lane

```text
OrbitFabric Core v1.3.0
    a25917e81c90396df2b189834e83cf852fa4da5f

NASA cFS v7.0.1
    088b2fa828db9ff7e00733f1908e0eeb59f66ce3

NASA EdsLib v7.0.1
    2acc963b34f77692c6396555dcfb10ef43eb1046

NASA cFE
    c5fb2b4d540bd55eb6c3707da7dd13eee679d4dd
```

Additional cFS sample applications and command-line tools used by native proofs are pinned by exact commit in their CI harnesses. NASA sources are not vendored in this repository.

No broader cFS, EdsLib or generic/full CCSDS EDS interoperability claim is currently made.

## Release model

The publisher-owned `v0.1.0` assets are intended to be:

```text
orbitfabric_eds_cfs_adapter-0.1.0-py3-none-any.whl
adapter-release.json
SHA256SUMS
```

A Project Lock is consumer/project-owned state and is deliberately excluded from published adapter release assets.

The release workflow creates a draft GitHub Release, downloads those published bytes back from GitHub, verifies them against `SHA256SUMS` and the canonical Source Coordinate, and only then makes the release public.

## Architecture authority

Cross-repository architecture, hypotheses, evidence, falsification and sequencing are maintained in the private OrbitFabric Architecture Lab.

This repository owns only the adapter implementation, local product tests, proof harnesses, release machinery and product evidence. If implementation evidence suggests a Core contract change, ownership change, different integration topology or broader interoperability claim, that finding returns to Architecture Lab before product scope changes.
