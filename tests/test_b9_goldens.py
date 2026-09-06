from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
GOLDEN_ROOT = ROOT / "tests" / "fixtures" / "p0_b9"

GOLDENS = {
    "b2": {
        "size": 2472,
        "sha256": "62549d9a7aff558677d057fb0a46c0dd1c002a912fd836a4a66ab3f51fd78a13",
        "phase": "input_compatibility",
        "code": "EDS-CFS-INPUT-001",
        "coverage": "unavailable",
    },
    "b3": {
        "size": 2376,
        "sha256": "5f57622b9c6d20484b3bb07e4f509775961cee2040ca605610d6d228bdb375eb",
        "phase": "profile_schema",
        "code": "EDS-CFS-PROFILE-001",
        "coverage": "unavailable",
    },
    "b4": {
        "size": 2579,
        "sha256": "7a0824c77344c08814c76c090c1b06aaac5007e864e2712eadcd1ab9c411adf7",
        "phase": "source_resolution",
        "code": "EDS-CFS-RESOLVE-001",
        "coverage": "unavailable",
    },
    "b5": {
        "size": 4570,
        "sha256": "014a9c634f4a0e110f688f37e6ce8cd67ae82c4eb3a1219beabcff6b0d0822d0",
        "phase": "projection_validation",
        "code": "EDS-CFS-PROJECT-001",
        "coverage": "complete",
    },
}


@pytest.mark.parametrize("layer", sorted(GOLDENS))
def test_retained_b9_failed_result_golden_is_exact(layer: str) -> None:
    contract = GOLDENS[layer]
    path = GOLDEN_ROOT / f"{layer}.json"
    data = path.read_bytes()

    assert len(data) == contract["size"]
    assert hashlib.sha256(data).hexdigest() == contract["sha256"]
    assert data.endswith(b"\n")
    assert b"\r\n" not in data

    result = json.loads(data)
    assert result["kind"] == "orbitfabric.integration_result"
    assert result["result_version"] == "0.2-candidate"
    assert result["result"] == "failed"
    assert result["operation"] == {"id": "eds_cfs_projection"}
    assert result["inputs"]["operation_inputs"] == []
    assert result["mappings"] == []
    assert result["resolutions"] == []
    assert result["evidence"] == []
    assert result["external_tools"] == []
    assert result["coverage"]["status"] == contract["coverage"]

    diagnostic = result["diagnostics"][0]
    assert diagnostic["id"] == "diag-001"
    assert diagnostic["owner"] == "integration"
    assert diagnostic["severity"] == "ERROR"
    assert diagnostic["phase"] == contract["phase"]
    assert diagnostic["code"] == contract["code"]

    assert [item["id"] for item in result["artifacts"]] == [
        "eds.package",
        "traceability",
    ]
    assert all(item["path"] is None for item in result["artifacts"])
    assert all(item["sha256"] is None for item in result["artifacts"])
    assert all(item["retained_partial"] is False for item in result["artifacts"])

    if layer == "b5":
        assert result["coverage"]["summary"] == {"blocked": 5}
        assert len(result["coverage"]["records"]) == 5
        assert all(
            record["state"] == "blocked" for record in result["coverage"]["records"]
        )
