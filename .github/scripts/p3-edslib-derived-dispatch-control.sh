#!/usr/bin/env bash
set -euo pipefail

RUN_ROOT="${RUNNER_TEMP:-/tmp}"
CFS_DIR="${RUN_ROOT}/orbitfabric-cfs-p2-runtime"
APP_ROOT="${RUN_ROOT}/orbitfabric-cfs-p2-runtime-apps"
BUILD_DIR="${CFS_DIR}/build-native_eds"
CPU_DIR="${BUILD_DIR}/exe/cpu1"
CPU_CF_DIR="${CPU_DIR}/cf"
HOST_DIR="${BUILD_DIR}/exe/host"
STARTUP_FILE="${CPU_CF_DIR}/cfe_es_startup.scr"
EDSLIB_DISPATCHER="${CFS_DIR}/tools/eds/cfecfs/edsmsg/fsw/src/edsmsg_dispatcher.c"
SAMPLE_APP_EDS="${CFS_DIR}/apps/sample_app/eds/sample_app.xml"
SAMPLE_APP_CMDS="${CFS_DIR}/apps/sample_app/fsw/src/sample_app_cmds.c"
SAMPLE_APP_MAIN="${CFS_DIR}/apps/sample_app/fsw/src/sample_app.c"
EVIDENCE_DIR="${RUN_ROOT}/orbitfabric-eds-cfs-p3-conformance-evidence"
CONTROL_RESULT="${EVIDENCE_DIR}/edslib-derived-dispatch-control.txt"
PATCH_DIFF="${EVIDENCE_DIR}/edslib-derived-dispatch-control.patch"
SAMPLE_INSTRUMENTATION_DIFF="${EVIDENCE_DIR}/sample-app-send-hk-instrumentation.patch"
NONDERIVED_MODEL="${EVIDENCE_DIR}/sample-app-send-hk-nonderived-model.txt"
RUNTIME_LOG="${EVIDENCE_DIR}/edslib-derived-dispatch-control-runtime.log"
ENABLE_LOG="${EVIDENCE_DIR}/edslib-derived-dispatch-control-enable.log"
SET_PERIOD_LOG="${EVIDENCE_DIR}/edslib-derived-dispatch-control-set-period.log"
UNKNOWN_LOG="${EVIDENCE_DIR}/edslib-derived-dispatch-control-unknown.log"
NONDERIVED_RUNTIME_LOG="${EVIDENCE_DIR}/edslib-nonderived-send-hk-runtime.log"
NONDERIVED_CMD_LOG="${EVIDENCE_DIR}/edslib-nonderived-send-hk-command.log"
BUILD_LOG="${EVIDENCE_DIR}/edslib-derived-dispatch-control-build.log"
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

