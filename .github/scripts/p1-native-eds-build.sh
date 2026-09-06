#!/usr/bin/env bash
set -euo pipefail

CFS_COMMIT="088b2fa828db9ff7e00733f1908e0eeb59f66ce3"
EDSLIB_COMMIT="2acc963b34f77692c6396555dcfb10ef43eb1046"
CFE_COMMIT="c5fb2b4d540bd55eb6c3707da7dd13eee679d4dd"
SAMPLE_APP_COMMIT="2f93d1a4159a02b18d67ee83342c9e96b90e23e4"
B6_SHA256="3586e1bbec5d13cff10e6310a71771e8f2b10ba1e084c681a7083ebc43e02a4e"
B8_SHA256="002f73792ac03e3b10faf9a73c593e904fb140245d5b0414bd07ae3c1f1e7517"

ADAPTER_ROOT="${GITHUB_WORKSPACE:-$(pwd)}"
RUN_ROOT="${RUNNER_TEMP:-/tmp}"
CFS_DIR="${RUN_ROOT}/orbitfabric-cfs-p1"
APP_ROOT="${RUN_ROOT}/orbitfabric-cfs-p1-apps"
APP_DIR="${APP_ROOT}/of_demo_app"
EVIDENCE_DIR="${RUN_ROOT}/orbitfabric-eds-cfs-p1-evidence"
BUILD_DIR="${CFS_DIR}/build-native_eds"
B6_SOURCE="${ADAPTER_ROOT}/tests/fixtures/p0_b6/expected.xml"
B8_GOLDEN="${ADAPTER_ROOT}/tests/fixtures/p0_b8/expected.json"
APP_SOURCE="${ADAPTER_ROOT}/examples/cfs/of_demo_app"
STAGED_EDS="${APP_DIR}/eds/of_demo.xml"
SOURCE_LIST="${BUILD_DIR}/edstool-sources-SampleMission.mk"
COMPILE_DB="${BUILD_DIR}/compile_commands.json"

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

require_file() {
  local path="$1"
  local label="$2"
  if [[ ! -f "$path" ]]; then
    echo "$label not found: $path" >&2
    return 1
  fi
  printf '%s %s\n' "$label" "$path"
}

run_positive_goal() {
  local goal="$1"
  local log="$2"
  (
    cd "$CFS_DIR"
    CFS_APP_PATH="$APP_ROOT" make "$goal"
  ) 2>&1 | tee "$EVIDENCE_DIR/$log"
}

rm -rf "$CFS_DIR" "$APP_ROOT" "$EVIDENCE_DIR"
mkdir -p "$APP_ROOT" "$EVIDENCE_DIR"

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
[[ "$(git -C "$CFS_DIR/apps/sample_app" rev-parse HEAD)" == "$SAMPLE_APP_COMMIT" ]]

cat > "$EVIDENCE_DIR/baseline.txt" <<EOF
cfs=$CFS_COMMIT
edslib=$EDSLIB_COMMIT
cfe=$CFE_COMMIT
sample_app=$SAMPLE_APP_COMMIT
b6_sha256=$B6_SHA256
b8_sha256=$B8_SHA256
EOF

printf '%s\n' "Preparing fixed external of_demo_app consumer"
cp -R "$APP_SOURCE" "$APP_DIR"
mkdir -p "$APP_DIR/eds"
cp "$B6_SOURCE" "$STAGED_EDS"
require_sha256 "$STAGED_EDS" "$B6_SHA256" "staged OF_DEMO EDS"

grep -F '#include "of_demo_eds_dictionary.h"' "$APP_DIR/fsw/src/of_demo_app.c"
grep -F '#include "of_demo_eds_dispatcher.h"' "$APP_DIR/fsw/src/of_demo_app.c"

cat >> "$CFS_DIR/sample_defs/targets.cmake" <<'EOF'

# OrbitFabric P1 disposable external application inclusion
list(APPEND MISSION_GLOBAL_APPLIST of_demo_app)
EOF

grep -F 'MISSION_GLOBAL_APPLIST of_demo_app' "$CFS_DIR/sample_defs/targets.cmake"

printf '%s\n' "Configuring complete native_eds build"
run_positive_goal native_eds.prep positive-prep.log

[[ -f "$SOURCE_LIST" ]]
grep -F "of_demo.xml" "$SOURCE_LIST"
cp "$SOURCE_LIST" "$EVIDENCE_DIR/edstool-sources-SampleMission.mk"

printf '%s\n' "Compiling complete native_eds mission"
run_positive_goal native_eds.compile positive-compile.log
require_file "$BUILD_DIR/stamp.compile" "native_eds compile stamp"

# cFS native_* is a composed build.  The top-level compile database does not
# necessarily aggregate compile commands emitted by every nested application
# build, so it is retained as optional diagnostic evidence rather than used as
# the participation gate.  Native build output plus the produced module are
# the authoritative P1 evidence for the external app.
find "$BUILD_DIR" -type f -name 'compile_commands.json' -print | sort \
  > "$EVIDENCE_DIR/compile-db-candidates.txt"
