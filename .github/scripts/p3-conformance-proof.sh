#!/usr/bin/env bash
set -euo pipefail

ADAPTER_ROOT="${GITHUB_WORKSPACE:-$(pwd)}"
RUN_ROOT="${RUNNER_TEMP:-/tmp}"
P2_SCRIPT="${ADAPTER_ROOT}/.github/scripts/p2-runtime-proof.sh"
CFS_DIR="${RUN_ROOT}/orbitfabric-cfs-p2-runtime"
BUILD_DIR="${CFS_DIR}/build-native_eds"
CPU_DIR="${BUILD_DIR}/exe/cpu1"
CPU_CF_DIR="${CPU_DIR}/cf"
HOST_DIR="${BUILD_DIR}/exe/host"
STARTUP_FILE="${CPU_CF_DIR}/cfe_es_startup.scr"
P2_EVIDENCE_DIR="${RUN_ROOT}/orbitfabric-eds-cfs-p2-runtime-evidence"
P3_EVIDENCE_DIR="${RUN_ROOT}/orbitfabric-eds-cfs-p3-conformance-evidence"
P3_CFS_LOG="${P3_EVIDENCE_DIR}/p3-runtime.log"
P3_UNKNOWN_CMD_LOG="${P3_EVIDENCE_DIR}/unknown-function-code-command.log"
P3_PROBE_START_LINE="${P3_EVIDENCE_DIR}/unknown-function-code-probe-start-line.txt"
P3_AFTER_PROBE_LOG="${P3_EVIDENCE_DIR}/unknown-function-code-runtime-after-probe.log"
P3_RESULT="${P3_EVIDENCE_DIR}/unknown-function-code-result.txt"
UNKNOWN_FUNCTION_CODE="127"

CFS_PID=""

cleanup() {
  set +e
  if [[ -n "$CFS_PID" ]]; then
    kill "$CFS_PID" 2>/dev/null || true
    wait "$CFS_PID" 2>/dev/null || true
  fi
}
trap cleanup EXIT

require_file() {
  local path="$1"
  local label="$2"
  if [[ ! -f "$path" ]]; then
    echo "$label not found: $path" >&2
    return 1
  fi
}

require_executable() {
  local path="$1"
  local label="$2"
  if [[ ! -x "$path" ]]; then
    echo "$label not executable: $path" >&2
    return 1
  fi
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

rm -rf "$P3_EVIDENCE_DIR"
mkdir -p "$P3_EVIDENCE_DIR/p2-baseline"

# P3 intentionally starts by executing the complete accepted P2 proof.
# The P2 harness leaves the exact built/staged image on disk after its
# startup dependency control, so the negative probe can reuse those bytes
# instead of creating a parallel target environment.
bash "$P2_SCRIPT"

require_executable "$CPU_DIR/core-cpu1" "P2-proven core-cpu1"
require_executable "$HOST_DIR/cmd_send" "P2-proven cmd_send"
require_file "$CPU_CF_DIR/of_demo_app.so" "P2-proven of_demo_app module"
require_file "$STARTUP_FILE" "P2-proven startup script"

for evidence_file in \
  baseline.txt \
  p2-a-acceptance.txt \
  p2-a-startup-control.txt \
  p2-b-acceptance.txt \
  p2-b-valid-range-observation.tsv \
  runtime-staging-inventory.txt; do
  require_file "$P2_EVIDENCE_DIR/$evidence_file" "P2 retained evidence $evidence_file"
  cp "$P2_EVIDENCE_DIR/$evidence_file" "$P3_EVIDENCE_DIR/p2-baseline/$evidence_file"
done

# P2-A7 leaves the generated startup script without OF_DEMO. Re-enable the
# same already-built module for the dedicated P3 negative runtime probe.
if grep -F 'of_demo_app' "$STARTUP_FILE" >/dev/null 2>&1; then
  echo "P3 expected the P2-A7 baseline startup script without OF_DEMO" >&2
  exit 1
fi

cat >> "$STARTUP_FILE" <<'EOF_STARTUP'
CFE_APP, of_demo_app, OF_DEMO_APP_Main, OF_DEMO_APP, 55, 32768, 0x0, 0;
EOF_STARTUP

(
  cd "$CPU_DIR"
  stdbuf -oL -eL ./core-cpu1
) > "$P3_CFS_LOG" 2>&1 &
CFS_PID=$!

wait_for_pattern "$P3_CFS_LOG" \
  'OF_DEMO_APP: initialized with EDS CMD topic 160 and STATUS_TLM topic 416' \
  'P3 OF_DEMO runtime initialization observed'

# Derive the CCSDS APID from the actual runtime MsgId instead of duplicating
# the SampleMission allocation as another harness constant.
CMD_MID_HEX="$(
  grep -E 'OF_DEMO_APP: mapped CMD topic 160 -> MID 0x[0-9A-Fa-f]+' "$P3_CFS_LOG" \
    | tail -n 1 \
    | sed -E 's/.*CMD topic 160 -> MID 0x([0-9A-Fa-f]+).*/\1/'
)"