stop_runtime() {
  set +e
  if [[ -n "$CFS_PID" ]]; then
    kill "$CFS_PID" 2>/dev/null || true
    wait "$CFS_PID" 2>/dev/null || true
    CFS_PID=""
  fi
  set -e
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

mkdir -p "$EVIDENCE_DIR"

if [[ ! -f "$EDSLIB_DISPATCHER" || ! -d "$BUILD_DIR" ]]; then
  echo "P3 EdsLib control requires the source/build tree retained by the P3 proof" >&2
  exit 1
fi
if [[ ! -f "$SAMPLE_APP_EDS" || ! -f "$SAMPLE_APP_CMDS" || ! -f "$SAMPLE_APP_MAIN" ]]; then
  echo "P3 EdsLib control requires the pinned NASA sample_app source tree" >&2
  exit 1
fi

if [[ "$(git -C "$CFS_DIR/tools/eds" rev-parse HEAD)" != "2acc963b34f77692c6396555dcfb10ef43eb1046" ]]; then
  echo "P3 EdsLib control is not running against the frozen EdsLib commit" >&2
  exit 1
fi
if [[ "$(git -C "$CFS_DIR/apps/sample_app" rev-parse HEAD)" != "2f93d1a4159a02b18d67ee83342c9e96b90e23e4" ]]; then
  echo "P3 EdsLib control is not running against the frozen NASA sample_app commit" >&2
  exit 1
fi

# Prove from the pinned NASA EDS that SAMPLE_APP/SEND_HK is the genuine
# non-derived CASE A needed by Architecture Lab Investigation 020 F4.
python3 - "$SAMPLE_APP_EDS" "$NONDERIVED_MODEL" <<'PY'
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

source = Path(sys.argv[1])
out = Path(sys.argv[2])
root = ET.parse(source).getroot()
ns = {"s": "http://www.ccsds.org/schema/sois/seds"}

send_hk = root.find(".//s:ContainerDataType[@name='SendHkCmd']", ns)
if send_hk is None:
    raise SystemExit("SendHkCmd EDS type not found")
if send_hk.get("baseType") != "CFE_HDR/CommandHeader":
    raise SystemExit("SendHkCmd is not based directly on CFE_HDR/CommandHeader")

derivatives = root.findall(".//s:ContainerDataType[@baseType='SendHkCmd']", ns)
if derivatives:
    raise SystemExit("SendHkCmd unexpectedly has derived container types")

maps = root.findall(".//s:Interface[@name='SEND_HK']/s:GenericTypeMapSet/s:GenericTypeMap", ns)
if not any(m.get("name") == "TelecommandDataType" and m.get("type") == "SendHkCmd" for m in maps):
    raise SystemExit("SEND_HK does not map TelecommandDataType directly to SendHkCmd")

out.write_text(
    "interface=SAMPLE_APP/SEND_HK\n"
    "telecommand_data_type=SendHkCmd\n"
    "base_type=CFE_HDR/CommandHeader\n"
    "derived_type_count=0\n"
    "classification=GENUINELY_NON_DERIVED_TELECOMMAND\n"
)
PY

# -----------------------------------------------------------------------------
# Evidence-only semantic pressure test.
#
# Do not turn this patch into product code. It exists only in the disposable
# GitHub Actions source tree to test the ownership hypothesis opened by
# Architecture Lab Investigation 020.
#
# The current dispatcher treats every IdentifyBufferWithSize() failure as a
# non-derived argument and selects dispatch position zero. The candidate
# behavior below preserves position zero only when the base container actually
# reports zero derivatives. If the base has derivatives but no derivative was
# identified, dispatch fails closed.
# -----------------------------------------------------------------------------
python3 - "$EDSLIB_DISPATCHER" <<'PY'
from pathlib import Path
import sys

path = Path(sys.argv[1])
text = path.read_text()

old_decl = """    EdsLib_DataTypeDB_TypeInfo_t             TypeInfo;\n    EdsLib_DataTypeDB_DerivativeObjectInfo_t DerivObjInfo;\n"""
new_decl = """    EdsLib_DataTypeDB_TypeInfo_t             TypeInfo;\n    EdsLib_DataTypeDB_DerivativeObjectInfo_t DerivObjInfo;\n    EdsLib_DataTypeDB_DerivedTypeInfo_t      DerivTypeInfo;\n"""

old_fallback = """    else\n    {\n        /* Non derived, there is just one entry, it is always first */\n        *DispatchTblPosition = 0;\n    }\n"""
new_fallback = """    else\n    {\n        /* Evidence-only P3 control: distinguish a genuinely non-derived\n         * base container from a base that has derivatives but matched none. */\n        Status = EdsLib_DataTypeDB_GetDerivedInfo(GD, *EdsId, &DerivTypeInfo);\n        if (Status != EDSLIB_SUCCESS || DerivTypeInfo.NumDerivatives > 0)\n        {\n            return CFE_STATUS_VALIDATION_FAILURE;\n        }\n\n        *DispatchTblPosition = 0;\n    }\n"""

if old_decl not in text:
    raise SystemExit("EdsLib dispatcher declaration anchor not found")
if old_fallback not in text:
    raise SystemExit("EdsLib dispatcher fallback anchor not found")

text = text.replace(old_decl, new_decl, 1)
text = text.replace(old_fallback, new_fallback, 1)
path.write_text(text)
PY

git -C "$CFS_DIR/tools/eds" diff -- cfecfs/edsmsg/fsw/src/edsmsg_dispatcher.c > "$PATCH_DIFF"
if ! grep -F 'DerivTypeInfo.NumDerivatives > 0' "$PATCH_DIFF" >/dev/null 2>&1; then
  echo "P3 EdsLib control patch was not materialized" >&2
  exit 1
fi

# Add evidence-only observability to the genuine NASA non-derived path:
# one handler marker and the exact MsgId value the app itself subscribes to.
# Neither changes dispatch or command semantics.
python3 - "$SAMPLE_APP_CMDS" "$SAMPLE_APP_MAIN" <<'PY'
from pathlib import Path
import sys

cmds_path = Path(sys.argv[1])
main_path = Path(sys.argv[2])

cmds_text = cmds_path.read_text()
old_cmds = """CFE_Status_t SAMPLE_APP_SendHkCmd(const SAMPLE_APP_SendHkCmd_t *Msg)\n{\n    int i;\n"""
new_cmds = """CFE_Status_t SAMPLE_APP_SendHkCmd(const SAMPLE_APP_SendHkCmd_t *Msg)\n{\n    int i;\n\n    CFE_ES_WriteToSysLog(\"P3 F4: SAMPLE_APP SendHk non-derived handler invoked\\n\");\n"""
if old_cmds not in cmds_text:
    raise SystemExit("SAMPLE_APP_SendHkCmd instrumentation anchor not found")
cmds_path.write_text(cmds_text.replace(old_cmds, new_cmds, 1))

main_text = main_path.read_text()
old_main = """        /*\n        ** Subscribe to Housekeeping request commands\n        */\n        status = CFE_SB_Subscribe(CFE_SB_ValueToMsgId(SAMPLE_APP_SEND_HK_MID), SAMPLE_APP_Data.CommandPipe);\n"""
new_main = """        /*\n        ** Subscribe to Housekeeping request commands\n        */\n        CFE_ES_WriteToSysLog(\n            \"P3 F4: SAMPLE_APP SendHk MID=0x%08X\\n\",\n            (unsigned int)CFE_SB_MsgIdToValue(CFE_SB_ValueToMsgId(SAMPLE_APP_SEND_HK_MID)));\n        status = CFE_SB_Subscribe(CFE_SB_ValueToMsgId(SAMPLE_APP_SEND_HK_MID), SAMPLE_APP_Data.CommandPipe);\n"""
if old_main not in main_text:
    raise SystemExit("SAMPLE_APP SendHk subscription instrumentation anchor not found")
main_path.write_text(main_text.replace(old_main, new_main, 1))
PY

git -C "$CFS_DIR/apps/sample_app" diff -- fsw/src/sample_app_cmds.c fsw/src/sample_app.c > "$SAMPLE_INSTRUMENTATION_DIFF"
if ! grep -F 'P3 F4: SAMPLE_APP SendHk non-derived handler invoked' "$SAMPLE_INSTRUMENTATION_DIFF" >/dev/null 2>&1; then
  echo "P3 F4 sample_app handler instrumentation was not materialized" >&2
  exit 1
fi
if ! grep -F 'P3 F4: SAMPLE_APP SendHk MID=' "$SAMPLE_INSTRUMENTATION_DIFF" >/dev/null 2>&1; then
  echo "P3 F4 sample_app MsgId instrumentation was not materialized" >&2
  exit 1
fi

# Rebuild only the disposable frozen cFS/native_eds workspace. The adapter
# repository and generated OF_DEMO EDS fixture remain byte-for-byte unchanged.
(
  cd "$CFS_DIR"
  CFS_APP_PATH="$APP_ROOT" make native_eds.compile
  CFS_APP_PATH="$APP_ROOT" make native_eds.install
) > "$BUILD_LOG" 2>&1

if [[ ! -x "$CPU_DIR/core-cpu1" || ! -x "$HOST_DIR/cmd_send" || ! -f "$STARTUP_FILE" ]]; then
  echo "P3 EdsLib control rebuild did not stage the expected runtime" >&2
  exit 1
fi

# native_eds.install regenerates the baseline startup file. Load the same
# already-proven OF_DEMO module for the first isolated control runtime.
if grep -F 'of_demo_app' "$STARTUP_FILE" >/dev/null 2>&1; then
  echo "P3 EdsLib control expected regenerated startup without OF_DEMO" >&2
  exit 1
fi
cat >> "$STARTUP_FILE" <<'EOF_STARTUP'
CFE_APP, of_demo_app, OF_DEMO_APP_Main, OF_DEMO_APP, 55, 32768, 0x0, 0;
EOF_STARTUP

(
  cd "$CPU_DIR"
  stdbuf -oL -eL ./core-cpu1
) > "$RUNTIME_LOG" 2>&1 &
CFS_PID=$!

wait_for_pattern "$RUNTIME_LOG" \
  'OF_DEMO_APP: initialized with EDS CMD topic 160 and STATUS_TLM topic 416' \
  'P3 EdsLib control OF_DEMO initialization observed'

# Positive control 1: derivative FC 0 must still resolve to payload.enable.
ENABLE_BEFORE="$(wc -l < "$RUNTIME_LOG")"
(
  cd "$HOST_DIR"
  ./cmd_send -v -I OF_DEMO/CMD.PayloadEnableCmd
) > "$ENABLE_LOG" 2>&1

if ! grep -F 'Using result from EDS encoder' "$ENABLE_LOG" >/dev/null 2>&1; then
  echo "P3 EdsLib control payload.enable did not use EDS encoder" >&2
  exit 1
fi

for attempt in $(seq 1 20); do
  ENABLE_RUNTIME="$(tail -n +$((ENABLE_BEFORE + 1)) "$RUNTIME_LOG")"
  if grep -F 'OF_DEMO_APP: payload.enable dispatched through generated EDS interface' \
    <<<"$ENABLE_RUNTIME" >/dev/null 2>&1; then
    break
  fi
  if [[ "$attempt" -eq 20 ]]; then
    echo "P3 EdsLib control FC 0 no longer reached payload.enable" >&2
    tail -n 120 "$RUNTIME_LOG" >&2 || true
    exit 1
  fi
  sleep 1
done

# Positive control 2: derivative FC 1 must still resolve to payload.set_period.
SET_PERIOD_BEFORE="$(wc -l < "$RUNTIME_LOG")"
(
  cd "$HOST_DIR"
  ./cmd_send -v -I OF_DEMO/CMD.PayloadSetPeriodCmd PeriodMs=1000
) > "$SET_PERIOD_LOG" 2>&1

if ! grep -F 'Using result from EDS encoder' "$SET_PERIOD_LOG" >/dev/null 2>&1; then
  echo "P3 EdsLib control payload.set_period did not use EDS encoder" >&2
  exit 1
fi

for attempt in $(seq 1 20); do
  SET_PERIOD_RUNTIME="$(tail -n +$((SET_PERIOD_BEFORE + 1)) "$RUNTIME_LOG")"
  if grep -F 'OF_DEMO_APP: payload.set_period dispatched through generated EDS interface PeriodMs=1000' \
    <<<"$SET_PERIOD_RUNTIME" >/dev/null 2>&1; then
    break
  fi
  if [[ "$attempt" -eq 20 ]]; then
    echo "P3 EdsLib control FC 1 no longer reached payload.set_period" >&2
    tail -n 120 "$RUNTIME_LOG" >&2 || true
    exit 1
  fi
  sleep 1
done

# Derive the same runtime APID rather than introducing another allocation
# constant into the evidence harness.
CMD_MID_HEX="$(
  grep -E 'OF_DEMO_APP: mapped CMD topic 160 -> MID 0x[0-9A-Fa-f]+' "$RUNTIME_LOG" \
    | tail -n 1 \
    | sed -E 's/.*CMD topic 160 -> MID 0x([0-9A-Fa-f]+).*/\1/'
)"
CMD_APID="$(python3 - "$CMD_MID_HEX" <<'PY'
import sys
print(hex(int(sys.argv[1], 16) & 0x07ff))
PY
)"

