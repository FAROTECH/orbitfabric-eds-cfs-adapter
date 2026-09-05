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
| conformance | `tests/`, CI, later native controls |
| evidence | Integration Result and traceability in P0+, CI evidence later |
| developer experience | README, `docs/`, CONTRIBUTING |
| automation | `.github/workflows/`, `tools/` |

## C0

C0 proves only bootstrap conformity:

- coherent product/package/execution identity;
- installable Python package shape;
- exactly one packaged Integration Package Manifest;
- promoted `orbitfabric.adapter_cli.v1` protocol selection;
- packaged Projection Profile schema;
- manifest conformance against OrbitFabric Core v1.3.0;
- no target semantics claimed before the P0 surface audit;
- no vendored NASA source;
- no inherited teaching scaffolding.

## Later checkpoints

C1 is evaluated after P3 and adds installed lifecycle, native cFS/EdsLib acceptance, complete traceability and drafted Integration Coverage.

C2 is evaluated before public `v0.1.0` and adds release construction, Project Lock proof, published-byte controls, public documentation review and Catalog identity coherence.

Core contract semantics always take precedence over this repository and over the Adapter Developer Template.
