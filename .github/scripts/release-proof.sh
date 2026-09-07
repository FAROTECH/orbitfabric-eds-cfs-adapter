#!/usr/bin/env bash
set -euo pipefail

if [[ "${GITHUB_ACTIONS:-}" != "true" ]]; then
  echo "This is the CI release-proof control. Use tools/build_release_bundle.py locally." >&2
  exit 2
fi

root="${GITHUB_WORKSPACE:?GITHUB_WORKSPACE is required}"
work="/tmp/orbitfabric-eds-cfs-release-proof"
state="$work/state"
evidence="$work/evidence"
wheelhouse="$work/wheelhouse"
release_dir="$work/release"
publisher_release_dir="$work/publisher-release"

export ORBITFABRIC_STATE_DIR="$state"

rm -rf "$work"
mkdir -p "$evidence" "$wheelhouse" "$release_dir" "$publisher_release_dir"

cd "$root"
rm -rf dist
python -m build --wheel
wheel="$(realpath "$(find "$root/dist" -maxdepth 1 -name '*.whl' -print -quit)")"
test -n "$wheel"

source_coordinate="$(PYTHONPATH="$root/src" python - <<'PY'
from orbitfabric_eds_cfs_adapter.constants import SOURCE_COORDINATE

print(
    f"{SOURCE_COORDINATE['authority']}:"
    f"{SOURCE_COORDINATE['publisher']}/{SOURCE_COORDINATE['name']}"
)
PY
)"

python tools/build_release_bundle.py \
  --wheel "$wheel" \
  --output-dir "$release_dir"

descriptor="$release_dir/adapter-release.json"
lock="$release_dir/adapter-project-lock.json"

PYTHONPATH="$root/src" python - <<PY
from orbitfabric.adapter_manager import ProjectLockService
from orbitfabric.conformance.adapter_release import load_release_descriptor
from orbitfabric_eds_cfs_adapter.constants import SOURCE_COORDINATE, VERSION

release = load_release_descriptor("$descriptor")
assert release["source_coordinate"] == SOURCE_COORDINATE
assert release["release_version"] == VERSION
ProjectLockService().load("$lock")
PY

cp "$descriptor" "$evidence/adapter-release.json"
cp "$lock" "$evidence/adapter-project-lock.json"
cp "$release_dir/SHA256SUMS" "$evidence/SHA256SUMS"

python tools/build_release_bundle.py \
  --wheel "$wheel" \
  --release-only \
  --output-dir "$publisher_release_dir"

test -f "$publisher_release_dir/adapter-release.json"
test -f "$publisher_release_dir/SHA256SUMS"
test ! -e "$publisher_release_dir/adapter-project-lock.json"

PYTHONPATH="$root/src" python - <<PY
from pathlib import Path

from orbitfabric.conformance.adapter_release import load_release_descriptor
from orbitfabric_eds_cfs_adapter.constants import SOURCE_COORDINATE, VERSION

release_dir = Path("$publisher_release_dir")
release = load_release_descriptor(release_dir / "adapter-release.json")
assert release["source_coordinate"] == SOURCE_COORDINATE
assert release["release_version"] == VERSION

lines = (release_dir / "SHA256SUMS").read_text(encoding="utf-8").splitlines()
assert len(lines) == 2
assert any(line.endswith("  " + Path("$wheel").name) for line in lines)
assert any(line.endswith("  adapter-release.json") for line in lines)
PY

mkdir -p "$evidence/publisher-release"
cp "$publisher_release_dir/adapter-release.json" \
  "$evidence/publisher-release/adapter-release.json"
cp "$publisher_release_dir/SHA256SUMS" "$evidence/publisher-release/SHA256SUMS"
cp "$wheel" "$evidence/publisher-release/$(basename "$wheel")"

python -m pip download --dest "$wheelhouse" "$wheel"
export PIP_NO_INDEX=1
export PIP_FIND_LINKS="$wheelhouse"

set +e
orbitfabric adapter lock check "$lock" --json > "$evidence/before-check.json"
before_status=$?
set -e
test "$before_status" -ne 0

python - <<'PY'
import json
from pathlib import Path

report = json.loads(
    Path("/tmp/orbitfabric-eds-cfs-release-proof/evidence/before-check.json").read_text()
)
assert report["status"] == "NOT_SATISFIED"
assert report["adapters"][0]["status"] == "MISSING"
PY

orbitfabric adapter lock install "$lock" \
  --source-coordinate "$source_coordinate" \
  --release-descriptor "$descriptor" \
  --artifact "$wheel" \
  --json | tee "$evidence/install-from-lock.json"

python - <<'PY' > "$work/install-env"
import json
from pathlib import Path

report = json.loads(
    Path("/tmp/orbitfabric-eds-cfs-release-proof/evidence/install-from-lock.json").read_text()
)
assert report["before_status"] == "MISSING"
assert report["action"] == "INSTALLED"
assert report["after_status"] == "MATCH"
assert report["installed_instance_id"]
print("INSTANCE_ID=" + report["installed_instance_id"])
PY
source "$work/install-env"

orbitfabric adapter lock check "$lock" --json | tee "$evidence/after-check.json"

python - <<'PY'
import json
from pathlib import Path

report = json.loads(
    Path("/tmp/orbitfabric-eds-cfs-release-proof/evidence/after-check.json").read_text()
)
assert report["status"] == "MATCH"
assert report["adapters"][0]["status"] == "MATCH"
PY

orbitfabric adapter lock install "$lock" \
  --source-coordinate "$source_coordinate" \
  --release-descriptor "$descriptor" \
  --artifact "$wheel" \
  --json | tee "$evidence/second-install-from-lock.json"

python - <<'PY'
import json
from pathlib import Path

report = json.loads(
    Path("/tmp/orbitfabric-eds-cfs-release-proof/evidence/second-install-from-lock.json").read_text()
)
assert report["before_status"] == "MATCH"
assert report["action"] == "NOOP"
assert report["after_status"] == "MATCH"
assert report["installed_instance_id"] is None
PY

orbitfabric adapter verify "$INSTANCE_ID" --json | tee "$evidence/verify.json"
orbitfabric adapter remove "$INSTANCE_ID" --json | tee "$evidence/remove.json"
orbitfabric adapter list --json | tee "$evidence/final-inventory.json"

python - <<'PY'
import json
from pathlib import Path

inventory = json.loads(
    Path("/tmp/orbitfabric-eds-cfs-release-proof/evidence/final-inventory.json").read_text()
)
assert inventory == []
PY

unset PIP_NO_INDEX
unset PIP_FIND_LINKS

printf '%s\n' \
  "C2 release construction: PASS" \
  "C2 Project Lock MISSING -> INSTALLED -> MATCH -> NOOP: PASS" \
  "C2 publisher release bundle excludes Project Lock: PASS"