# Negative control: the same structurally valid FC 127 probe must now be
# rejected by generated dispatch and must not invoke either valid handler.
UNKNOWN_BEFORE="$(wc -l < "$RUNTIME_LOG")"
(
  cd "$HOST_DIR"
  ./cmd_send -v -Q cfsv1 -A "$CMD_APID" -C "$UNKNOWN_FUNCTION_CODE"
) > "$UNKNOWN_LOG" 2>&1

if ! grep -F 'Using result from PassThrough encoder' "$UNKNOWN_LOG" >/dev/null 2>&1; then
  echo "P3 EdsLib control unknown probe did not use PassThrough encoder" >&2
  exit 1
fi

UNKNOWN_CLASSIFICATION="NO_OBSERVABLE_RESULT"
UNKNOWN_RUNTIME=""
for attempt in $(seq 1 20); do
  UNKNOWN_RUNTIME="$(tail -n +$((UNKNOWN_BEFORE + 1)) "$RUNTIME_LOG")"

  if grep -E 'OF_DEMO_APP: payload\.(enable|set_period) dispatched through generated EDS interface' \
    <<<"$UNKNOWN_RUNTIME" >/dev/null 2>&1; then
    UNKNOWN_CLASSIFICATION="VALID_TYPED_HANDLER_INVOKED"
    break
  fi

  if grep -F 'OF_DEMO_APP: generated EDS dispatch rejected command' \
    <<<"$UNKNOWN_RUNTIME" >/dev/null 2>&1; then
    UNKNOWN_CLASSIFICATION="REJECTED_AT_GENERATED_OF_DEMO_DISPATCH"
    break
  fi

  if ! kill -0 "$CFS_PID" 2>/dev/null; then
    UNKNOWN_CLASSIFICATION="RUNTIME_EXITED"
    break
  fi
  sleep 1
