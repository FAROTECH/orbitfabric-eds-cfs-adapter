# Adapter Repository Conformance

This repository is clean-bootstrapped rather than created with GitHub `Use this template`.

Conformance is responsibility- and contract-based, not file-for-file similarity.

| Adapter Developer Template responsibility | EDS-cFS repository home |
|---|---|
| identity | `pyproject.toml`, `integration_package.json`, README |
| packaging | `pyproject.toml`, packaged manifest/schema |
| integration contract | manifest, `cli.py`, `result.py`, contract tests |
| projection | Profile schema and `projection/` |
| implementation | `src/orbitfabric_eds_cfs_adapter/` |
| conformance | `tests/`, CI, native controls, installed lifecycle proof |
| evidence | Integration Result, traceability, native proof artifacts, lifecycle evidence |
| developer experience | README, `docs/`, CONTRIBUTING |
| automation | `.github/workflows/`, `.github/scripts/`, `tools/` |

## C0

C0 proves bootstrap conformity:

- coherent product/package/execution identity;
- installable Python package shape;
- exactly one packaged Integration Package Manifest;
- promoted `orbitfabric.adapter_cli.v1` protocol selection;
- packaged Projection Profile and traceability schemas;
- manifest conformance against OrbitFabric Core v1.3.0;
- no target semantics claimed before the P0 surface audit;
- no vendored NASA source;
- no inherited teaching scaffolding.

## C1

C1 is the repository-readiness gate after P3 and Target Allocation Readiness.

It requires:

- native cFS/EdsLib acceptance on the exact pinned lane;
- complete machine-readable traceability for the retained proof slice;
- evidence-backed Integration Coverage;
- installed lifecycle proof through the OrbitFabric Adapter Manager.

The installed lifecycle control deliberately proves more than importability:

```text
build wheel
    -> provider-neutral Release Descriptor
    -> Adapter Manager install
    -> managed-environment verification
    -> delete source checkout package + wheel + acquisition wheelhouse
    -> Adapter Manager execute eds_cfs_projection
    -> Core result conformance check
    -> exact B6/B7/B8 golden-byte comparison
    -> Adapter Manager remove
    -> empty final inventory
```

The installed execution therefore must remain independent of `src/` from the repository checkout.

The retained projection output must still match the accepted deterministic product bytes:

```text
B6 EDS XML
B7 traceability
B8 Integration Result
```

C1 does not prove release publication, Project Lock consumption or published-byte acquisition. Those remain C2 responsibilities.

## C2

C2 is evaluated before public `v0.1.0` and adds:

- release construction;
- Project Lock proof;
- published-byte controls;
- public documentation review;
- Catalog identity coherence.

Core contract semantics always take precedence over this repository and over the Adapter Developer Template.
