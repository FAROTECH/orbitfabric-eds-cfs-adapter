from __future__ import annotations

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
GOLDEN_ROOT = ROOT / "tests" / "fixtures" / "p0_b9"

GOLDENS = {
    "b2": {
        "phase": "input_compatibility",
        "code": "EDS-CFS-INPUT-001",
        "coverage": "unavailable",
    },
    "b3": {
        "phase": "profile_schema",
        "code": "EDS-CFS-PROFILE-001",
        "coverage": "unavailable",
    },
    "b4": {
        "phase": "source_resolution",
        "code": "EDS-CFS-RESOLVE-001",
        "coverage": "unavailable",
    },
    "b5": {
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

    assert data.endswith(b"\n")
    assert b"\r\n" not in data

    result = json.loads(data)
    assert result["kind"] == "orbitfabric.integration_result"
    assert result["result_version"] == "0.2-candidate"
    assert result["result"] == "failed"
    assert result["adapter"] == {"id": "orbitfabric-eds-cfs", "version": "0.1.0"}
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