done

{
  printf '%s\n' '# P3 EdsLib derived-dispatch control'
  printf '%s\n' 'control_scope=evidence_harness_only'
  printf '%s\n' 'product_patch=false'
  printf '%s\n' 'edslib_commit=2acc963b34f77692c6396555dcfb10ef43eb1046'
  printf '%s\n' 'candidate_rule=base_has_derivatives_and_no_match_must_fail_closed'
  printf '%s\n' 'positive_fc0=payload.enable_observed'
  printf '%s\n' 'positive_fc1=payload.set_period_1000_observed'
  printf 'unknown_function_code=%s\n' "$UNKNOWN_FUNCTION_CODE"
  printf '%s\n' 'unknown_probe_encoder=PassThrough'
  printf 'unknown_classification=%s\n' "$UNKNOWN_CLASSIFICATION"
  printf '%s\n' '# unknown-probe relevant runtime evidence'
  grep -E 'OF_DEMO_APP: payload\.(enable|set_period) dispatched through generated EDS interface|OF_DEMO_APP: generated EDS dispatch rejected command' \
    <<<"$UNKNOWN_RUNTIME" || true
} > "$CONTROL_RESULT"

if [[ "$UNKNOWN_CLASSIFICATION" != "REJECTED_AT_GENERATED_OF_DEMO_DISPATCH" ]]; then
  echo "P3 EdsLib candidate guard control did not fail closed for FC 127" >&2
  cat "$CONTROL_RESULT" >&2
  exit 1
