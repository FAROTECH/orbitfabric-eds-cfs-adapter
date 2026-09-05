from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from importlib.resources import files
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft202012Validator


@dataclass(frozen=True)
class LoadedProfile:
    path: Path
    document: dict[str, Any]
    sha256: str


def _schema() -> dict[str, Any]:
    schema_path = files("orbitfabric_eds_cfs_adapter").joinpath("schemas/profile-0.1.schema.json")
    return json.loads(schema_path.read_text(encoding="utf-8"))


def load_profile_with_provenance(path: Path) -> LoadedProfile:
    source = path.resolve()
    try:
        raw_bytes = source.read_bytes()
    except OSError as exc:
        raise ValueError(f"Cannot read Projection Profile {source}: {exc}") from exc

    try:
        text = raw_bytes.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError(f"Projection Profile is not valid UTF-8: {source}") from exc

    raw = yaml.safe_load(text)
    if not isinstance(raw, dict):
        raise ValueError("Projection Profile root must be an object")

    Draft202012Validator(_schema()).validate(raw)
    return LoadedProfile(
        path=source,
        document=raw,
        sha256=hashlib.sha256(raw_bytes).hexdigest(),
    )


def load_profile(path: Path) -> dict[str, Any]:
    return load_profile_with_provenance(path).document
