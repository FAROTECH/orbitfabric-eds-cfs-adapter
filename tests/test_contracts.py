from __future__ import annotations

import json
from importlib.resources import files

from orbitfabric.conformance.integration_contracts import validate_manifest


def test_manifest_conforms_to_core_1_3_contract() -> None:
    manifest_path = files("orbitfabric_eds_cfs_adapter").joinpath("integration_package.json")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    validate_manifest(manifest)

    assert manifest["integration"]["id"] == "orbitfabric-eds-cfs"
    assert manifest["adapter"]["id"] == "orbitfabric-eds-cfs"
    assert [item["id"] for item in manifest["operations"]] == ["eds_cfs_projection"]
    assert manifest["core_input_compatibility"]["surfaces"] == []