fi

# -----------------------------------------------------------------------------
# F4: prove the candidate distinction does not break a genuinely non-derived
# EDS telecommand. Use the pinned NASA SAMPLE_APP/SEND_HK interface itself.
# Restart without sch_lab so the handler cannot be reached by periodic schedule
# traffic. Derive the exact MsgId from the value used by sample_app itself, then
# use PassThrough only as evidence instrumentation to inject the corresponding
# structurally valid header-only cfsv1 command.
# -----------------------------------------------------------------------------
stop_runtime
sleep 1

F4_STARTUP="${STARTUP_FILE}.p3-f4"
grep -viE 'of_demo_app|sch_lab' "$STARTUP_FILE" > "$F4_STARTUP"
mv "$F4_STARTUP" "$STARTUP_FILE"

(
  cd "$CPU_DIR"
  stdbuf -oL -eL ./core-cpu1
) > "$NONDERIVED_RUNTIME_LOG" 2>&1 &
CFS_PID=$!

wait_for_pattern "$NONDERIVED_RUNTIME_LOG" 'Sample App Initialized' \
  'P3 F4 NASA sample_app initialization observed'
wait_for_pattern "$NONDERIVED_RUNTIME_LOG" 'CFE_ES_Main: CFE_ES_Main entering OPERATIONAL state' \
  'P3 F4 cFS operational state observed'
wait_for_pattern "$NONDERIVED_RUNTIME_LOG" 'P3 F4: SAMPLE_APP SendHk MID=0x[0-9A-Fa-f]+' \
  'P3 F4 runtime-derived SAMPLE_APP SendHk MsgId observed'

