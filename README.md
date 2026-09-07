# OrbitFabric EDS-cFS Adapter

`orbitfabric-eds-cfs-adapter` projects OrbitFabric mission contracts into CCSDS Electronic Data Sheets and carries that contract into the native NASA EdsLib / cFS integration lane.

The adapter is deliberately a bridge, not a replacement for cFS mission architecture. OrbitFabric owns mission-level semantics, the Projection Profile owns explicit target binding, the selected cFS mission owns concrete topic allocation, and EdsLib / MissionLib / cFE remain authoritative for native realization and runtime behavior.

> **Release line:** `0.1.0`. Release identity is established by the immutable `v0.1.0` tag and verified GitHub Release assets. A branch checkout is not a release substitute.

## Choose your path

### I want to use the adapter

Use the published release through **OrbitFabric Adapter Manager**.

```text
OrbitFabric Core
    -> published adapter release
    -> Adapter Manager install
    -> verify
    -> execute eds_cfs_projection
    -> CCSDS EDS + traceability + Integration Result
```

A normal consumer should not need an editable source install, locally rebuilt wheel or publisher tooling.

Start with **[Getting Started](docs/getting-started.md)**.

### I want to try the integration

Start with the **[Reference Project: OrbitFabric Contract to Native cFS Runtime](examples/cfs/of_demo_app/README.md)**.

It demonstrates the complete architectural boundary exercised by this adapter:

```text
OrbitFabric mission semantics
    -> Core Integration Input Set
    -> EDS-cFS Projection Profile
    -> generated CCSDS EDS
    -> mission-owned CFE_MISSION topic allocation
    -> EdsLib generated types and dispatcher
    -> fixed cFS application
    -> native build and runtime evidence
```

The reference cFS application does not carry a parallel hand-written message contract. Its command handlers use generated OF_DEMO types and dispatch, and its command/telemetry TopicIds come from the selected mission's generated EDS design parameters.

The same retained slice is used to prove native build dependency, runtime command/telemetry flow, typed argument delivery, target allocation ownership and negative conformance behavior.

### I want to understand the integration boundary

Read:

- **[Architecture and Ownership](docs/architecture-and-ownership.md)**
- **[Target Allocation](docs/target-allocation.md)**
- **[Integration Coverage](coverage/integration-coverage.md)**

These documents separate what OrbitFabric means, what the adapter projects, what the selected cFS mission owns and what the native NASA runtime actually proves.

### I want to develop or contribute

Clone the repository and use the contributor surface.

The direct console command:

```text
orbitfabric-eds-cfs
```

is primarily a development surface. Normal consumers should execute the installed adapter through OrbitFabric Adapter Manager.

Start with **[Development](docs/development.md)** and [CONTRIBUTING.md](CONTRIBUTING.md).

## What the adapter does

The `0.1.0` product line consumes the public OrbitFabric Core Integration Input Set and supports one deliberately narrow operation:

```text
eds_cfs_projection
```

For the retained product slice it projects:

```text
OrbitFabric commands
OrbitFabric telemetry
OrbitFabric packet membership
command argument constraints represented by EDS
explicit command Function Code bindings
mission-owned cFS topic allocation identities
```

Representative output is:

```text
eds/mission.xml
traceability.json
integration_result.json
```

The generated EDS is the interoperability boundary. The adapter does not bypass it with a hidden direct OrbitFabric-to-cFS inference path.

## Integration topology

```text
OrbitFabric Mission Model
        |
        v
OrbitFabric Core
Integration Input Set
        |
        + EDS-cFS Projection Profile
        |
        v
OrbitFabric EDS-cFS Adapter
        |
        v
CCSDS EDS
        |
        v
NASA EdsLib
        |
        + selected cFS mission allocation
        + MissionLib / cFE realization
        |
        v
NASA cFS native build/runtime
```

The ownership rule is:

```text
OrbitFabric owns mission semantics.
The adapter owns explicit projection and traceability.
The cFS mission owns concrete target allocation.
NASA target tooling owns native realization and runtime behavior.
Evidence preserves the boundary between them.
```

## Mission-owned target allocation

The reusable Projection Profile does not contain universal absolute cFS TopicId values.

Instead it binds interfaces to mission-owned allocation identities:

```yaml
interfaces:
  command:
    name: CMD
    topic_ref: CFE_MISSION/OF_DEMO_CMD_TOPICID
  telemetry:
    name: STATUS_TLM
    topic_ref: CFE_MISSION/OF_DEMO_STATUS_TLM_TOPICID
```

The generated EDS carries those native design-parameter references. The selected mission defines their concrete values, and MissionLib / cFE performs the mission-specific TopicId to MsgId realization.

For the retained SampleMission lane the two identities resolve to `160` and `416`. Those values are reference-mission evidence, not adapter policy.

The reference application consumes the same mission-owned values through `cfe_mission_eds_designparameters.h`; it does not duplicate them as local numeric constants.

See **[Target Allocation](docs/target-allocation.md)**.

## Reference Project

The repository contains a fixed cFS application under:

```text
examples/cfs/of_demo_app
```

Its purpose is not to demonstrate that OrbitFabric generates a cFS application. It demonstrates the opposite boundary:

> A normal cFS application can remain application-owned while consuming interfaces generated from an OrbitFabric-derived EDS contract.

