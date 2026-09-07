# Adapter Repository Conformance

This repository is clean-bootstrapped rather than created with GitHub `Use this template`.

Conformance is responsibility- and contract-based, not file-for-file similarity.

| Adapter Developer Template responsibility | EDS-cFS repository home |
|---|---|
| identity | `constants.py`, `pyproject.toml`, `integration_package.json`, README |
| packaging | `pyproject.toml`, packaged manifest/schema |
| integration contract | manifest, `cli.py`, `result.py`, contract tests |
| projection | Profile schema and `projection/` |
| implementation | `src/orbitfabric_eds_cfs_adapter/` |
| conformance | `tests/`, CI, native controls, installed lifecycle, release proof |
| evidence | Integration Result, traceability, native proof artifacts, lifecycle/release evidence |
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

C1 is complete, promoted and main-revalidated.

It proves:

- native cFS/EdsLib acceptance on the exact pinned lane;
- complete machine-readable traceability for the retained proof slice;
- evidence-backed Integration Coverage;
- installed lifecycle through OrbitFabric Adapter Manager.

The installed lifecycle control deliberately proves more than importability:

```text
build wheel
    -> canonical Release Descriptor
    -> Adapter Manager install
    -> managed-environment verification
    -> delete source checkout package + wheel + acquisition wheelhouse
    -> Adapter Manager execute eds_cfs_projection
    -> Core result conformance check
    -> exact B6/B7/B8 golden-byte comparison
    -> Adapter Manager remove
    -> empty final inventory
```

The installed execution must remain independent of `src/` from the repository checkout.

## C2

C2 is the public-productization gate for `v0.1.0`.

It is intentionally split into two ordered stages.

### C2-A: release-ready source

C2-A must be complete before a public tag is created.

It requires:

- one canonical Adapter Source Coordinate owned by the product;
- source/package/manifest version coherence at `0.1.0`;
- deterministic Release Descriptor construction;
- deterministic Project Lock construction;
- Project Lock lifecycle proof:

```text
MISSING
    -> INSTALLED
    -> MATCH
    -> repeated install NOOP
    -> verify PASS
    -> remove
    -> empty inventory
```

- publisher-only release construction containing the wheel, `adapter-release.json` and `SHA256SUMS` but not a Project Lock;
- public Getting Started documentation;
- `v0.1.0` release notes;
- a tag-triggered GitHub Release workflow that creates a draft, downloads the release assets back from GitHub, verifies the published bytes, and only then publishes the release;
- full P0/P1/P2/P3/C1 regression on one final source HEAD.

The canonical Source Coordinate is:

```text
github.com/FAROTECH:orbitfabric/eds-cfs
```

### C2-B: published product and Catalog consumer proof

C2-B starts only after the verified `v0.1.0` GitHub Release exists.

It requires:

- exact published `adapter-release.json` digest;
- canonical Adapter Catalog entry for `eds-cfs` `0.1.0`;
- GitHub Release source binding for `FAROTECH/orbitfabric-eds-cfs-adapter`;
- exact consumer Project Lock fixture;
- Catalog validation;
- Catalog product-consumer E2E against the actual published release bytes.

The Catalog must never be populated from a locally reconstructed descriptor digest when published release bytes already exist.

Core contract semantics always take precedence over this repository and over the Adapter Developer Template.
