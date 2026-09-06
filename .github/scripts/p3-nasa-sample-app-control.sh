#!/usr/bin/env bash
set -euo pipefail

RUN_ROOT="${RUNNER_TEMP:-/tmp}"
CFS_DIR="${RUN_ROOT}/orbitfabric-cfs-p2-runtime"
BUILD_DIR="${CFS_DIR}/build-native_eds"
CPU_DIR="${BUILD_DIR}/exe/cpu1"
CPU_CF_DIR="${CPU_DIR}/cf"
HOST_DIR="${BUILD_DIR}/exe/host"
STARTUP_FILE="${CPU_CF_DIR}/cfe_es_startup.scr"
P3_EVIDENCE_DIR="${RUN_ROOT}/orbitfabric-eds-cfs-p3-conformance-evidence"
RUNTIME_LOG="${P3_EVIDENCE_DIR}/nasa-sample-app-runtime.log"
VALID_LOG="${P3_EVIDENCE_DIR}/nasa-sample-app-valid-noop.log"
UNKNOWN_LOG="${P3_EVIDENCE_DIR}/nasa-sample-app-unknown-fc.log"
RESULT_FILE="${P3_EVIDENCE_DIR}/nasa-sample-app-control.txt"
UNKNOWN_FUNCTION_CODE="127"
UNUSED_UDP_PORT="65534"

CFS_PID=""

cleanup() {
  set +e
  if [[ -n "$CFS_PID" ]]; then
    kill "$CFS_PID" 2>/dev/null || true
    wait "$CFS_PID" 2>/dev/null || true
  fi
}
trap cleanup EXIT

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

mkdir -p "$P3_EVIDENCE_DIR"

if [[ ! -x "$CPU_DIR/core-cpu1" || ! -x "$HOST_DIR/cmd_send" || ! -f "$STARTUP_FILE" ]]; then
  {
    printf '%s\n' '# NASA sample_app P3 control'
    printf '%s\n' 'classification=NOT_RUN'
    printf '%s\n' 'reason=P2-built runtime image unavailable'
  } > "$RESULT_FILE"
  exit 0
fi

# Remove OF_DEMO from startup and exercise only the stock NASA sample_app
# command interface on the same pinned native_eds SampleMission.
tmp_startup="${STARTUP_FILE}.p3-sample-app"
grep -v 'of_demo_app' "$STARTUP_FILE" > "$tmp_startup"
mv "$tmp_startup" "$STARTUP_FILE"

(
  cd "$CPU_DIR"
  stdbuf -oL -eL ./core-cpu1
) > "$RUNTIME_LOG" 2>&1 &
CFS_PID=$!

wait_for_pattern "$RUNTIME_LOG" 'Sample App Initialized' 'NASA sample_app initialization observed'
wait_for_pattern "$RUNTIME_LOG" 'CFE_ES_Main: CFE_ES_Main entering OPERATIONAL state' 'NASA SampleMission operational state observed'

# Encode the stock NoopCmd through the nominal EDS encoder only to derive the
# exact packet/APID. Send it to an unused UDP port so it does not enter the
# runtime and cannot consume/filter the NOOP event that the unknown probe may
# accidentally trigger.
(
  cd "$HOST_DIR"
  ./cmd_send -v -P "$UNUSED_UDP_PORT" -I SAMPLE_APP/CMD.NoopCmd
) > "$VALID_LOG" 2>&1

if ! grep -F 'Using result from EDS encoder' "$VALID_LOG" >/dev/null 2>&1; then
  echo "NASA sample_app APID derivation did not use EDS encoder" >&2
  cat "$VALID_LOG" >&2
  exit 1
fi

SAMPLE_APID="$(python3 - "$VALID_LOG" <<'PY'
from pathlib import Path
import re
import sys
text = Path(sys.argv[1]).read_text()
m = re.search(r'^0x0*00:\s+([0-9A-Fa-f]{2})\s+([0-9A-Fa-f]{2})', text, re.M)
if not m:
    raise SystemExit('positive packet hexdump not found')
packet_id = (int(m.group(1), 16) << 8) | int(m.group(2), 16)
print(hex(packet_id & 0x07ff))
PY
)"

UNKNOWN_BEFORE="$(wc -l < "$RUNTIME_LOG")"
(
  cd "$HOST_DIR"
  ./cmd_send -v -Q cfsv1 -A "$SAMPLE_APID" -C "$UNKNOWN_FUNCTION_CODE"
) > "$UNKNOWN_LOG" 2>&1

if ! grep -F 'Using result from PassThrough encoder' "$UNKNOWN_LOG" >/dev/null 2>&1; then
  echo "NASA sample_app unknown-FC control did not use PassThrough encoder" >&2
  cat "$UNKNOWN_LOG" >&2
  exit 1
fi
if grep -F 'Using result from EDS encoder' "$UNKNOWN_LOG" >/dev/null 2>&1; then
  echo "NASA sample_app unknown-FC control unexpectedly used EDS encoder" >&2
  exit 1
fi

CLASSIFICATION="NO_OBSERVABLE_RESULT"
NEW_RUNTIME=""
for attempt in $(seq 1 20); do
  NEW_RUNTIME="$(tail -n +$((UNKNOWN_BEFORE + 1)) "$RUNTIME_LOG")"

  if grep -F 'SAMPLE: NOOP command' <<<"$NEW_RUNTIME" >/dev/null 2>&1; then
    CLASSIFICATION="UNKNOWN_FC_DISPATCHED_AS_NOOP"
    break
  fi

  if grep -F 'SAMPLE: Invalid ground command code: CC = 127' <<<"$NEW_RUNTIME" >/dev/null 2>&1; then
    CLASSIFICATION="UNKNOWN_FC_REJECTED_BY_SAMPLE_APP_DISPATCH"
    break
  fi

  if ! kill -0 "$CFS_PID" 2>/dev/null; then
    CLASSIFICATION="RUNTIME_EXITED"
    break
  fi

  sleep 1
done

{
  printf '%s\n' '# NASA sample_app P3 control'
  printf '%s\n' 'orbitfabric_app_started=false'
  printf '%s\n' 'apid_derivation=SAMPLE_APP/CMD.NoopCmd encoded by EDS to unused UDP port'
  printf 'derived_sample_app_apid=%s\n' "$SAMPLE_APID"
  printf 'unknown_function_code=%s\n' "$UNKNOWN_FUNCTION_CODE"
  printf '%s\n' 'unknown_probe_encoder=PassThrough'
  printf 'classification=%s\n' "$CLASSIFICATION"
  printf '%s\n' '# relevant runtime evidence after unknown probe'
  grep -E 'SAMPLE: NOOP command|SAMPLE: Invalid ground command code' <<<"$NEW_RUNTIME" || true
} > "$RESULT_FILE"

printf 'NASA sample_app P3 control classification: %s\n' "$CLASSIFICATION"

kill "$CFS_PID" 2>/dev/null || true
wait "$CFS_PID" 2>/dev/null || true
CFS_PID=""
