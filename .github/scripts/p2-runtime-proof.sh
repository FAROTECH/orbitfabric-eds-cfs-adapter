#!/usr/bin/env bash
set -euo pipefail

CFS_COMMIT="088b2fa828db9ff7e00733f1908e0eeb59f66ce3"
EDSLIB_COMMIT="2acc963b34f77692c6396555dcfb10ef43eb1046"
CFE_COMMIT="c5fb2b4d540bd55eb6c3707da7dd13eee679d4dd"
CI_LAB_COMMIT="f5d36625336249312ee9d5815bc875e231815bb4"
TO_LAB_COMMIT="38f7312ec4c1109b8f1c0738730b6e5ac5860f05"
COMMANDLINE_TOOLS_COMMIT="d70c56ec035694c9a64b317897403266166f5d68"
B6_SHA256="afac1000713f6fdb0b15cdf71641b40c346c29fcf63ab074a934b6b7dfb969bb"

ADAPTER_ROOT="${GITHUB_WORKSPACE:-$(pwd)}"
RUN_ROOT="${RUNNER_TEMP:-/tmp}"
CFS_DIR="${RUN_ROOT}/orbitfabric-cfs-p2-runtime"
APP_ROOT="${RUN_ROOT}/orbitfabric-cfs-p2-runtime-apps"
APP_DIR="${APP_ROOT}/of_demo_app"
BUILD_DIR="${CFS_DIR}/build-native_eds"
CPU_DIR="${BUILD_DIR}/exe/cpu1"
CPU_CF_DIR="${CPU_DIR}/cf"
HOST_DIR="${BUILD_DIR}/exe/host"
EVIDENCE_DIR="${RUN_ROOT}/orbitfabric-eds-cfs-p2-runtime-evidence"
B6_SOURCE="${ADAPTER_ROOT}/tests/fixtures/p0_b6/expected.xml"
APP_SOURCE="${ADAPTER_ROOT}/examples/cfs/of_demo_app"
ALLOCATION_SCRIPT="${ADAPTER_ROOT}/.github/scripts/stage-reference-topic-allocations.sh"
STAGED_EDS="${APP_DIR}/eds/of_demo.xml"
TO_SUB_SOURCE="${CFS_DIR}/sample_defs/tables/to_lab_sub.c"
STARTUP_FILE="${CPU_CF_DIR}/cfe_es_startup.scr"
STARTUP_BASELINE="${EVIDENCE_DIR}/cfe_es_startup.without-of-demo.scr"
CFS_LOG="${EVIDENCE_DIR}/cfs-runtime.log"
TLM_LOG="${EVIDENCE_DIR}/tlm-recv.log"
TO_ENABLE_LOG="${EVIDENCE_DIR}/to-enable-command.log"
OF_ENABLE_LOG="${EVIDENCE_DIR}/of-enable-command.log"
P2B_TABLE="${EVIDENCE_DIR}/p2-b-valid-range-observation.tsv"
STARTUP_CONTROL_LOG="${EVIDENCE_DIR}/startup-control-cfs.log"

CFS_PID=""
TLM_PID=""

cleanup() {
  set +e
  if [[ -n "$CFS_PID" ]]; then
    kill "$CFS_PID" 2>/dev/null || true
    wait "$CFS_PID" 2>/dev/null || true
  fi
  if [[ -n "$TLM_PID" ]]; then
    kill "$TLM_PID" 2>/dev/null || true
    wait "$TLM_PID" 2>/dev/null || true
  fi
}
trap cleanup EXIT

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

require_executable() {
  local path="$1"
  local label="$2"
  if [[ ! -x "$path" ]]; then
    echo "$label not executable: $path" >&2
    return 1
  fi
  printf '%s %s\n' "$label" "$path"
}

wait_for_pattern() {
  local path="$1"
  local pattern="$2"
  local label="$3"
  local attempt

  for attempt in $(seq 1 40); do
    if [[ -f "$path" ]] && grep -E "$pattern" "$path" >/dev/null 2>&1; then
      printf '%s\n' "$label"
      return 0
    fi
    if [[ -n "$CFS_PID" ]] && ! kill -0 "$CFS_PID" 2>/dev/null; then
      echo "cFS exited before observing: $label" >&2
      return 1
    fi
    sleep 1
  done

  echo "timeout waiting for: $label" >&2
  return 1
}

