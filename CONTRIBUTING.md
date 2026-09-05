# Contributing

This repository is currently a private experimental OrbitFabric adapter workspace.

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

Tests that depend on OrbitFabric Core use the exact Core `v1.3.0` baseline selected by CI.

## Architecture findings

If implementation suggests any of the following, stop the product change and return the finding to Architecture Lab first:

- a new Core semantic requirement;
- a change to the Core Integration Input Set contract;
- a change to the Adapter Manager or release lifecycle;
- a different EDS-cFS ownership boundary;
- a generic CCSDS EDS interoperability claim;
- a target identifier that appears to need Core ownership.

## NASA dependencies

Do not vendor cFS or EdsLib into this repository. Native validation workspaces must use exact pinned upstream refs and remain disposable.
