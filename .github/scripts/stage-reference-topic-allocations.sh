#!/usr/bin/env bash
set -euo pipefail

if [[ "$#" -lt 1 || "$#" -gt 2 ]]; then
  echo "usage: $0 <cfs-root> [evidence-dir]" >&2
  exit 2
fi

CFS_ROOT="$1"
EVIDENCE_DIR="${2:-}"
ADAPTER_ROOT="${GITHUB_WORKSPACE:-$(cd "$(dirname "$0")/../.." && pwd)}"
FRAGMENT="${ADAPTER_ROOT}/examples/cfs/sample_mission/of_demo-topicids.xml.inc"
REGISTRY="${CFS_ROOT}/sample_defs/eds/cfe-topicids.xml"

[[ -f "$FRAGMENT" ]] || { echo "reference allocation fragment missing: $FRAGMENT" >&2; exit 1; }
[[ -f "$REGISTRY" ]] || { echo "cFS mission topic registry missing: $REGISTRY" >&2; exit 1; }

python3 - "$REGISTRY" "$FRAGMENT" <<'PY'
from pathlib import Path
import sys

registry = Path(sys.argv[1])
fragment = Path(sys.argv[2])
text = registry.read_text(encoding="utf-8")
addition = fragment.read_text(encoding="utf-8").strip()

symbols = (
    "OF_DEMO_CMD_TOPICID",
    "OF_DEMO_STATUS_TLM_TOPICID",
)
for symbol in symbols:
    if symbol in text:
        raise SystemExit(f"reference mission symbol already exists: {symbol}")

anchor = "  </Package>"
if text.count(anchor) != 1:
    raise SystemExit(f"expected exactly one mission Package closing anchor, got {text.count(anchor)}")

text = text.replace(anchor, "\n" + addition + "\n\n" + anchor, 1)
registry.write_text(text, encoding="utf-8")
PY

grep -F 'name="OF_DEMO_CMD_TOPICID"' "$REGISTRY" >/dev/null
grep -F 'value="${CFE_MISSION/TELECOMMAND_BASE_TOPICID} + 151"' "$REGISTRY" >/dev/null
grep -F 'name="OF_DEMO_STATUS_TLM_TOPICID"' "$REGISTRY" >/dev/null
grep -F 'value="${CFE_MISSION/TELEMETRY_BASE_TOPICID} + 151"' "$REGISTRY" >/dev/null

if [[ -n "$EVIDENCE_DIR" ]]; then
  mkdir -p "$EVIDENCE_DIR"
  cp "$FRAGMENT" "$EVIDENCE_DIR/of-demo-topicids-reference.xml.inc"
  cp "$REGISTRY" "$EVIDENCE_DIR/cfe-topicids.effective.xml"
fi

printf '%s\n' "reference SampleMission allocations staged"
