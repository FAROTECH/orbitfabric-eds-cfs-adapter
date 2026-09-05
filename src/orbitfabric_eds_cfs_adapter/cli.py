from __future__ import annotations

import argparse
import sys
from pathlib import Path

from orbitfabric_eds_cfs_adapter.input_set import InputSetError, load_input_set
from orbitfabric_eds_cfs_adapter.profile import load_profile_with_provenance
from orbitfabric_eds_cfs_adapter.projection.eds_xml import serialize_eds_xml
from orbitfabric_eds_cfs_adapter.projection.model import build_projection_model
from orbitfabric_eds_cfs_adapter.projection.resolution import ResolutionError, resolve_profile
from orbitfabric_eds_cfs_adapter.projection.traceability import (
    TraceabilityError,
    build_traceability,
    serialize_traceability,
)
from orbitfabric_eds_cfs_adapter.result import (
    EDS_RELATIVE_PATH,
    OPERATION_ID,
    RESULT_RELATIVE_PATH,
    TRACEABILITY_RELATIVE_PATH,
    ResultError,
    build_success_result,
    write_result,
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="orbitfabric-eds-cfs")
    subparsers = parser.add_subparsers(dest="command", required=True)
    run = subparsers.add_parser("run")
    run.add_argument("--operation", required=True)
    run.add_argument("--input-set-manifest", required=True)
    run.add_argument("--profile", required=True)
    run.add_argument("--output-dir", required=True)
    return parser


def _remove_stale_success_marker(output_dir: Path) -> None:
    result_path = output_dir / RESULT_RELATIVE_PATH
    if result_path.exists():
        if not result_path.is_file():
            raise OSError(f"Expected Integration Result path to be a file: {result_path}")
        result_path.unlink()


def _run_projection(input_manifest: Path, profile_path: Path, output_dir: Path) -> Path:
    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    _remove_stale_success_marker(output_dir)

    core = load_input_set(input_manifest)
    loaded_profile = load_profile_with_provenance(profile_path)
    resolved = resolve_profile(loaded_profile.document, core)
    model = build_projection_model(resolved)

    xml_bytes = serialize_eds_xml(model)
    traceability = build_traceability(resolved, model, xml_bytes)
    traceability_bytes = serialize_traceability(traceability)

    eds_path = output_dir / EDS_RELATIVE_PATH
    eds_path.parent.mkdir(parents=True, exist_ok=True)
    eds_path.write_bytes(xml_bytes)

    traceability_path = output_dir / TRACEABILITY_RELATIVE_PATH
    traceability_path.write_bytes(traceability_bytes)

    result = build_success_result(
        core,
        loaded_profile,
        resolved,
        traceability,
        output_dir,
    )
    return write_result(output_dir, result, traceability)


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.operation != OPERATION_ID:
        print(f"Unsupported operation: {args.operation}", file=sys.stderr)
        return 2

    try:
        result_path = _run_projection(
            Path(args.input_set_manifest),
            Path(args.profile),
            Path(args.output_dir),
        )
    except (
        InputSetError,
        ResolutionError,
        TraceabilityError,
        ResultError,
        OSError,
        ValueError,
    ) as exc:
        print(f"EDS-cFS projection failed: {exc}", file=sys.stderr)
        return 1

    print(f"Integration Result: {result_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
