# Development

## Local bootstrap checks

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

The console entry point is present because execution identity is part of C0, but substantive projection is deliberately disabled until P0.

Running `eds_cfs_projection` during C0 fails explicitly rather than reporting synthetic success.

## Native dependencies

Do not vendor NASA cFS or EdsLib. Native validation workspaces will be created from exact pinned refs when P0/P1 requires them.

```text
cFS     088b2fa828db9ff7e00733f1908e0eeb59f66ce3
EdsLib  2acc963b34f77692c6396555dcfb10ef43eb1046
```
