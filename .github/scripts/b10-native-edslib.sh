#!/usr/bin/env bash
set -euo pipefail

CFS_COMMIT="088b2fa828db9ff7e00733f1908e0eeb59f66ce3"
EDSLIB_COMMIT="2acc963b34f77692c6396555dcfb10ef43eb1046"
CFE_COMMIT="c5fb2b4d540bd55eb6c3707da7dd13eee679d4dd"
B6_SHA256="3586e1bbec5d13cff10e6310a71771e8f2b10ba1e084c681a7083ebc43e02a4e"
B8_SHA256="002f73792ac03e3b10faf9a73c593e904fb140245d5b0414bd07ae3c1f1e7517"

ADAPTER_ROOT="${GITHUB_WORKSPACE:-$(pwd)}"
RUN_ROOT="${RUNNER_TEMP:-/tmp}"
CFS_DIR="${RUN_ROOT}/orbitfabric-cfs-b10"
EVIDENCE_DIR="${RUN_ROOT}/orbitfabric-eds-cfs-b10-evidence"
B6_SOURCE="${ADAPTER_ROOT}/tests/fixtures/p0_b6/expected.xml"
B8_GOLDEN="${ADAPTER_ROOT}/tests/fixtures/p0_b8/expected.json"
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

cat > "$EVIDENCE_DIR/baseline.txt" <<EOF
cfs=$CFS_COMMIT
edslib=$EDSLIB_COMMIT
cfe=$CFE_COMMIT
b6_sha256=$B6_SHA256
b8_sha256=$B8_SHA256
EOF

cp "$B6_SOURCE" "$STAGED_XML"
require_sha256 "$STAGED_XML" "$B6_SHA256" "staged B6"

printf '%s\n' "Configuring native_eds"
(
  cd "$CFS_DIR"
  make native_eds.prep
) 2>&1 | tee "$EVIDENCE_DIR/native-eds-prep.log"

[[ -f "$SOURCE_LIST" ]]
grep -F "orbitfabric-mission.xml" "$SOURCE_LIST"
cp "$SOURCE_LIST" "$EVIDENCE_DIR/edstool-sources-SampleMission.mk"

printf '%s\n' "Executing native mission EDS toolchain"
(
  cd "$CFS_DIR"
  cmake --build build-native_eds --target edstool-execute -- -j2
) 2>&1 | tee "$EVIDENCE_DIR/edstool-positive.log"

[[ -f "$STAMP" ]]
grep -Eq 'SEDS tool complete -- 0 error\(s\)' "$EVIDENCE_DIR/edstool-positive.log"
require_sha256 "$STAGED_XML" "$B6_SHA256" "staged B6 after positive native processing"

{
  printf '%s\n' "# Native B10 generated inventory"
  find "$BUILD_DIR" -maxdepth 4 -type f \
    \( -path '*/export_eds/*' -o -name '*eds*' -o -name '*.stamp' \) \
    -print | sort
} > "$EVIDENCE_DIR/native-generated-inventory.txt"

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

require_sha256 "$B6_SOURCE" "$B6_SHA256" "retained B6 after native control"
require_sha256 "$B8_GOLDEN" "$B8_SHA256" "retained B8 after native control"

printf '%s\n' "B10 native EdsLib validation harness completed"
