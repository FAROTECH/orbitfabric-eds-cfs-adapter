import argparse
import sys

OPERATION = "eds_cfs_projection"


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
    if args.operation != OPERATION:
        print(f"Unsupported operation: {args.operation}", file=sys.stderr)
        return 2

    print(
        "EDS-cFS projection is not implemented yet; repository is at C0 bootstrap conformity.",
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
