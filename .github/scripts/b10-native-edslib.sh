#!/usr/bin/env bash
set -euo pipefail

CFS_COMMIT="088b2fa828db9ff7e00733f1908e0eeb59f66ce3"
EDSLIB_COMMIT="2acc963b34f77692c6396555dcfb10ef43eb1046"
CFE_COMMIT="c5fb2b4d540bd55eb6c3707da7dd13eee679d4dd"
B6_SHA256="afac1000713f6fdb0b15cdf71641b40c346c29fcf63ab074a934b6b7dfb969bb"
B8_SHA256="39189455279652fd6f15694dd464539d2ad3f000dfdb12baf3f7a7fae8cbde34"

ADAPTER_ROOT="${GITHUB_WORKSPACE:-$(pwd)}"
RUN_ROOT="${RUNNER_TEMP:-/tmp}"
CFS_DIR="${RUN_ROOT}/orbitfabric-cfs-b10"
EVIDENCE_DIR="${RUN_ROOT}/orbitfabric-eds-cfs-b10-evidence"
B6_SOURCE="${ADAPTER_ROOT}/tests/fixtures/p0_b6/expected.xml"
B8_GOLDEN="${ADAPTER_ROOT}/tests/fixtures/p0_b8/expected.json"
ALLOCATION_SCRIPT="${ADAPTER_ROOT}/.github/scripts/stage-reference-topic-allocations.sh"
TOPIC_REGISTRY="${CFS_DIR}/sample_defs/eds/cfe-topicids.xml"
STAGED_XML="${CFS_DIR}/sample_defs/eds/orbitfabric-mission.xml"
BUILD_DIR="${CFS_DIR}/build-native_eds"
SOURCE_LIST="${BUILD_DIR}/edstool-sources-SampleMission.mk"
STAMP="${BUILD_DIR}/obj/edstool-execute-SampleMission.stamp"

sha256_file() {
  sha256sum "$1" | awk '{print $1}'
}

require_sha256() {
  local path="$1"
  local expected="$2"
  local label="$3"
  local actual
  actual="$(sha256_file "$path")"
  if [[ "$actual" != "$expected" ]]; then
    echo "$label SHA-256 mismatch: expected $expected, got $actual" >&2
    return 1
  fi
  printf '%s %s\n' "$actual" "$path"
}

run_edstool() {
  local log="$1"
  (
    cd "$CFS_DIR"
    cmake --build build-native_eds --target edstool-execute -- -j2
  ) 2>&1 | tee "$log"
}

rm -rf "$CFS_DIR" "$EVIDENCE_DIR"
mkdir -p "$EVIDENCE_DIR"

require_sha256 "$B6_SOURCE" "$B6_SHA256" "retained B6"
require_sha256 "$B8_GOLDEN" "$B8_SHA256" "retained B8"

printf '%s\n' "Cloning exact NASA cFS baseline"
git init -q "$CFS_DIR"
git -C "$CFS_DIR" remote add origin https://github.com/nasa/cFS.git
git -C "$CFS_DIR" fetch --depth 1 origin "$CFS_COMMIT"
git -C "$CFS_DIR" checkout -q --detach FETCH_HEAD
[[ "$(git -C "$CFS_DIR" rev-parse HEAD)" == "$CFS_COMMIT" ]]

git -C "$CFS_DIR" submodule update --init --recursive
[[ "$(git -C "$CFS_DIR/tools/eds" rev-parse HEAD)" == "$EDSLIB_COMMIT" ]]
[[ "$(git -C "$CFS_DIR/cfe" rev-parse HEAD)" == "$CFE_COMMIT" ]]

bash "$ALLOCATION_SCRIPT" "$CFS_DIR"
cp "$TOPIC_REGISTRY" "$EVIDENCE_DIR/cfe-topicids.with-of-demo.xml"

cat > "$EVIDENCE_DIR/baseline.txt" <<EOF
cfs=$CFS_COMMIT
edslib=$EDSLIB_COMMIT
cfe=$CFE_COMMIT
b6_sha256=$B6_SHA256
b8_sha256=$B8_SHA256
command_topic_ref=CFE_MISSION/OF_DEMO_CMD_TOPICID
telemetry_topic_ref=CFE_MISSION/OF_DEMO_STATUS_TLM_TOPICID
reference_command_topic_id=160
reference_telemetry_topic_id=416
EOF

cp "$B6_SOURCE" "$STAGED_XML"
require_sha256 "$STAGED_XML" "$B6_SHA256" "staged B6"
grep -F 'initialValue="${CFE_MISSION/OF_DEMO_CMD_TOPICID}"' "$STAGED_XML"
grep -F 'initialValue="${CFE_MISSION/OF_DEMO_STATUS_TLM_TOPICID}"' "$STAGED_XML"

