from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from jsonschema import ValidationError

from orbitfabric_eds_cfs_adapter.coverage import CoverageError
from orbitfabric_eds_cfs_adapter.input_set import InputSetError, LoadedInputSet, load_input_set
from orbitfabric_eds_cfs_adapter.profile import LoadedProfile, load_profile_with_provenance
from orbitfabric_eds_cfs_adapter.projection.eds_xml import serialize_eds_xml
from orbitfabric_eds_cfs_adapter.projection.model import (
    ProjectionModelError,
    build_projection_model,
)
from orbitfabric_eds_cfs_adapter.projection.resolution import (
    ResolutionError,
    ResolvedProfile,
    resolve_profile,
)
from orbitfabric_eds_cfs_adapter.projection.traceability import (
    TraceabilityError,
    build_traceability,
    serialize_traceability,
)
from orbitfabric_eds_cfs_adapter.result import (
    ARTIFACT_FAILURE,
    EDS_RELATIVE_PATH,
    INPUT_FAILURE,
    PROFILE_FAILURE,
    PROJECTION_FAILURE,
    RESOLUTION_FAILURE,
    RESULT_RELATIVE_PATH,
    TRACEABILITY_RELATIVE_PATH,
    FailureSpec,
    ResultError,
    build_failed_result,
    build_success_result,
    write_failed_result,
    write_result,
)


@dataclass(frozen=True)
class ExecutionOutcome:
    succeeded: bool
    result_path: Path | None
    detail: str | None


def _unlink_owned_file(path: Path) -> None:
    if not path.exists():
        return
    if not path.is_file():
        raise OSError(f"Expected owned output path to be a file: {path}")
    path.unlink()


def _clear_owned_outputs(output_dir: Path) -> None:
    _unlink_owned_file(output_dir / RESULT_RELATIVE_PATH)
    _clear_transient_artifacts(output_dir)


def _clear_transient_artifacts(output_dir: Path) -> None:
    _unlink_owned_file(output_dir / TRACEABILITY_RELATIVE_PATH)
    _unlink_owned_file(output_dir / EDS_RELATIVE_PATH)

    eds_dir = output_dir / EDS_RELATIVE_PATH.parent
    if eds_dir.is_dir():
        try:
            eds_dir.rmdir()
        except OSError:
            # Preserve unrelated caller-owned files that may share this directory.
            pass


def _report_failure(
    output_dir: Path,
    failure: FailureSpec,
    cause: Exception,
    *,
    core: LoadedInputSet | None = None,
    loaded_profile: LoadedProfile | None = None,
    resolved: ResolvedProfile | None = None,
    failed_artifacts: frozenset[str] = frozenset(),
) -> ExecutionOutcome:
    try:
        _clear_transient_artifacts(output_dir)
        result = build_failed_result(
            failure,
            core=core,
            loaded_profile=loaded_profile,
            resolved=resolved,
            failed_artifacts=failed_artifacts,
        )
        result_path = write_failed_result(output_dir, result)
    except (OSError, ResultError, CoverageError) as reporting_error:
        return ExecutionOutcome(
            succeeded=False,
            result_path=None,
            detail=(
                f"{cause}; failed to materialize coherent failure result: "
                f"{reporting_error}"
            ),
        )

    return ExecutionOutcome(
        succeeded=False,
        result_path=result_path,
        detail=str(cause),
    )


def execute_projection(
    input_manifest: Path,
    profile_path: Path,
    output_dir: Path,
) -> ExecutionOutcome:
    """Execute the declared P0 operation with the frozen B9 transaction semantics."""

    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    _clear_owned_outputs(output_dir)

    try:
        core = load_input_set(input_manifest)
    except InputSetError as exc:
        return _report_failure(output_dir, INPUT_FAILURE, exc)

    try:
        loaded_profile = load_profile_with_provenance(profile_path)
    except (ValidationError, ValueError) as exc:
        return _report_failure(
            output_dir,
            PROFILE_FAILURE,
            exc,
            core=core,
        )

    try:
        resolved = resolve_profile(loaded_profile.document, core)
    except ResolutionError as exc:
        return _report_failure(
            output_dir,
            RESOLUTION_FAILURE,
            exc,
            core=core,
            loaded_profile=loaded_profile,
        )

    try:
        model = build_projection_model(resolved)
    except ProjectionModelError as exc:
        return _report_failure(
            output_dir,
            PROJECTION_FAILURE,
            exc,
            core=core,
            loaded_profile=loaded_profile,
            resolved=resolved,
        )

    try:
        xml_bytes = serialize_eds_xml(model)
        eds_path = output_dir / EDS_RELATIVE_PATH
        eds_path.parent.mkdir(parents=True, exist_ok=True)
        eds_path.write_bytes(xml_bytes)
    except (OSError, ValueError) as exc:
        return _report_failure(
            output_dir,
            ARTIFACT_FAILURE,
            exc,
            core=core,
            loaded_profile=loaded_profile,
            resolved=resolved,
            failed_artifacts=frozenset({"eds.package"}),
        )

    try:
        traceability = build_traceability(resolved, model, xml_bytes)
        traceability_bytes = serialize_traceability(traceability)
        traceability_path = output_dir / TRACEABILITY_RELATIVE_PATH
        traceability_path.write_bytes(traceability_bytes)
    except (OSError, TraceabilityError, ValueError) as exc:
        return _report_failure(
            output_dir,
            ARTIFACT_FAILURE,
            exc,
            core=core,
            loaded_profile=loaded_profile,
            resolved=resolved,
            failed_artifacts=frozenset({"eds.package", "traceability"}),
        )

    try:
        result = build_success_result(
            core,
            loaded_profile,
            resolved,
            traceability,
            output_dir,
        )
        result_path = write_result(output_dir, result, traceability)
    except (OSError, ResultError, CoverageError) as exc:
        return _report_failure(
            output_dir,
            ARTIFACT_FAILURE,
            exc,
            core=core,
            loaded_profile=loaded_profile,
            resolved=resolved,
            failed_artifacts=frozenset({"eds.package", "traceability"}),
        )

    return ExecutionOutcome(
        succeeded=True,
        result_path=result_path,
        detail=None,
    )
