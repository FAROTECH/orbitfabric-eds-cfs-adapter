# Contributing

This repository is an experimental, pre-release OrbitFabric adapter under active evidence-driven development.

## Current development rule

Work follows the active gates recorded in OrbitFabric Architecture Lab. Do not broaden product scope or change ownership boundaries from this repository alone.

Before proposing implementation changes:

```bash
python -m pip install -e ".[dev]"
python tools/check_repository_consistency.py
ruff check .
pytest -q
python -m build --wheel
```

Tests that depend on OrbitFabric Core use the exact Core `v1.3.0` baseline selected by CI. Native cFS/EdsLib proofs use exact upstream commits recorded in their harnesses.

## Architecture findings

If implementation suggests any of the following, stop the product change and return the finding to Architecture Lab first:

- a new Core semantic requirement;
- a change to the Core Integration Input Set contract;
- a change to the Adapter Manager or release lifecycle;
- a different EDS-cFS ownership boundary;
- a generic CCSDS EDS interoperability claim;
- a target identifier that appears to need Core ownership.

Downstream failures must first be isolated as adapter realization, fixed-app, mission integration/runtime configuration, evidence-harness, upstream/toolchain or CI/environment findings.

## NASA dependencies

Do not vendor cFS or EdsLib into this repository. Native validation workspaces must use exact pinned upstream refs and remain disposable.

## Current maturity

P0 deterministic projection/native EdsLib validation and P1 complete native build/install are proven. P2 runtime command/telemetry acceptance remains in progress. No versioned public release is claimed yet.
