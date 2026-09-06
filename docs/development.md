# Development

## Local checks

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
python -m pip install "orbitfabric @ git+https://github.com/FAROTECH/orbitfabric.git@a25917e81c90396df2b189834e83cf852fa4da5f"

ruff check .
python tools/check_repository_consistency.py
pytest -q
python -m build --wheel
```

## Current execution status

The public console entry point `orbitfabric-eds-cfs` implements the accepted P0 projection lane and emits deterministic EDS, traceability and Integration Result artifacts for the supported Profile/Core boundary.

P0 and P1 are retained proof gates, not claims of complete cFS/CCSDS EDS interoperability. P2 runtime proof remains active.

## Native proof lane

NASA cFS and EdsLib are not vendored. CI creates disposable workspaces from exact pinned refs:

```text
cFS     088b2fa828db9ff7e00733f1908e0eeb59f66ce3
EdsLib  2acc963b34f77692c6396555dcfb10ef43eb1046
cFE     c5fb2b4d540bd55eb6c3707da7dd13eee679d4dd
```

P1 additionally builds the fixed `examples/cfs/of_demo_app` through the external `CFS_APP_PATH` seam and requires generated OF_DEMO interfaces.

P2 uses the same pinned lane plus NASA EDS-enabled command-line tools to exercise the first runtime command/telemetry slice. Runtime startup and TO routing modifications are made only in disposable downstream workspaces.

## Evidence discipline

A failing native proof must be classified before product semantics are changed. Distinguish at least:

```text
adapter semantic / target realization
fixed application
mission integration/runtime configuration
evidence harness
upstream/toolchain
CI/environment
```

Core or Projection Profile scope is not broadened from an unexplained downstream failure.