printf '%s\n' "Configuring native_eds"
(
  cd "$CFS_DIR"
  make native_eds.prep
) 2>&1 | tee "$EVIDENCE_DIR/native-eds-prep.log"

[[ -f "$SOURCE_LIST" ]]
grep -F "orbitfabric-mission.xml" "$SOURCE_LIST"
cp "$SOURCE_LIST" "$EVIDENCE_DIR/edstool-sources-SampleMission.mk"

printf '%s\n' "Executing native mission EDS toolchain"
run_edstool "$EVIDENCE_DIR/edstool-positive.log"

[[ -f "$STAMP" ]]
grep -Eq 'SEDS tool complete -- 0 error\(s\)' "$EVIDENCE_DIR/edstool-positive.log"
require_sha256 "$STAGED_XML" "$B6_SHA256" "staged B6 after positive native processing"

{
  printf '%s\n' "# Native B10 generated inventory"
  find "$BUILD_DIR" -maxdepth 4 -type f \
    \( -path '*/export_eds/*' -o -name '*eds*' -o -name '*.stamp' \) \
    -print | sort
} > "$EVIDENCE_DIR/native-generated-inventory.txt"

printf '%s\n' "Executing unresolved mission-allocation control"
python3 - "$TOPIC_REGISTRY" <<'PY'
from pathlib import Path
import re
import sys

path = Path(sys.argv[1])
text = path.read_text(encoding="utf-8")
pattern = re.compile(
    r'\n\s*<Define name="OF_DEMO_STATUS_TLM_TOPICID"\s*\n'
    r'\s*value="\$\{CFE_MISSION/TELEMETRY_BASE_TOPICID\} \+ 151"/>\n'
)
updated, count = pattern.subn("\n", text, count=1)
if count != 1:
    raise SystemExit("reference telemetry allocation definition was not found exactly once")
path.write_text(updated, encoding="utf-8")
PY

if grep -F 'name="OF_DEMO_STATUS_TLM_TOPICID"' "$TOPIC_REGISTRY" >/dev/null 2>&1; then
  echo "telemetry allocation definition was not removed" >&2
  exit 1
fi
grep -F '${CFE_MISSION/OF_DEMO_STATUS_TLM_TOPICID}' "$STAGED_XML"
rm -f "$STAMP"
set +e
(
  cd "$CFS_DIR"
  cmake --build build-native_eds --target edstool-execute -- -j2
) > >(tee "$EVIDENCE_DIR/edstool-missing-allocation.log") 2>&1
missing_allocation_rc=$?
set -e
if [[ "$missing_allocation_rc" -eq 0 ]]; then
  echo "missing mission-allocation control unexpectedly succeeded" >&2
  exit 1
fi
printf 'missing_symbol=CFE_MISSION/OF_DEMO_STATUS_TLM_TOPICID\nexit_code=%s\n' \
  "$missing_allocation_rc" > "$EVIDENCE_DIR/missing-allocation-control.txt"

printf '%s\n' "Restoring mission allocation registry after negative control"
cp "$EVIDENCE_DIR/cfe-topicids.with-of-demo.xml" "$TOPIC_REGISTRY"
rm -f "$STAMP"
run_edstool "$EVIDENCE_DIR/edstool-restored-allocation.log"
grep -Eq 'SEDS tool complete -- 0 error\(s\)' "$EVIDENCE_DIR/edstool-restored-allocation.log"

printf '%s\n' "Executing native invalid-reference control"
python3 - "$STAGED_XML" <<'PY'
from pathlib import Path
import sys

path = Path(sys.argv[1])
data = path.read_text(encoding="utf-8")
old = 'CFE_HDR/CommandHeader'
new = 'CFE_HDR/OrbitFabricMissingHeader'
if data.count(old) != 1:
    raise SystemExit(f"expected exactly one {old!r} occurrence")
path.write_text(data.replace(old, new, 1), encoding="utf-8")
PY

grep -F "CFE_HDR/OrbitFabricMissingHeader" "$STAGED_XML"
rm -f "$STAMP"
set +e
(
  cd "$CFS_DIR"
  cmake --build build-native_eds --target edstool-execute -- -j2
) > >(tee "$EVIDENCE_DIR/edstool-negative.log") 2>&1
negative_rc=$?
set -e
if [[ "$negative_rc" -eq 0 ]]; then
  echo "native invalid-reference control unexpectedly succeeded" >&2
  exit 1
fi
printf 'negative_exit_code=%s\n' "$negative_rc" > "$EVIDENCE_DIR/negative-control.txt"

require_sha256 "$B6_SOURCE" "$B6_SHA256" "retained B6 after native controls"
require_sha256 "$B8_GOLDEN" "$B8_SHA256" "retained B8 after native controls"

printf '%s\n' "B10 native EdsLib validation harness completed"
