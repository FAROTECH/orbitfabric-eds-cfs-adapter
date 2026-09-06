# Integration Coverage

Status: **P2 PROVEN / P3 CONFORMANCE CHARACTERIZED**

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
| undefined command selector automatic runtime rejection | target behavior characterized | a structurally valid OF_DEMO command with undefined FC 127 reaches generated typed dispatch as `payload.enable` on the frozen lane; an evidence-only EdsLib intervention distinguishes unmatched derived dispatch from genuine non-derived dispatch | CHARACTERIZED_NOT_AUTOMATIC |
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

P3 pressure-tests the same promoted runtime lane with an undefined command selector. The retained negative probe is structurally valid for the OF_DEMO command message family but uses Function Code 127, which is absent from the generated OF_DEMO command derivatives.

Observed frozen-lane behavior:

```text
unknown Function Code 127
    -> target ingress
    -> generated EDS dispatch
    -> payload.enable typed handler
```

P3 therefore falsifies the prospective property that every undefined Function Code is automatically rejected before a valid typed handler is reached.

The dedicated evidence-only EdsLib control changes only the disposable pinned upstream build and proves the narrower causal distinction:

```text
known derivative FC 0
    -> payload.enable preserved

known derivative FC 1
    -> payload.set_period preserved

base has derivatives + no derivative matches
    -> fail closed with the candidate distinction

genuinely non-derived SAMPLE_APP/SEND_HK
    -> sole non-derived handler at position zero preserved
```

This control supports the derived-dispatch fallback mechanism as the relevant causal boundary. It is not product code, does not modify the adapter, and does not by itself establish whether upstream semantics are intended or defective.

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

The same evidence rule applies to command-selector conformance:

```text
defined EDS derivative set
    !=
automatic rejection of every undefined runtime discriminator
```

The adapter therefore does not claim automatic unknown-FC rejection on the frozen target lane and does not add a handwritten adapter-side Function Code guard.

Executable command acceptance policy remains part of the target runtime/application realization unless a target-native generic validation mechanism is separately selected and proven.

## Rule

Coverage is expanded only from concrete target evidence. A reusable/versioned public adapter release still requires Target Allocation Readiness and the later repository/release readiness gates.
