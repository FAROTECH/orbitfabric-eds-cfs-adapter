from pathlib import Path

import pytest
from jsonschema import ValidationError

from orbitfabric_eds_cfs_adapter.profile import load_profile

VALID_BOOTSTRAP_PROFILE = """\
kind: orbitfabric.projection_profile
profile_version: 0.1-candidate
profile:
  id: c0-bootstrap
  version: 0.0.0
integration:
  id: orbitfabric-eds-cfs
  schema_version: 0.1-candidate
settings: {}
bindings: []
"""


def test_bootstrap_profile_is_valid(tmp_path: Path) -> None:
    path = tmp_path / "profile.yaml"
    path.write_text(VALID_BOOTSTRAP_PROFILE, encoding="utf-8")

    profile = load_profile(path)

    assert profile["integration"]["id"] == "orbitfabric-eds-cfs"


def test_target_fields_are_not_speculatively_accepted_at_c0(tmp_path: Path) -> None:
    path = tmp_path / "profile.yaml"
    path.write_text(
        VALID_BOOTSTRAP_PROFILE.replace("settings: {}", "settings:\n  cfs_app: OF_DEMO"),
        encoding="utf-8",
    )

    with pytest.raises(ValidationError):
        load_profile(path)