observe_set_period() {
  local value="$1"
  local label="$2"
  local cmd_log="${EVIDENCE_DIR}/p2-b-set-period-${label}.log"
  local cfs_before
  local cmd_rc
  local host_encode="rejected"
  local sent="no"
  local dispatch="not_observed"
  local handler="no"
  local received="-"
  local new_runtime
  local attempt

  cfs_before="$(wc -l < "$CFS_LOG")"

  set +e
  (
    cd "$HOST_DIR"
    ./cmd_send -v -I OF_DEMO/CMD.PayloadSetPeriodCmd "PeriodMs=${value}"
  ) > "$cmd_log" 2>&1
  cmd_rc=$?
  set -e

  printf '%s\n' "$cmd_rc" > "${EVIDENCE_DIR}/p2-b-set-period-${label}.exit-code.txt"

  if [[ "$cmd_rc" -eq 0 ]] \
    && ! grep -F 'Option parsing failed' "$cmd_log" >/dev/null 2>&1 \
    && grep -F 'Using result from EDS encoder' "$cmd_log" >/dev/null 2>&1; then
    host_encode="accepted"
    sent="yes"

    for attempt in $(seq 1 10); do
      new_runtime="$(tail -n +$((cfs_before + 1)) "$CFS_LOG")"
      if grep -F "OF_DEMO_APP: payload.set_period dispatched through generated EDS interface PeriodMs=${value}" \
        <<<"$new_runtime" >/dev/null 2>&1; then
        dispatch="accepted"
        handler="yes"
        received="$value"
        break
      fi
      if grep -F 'OF_DEMO_APP: generated EDS dispatch rejected command' \
        <<<"$new_runtime" >/dev/null 2>&1; then
        dispatch="rejected"
        break
      fi
      if [[ -n "$CFS_PID" ]] && ! kill -0 "$CFS_PID" 2>/dev/null; then
        dispatch="runtime_exited"
        break
      fi
      sleep 1
    done
  fi

  printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\n' \
    "$value" "$cmd_rc" "$host_encode" "$sent" "$dispatch" "$handler" "$received" >> "$P2B_TABLE"

  if [[ "$value" == "1000" ]]; then
    if [[ "$host_encode" != "accepted" || "$dispatch" != "accepted" || "$handler" != "yes" || "$received" != "1000" ]]; then
      echo "P2-B valid value 1000 did not reach generated typed handler" >&2
      cat "$cmd_log" >&2 || true
      return 1
    fi
  else
    if [[ "$host_encode" == "accepted" && "$dispatch" == "not_observed" ]]; then
      echo "P2-B probe ${value} was sent but no dispatch/handler boundary was observed" >&2
      cat "$cmd_log" >&2 || true
      return 1
    fi
  fi
}

rm -rf "$CFS_DIR" "$APP_ROOT" "$EVIDENCE_DIR"
mkdir -p "$APP_ROOT" "$EVIDENCE_DIR"

require_sha256 "$B6_SOURCE" "$B6_SHA256" "retained B6"

git init -q "$CFS_DIR"
git -C "$CFS_DIR" remote add origin https://github.com/nasa/cFS.git
git -C "$CFS_DIR" fetch --depth 1 origin "$CFS_COMMIT"
git -C "$CFS_DIR" checkout -q --detach FETCH_HEAD
git -C "$CFS_DIR" submodule update --init --recursive

[[ "$(git -C "$CFS_DIR" rev-parse HEAD)" == "$CFS_COMMIT" ]]
[[ "$(git -C "$CFS_DIR/tools/eds" rev-parse HEAD)" == "$EDSLIB_COMMIT" ]]
[[ "$(git -C "$CFS_DIR/cfe" rev-parse HEAD)" == "$CFE_COMMIT" ]]
[[ "$(git -C "$CFS_DIR/apps/ci_lab" rev-parse HEAD)" == "$CI_LAB_COMMIT" ]]
[[ "$(git -C "$CFS_DIR/apps/to_lab" rev-parse HEAD)" == "$TO_LAB_COMMIT" ]]
[[ "$(git -C "$CFS_DIR/tools/commandline-tools" rev-parse HEAD)" == "$COMMANDLINE_TOOLS_COMMIT" ]]

bash "$ALLOCATION_SCRIPT" "$CFS_DIR"
cp "$CFS_DIR/sample_defs/eds/cfe-topicids.xml" "$EVIDENCE_DIR/cfe-topicids.with-of-demo.xml"

cat > "$EVIDENCE_DIR/baseline.txt" <<EOF
cfs=$CFS_COMMIT
edslib=$EDSLIB_COMMIT
cfe=$CFE_COMMIT
ci_lab=$CI_LAB_COMMIT
to_lab=$TO_LAB_COMMIT
commandline_tools=$COMMANDLINE_TOOLS_COMMIT
b6_sha256=$B6_SHA256
command_topic_ref=CFE_MISSION/OF_DEMO_CMD_TOPICID
telemetry_topic_ref=CFE_MISSION/OF_DEMO_STATUS_TLM_TOPICID
reference_command_topic_id=160
reference_telemetry_topic_id=416
EOF

cp -R "$APP_SOURCE" "$APP_DIR"
mkdir -p "$APP_DIR/eds"
cp "$B6_SOURCE" "$STAGED_EDS"
require_sha256 "$STAGED_EDS" "$B6_SHA256" "staged OF_DEMO EDS"

