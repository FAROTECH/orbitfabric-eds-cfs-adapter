#!/usr/bin/env bash
set -euo pipefail

if [[ "${GITHUB_ACTIONS:-}" != "true" ]]; then
  echo "This destructive isolation proof must run only inside GitHub Actions." >&2
  exit 2
fi

root="${GITHUB_WORKSPACE:?GITHUB_WORKSPACE is required}"
core="$root/_orbitfabric_core"
work="/tmp/orbitfabric-eds-cfs-installed-lifecycle"
state="$work/state"
evidence="$work/evidence"
wheelhouse="$work/wheelhouse"
release_dir="$work/release"
core_input="$work/core-input"
output="$work/output"
reference="$work/reference"
mission_workspace="/tmp/orbitfabric-eds-cfs-p0-mission"

export ORBITFABRIC_STATE_DIR="$state"

rm -rf "$work" "$mission_workspace"
mkdir -p "$evidence" "$wheelhouse" "$release_dir" "$reference" "$mission_workspace"

cd "$root"
rm -rf dist
python -m build --wheel
wheel="$(realpath "$(find "$root/dist" -maxdepth 1 -name '*.whl' -print -quit)")"
test -n "$wheel"

cp -a tests/fixtures/p0_b1/mission/. "$mission_workspace/"
cp tests/fixtures/p0_b3/profile.yaml "$reference/profile.yaml"
cp tests/fixtures/p0_b6/expected.xml "$reference/expected.xml"
cp tests/fixtures/p0_b7/expected.json "$reference/expected-traceability.json"
cp tests/fixtures/p0_b8/expected.json "$reference/expected-result.json"

orbitfabric export integration-input-set "$mission_workspace" \
  --output-dir "$core_input"
test -f "$core_input/integration_input_manifest.json"

python tools/build_release_bundle.py \
  --wheel "$wheel" \
  --authority github.com/FAROTECH \
  --publisher orbitfabric \
  --name eds-cfs \
  --output-dir "$release_dir" \
  --release-only

descriptor="$release_dir/adapter-release.json"
descriptor_sha="$(sha256sum "$descriptor" | awk '{print $1}')"
cp "$descriptor" "$evidence/release-descriptor.json"
cp "$core_input/integration_input_manifest.json" "$evidence/core-input-manifest.json"
sha256sum "$wheel" > "$evidence/adapter-wheel.sha256"

DESCRIPTOR="$descriptor" python - <<'PY'
import json
import os
from pathlib import Path

payload = json.loads(Path(os.environ["DESCRIPTOR"]).read_text(encoding="utf-8"))
assert payload["kind"] == "orbitfabric.adapter_release"
assert payload["source_coordinate"] == {
    "authority": "github.com/FAROTECH",
    "publisher": "orbitfabric",
    "name": "eds-cfs",
}
assert payload["release_version"] == "0.1.0.dev0"
assert len(payload["artifacts"]) == 1
assert payload["artifacts"][0]["artifact_type"] == "python-wheel"
PY

python -m pip download --dest "$wheelhouse" "$wheel"
test -n "$(find "$wheelhouse" -maxdepth 1 -type f -print -quit)"

export PIP_NO_INDEX=1
export PIP_FIND_LINKS="$wheelhouse"
orbitfabric adapter install "$descriptor" \
  --artifact "$wheel" \
  --descriptor-sha256 "$descriptor_sha" \
  --json | tee "$evidence/install.json"
unset PIP_NO_INDEX
unset PIP_FIND_LINKS

EVIDENCE="$evidence" python - <<'PY' > "$work/install-env"
import json
import os
from pathlib import Path

record = json.loads((Path(os.environ["EVIDENCE"]) / "install.json").read_text(encoding="utf-8"))
assert record["backend_id"] == "python-wheel-managed-env"
assert Path(record["execution_argv_prefix"][0]).is_absolute()
assert Path(record["manifest_path"]).is_file()
print("INSTANCE_ID=" + record["instance_id"])
print("INSTALLED_MANIFEST=" + record["manifest_path"])
print("EXECUTABLE=" + record["execution_argv_prefix"][0])
PY
source "$work/install-env"