if [[ -z "$CMD_MID_HEX" ]]; then
  echo "P3 could not derive OF_DEMO command MsgId from runtime evidence" >&2
  exit 1
fi

CMD_APID="$(python3 - "$CMD_MID_HEX" <<'PY'
import sys
mid = int(sys.argv[1], 16)
print(hex(mid & 0x07FF))
PY
)"

# Retain the exact log boundary before sending the invalid probe. This makes
# handler attribution mechanical even when the proof intentionally fails.
CFS_BEFORE="$(wc -l < "$P3_CFS_LOG")"
printf '%s\n' "$CFS_BEFORE" > "$P3_PROBE_START_LINE"

# This is deliberately NOT a product command path. The unknown command does
# not exist in EDS, so the pinned NASA cmd_send PassThrough encoder is used
# only as negative-test instrumentation to create a syntactically valid cFS
# command header with an unknown Function Code. It still enters through the
# same UDP/ci_lab path used by the positive EDS command flow.
(
  cd "$HOST_DIR"
  ./cmd_send -v -Q cfsv1 -A "$CMD_APID" -C "$UNKNOWN_FUNCTION_CODE"
) > "$P3_UNKNOWN_CMD_LOG" 2>&1

if grep -F 'Option parsing failed' "$P3_UNKNOWN_CMD_LOG" >/dev/null 2>&1; then
  echo "P3 PassThrough negative probe was not encoded" >&2
  cat "$P3_UNKNOWN_CMD_LOG" >&2
  exit 1
fi
if ! grep -F 'Using result from PassThrough encoder' "$P3_UNKNOWN_CMD_LOG" >/dev/null 2>&1; then
  echo "P3 negative probe did not use the pinned NASA PassThrough encoder" >&2
  cat "$P3_UNKNOWN_CMD_LOG" >&2
  exit 1
fi
if grep -F 'Using result from EDS encoder' "$P3_UNKNOWN_CMD_LOG" >/dev/null 2>&1; then
  echo "P3 unknown Function Code unexpectedly resolved through the EDS encoder" >&2
  cat "$P3_UNKNOWN_CMD_LOG" >&2
  exit 1
fi

CLASSIFICATION=""
FIRST_OBSERVED_BOUNDARY=""
VALID_HANDLER="none"
NEW_RUNTIME=""

for attempt in $(seq 1 20); do
  NEW_RUNTIME="$(tail -n +$((CFS_BEFORE + 1)) "$P3_CFS_LOG")"

  # A valid typed handler is the strongest P3 stop/reopen signal. Check this
  # before waiting for a rejection diagnostic so the evidence cannot time out
  # while the invalid command has already crossed the generated boundary.
  if grep -F 'OF_DEMO_APP: payload.enable dispatched through generated EDS interface' \
    <<<"$NEW_RUNTIME" >/dev/null 2>&1; then
    CLASSIFICATION="VALID_TYPED_HANDLER_INVOKED"
    FIRST_OBSERVED_BOUNDARY="GENERATED_OF_DEMO_TYPED_HANDLER"
    VALID_HANDLER="payload.enable"
    break
  fi

  if grep -F 'OF_DEMO_APP: payload.set_period dispatched through generated EDS interface' \
    <<<"$NEW_RUNTIME" >/dev/null 2>&1; then
    CLASSIFICATION="VALID_TYPED_HANDLER_INVOKED"
    FIRST_OBSERVED_BOUNDARY="GENERATED_OF_DEMO_TYPED_HANDLER"
    VALID_HANDLER="payload.set_period"
    break
  fi

  if grep -E 'EdsLib_DataTypeDB_UnpackPartialObject\(Payload\):|EdsLib_DataTypeDB_VerifyUnpackedObject\(\):|CI_LAB: Ingest failed' \
    <<<"$NEW_RUNTIME" >/dev/null 2>&1; then
    CLASSIFICATION="REJECTED_AT_CI_LAB_EDS_INGRESS"
    FIRST_OBSERVED_BOUNDARY="CI_LAB_EDS_INGRESS"
    break
  fi

  if grep -F 'OF_DEMO_APP: generated EDS dispatch rejected command' \
    <<<"$NEW_RUNTIME" >/dev/null 2>&1; then
    CLASSIFICATION="REJECTED_AT_GENERATED_OF_DEMO_DISPATCH"
    FIRST_OBSERVED_BOUNDARY="GENERATED_OF_DEMO_DISPATCH"
    break
  fi

  if ! kill -0 "$CFS_PID" 2>/dev/null; then
    CLASSIFICATION="RUNTIME_EXITED_BEFORE_CLASSIFICATION"
    FIRST_OBSERVED_BOUNDARY="CFS_RUNTIME"
    break
  fi
  sleep 1
