#!/usr/bin/env bash
set -euo pipefail

CFS_COMMIT="088b2fa828db9ff7e00733f1908e0eeb59f66ce3"
EDSLIB_COMMIT="2acc963b34f77692c6396555dcfb10ef43eb1046"
CFE_COMMIT="c5fb2b4d540bd55eb6c3707da7dd13eee679d4dd"
SAMPLE_APP_COMMIT="2f93d1a4159a02b18d67ee83342c9e96b90e23e4"
CI_LAB_COMMIT="f5d36625336249312ee9d5815bc875e231815bb4"
TO_LAB_COMMIT="38f7312ec4c1109b8f1c0738730b6e5ac5860f05"
COMMANDLINE_TOOLS_COMMIT="d70c56ec035694c9a64b317897403266166f5d68"
B6_SHA256="e068223bd996321a46a9a276ed7cb64c215d04d11fccb1cf416eaf5225ad887b"

ADAPTER_ROOT="${GITHUB_WORKSPACE:-$(pwd)}"
RUN_ROOT="${RUNNER_TEMP:-/tmp}"
CFS_DIR="${RUN_ROOT}/orbitfabric-cfs-p2-probe"
APP_ROOT="${RUN_ROOT}/orbitfabric-cfs-p2-probe-apps"
APP_DIR="${APP_ROOT}/of_demo_app"
BUILD_DIR="${CFS_DIR}/build-native_eds"
EVIDENCE_DIR="${RUN_ROOT}/orbitfabric-eds-cfs-p2-probe-evidence"
GENERATED_DIR="${EVIDENCE_DIR}/generated"
B6_SOURCE="${ADAPTER_ROOT}/tests/fixtures/p0_b6/expected.xml"
APP_SOURCE="${ADAPTER_ROOT}/examples/cfs/of_demo_app"
STAGED_EDS="${APP_DIR}/eds/of_demo.xml"

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

rm -rf "$CFS_DIR" "$APP_ROOT" "$EVIDENCE_DIR"
mkdir -p "$APP_ROOT" "$GENERATED_DIR"

require_sha256 "$B6_SOURCE" "$B6_SHA256" "retained B6"

git init -q "$CFS_DIR"
git -C "$CFS_DIR" remote add origin https://github.com/nasa/cFS.git
git -C "$CFS_DIR" fetch --depth 1 origin "$CFS_COMMIT"
git -C "$CFS_DIR" checkout -q --detach FETCH_HEAD
git -C "$CFS_DIR" submodule update --init --recursive

[[ "$(git -C "$CFS_DIR" rev-parse HEAD)" == "$CFS_COMMIT" ]]
[[ "$(git -C "$CFS_DIR/tools/eds" rev-parse HEAD)" == "$EDSLIB_COMMIT" ]]
[[ "$(git -C "$CFS_DIR/cfe" rev-parse HEAD)" == "$CFE_COMMIT" ]]
[[ "$(git -C "$CFS_DIR/apps/sample_app" rev-parse HEAD)" == "$SAMPLE_APP_COMMIT" ]]
[[ "$(git -C "$CFS_DIR/apps/ci_lab" rev-parse HEAD)" == "$CI_LAB_COMMIT" ]]
[[ "$(git -C "$CFS_DIR/apps/to_lab" rev-parse HEAD)" == "$TO_LAB_COMMIT" ]]
[[ "$(git -C "$CFS_DIR/tools/commandline-tools" rev-parse HEAD)" == "$COMMANDLINE_TOOLS_COMMIT" ]]

cat > "$EVIDENCE_DIR/baseline.txt" <<EOF
cfs=$CFS_COMMIT
edslib=$EDSLIB_COMMIT
cfe=$CFE_COMMIT
sample_app=$SAMPLE_APP_COMMIT
ci_lab=$CI_LAB_COMMIT
to_lab=$TO_LAB_COMMIT
commandline_tools=$COMMANDLINE_TOOLS_COMMIT
b6_sha256=$B6_SHA256
EOF

cp -R "$APP_SOURCE" "$APP_DIR"
mkdir -p "$APP_DIR/eds"
cp "$B6_SOURCE" "$STAGED_EDS"
require_sha256 "$STAGED_EDS" "$B6_SHA256" "staged OF_DEMO EDS"

cat >> "$CFS_DIR/sample_defs/targets.cmake" <<'EOF'

# OrbitFabric P2 disposable external application inclusion
list(APPEND MISSION_GLOBAL_APPLIST of_demo_app)
EOF

(
  cd "$CFS_DIR"
  CFS_APP_PATH="$APP_ROOT" make native_eds.prep
) 2>&1 | tee "$EVIDENCE_DIR/prep.log"

(
  cd "$CFS_DIR"
  CFS_APP_PATH="$APP_ROOT" make native_eds.compile
) 2>&1 | tee "$EVIDENCE_DIR/compile.log"

(
  cd "$CFS_DIR"
  CFS_APP_PATH="$APP_ROOT" make native_eds.install
) 2>&1 | tee "$EVIDENCE_DIR/install.log"

find "$BUILD_DIR" -type f -name 'of_demo_eds_*.h' -print | sort \
  > "$EVIDENCE_DIR/generated-api-files.txt"

if [[ ! -s "$EVIDENCE_DIR/generated-api-files.txt" ]]; then
  echo "no OF_DEMO generated API headers discovered" >&2
  exit 1
fi

while IFS= read -r header; do
  cp "$header" "$GENERATED_DIR/$(basename "$header")"
done < "$EVIDENCE_DIR/generated-api-files.txt"

find "$BUILD_DIR/exe" -type f \( -name 'cmd_send' -o -name 'tlm_recv' \) -print | sort \
  > "$EVIDENCE_DIR/host-tools.txt"

if ! grep -q '/cmd_send$' "$EVIDENCE_DIR/host-tools.txt"; then
  echo "EDS-enabled cmd_send not staged" >&2
  exit 1
fi
if ! grep -q '/tlm_recv$' "$EVIDENCE_DIR/host-tools.txt"; then
  echo "EDS-enabled tlm_recv not staged" >&2
  exit 1
fi

grep -hE 'EdsDispatch_EdsComponent_OF_DEMO|DispatchTable_EdsComponent_OF_DEMO|PayloadEnableCmd|PayloadSetPeriodCmd' \
  "$GENERATED_DIR"/*.h > "$EVIDENCE_DIR/of-demo-dispatch-symbols.raw" || true
if [[ ! -s "$EVIDENCE_DIR/of-demo-dispatch-symbols.raw" ]]; then
  echo "OF_DEMO dispatcher symbols were not discoverable from generated headers" >&2
  exit 1
fi
{
  printf '%s\n' '# OF_DEMO generated dispatcher symbols'
  cat "$EVIDENCE_DIR/of-demo-dispatch-symbols.raw"
} > "$EVIDENCE_DIR/of-demo-dispatch-symbols.txt"
rm "$EVIDENCE_DIR/of-demo-dispatch-symbols.raw"

{
  printf '%s\n' '# OF_DEMO generated typedef symbols'
  grep -hE 'PayloadEnableCmd|PayloadSetPeriod|PayloadStatusTlm|OF_DEMO' \
    "$GENERATED_DIR"/*.h || true
} > "$EVIDENCE_DIR/of-demo-type-symbols.txt"

require_sha256 "$B6_SOURCE" "$B6_SHA256" "retained B6 after probe"

printf '%s\n' "P2 generated API probe completed"
