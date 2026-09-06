# Integration Coverage

Status: **P2-A PROVEN / P2-B RUNTIME CHARACTERIZED**

This document records only coverage established by retained evidence. Repository presence or upstream cFS/EDS capability must not be interpreted as broader OrbitFabric coverage.

## Current disposition

| OrbitFabric semantic area | Target applicability | Adapter scope | Status |
|---|---|---|---|
| command identity | applicable | projected into EDS command interfaces/containers | P0_PROVEN |
| command arguments/types/constraints | applicable | Core command signatures and min/max constraints projected for the frozen proof slice | P0_PROVEN |
| telemetry identity/types | applicable | projected into EDS telemetry payload/message types | P0_PROVEN |
| packet membership | applicable | projected from Core `packet_includes_telemetry` membership plus Profile field order | P0_PROVEN |
| command sequence | applicable as source traceability | retained in mapping/evidence boundary; no cFS runtime sequence engine claimed | TRACEABILITY_ONLY |
| expected outputs | applicable as source traceability | retained in mapping/evidence boundary; generic ACK semantics not claimed | TRACEABILITY_ONLY |
| relationships | narrowly applicable | `packet_includes_telemetry` is the only consumed relationship family | P0_PROVEN |
| native EDS processing | applicable | exact retained B6 processed by pinned EdsLib/cFS lane | P0_PROVEN |
| complete native cFS build/install | applicable | fixed `of_demo_app` consumes generated OF_DEMO interfaces | P1_PROVEN |
| runtime command dispatch | applicable | `payload.enable` and typed `payload.set_period(PeriodMs)` reach generated OF_DEMO dispatch/handlers | P2_PROVEN |
| runtime telemetry encode/decode | applicable | `PayloadStatusTlm` is transmitted and EDS-decoded with `PayloadEnabled=true` | P2_PROVEN |
| command constraint automatic runtime enforcement | target behavior characterized | `PeriodMs` `ValidRange 100..60000` is retained in EDS; pinned host encoder/generated dispatch still deliver `99` and `60001` to the typed application handler | CHARACTERIZED_NOT_AUTOMATIC |
| scenarios | outside current proof | not implemented | OUT_OF_SCOPE |

## Proven boundaries

P0 establishes deterministic projection, traceability, Integration Result behavior, failure semantics and native EdsLib processing for the frozen OF_DEMO mission slice.

P1 establishes dependency of a fixed cFS application on generated OF_DEMO interfaces and proves complete pinned `native_eds` compile/install staging. It does not by itself prove runtime behavior.

P2-A proves the retained EDS-backed runtime closed loop:

```text
payload.enable
    -> EDS-enabled host command encoding
    -> ci_lab / cFS Software Bus
    -> generated OF_DEMO dispatch
    -> fixed typed handler
    -> PayloadStatusTlm
    -> to_lab
    -> EDS-enabled host telemetry decode
    -> PayloadEnabled=true
```

P2-B proves typed `PeriodMs` delivery through the same generated command path. The retained observation shows `1000`, `99`, and `60001` are all encoded, sent, generated-dispatched and delivered exactly to the typed handler on the pinned lane.

## Constraint projection versus enforcement

For the current proof slice:

```text
Core command argument constraint
    period_ms: 100..60000

adapter projection
    EDS Entry PeriodMs + ValidRange 100..60000

pinned runtime behavior
    no automatic range rejection observed before typed application delivery
```

Therefore:

```text
projected constraint
    !=
automatically enforced runtime constraint
```

The adapter claims faithful projection of the Core constraint into EDS. It does not claim that EdsLib/cFS automatically enforces every projected `ValidRange` in every runtime path.

Executable command acceptance policy remains part of the target runtime/application realization unless a target-native generic validation mechanism is separately selected and proven.

## Rule

Coverage is expanded only from concrete target evidence. A reusable/versioned public adapter release still requires a complete Target Applicable Surface review and the later repository/release readiness gates.
