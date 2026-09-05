# Retained Core Integration Input Set

This directory freezes the exact P0/B1 output produced by OrbitFabric Core `v1.3.0` from the sibling `mission/` fixture.

Generation baseline:

```text
OrbitFabric Core v1.3.0
a25917e81c90396df2b189834e83cf852fa4da5f
```

Deterministic mission workspace:

```text
/tmp/orbitfabric-eds-cfs-p0-mission
```

The fixed workspace path is deliberate because Core surfaces retain `source.mission_dir` provenance. It prevents the retained bytes from depending on an arbitrary Git checkout location.

## Retained evidence

`retained.zip` contains the six exact Core-produced files:

```text
integration_input_manifest.json
mission_snapshot.json
entity_index.json
relationship_manifest.json
lint_report.json
model_summary.json
```

The archive is a review/evidence convenience. `SHA256SUMS` is the normative repository check for the individual retained surface bytes. CI regenerates the Integration Input Set with the exact Core baseline and requires every generated file to match these digests.

The retained manifest declares:

```text
input_set_version  0.1-candidate
input_set_sha256   e8b70eebbda845a91546f40121ee6d927f96a2a39de2776437930e009b20bc98
load_result        loaded
lint_result        passed_with_warnings
```

The warnings are retained intentionally. P0 does not add mission semantics merely to make lint output empty.