cat >> "$CFS_DIR/sample_defs/targets.cmake" <<'EOF'

# OrbitFabric P2 disposable external application inclusion
list(APPEND MISSION_GLOBAL_APPLIST of_demo_app)
EOF

python3 - "$TO_SUB_SOURCE" <<'PY'
from pathlib import Path
import sys

path = Path(sys.argv[1])
text = path.read_text()

include_anchor = '#include "cfe_msgids.h"\n'
include_line = '#include "cfe_core_api_base_msgids.h"\n'
if include_line not in text:
    if include_anchor not in text:
        raise SystemExit('TO_LAB subscription include anchor not found')
    text = text.replace(include_anchor, include_anchor + include_line, 1)

subscription = '        {CFE_SB_MSGID_WRAP_VALUE(CFE_PLATFORM_TLM_TOPICID_TO_MIDV(416)), {0, 0}, 1},\n'
anchor = '        /* TO_UNUSED entry to mark the end of valid MsgIds */\n'
if subscription not in text:
    if anchor not in text:
        raise SystemExit('TO_LAB subscription insertion anchor not found')
    text = text.replace(anchor, subscription + anchor, 1)

path.write_text(text)
PY

grep -F 'CFE_PLATFORM_TLM_TOPICID_TO_MIDV(416)' "$TO_SUB_SOURCE" \
  > "$EVIDENCE_DIR/to-lab-of-demo-subscription.txt"

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

{
  printf '%s\n' '# P2 runtime staged paths'
  find "$BUILD_DIR/exe" -type f \
    \( -name 'core-cpu1' -o -name 'of_demo_app.so' -o -name 'cmd_send' -o -name 'tlm_recv' -o -name 'cfe_es_startup.scr' \) \
    -print | sort
} > "$EVIDENCE_DIR/runtime-staging-inventory.txt"

require_executable "$CPU_DIR/core-cpu1" "staged core-cpu1"
require_file "$CPU_CF_DIR/of_demo_app.so" "staged of_demo_app module"
require_executable "$HOST_DIR/cmd_send" "staged EDS cmd_send"
require_executable "$HOST_DIR/tlm_recv" "staged EDS tlm_recv"
require_file "$STARTUP_FILE" "generated CPU1 startup script"

cp "$STARTUP_FILE" "$STARTUP_BASELINE"
if grep -F 'of_demo_app' "$STARTUP_BASELINE" >/dev/null 2>&1; then
  echo "generated baseline startup script unexpectedly contains of_demo_app" >&2
  exit 1
fi

cat >> "$STARTUP_FILE" <<'EOF'
CFE_APP, of_demo_app, OF_DEMO_APP_Main, OF_DEMO_APP, 55, 32768, 0x0, 0;
EOF

grep -F 'CFE_APP, of_demo_app, OF_DEMO_APP_Main' "$STARTUP_FILE" \
  > "$EVIDENCE_DIR/of-demo-startup-entry.txt"

require_sha256 "$STAGED_EDS" "$B6_SHA256" "staged OF_DEMO EDS before runtime"
require_sha256 "$B6_SOURCE" "$B6_SHA256" "retained B6 before runtime"

(
  cd "$HOST_DIR"
  timeout 45s ./tlm_recv -v
) > "$TLM_LOG" 2>&1 &
TLM_PID=$!

(
  cd "$CPU_DIR"
  stdbuf -oL -eL ./core-cpu1
) > "$CFS_LOG" 2>&1 &
CFS_PID=$!

wait_for_pattern "$CFS_LOG" 'OF_DEMO_APP: initialized with EDS CMD topic 160 and STATUS_TLM topic 416' \
  'OF_DEMO_APP runtime initialization observed'

(
  cd "$HOST_DIR"
  ./cmd_send -v -I TO_LAB/CMD.EnableOutputCmd dest_IP=127.0.0.1
) > "$TO_ENABLE_LOG" 2>&1

if grep -F 'Option parsing failed' "$TO_ENABLE_LOG" >/dev/null 2>&1 \
  || ! grep -F 'Using result from EDS encoder' "$TO_ENABLE_LOG" >/dev/null 2>&1; then
  echo "TO_LAB enable command was not encoded through EDS" >&2
  exit 1
fi

wait_for_pattern "$CFS_LOG" 'TO telemetry output enabled for IP 127\.0\.0\.1' \
  'TO_LAB telemetry output enablement observed'

(
  cd "$HOST_DIR"
  ./cmd_send -v -I OF_DEMO/CMD.PayloadEnableCmd
) > "$OF_ENABLE_LOG" 2>&1

