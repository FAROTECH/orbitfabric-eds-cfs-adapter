#!/usr/bin/env bash
set -euo pipefail

RUN_ROOT="${RUNNER_TEMP:-/tmp}"
EVIDENCE_DIR="${RUN_ROOT}/orbitfabric-eds-cfs-p3-conformance-evidence"
RAW_RESULT="${EVIDENCE_DIR}/unknown-function-code-result.txt"
POSTMORTEM="${EVIDENCE_DIR}/unknown-function-code-postmortem.txt"
NASA_CONTROL="${EVIDENCE_DIR}/nasa-sample-app-control.txt"
EDSLIB_CONTROL="${EVIDENCE_DIR}/edslib-derived-dispatch-control.txt"
ACCEPTANCE="${EVIDENCE_DIR}/p3-acceptance.txt"

require_file() {
  local path="$1"
  if [[ ! -f "$path" ]]; then
    echo "P3 acceptance evidence missing: $path" >&2
    exit 1
  fi
}

require_line() {
  local path="$1"
  local text="$2"
  local label="$3"
  if ! grep -F "$text" "$path" >/dev/null 2>&1; then
    echo "P3 acceptance failed: $label" >&2
    echo "Expected: $text" >&2
    cat "$path" >&2 || true
    exit 1
  fi
}

require_file "$RAW_RESULT"
require_file "$POSTMORTEM"
require_file "$NASA_CONTROL"
require_file "$EDSLIB_CONTROL"

# The frozen lane is accepted as a characterization, not as automatic runtime
# rejection. The raw falsification must remain exactly observable.
require_line "$RAW_RESULT" 'classification=VALID_TYPED_HANDLER_INVOKED' \
  'the unknown-FC falsification was not reproduced'
require_line "$RAW_RESULT" 'unknown_function_code=127' \
  'the retained probe is not FC 127'
require_line "$RAW_RESULT" 'valid_generated_typed_handler_invoked=true' \
  'the demonstrated typed-handler crossing is absent'
require_line "$RAW_RESULT" 'valid_handler=payload.enable' \
  'the frozen-lane entry-zero outcome changed'
require_line "$POSTMORTEM" 'classification=UNDEFINED_FC_DISPATCHED_TO_VALID_TYPED_HANDLER' \
  'postmortem did not normalize the observed behavior'

# NASA sample_app is a target-lane control. It must prove positive reachability
# and must not transform the same unknown FC into its normal NOOP operation.
require_line "$NASA_CONTROL" 'positive_control_pass=true' \
  'NASA sample_app positive ingress control failed'
if grep -F 'classification=UNKNOWN_FC_DISPATCHED_AS_NOOP' "$NASA_CONTROL" >/dev/null 2>&1; then
  echo 'P3 acceptance failed: NASA sample_app unknown FC became a valid NOOP' >&2
  cat "$NASA_CONTROL" >&2
  exit 1
fi

# The disposable EdsLib intervention is the causal control. It must preserve
# known derivative dispatch, reject the unmatched derivative case, and preserve
# a genuinely non-derived command at position zero.
require_line "$EDSLIB_CONTROL" 'positive_fc0=payload.enable_observed' \
  'EdsLib causal control broke FC 0'
require_line "$EDSLIB_CONTROL" 'positive_fc1=payload.set_period_1000_observed' \
  'EdsLib causal control broke FC 1'
require_line "$EDSLIB_CONTROL" 'unknown_classification=REJECTED_AT_GENERATED_OF_DEMO_DISPATCH' \
  'EdsLib causal intervention did not fail closed for FC 127'
require_line "$EDSLIB_CONTROL" 'nonderived_control_model=GENUINELY_NON_DERIVED_TELECOMMAND' \
  'non-derived regression model was not established'
require_line "$EDSLIB_CONTROL" 'nonderived_handler_observed=true' \
  'candidate distinction broke genuine non-derived dispatch'

{
  printf '%s\n' '# P3 characterization acceptance'
  printf '%s\n' 'status=PASS'
  printf '%s\n' 'acceptance_semantics=CHARACTERIZATION'
  printf '%s\n' 'unknown_function_code=127'
  printf '%s\n' 'observed_behavior=UNDEFINED_FC_DISPATCHED_TO_VALID_TYPED_HANDLER'
  printf '%s\n' 'observed_handler=payload.enable'
  printf '%s\n' 'prospective_automatic_rejection_property=FALSIFIED'
  printf '%s\n' 'edslib_causal_control=PASS'
  printf '%s\n' 'genuine_nonderived_regression=PASS'
  printf '%s\n' 'automatic_unknown_fc_rejection_claim=false'
  printf '%s\n' 'adapter_runtime_guard_added=false'
  printf '%s\n' 'core_change=false'
  printf '%s\n' 'projection_profile_change=false'
  printf '%s\n' 'upstream_semantics_confirmation=PENDING_FOLLOW_UP'
} > "$ACCEPTANCE"

printf '%s\n' 'P3 characterization acceptance PASS'