: > "$EVIDENCE_DIR/of-demo-compile-command.txt"
while IFS= read -r compile_db; do
  grep -F "of_demo_app.c" "$compile_db" >> "$EVIDENCE_DIR/of-demo-compile-command.txt" || true
done < "$EVIDENCE_DIR/compile-db-candidates.txt"

if ! grep -F 'Building C object apps/of_demo_app/' "$EVIDENCE_DIR/positive-compile.log" >/dev/null \
  || ! grep -F 'Linking C shared module of_demo_app.so' "$EVIDENCE_DIR/positive-compile.log" >/dev/null \
  || ! grep -F 'Built target of_demo_app' "$EVIDENCE_DIR/positive-compile.log" >/dev/null; then
  echo "native build log does not prove complete of_demo_app participation" >&2
  exit 1
fi
{
  grep -F 'Building C object apps/of_demo_app/' "$EVIDENCE_DIR/positive-compile.log"
  grep -F 'Linking C shared module of_demo_app.so' "$EVIDENCE_DIR/positive-compile.log"
  grep -F 'Built target of_demo_app' "$EVIDENCE_DIR/positive-compile.log"
} > "$EVIDENCE_DIR/of-demo-native-build-evidence.txt"

find "$BUILD_DIR" -type f \
  \( -name 'of_demo_app.so' -o -name 'of_demo_app' -o -name 'libof_demo_app.so' \) \
  -print | sort > "$EVIDENCE_DIR/of-demo-built-artifacts.txt"
if [[ ! -s "$EVIDENCE_DIR/of-demo-built-artifacts.txt" ]]; then
  echo "of_demo_app build artifact not found" >&2
  exit 1
fi

printf '%s\n' "Installing complete native_eds mission"
run_positive_goal native_eds.install positive-install.log
require_file "$BUILD_DIR/stamp.install" "native_eds install stamp"

find "$BUILD_DIR/exe" -type f -iname '*of_demo_app*' -print | sort \
  > "$EVIDENCE_DIR/of-demo-staged-artifacts.txt"
if [[ ! -s "$EVIDENCE_DIR/of-demo-staged-artifacts.txt" ]]; then
  echo "staged of_demo_app artifact not found" >&2
  exit 1
fi

find "$BUILD_DIR/exe" -type f -name 'core-cpu1' -print | sort \
  > "$EVIDENCE_DIR/core-cpu1-staged.txt"
if [[ ! -s "$EVIDENCE_DIR/core-cpu1-staged.txt" ]]; then
  echo "staged core-cpu1 not found" >&2
  exit 1
fi

{
  printf '%s\n' "# P1 positive build inventory"
  find "$BUILD_DIR" -type f \
    \( -iname '*of_demo*' -o -name 'core-cpu1' -o -name 'stamp.compile' -o -name 'stamp.install' \) \
    -print | sort
} > "$EVIDENCE_DIR/positive-build-inventory.txt"

require_sha256 "$STAGED_EDS" "$B6_SHA256" "staged OF_DEMO EDS after install"
require_sha256 "$B6_SOURCE" "$B6_SHA256" "retained B6 after positive build"
require_sha256 "$B8_GOLDEN" "$B8_SHA256" "retained B8 after positive build"

printf '%s\n' "Executing missing-EDS dependency negative control"
rm -rf "$BUILD_DIR"
rm -f "$STAGED_EDS"
[[ ! -e "$STAGED_EDS" ]]

set +e
(
  cd "$CFS_DIR"
  CFS_APP_PATH="$APP_ROOT" make native_eds.prep
) > >(tee "$EVIDENCE_DIR/negative-prep.log") 2>&1
negative_prep_rc=$?
set -e

if [[ "$negative_prep_rc" -ne 0 ]]; then
  printf 'failure_stage=prep\nnegative_exit_code=%s\n' "$negative_prep_rc" \
    > "$EVIDENCE_DIR/negative-control.txt"
else
  set +e
  (
    cd "$CFS_DIR"
    CFS_APP_PATH="$APP_ROOT" make native_eds.compile
  ) > >(tee "$EVIDENCE_DIR/negative-compile.log") 2>&1
  negative_compile_rc=$?
  set -e

  if [[ "$negative_compile_rc" -eq 0 ]]; then
    echo "missing-EDS dependency control unexpectedly compiled" >&2
    exit 1
  fi

  printf 'failure_stage=compile\nnegative_exit_code=%s\n' "$negative_compile_rc" \
    > "$EVIDENCE_DIR/negative-control.txt"
fi

require_sha256 "$B6_SOURCE" "$B6_SHA256" "retained B6 after negative control"
require_sha256 "$B8_GOLDEN" "$B8_SHA256" "retained B8 after negative control"

printf '%s\n' "P1 pinned native_eds build proof completed"