if grep -F 'Option parsing failed' "$OF_ENABLE_LOG" >/dev/null 2>&1 \
  || ! grep -F 'Using result from EDS encoder' "$OF_ENABLE_LOG" >/dev/null 2>&1; then
  echo "OF_DEMO payload.enable command was not encoded through EDS" >&2
  exit 1
fi

wait_for_pattern "$CFS_LOG" 'OF_DEMO_APP: payload.enable dispatched through generated EDS interface' \
  'generated OF_DEMO runtime dispatch observed'
wait_for_pattern "$TLM_LOG" 'OF_DEMO/PayloadStatusTlm' \
  'EDS decoder identified OF_DEMO PayloadStatusTlm'
wait_for_pattern "$TLM_LOG" 'PayloadEnabled[[:space:]]*=[[:space:]]*(true|1)' \
  'EDS decoder observed PayloadEnabled=true'

{
  printf '%s\n' '# P2-A runtime acceptance'
  grep -F 'OF_DEMO_APP: initialized with EDS CMD topic 160 and STATUS_TLM topic 416' "$CFS_LOG"
  grep -F 'TO telemetry output enabled for IP 127.0.0.1' "$CFS_LOG"
  grep -F 'OF_DEMO_APP: payload.enable dispatched through generated EDS interface' "$CFS_LOG"
  grep -F 'Using result from EDS encoder' "$OF_ENABLE_LOG"
  grep -F 'OF_DEMO/PayloadStatusTlm' "$TLM_LOG" | tail -n 1
  grep -E 'PayloadEnabled[[:space:]]*=[[:space:]]*(true|1)' "$TLM_LOG" | tail -n 1
} > "$EVIDENCE_DIR/p2-a-acceptance.txt"

# P2-B observational typed-argument proof. Do not add application-side
# range policy here: Decision 018 requires observing the first rejecting
# boundary for the out-of-range probes.
printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\n' \
  'value' 'host_exit' 'host_encode' 'sent' 'generated_dispatch' 'typed_handler' 'received_value' > "$P2B_TABLE"

observe_set_period 1000 valid-1000
observe_set_period 99 below-min-99
observe_set_period 60001 above-max-60001

{
  printf '%s\n' '# P2-B observational ValidRange result'
  cat "$P2B_TABLE"
  printf '%s\n' '# retained EDS ValidRange'
  grep -A3 -B1 'Entry name="PeriodMs"' "$B6_SOURCE"
} > "$EVIDENCE_DIR/p2-b-acceptance.txt"

# P2-A7 startup dependency control: use the exact same built/staged image,
# but restore the generated startup script from before OF_DEMO was appended.
kill "$CFS_PID" 2>/dev/null || true
wait "$CFS_PID" 2>/dev/null || true
CFS_PID=""
kill "$TLM_PID" 2>/dev/null || true
wait "$TLM_PID" 2>/dev/null || true
TLM_PID=""

cp "$STARTUP_BASELINE" "$STARTUP_FILE"
if grep -F 'of_demo_app' "$STARTUP_FILE" >/dev/null 2>&1; then
  echo "OF_DEMO startup entry still present in startup dependency control" >&2
  exit 1
fi
require_file "$CPU_CF_DIR/of_demo_app.so" "staged of_demo_app module for startup control"

(
  cd "$CPU_DIR"
  stdbuf -oL -eL ./core-cpu1
) > "$STARTUP_CONTROL_LOG" 2>&1 &
CFS_PID=$!

wait_for_pattern "$STARTUP_CONTROL_LOG" 'CFE_ES_Main: CFE_ES_Main entering OPERATIONAL state' \
  'startup control cFS operational state observed'
sleep 2

if ! kill -0 "$CFS_PID" 2>/dev/null; then
  echo "cFS did not remain operational during startup dependency control" >&2
  exit 1
fi
if grep -E 'OF_DEMO_APP|Loading file: /cf/of_demo_app\.so' "$STARTUP_CONTROL_LOG" >/dev/null 2>&1; then
  echo "OF_DEMO unexpectedly started when startup inclusion was omitted" >&2
  exit 1
fi

{
  printf '%s\n' '# P2-A startup dependency control'
  printf '%s\n' 'same_built_staged_image=true'
  printf '%s\n' 'of_demo_app_module_staged=true'
  printf '%s\n' 'of_demo_startup_entry_present=false'
  grep -F 'CFE_ES_Main: CFE_ES_Main entering OPERATIONAL state' "$STARTUP_CONTROL_LOG" | tail -n 1
  printf '%s\n' 'of_demo_runtime_initialization_observed=false'
} > "$EVIDENCE_DIR/p2-a-startup-control.txt"

kill "$CFS_PID" 2>/dev/null || true
wait "$CFS_PID" 2>/dev/null || true
CFS_PID=""

require_sha256 "$B6_SOURCE" "$B6_SHA256" "retained B6 after runtime"

printf '%s\n' "P2-A regression and P2-B typed ValidRange observation completed"
