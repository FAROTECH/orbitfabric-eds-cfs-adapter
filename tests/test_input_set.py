from __future__ import annotations

import json
import zipfile
from pathlib import Path

import pytest

from orbitfabric_eds_cfs_adapter.input_set import (
    InputSetError,
    compute_input_set_sha256,
    load_input_set,
)

ROOT = Path(__file__).resolve().parents[1]
RETAINED = ROOT / "tests" / "fixtures" / "p0_b1" / "integration_input" / "retained.zip"


def _fixture(tmp_path: Path) -> Path:
    with zipfile.ZipFile(RETAINED) as archive:
        archive.extractall(tmp_path)
    return tmp_path / "integration_input_manifest.json"


def test_retained_b1_input_set_loads_with_frozen_b2_boundary(tmp_path: Path) -> None:
    loaded = load_input_set(_fixture(tmp_path))

    assert loaded.manifest["input_set_sha256"] == (
        "e8b70eebbda845a91546f40121ee6d927f96a2a39de2776437930e009b20bc98"
    )
    assert loaded.resolve_entity("commands", "payload.enable")["id"] == "payload.enable"
    assert loaded.resolve_entity("telemetry", "payload.sample_count")["domain"] == "telemetry"
    assert loaded.packet_telemetry_ids("payload_status") == (
        "payload.enabled",
        "payload.sample_count",
    )
    assert len(loaded.lint_warnings) == 6


def test_model_summary_is_not_semantically_consumed(tmp_path: Path) -> None:
    manifest_path = _fixture(tmp_path)
    (tmp_path / "model_summary.json").unlink()

    loaded = load_input_set(manifest_path)

    assert loaded.resolve_entity("packets", "payload_status")["id"] == "payload_status"


def test_required_surface_hash_mismatch_fails_closed(tmp_path: Path) -> None:
    manifest_path = _fixture(tmp_path)
    path = tmp_path / "entity_index.json"
    path.write_text(path.read_text(encoding="utf-8") + "\n", encoding="utf-8")

    with pytest.raises(InputSetError, match="entity_index: SHA-256 mismatch"):
        load_input_set(manifest_path)


def test_failed_lint_state_is_rejected_even_with_valid_manifest_digest(tmp_path: Path) -> None:
    manifest_path = _fixture(tmp_path)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["lint_result"] = "failed"
    manifest["input_set_sha256"] = compute_input_set_sha256(manifest)
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    with pytest.raises(InputSetError, match="semantic lint blocks projection"):
        load_input_set(manifest_path)


def test_unknown_core_identity_fails_closed(tmp_path: Path) -> None:
    loaded = load_input_set(_fixture(tmp_path))

    with pytest.raises(InputSetError, match="must resolve exactly once"):
        loaded.resolve_entity("commands", "payload.unknown")
