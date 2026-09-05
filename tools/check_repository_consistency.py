from __future__ import annotations

import hashlib
import json
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "src" / "orbitfabric_eds_cfs_adapter"
MANIFEST = PACKAGE / "integration_package.json"
SCHEMA = PACKAGE / "schemas" / "profile-0.1.schema.json"

EXPECTED = {
    "distribution": "orbitfabric-eds-cfs-adapter",
    "version": "0.1.0.dev0",
    "console": "orbitfabric-eds-cfs",
    "adapter_id": "orbitfabric-eds-cfs",
    "integration_id": "orbitfabric-eds-cfs",
    "operation": "eds_cfs_projection",
}

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
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    project = pyproject["project"]
    scripts = project["scripts"]
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))

    if project["name"] != EXPECTED["distribution"]:
        _fail("Distribution identity mismatch")
    if project["version"] != EXPECTED["version"]:
        _fail("Distribution version mismatch")
    if scripts.get(EXPECTED["console"]) != "orbitfabric_eds_cfs_adapter.cli:main":
        _fail("Console script identity mismatch")
    if manifest["adapter"] != {
        "id": EXPECTED["adapter_id"],
        "version": EXPECTED["version"],
    }:
        _fail("Manifest adapter identity mismatch")
    if manifest["integration"]["id"] != EXPECTED["integration_id"]:
        _fail("Manifest integration identity mismatch")
    if manifest["execution"] != {
        "argv_prefix": [EXPECTED["console"]],
        "protocol": "orbitfabric.adapter_cli.v1",
    }:
        _fail("Execution protocol identity mismatch")
    if [item["id"] for item in manifest["operations"]] != [EXPECTED["operation"]]:
        _fail("Operation identity mismatch")

    manifests = list((ROOT / "src").rglob("integration_package.json"))
    if manifests != [MANIFEST]:
        _fail("The Python distribution must own exactly one integration_package.json")

    schema_digest = hashlib.sha256(SCHEMA.read_bytes()).hexdigest()
    declared_digest = manifest["profile_schemas"][0]["sha256"]
    if schema_digest != declared_digest:
        _fail("Projection Profile schema digest mismatch")

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
