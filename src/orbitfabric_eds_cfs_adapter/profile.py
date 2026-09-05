from __future__ import annotations

import json
from importlib.resources import files
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft202012Validator


def load_profile(path: Path) -> dict[str, Any]:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("Projection Profile root must be an object")

    schema_path = files("orbitfabric_eds_cfs_adapter").joinpath("schemas/profile-0.1.schema.json")
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    Draft202012Validator(schema).validate(raw)
    return raw
