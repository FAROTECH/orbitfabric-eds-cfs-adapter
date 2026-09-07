# Getting Started

This guide describes the normal consumer path for the `v0.1.0` OrbitFabric EDS-cFS Adapter release.

Until `v0.1.0` is actually published, the repository remains pre-release. Do not treat repository source bytes as a substitute for published release assets.

## Validated baseline

The first release is deliberately narrow and evidence-backed.

| System | Validated baseline |
| --- | --- |
| OrbitFabric Core | `v1.3.0`, commit `a25917e81c90396df2b189834e83cf852fa4da5f` |
| NASA cFS | `v7.0.1`, commit `088b2fa828db9ff7e00733f1908e0eeb59f66ce3` |
| NASA EdsLib | `v7.0.1`, commit `2acc963b34f77692c6396555dcfb10ef43eb1046` |
| NASA cFE | commit `c5fb2b4d540bd55eb6c3707da7dd13eee679d4dd` |

No broader cFS, EdsLib or generic CCSDS EDS compatibility range is claimed by `v0.1.0`.

## 1. Create a clean consumer environment

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
```

Optionally isolate Adapter Manager state:

```bash
export ORBITFABRIC_STATE_DIR="$PWD/.orbitfabric-state"
```

## 2. Install OrbitFabric Core

Install OrbitFabric Core `v1.3.0` or the exact validated commit above.

Check the Adapter Manager surface:

```bash
orbitfabric --help
orbitfabric adapter list
```

## 3. Obtain the published adapter assets

For `v0.1.0`, the GitHub Release contains publisher-owned assets only:

```text
orbitfabric_eds_cfs_adapter-0.1.0-py3-none-any.whl
adapter-release.json
SHA256SUMS
```

Keep them together and verify the downloaded bytes:

```bash
sha256sum -c SHA256SUMS
```

The canonical Adapter Source Coordinate is:

```text
github.com/FAROTECH:orbitfabric/eds-cfs
```

A Project Lock is project-owned consumer state and is not published as an adapter release asset.

## 4. Install through Adapter Manager

```bash
orbitfabric adapter install \
  adapter-release.json \
  --artifact orbitfabric_eds_cfs_adapter-0.1.0-py3-none-any.whl
```

Then inspect and verify the installed instance:

```bash
orbitfabric adapter list --json
orbitfabric adapter inspect <instance-id>
orbitfabric adapter verify <instance-id>
```

## 5. Produce a Core Integration Input Set

The adapter does not parse Mission Model YAML as a private API. It consumes the public Core Integration Input Set.

```bash
orbitfabric export integration-input-set \
  <mission-directory> \
  --output-dir <core-input-directory>
```

The handoff manifest is:

```text
<core-input-directory>/integration_input_manifest.json
```

## 6. Provide the EDS-cFS Projection Profile

The Profile owns explicit target binding intent. For cFS message allocation it binds OrbitFabric interfaces to mission-owned symbolic `CFE_MISSION` identities rather than universal absolute TopicId numbers.

Representative bindings are:

```text
CFE_MISSION/OF_DEMO_CMD_TOPICID
CFE_MISSION/OF_DEMO_STATUS_TLM_TOPICID
```

The selected cFS mission remains authoritative for concrete allocation values and MissionLib realization.

See [Target allocation](target-allocation.md).

## 7. Execute the adapter

```bash
orbitfabric adapter execute <instance-id> \
  --operation eds_cfs_projection \
  --input-set-manifest <core-input-directory>/integration_input_manifest.json \
  --profile <eds-cfs-profile.yaml> \
  --output-dir <output-directory>
```

The retained product output is:

```text
eds/mission.xml
traceability.json
integration_result.json
```

The EDS XML is an explicit interoperability boundary. The adapter does not bypass it with a hidden OrbitFabric-to-cFS direct path.

## Important runtime boundaries

`v0.1.0` records two target-runtime characterizations that consumers should understand:

1. EDS `ValidRange` metadata is projected faithfully, but the validated native lane does not automatically enforce every projected range at runtime.
2. On the frozen native lane, an undefined Function Code in a derived OF_DEMO command family can reach a valid generated typed handler. The adapter therefore does not claim automatic unknown-Function-Code rejection.

No adapter-local runtime guards are inserted to manufacture stronger target behavior than the validated lane provides.

See [Integration Coverage](../coverage/integration-coverage.md) for exact claim boundaries.