The application source depends on generated OF_DEMO types and dispatcher APIs. Native proof harnesses stage the exact retained EDS artifact into a disposable pinned cFS mission and require the application to compile, link, install and run against that generated interface.

Read **[Reference Project: OrbitFabric Contract to Native cFS Runtime](examples/cfs/of_demo_app/README.md)**.

## Evidence model

The release line is backed by independent proof layers rather than one aggregate test:

```text
P0  deterministic projection + native EdsLib acceptance
P1  complete native_eds build/install dependency
P2  generated API + native command/telemetry runtime loop
P3  negative/conformance runtime characterization
     +
mission-owned target allocation proof
     +
installed Adapter Manager lifecycle
     +
release and Project Lock proof
     +
published-byte verification
```

### P0: standards-backed projection

P0 proves deterministic EDS XML, machine-readable traceability, Core-conformant Integration Results, deterministic failure semantics and native EdsLib processing against exact pinned upstream refs.

### P1: real cFS build dependency

P1 proves that the fixed reference application consumes generated OF_DEMO EDS interfaces and participates in the complete pinned `native_eds` build/install path.

A negative dependency control removes the staged OF_DEMO EDS and requires the native consumer build to fail.

### P2: runtime behavior

The nominal closed loop is:

```text
payload.enable
    -> EDS-enabled cmd_send
    -> cFS / ci_lab
    -> Software Bus
    -> generated OF_DEMO dispatcher
    -> fixed typed handler
    -> PayloadStatusTlm
    -> to_lab
    -> EDS-enabled tlm_recv
    -> PayloadEnabled=true
```

P2 also proves typed delivery of `payload.set_period(period_ms)` and explicitly characterizes EDS `ValidRange` metadata versus observed runtime enforcement.

### P3: conformance characterization

P3 sends a structurally valid OF_DEMO command with undefined Function Code `127` through the frozen lane. The observed native path dispatches it to the valid generated `payload.enable` typed handler.

The adapter therefore records the actual target behavior instead of adding a local Function Code guard merely to manufacture automatic rejection.

The same discipline is used for range constraints: projection of a semantic constraint into EDS is not claimed to be equivalent to automatic runtime enforcement unless the selected target path proves it.

## Validated target lane

| System | Validated baseline |
| --- | --- |
| OrbitFabric Core | `v1.3.0`, `a25917e81c90396df2b189834e83cf852fa4da5f` |
| NASA cFS | `v7.0.1`, `088b2fa828db9ff7e00733f1908e0eeb59f66ce3` |
| NASA EdsLib | `v7.0.1`, `2acc963b34f77692c6396555dcfb10ef43eb1046` |
| NASA cFE | `c5fb2b4d540bd55eb6c3707da7dd13eee679d4dd` |

Additional cFS applications and command-line tools used by the native proofs are pinned by exact commit in their harnesses. NASA source code is not vendored in this repository.

No broader cFS, EdsLib or generic/full CCSDS EDS compatibility range is claimed by `0.1.0`.

## Integration Coverage

Integration Coverage records how the analyzed OrbitFabric semantic surface is represented toward this target and where the selected target runtime does not provide the semantics that a stronger claim would require.

It distinguishes faithful projection from runtime enforcement and distinguishes adapter responsibility from mission-owned target realization.

See **[Integration Coverage](coverage/integration-coverage.md)**.

## Installed and release lifecycle

The adapter is verified through OrbitFabric Adapter Manager after the checkout package source, built wheel and acquisition wheelhouse are removed. Installed execution must reproduce the retained EDS, traceability and Integration Result bytes exactly.

The `v0.1.0` release workflow publishes only:

```text
orbitfabric_eds_cfs_adapter-0.1.0-py3-none-any.whl
adapter-release.json
SHA256SUMS
```

A Project Lock is consumer-owned project state and is not a publisher release asset.

The release workflow creates a draft GitHub Release, downloads the actual uploaded bytes back from GitHub, verifies them, and only then makes the release public.

## Product identity

```text
repository / distribution  orbitfabric-eds-cfs-adapter
Python package              orbitfabric_eds_cfs_adapter
console command             orbitfabric-eds-cfs
adapter / integration id    orbitfabric-eds-cfs
operation                   eds_cfs_projection
source coordinate           github.com/FAROTECH:orbitfabric/eds-cfs
version                     0.1.0
```

## Documentation

### User

- [Getting Started](docs/getting-started.md)
- [Reference Project](examples/cfs/of_demo_app/README.md)
- [Target Allocation](docs/target-allocation.md)
- [Integration Coverage](coverage/integration-coverage.md)

### Developer / Contributor

- [Development](docs/development.md)
- [Architecture and Ownership](docs/architecture-and-ownership.md)
- [Core Input Consumption](docs/core-input-consumption.md)
- [Repository Conformance](docs/repository-conformance.md)
- [CONTRIBUTING.md](CONTRIBUTING.md)

### Release

- [0.1.0 Release Notes](docs/releases/0.1.0.md)

## Project relationships

NASA cFS, cFE and EdsLib are independent upstream projects. This repository is an independent OrbitFabric integration and does not imply endorsement by NASA or the upstream projects.

## License

Apache License 2.0. See [LICENSE](LICENSE).
