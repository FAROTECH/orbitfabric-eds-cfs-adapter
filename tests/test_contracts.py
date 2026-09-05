from __future__ import annotations

import json
from importlib.resources import files

from orbitfabric.conformance.integration_contracts import validate_manifest

EXPECTED_SURFACES = [
    ("entity_index", "orbitfabric.entity_index", ["0.1"]),
    ("lint_report", "orbitfabric-lint", ["v1"]),
    ("mission_snapshot", "orbitfabric.mission_snapshot", ["0.1-candidate"]),
    (
        "relationship_manifest",
        "orbitfabric.relationship_manifest",
        ["0.1-candidate"],
    ),
]


def test_manifest_conforms_to_core_1_3_contract() -> None:
    manifest_path = files("orbitfabric_eds_cfs_adapter").joinpath("integration_package.json")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    validate_manifest(manifest)

    assert manifest["integration"]["id"] == "orbitfabric-eds-cfs"
    assert manifest["adapter"]["id"] == "orbitfabric-eds-cfs"
    assert [item["id"] for item in manifest["operations"]] == ["eds_cfs_projection"]

    compatibility = manifest["core_input_compatibility"]
    assert [
        (item["role"], item["kind"], item["format_versions"])
        for item in compatibility["surfaces"]
    ] == EXPECTED_SURFACES
    assert compatibility["relationship_families"] == ["packet_includes_telemetry"]