if grep -F 'P3 F4: SAMPLE_APP SendHk non-derived handler invoked' "$NONDERIVED_RUNTIME_LOG" >/dev/null 2>&1; then
  echo "P3 F4 non-derived handler was invoked before the explicit probe" >&2
  exit 1
fi

NONDERIVED_MID_HEX="$(
  grep -E 'P3 F4: SAMPLE_APP SendHk MID=0x[0-9A-Fa-f]+' "$NONDERIVED_RUNTIME_LOG" \
    | tail -n 1 \
    | sed -E 's/.*MID=0x([0-9A-Fa-f]+).*/\1/'
)"
if [[ -z "$NONDERIVED_MID_HEX" ]]; then
  echo "P3 F4 could not derive SAMPLE_APP SendHk MsgId from runtime" >&2
  exit 1
fi
NONDERIVED_APID="$(python3 - "$NONDERIVED_MID_HEX" <<'PY'
import sys
print(hex(int(sys.argv[1], 16) & 0x07ff))
PY
)"

NONDERIVED_BEFORE="$(wc -l < "$NONDERIVED_RUNTIME_LOG")"
(
  cd "$HOST_DIR"
  ./cmd_send -v -Q cfsv1 -A "$NONDERIVED_APID" -C 0
) > "$NONDERIVED_CMD_LOG" 2>&1

if ! grep -F 'Using result from PassThrough encoder' "$NONDERIVED_CMD_LOG" >/dev/null 2>&1; then
  echo "P3 F4 SAMPLE_APP/SEND_HK probe did not use PassThrough encoder" >&2
  cat "$NONDERIVED_CMD_LOG" >&2
  exit 1
fi
if grep -F 'Using result from EDS encoder' "$NONDERIVED_CMD_LOG" >/dev/null 2>&1; then
  echo "P3 F4 SAMPLE_APP/SEND_HK probe unexpectedly used EDS encoder" >&2
  exit 1
fi

NONDERIVED_OBSERVED="false"
NONDERIVED_RUNTIME=""
for attempt in $(seq 1 20); do
  NONDERIVED_RUNTIME="$(tail -n +$((NONDERIVED_BEFORE + 1)) "$NONDERIVED_RUNTIME_LOG")"
  if grep -F 'P3 F4: SAMPLE_APP SendHk non-derived handler invoked' \
    <<<"$NONDERIVED_RUNTIME" >/dev/null 2>&1; then
    NONDERIVED_OBSERVED="true"
    break
  fi
  if grep -F 'SAMPLE: Invalid ground command code' <<<"$NONDERIVED_RUNTIME" >/dev/null 2>&1; then
    break
  fi
  if ! kill -0 "$CFS_PID" 2>/dev/null; then
    break
  fi
  sleep 1
done

{
  printf '%s\n' 'nonderived_control_interface=SAMPLE_APP/SEND_HK'
  printf '%s\n' 'nonderived_control_model=GENUINELY_NON_DERIVED_TELECOMMAND'
  printf '%s\n' 'nonderived_control_encoder=PassThrough'
  printf '%s\n' 'nonderived_control_injection=runtime_derived_cfsv1_header_only'
  printf 'nonderived_runtime_mid=0x%s\n' "$NONDERIVED_MID_HEX"
  printf 'nonderived_runtime_apid=%s\n' "$NONDERIVED_APID"
  printf 'nonderived_handler_observed=%s\n' "$NONDERIVED_OBSERVED"
  printf '%s\n' '# non-derived relevant runtime evidence'
  grep -E 'P3 F4: SAMPLE_APP SendHk non-derived handler invoked|SAMPLE: Invalid ground command code' \
    <<<"$NONDERIVED_RUNTIME" || true
} >> "$CONTROL_RESULT"

if [[ "$NONDERIVED_OBSERVED" != "true" ]]; then
  echo "P3 F4 candidate distinction broke genuine non-derived EDS dispatch" >&2
  cat "$CONTROL_RESULT" >&2
  tail -n 120 "$NONDERIVED_RUNTIME_LOG" >&2 || true
  exit 1
fi

stop_runtime
printf '%s\n' 'P3 EdsLib derived-dispatch control PASS including F4 non-derived regression'