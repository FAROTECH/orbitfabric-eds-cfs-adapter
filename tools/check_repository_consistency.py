from __future__ import annotations

import hashlib
import json
import runpy
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "src" / "orbitfabric_eds_cfs_adapter"
MANIFEST = PACKAGE / "integration_package.json"
SCHEMA = PACKAGE / "schemas" / "profile-0.1.schema.json"
TRACEABILITY_SCHEMA = PACKAGE / "schemas" / "traceability-0.1.schema.json"
CONSTANTS = PACKAGE / "constants.py"

EXPECTED_CORE_COMPATIBILITY = {
    "input_set_versions": ["0.1-candidate"],
    "relationship_families": ["packet_includes_telemetry"],
    "surfaces": [
        {
            "role": "entity_index",
            "kind": "orbitfabric.entity_index",
            "format_versions": ["0.1"],
        },
        {
            "role": "lint_report",
            "kind": "orbitfabric-lint",
            "format_versions": ["v1"],
        },
        {
            "role": "mission_snapshot",
            "kind": "orbitfabric.mission_snapshot",
            "format_versions": ["0.1-candidate"],
        },
        {
            "role": "relationship_manifest",
            "kind": "orbitfabric.relationship_manifest",
            "format_versions": ["0.1-candidate"],
        },
    ],
}


def _fail(message: str) -> None:
    raise SystemExit(message)


def main() -> int:
    identity = runpy.run_path(str(CONSTANTS))
    expected = {
        "distribution": identity["DISTRIBUTION_NAME"],
        "version": identity["VERSION"],
        "console": identity["CONSOLE_COMMAND"],
        "adapter_id": identity["ADAPTER_ID"],
        "integration_id": identity["INTEGRATION_ID"],
        "operation": identity["OPERATION_ID"],
        "python_package": identity["PYTHON_PACKAGE"],
        "source_coordinate": identity["SOURCE_COORDINATE"],
    }

    if expected["source_coordinate"] != {
        "authority": "github.com/FAROTECH",
        "publisher": "orbitfabric",
        "name": "eds-cfs",
    }:
        _fail("Canonical Adapter Source Coordinate mismatch")

    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    project = pyproject["project"]
    scripts = project["scripts"]
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))

    if project["name"] != expected["distribution"]:
        _fail("Distribution identity mismatch")
    if project["version"] != expected["version"]:
        _fail("Distribution version mismatch")
    if scripts.get(expected["console"]) != f"{expected['python_package']}.cli:main":
        _fail("Console script identity mismatch")
    if manifest["adapter"] != {
        "id": expected["adapter_id"],
        "version": expected["version"],
    }:
        _fail("Manifest adapter identity mismatch")
    if manifest["integration"]["id"] != expected["integration_id"]:
        _fail("Manifest integration identity mismatch")
    if manifest["execution"] != {
        "argv_prefix": [expected["console"]],
        "protocol": "orbitfabric.adapter_cli.v1",
    }:
        _fail("Execution protocol identity mismatch")
    if [item["id"] for item in manifest["operations"]] != [expected["operation"]]:
        _fail("Operation identity mismatch")

    manifests = list((ROOT / "src").rglob("integration_package.json"))
    if manifests != [MANIFEST]:
        _fail("The Python distribution must own exactly one integration_package.json")

    schema_digest = hashlib.sha256(SCHEMA.read_bytes()).hexdigest()
    declared_digest = manifest["profile_schemas"][0]["sha256"]
    if schema_digest != declared_digest:
        _fail("Projection Profile schema digest mismatch")

    if not TRACEABILITY_SCHEMA.is_file():
        _fail("B7 traceability schema is missing")
    traceability_schema = json.loads(TRACEABILITY_SCHEMA.read_text(encoding="utf-8"))
    if traceability_schema["properties"]["kind"].get("const") != (
        "orbitfabric.eds_cfs.traceability"
    ):
        _fail("B7 traceability schema kind mismatch")
    if traceability_schema["properties"]["traceability_version"].get("const") != (
        "0.1-candidate"
    ):
        _fail("B7 traceability schema version mismatch")

    if manifest["core_input_compatibility"] != EXPECTED_CORE_COMPATIBILITY:
        _fail("Core consumption declaration differs from Architecture Lab B2 freeze")

    residue_tokens = (
        "orbitfabric" + "-dummy",
        "orbitfabric" + "_dummy_adapter",
        "dummy" + " adapter",
    )
    scan_roots = [ROOT / "README.md", ROOT / "src", ROOT / "docs", ROOT / "tests"]
    for scan_root in scan_roots:
        paths = [scan_root] if scan_root.is_file() else scan_root.rglob("*")
        for path in paths:
            if not path.is_file():
                continue
            try:
                text = path.read_text(encoding="utf-8").lower()
            except UnicodeDecodeError:
                continue
            for token in residue_tokens:
                if token in text:
                    _fail(f"Template teaching residue found in {path.relative_to(ROOT)}")

    print("Repository consistency: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