done

NEW_RUNTIME="$(tail -n +$((CFS_BEFORE + 1)) "$P3_CFS_LOG")"
printf '%s\n' "$NEW_RUNTIME" > "$P3_AFTER_PROBE_LOG"

if [[ -z "$CLASSIFICATION" ]]; then
  CLASSIFICATION="NO_OBSERVABLE_RESULT"
  FIRST_OBSERVED_BOUNDARY="none"
fi

TARGET_INGRESS_OBSERVED="false"
VALID_TYPED_HANDLER_INVOKED="false"
if [[ "$CLASSIFICATION" == "VALID_TYPED_HANDLER_INVOKED" ]]; then
  TARGET_INGRESS_OBSERVED="true"
  VALID_TYPED_HANDLER_INVOKED="true"
elif [[ "$CLASSIFICATION" == "REJECTED_AT_CI_LAB_EDS_INGRESS" \
     || "$CLASSIFICATION" == "REJECTED_AT_GENERATED_OF_DEMO_DISPATCH" ]]; then
  TARGET_INGRESS_OBSERVED="true"
fi

{
  printf '%s\n' '# P3-C2 unknown Function Code conformance result'
  printf 'command_mid=0x%s\n' "$CMD_MID_HEX"
  printf 'derived_apid=%s\n' "$CMD_APID"
  printf 'unknown_function_code=%s\n' "$UNKNOWN_FUNCTION_CODE"
  printf '%s\n' 'host_encoder=PassThrough'
  printf '%s\n' 'host_eds_encoder_used=false'
  printf 'probe_runtime_start_line=%s\n' "$CFS_BEFORE"
  printf 'classification=%s\n' "$CLASSIFICATION"
  printf 'first_observed_boundary=%s\n' "$FIRST_OBSERVED_BOUNDARY"
  printf 'target_ingress_observed=%s\n' "$TARGET_INGRESS_OBSERVED"
  printf 'valid_generated_typed_handler_invoked=%s\n' "$VALID_TYPED_HANDLER_INVOKED"
  printf 'valid_handler=%s\n' "$VALID_HANDLER"
  printf '%s\n' '# relevant target diagnostics after probe'
  grep -E 'OF_DEMO_APP: payload\.(enable|set_period) dispatched through generated EDS interface|OF_DEMO_APP: generated EDS dispatch rejected command|EdsLib_DataTypeDB_UnpackPartialObject\(Payload\):|EdsLib_DataTypeDB_VerifyUnpackedObject\(\):|CI_LAB: Ingest failed' \
    <<<"$NEW_RUNTIME" || true
} > "$P3_RESULT"

case "$CLASSIFICATION" in
  VALID_TYPED_HANDLER_INVOKED)
    echo "P3 stop/reopen: unknown Function Code invoked valid typed handler ${VALID_HANDLER}" >&2
    cat "$P3_RESULT" >&2
    exit 1
    ;;
  REJECTED_AT_CI_LAB_EDS_INGRESS|REJECTED_AT_GENERATED_OF_DEMO_DISPATCH)
    ;;
  NO_OBSERVABLE_RESULT)
    echo "P3 unknown Function Code produced no observable target result" >&2
    cat "$P3_UNKNOWN_CMD_LOG" >&2 || true
    tail -n 100 "$P3_CFS_LOG" >&2 || true
    exit 1
    ;;
  *)
    echo "P3 unknown Function Code classification failed: ${CLASSIFICATION}" >&2
    cat "$P3_RESULT" >&2
    exit 1
    ;;
esac

# Even when a rejection boundary was observed, the same post-probe slice must
# not contain a valid generated OF_DEMO operation.
if grep -E 'OF_DEMO_APP: payload\.(enable|set_period) dispatched through generated EDS interface' \
  <<<"$NEW_RUNTIME" >/dev/null 2>&1; then
  echo "P3 unknown Function Code crossed the EDS boundary as a valid typed OF_DEMO operation" >&2
  printf '%s\n' "$NEW_RUNTIME" >&2
  exit 1
fi

kill "$CFS_PID" 2>/dev/null || true
wait "$CFS_PID" 2>/dev/null || true
CFS_PID=""

printf '%s\n' "P3-C2 unknown Function Code conformance probe completed at ${FIRST_OBSERVED_BOUNDARY}"
