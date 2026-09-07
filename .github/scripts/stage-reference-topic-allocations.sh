#!/usr/bin/env bash
set -euo pipefail

CFS_DIR="${1:?usage: stage-reference-topic-allocations.sh <cfs-dir>}"
REGISTRY="${CFS_DIR}/sample_defs/eds/cfe-topicids.xml"

if [[ ! -f "$REGISTRY" ]]; then
  echo "cFS mission topic registry not found: $REGISTRY" >&2
  exit 1
fi

python3 - "$REGISTRY" <<'PY'
from pathlib import Path
import sys

path = Path(sys.argv[1])
text = path.read_text(encoding="utf-8")

symbols = (
    "OF_DEMO_CMD_TOPICID",
    "OF_DEMO_STATUS_TLM_TOPICID",
)
for symbol in symbols:
    if symbol in text:
        raise SystemExit(f"reference mission allocation already exists: {symbol}")

marker = "  </Package>"
if text.count(marker) != 1:
    raise SystemExit("CFE_MISSION package closing marker is not unique")

allocation_block = '''
    <!-- OrbitFabric disposable reference-mission allocations.
         The reusable adapter binds only to these identities; SampleMission owns
         the concrete values used by the retained native/runtime proof lane. -->
    <Define name="OF_DEMO_CMD_TOPICID"
            value="${CFE_MISSION/TELECOMMAND_BASE_TOPICID} + 151"/>
    <Define name="OF_DEMO_STATUS_TLM_TOPICID"
            value="${CFE_MISSION/TELEMETRY_BASE_TOPICID} + 151"/>

'''
path.write_text(text.replace(marker, allocation_block + marker, 1), encoding="utf-8")
PY

grep -F 'name="OF_DEMO_CMD_TOPICID"' "$REGISTRY"
grep -F 'value="${CFE_MISSION/TELECOMMAND_BASE_TOPICID} + 151"' "$REGISTRY"
grep -F 'name="OF_DEMO_STATUS_TLM_TOPICID"' "$REGISTRY"
grep -F 'value="${CFE_MISSION/TELEMETRY_BASE_TOPICID} + 151"' "$REGISTRY"

printf '%s\n' "SampleMission reference allocations staged"
