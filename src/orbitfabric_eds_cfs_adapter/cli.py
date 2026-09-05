from __future__ import annotations

import argparse
import sys
from pathlib import Path

from orbitfabric_eds_cfs_adapter.execution import execute_projection
from orbitfabric_eds_cfs_adapter.result import OPERATION_ID


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="orbitfabric-eds-cfs")
    subparsers = parser.add_subparsers(dest="command", required=True)
    run = subparsers.add_parser("run")
    run.add_argument("--operation", required=True)
    run.add_argument("--input-set-manifest", required=True)
    run.add_argument("--profile", required=True)
    run.add_argument("--output-dir", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.operation != OPERATION_ID:
        print(f"Unsupported operation: {args.operation}", file=sys.stderr)
        return 2

    try:
        outcome = execute_projection(
            Path(args.input_set_manifest),
            Path(args.profile),
            Path(args.output_dir),
        )
    except OSError as exc:
        print(f"EDS-cFS projection failed: {exc}", file=sys.stderr)
        return 1

    if outcome.succeeded:
        assert outcome.result_path is not None
        print(f"Integration Result: {outcome.result_path}")
        return 0

    print(f"EDS-cFS projection failed: {outcome.detail}", file=sys.stderr)
    if outcome.result_path is not None:
        print(f"Failed Integration Result: {outcome.result_path}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