rm -f "$wheel" "$descriptor"
rm -rf "$wheelhouse"
rm -rf "$root/src"
test ! -e "$wheel"
test ! -e "$descriptor"
test ! -d "$wheelhouse"
test ! -d "$root/src"

cd /tmp
PYTHONPATH= orbitfabric adapter verify "$INSTANCE_ID" --json \
  | tee "$evidence/verify.json"

EVIDENCE="$evidence" python - <<'PY'
import json
import os
from pathlib import Path

report = json.loads((Path(os.environ["EVIDENCE"]) / "verify.json").read_text(encoding="utf-8"))
for name in (
    "release_descriptor_integrity",
    "manifest_integrity",
    "manifest_conformance",
    "execution_binding",
    "backend_materialization",
):
    assert report[name]["status"] == "PASS", (name, report[name])
PY

rm -rf "$output"
PYTHONPATH= orbitfabric adapter execute "$INSTANCE_ID" \
  --operation eds_cfs_projection \
  --input-set-manifest "$core_input/integration_input_manifest.json" \
  --profile "$reference/profile.yaml" \
  --output-dir "$output" \
  --json | tee "$evidence/execution.json"

python -m orbitfabric.conformance.integration_contracts result \
  "$INSTALLED_MANIFEST" \
  "$output/integration_result.json"

cmp -s "$output/eds/mission.xml" "$reference/expected.xml"
cmp -s "$output/traceability.json" "$reference/expected-traceability.json"
cmp -s "$output/integration_result.json" "$reference/expected-result.json"

OUTPUT="$output" REFERENCE="$reference" python - <<'PY'
import hashlib
import json
import os
from pathlib import Path

output = Path(os.environ["OUTPUT"])
reference = Path(os.environ["REFERENCE"])
expected_files = {
    "eds/mission.xml",
    "traceability.json",
    "integration_result.json",
}
actual_files = {
    path.relative_to(output).as_posix()
    for path in output.rglob("*")
    if path.is_file()
}
assert actual_files == expected_files

result = json.loads((output / "integration_result.json").read_text(encoding="utf-8"))
assert result["result"] == "succeeded"
assert result["operation"] == {"id": "eds_cfs_projection"}
assert result["adapter"] == {"id": "orbitfabric-eds-cfs", "version": "0.1.0.dev0"}
assert result["inputs"]["operation_inputs"] == []
assert result["inputs"]["profile"]["sha256"] == hashlib.sha256(
    (reference / "profile.yaml").read_bytes()
).hexdigest()

expected_digests = {
    "eds/mission.xml": "afac1000713f6fdb0b15cdf71641b40c346c29fcf63ab074a934b6b7dfb969bb",
    "traceability.json": "3480f57f0461839ec66b62ded192be2aac71f2446b5baa869e82f410256a20f8",
    "integration_result.json": "38705931d3c89b16522c94ff180dcaa349ded32f8d51cab04d2b85389a274322",
}
for relative, expected in expected_digests.items():
    actual = hashlib.sha256((output / relative).read_bytes()).hexdigest()
    assert actual == expected, (relative, actual)

print("C1 installed lifecycle projection bytes: PASS")
PY

cp "$output/eds/mission.xml" "$evidence/mission.xml"
cp "$output/traceability.json" "$evidence/traceability.json"
cp "$output/integration_result.json" "$evidence/integration-result.json"
sha256sum \
  "$output/eds/mission.xml" \
  "$output/traceability.json" \
  "$output/integration_result.json" \
  > "$evidence/installed-output.sha256"

orbitfabric adapter remove "$INSTANCE_ID" --json | tee "$evidence/remove.json"
orbitfabric adapter list --json | tee "$evidence/final-inventory.json"

EVIDENCE="$evidence" python - <<'PY'
import json
import os
from pathlib import Path

inventory = json.loads(
    (Path(os.environ["EVIDENCE"]) / "final-inventory.json").read_text(encoding="utf-8")
)
assert inventory == []
PY

printf '%s\n' \
  "C1 installed lifecycle: PASS" \
  "installed execution independent of checkout src/: PASS" \
  "B6 installed bytes match retained golden: PASS" \
  "B7 installed bytes match retained golden: PASS" \
  "B8 installed bytes match retained golden: PASS"
