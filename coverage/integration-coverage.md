# Integration Coverage

Status: **P1 PROVEN / P2 RUNTIME IN PROGRESS**

This document records only coverage established by retained evidence. Repository presence or upstream cFS/EDS capability must not be interpreted as broader OrbitFabric coverage.

## Current disposition

| OrbitFabric semantic area | Target applicability | Adapter scope | Status |
|---|---|---|---|
| command identity | applicable | projected into EDS command interfaces/containers | P0_PROVEN |
| command arguments/types/constraints | applicable | projected for the frozen proof slice | P0_PROVEN |
| telemetry identity/types | applicable | projected into EDS telemetry payload/message types | P0_PROVEN |
| packet membership | applicable | projected from Core `packet_includes_telemetry` membership plus Profile field order | P0_PROVEN |
| command sequence | applicable as source traceability | retained in mapping/evidence boundary; no cFS runtime sequence engine claimed | TRACEABILITY_ONLY |
| expected outputs | applicable as source traceability | retained in mapping/evidence boundary; generic ACK semantics not claimed | TRACEABILITY_ONLY |
| relationships | narrowly applicable | `packet_includes_telemetry` is the only consumed relationship family | P0_PROVEN |
| native EDS processing | applicable | exact retained B6 processed by pinned EdsLib/cFS lane | P0_PROVEN |
| complete native cFS build/install | applicable | fixed `of_demo_app` consumes generated OF_DEMO interfaces | P1_PROVEN |
| runtime command dispatch | applicable | first `payload.enable` generated-dispatch slice | P2_IN_PROGRESS |
| runtime telemetry encode/decode | applicable | first `PayloadStatusTlm` / `PayloadEnabled=true` slice | P2_IN_PROGRESS |
| scenarios | outside current proof | not implemented | OUT_OF_SCOPE |

## Proven boundaries

P0 establishes deterministic projection, traceability, Integration Result behavior, failure semantics and native EdsLib processing for the frozen OF_DEMO mission slice.

P1 establishes dependency of a fixed cFS application on generated OF_DEMO interfaces and proves complete pinned `native_eds` compile/install staging. It does not prove runtime behavior.

P2 is intentionally narrow. Runtime acceptance is not complete until the retained end-to-end command/telemetry proof passes on the pinned lane.

## Rule

Coverage is expanded only from concrete target evidence. A reusable/versioned public adapter release still requires a complete Target Applicable Surface review and the later repository/release readiness gates.
