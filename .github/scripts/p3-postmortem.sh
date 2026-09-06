#!/usr/bin/env bash
set -euo pipefail

RUN_ROOT="${RUNNER_TEMP:-/tmp}"
P3_EVIDENCE_DIR="${RUN_ROOT}/orbitfabric-eds-cfs-p3-conformance-evidence"
RUNTIME_LOG="${P3_EVIDENCE_DIR}/p3-runtime.log"
COMMAND_LOG="${P3_EVIDENCE_DIR}/unknown-function-code-command.log"
RESULT_FILE="${P3_EVIDENCE_DIR}/unknown-function-code-postmortem.txt"

mkdir -p "$P3_EVIDENCE_DIR"

if [[ ! -f "$RUNTIME_LOG" || ! -f "$COMMAND_LOG" ]]; then
  {
    printf '%s\n' '# P3 unknown Function Code postmortem'
    printf '%s\n' 'classification=INSUFFICIENT_EVIDENCE'
    printf '%s\n' 'reason=required runtime or command log missing'
  } > "$RESULT_FILE"
  exit 0
fi

ENCODER="unknown"
if grep -F 'Using result from PassThrough encoder' "$COMMAND_LOG" >/dev/null 2>&1; then
  ENCODER="PassThrough"
fi

CLASSIFICATION="NO_OBSERVABLE_REJECTION_OR_HANDLER"
HANDLER="none"

if grep -F 'OF_DEMO_APP: payload.enable dispatched through generated EDS interface' "$RUNTIME_LOG" >/dev/null 2>&1; then
  CLASSIFICATION="UNKNOWN_FC_DISPATCHED_AS_VALID_TYPED_HANDLER"
  HANDLER="payload.enable"
elif grep -F 'OF_DEMO_APP: payload.set_period dispatched through generated EDS interface' "$RUNTIME_LOG" >/dev/null 2>&1; then
  CLASSIFICATION="UNKNOWN_FC_DISPATCHED_AS_VALID_TYPED_HANDLER"
  HANDLER="payload.set_period"
elif grep -E 'EdsLib_DataTypeDB_UnpackPartialObject\(Payload\):|EdsLib_DataTypeDB_VerifyUnpackedObject\(\):|CI_LAB: Ingest failed' "$RUNTIME_LOG" >/dev/null 2>&1; then
  CLASSIFICATION="REJECTED_AT_CI_LAB_EDS_INGRESS"
elif grep -F 'OF_DEMO_APP: generated EDS dispatch rejected command' "$RUNTIME_LOG" >/dev/null 2>&1; then
  CLASSIFICATION="REJECTED_AT_GENERATED_OF_DEMO_DISPATCH"
fi

{
  printf '%s\n' '# P3 unknown Function Code postmortem'
  printf 'host_encoder=%s\n' "$ENCODER"
  printf '%s\n' 'unknown_function_code=127'
  printf 'classification=%s\n' "$CLASSIFICATION"
  printf 'valid_handler=%s\n' "$HANDLER"
  printf '%s\n' '# negative command bytes'
  grep -E '^0x0*00:|^0000:' "$COMMAND_LOG" || true
  printf '%s\n' '# relevant runtime evidence'
  grep -E 'OF_DEMO_APP: payload\.(enable|set_period) dispatched through generated EDS interface|OF_DEMO_APP: generated EDS dispatch rejected command|EdsLib_DataTypeDB_UnpackPartialObject\(Payload\):|EdsLib_DataTypeDB_VerifyUnpackedObject\(\):|CI_LAB: Ingest failed' "$RUNTIME_LOG" || true
} > "$RESULT_FILE"

printf 'P3 postmortem classification: %s\n' "$CLASSIFICATION"
