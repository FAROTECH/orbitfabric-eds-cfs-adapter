# Reference Project: OrbitFabric Contract to Native cFS Runtime

`of_demo_app` is the fixed cFS application used to prove the native side of the OrbitFabric EDS-cFS Adapter.

It is intentionally small, but it is not a toy message-definition example. Its role is to make one architectural property executable:

> OrbitFabric can define stable mission-level intent, the adapter can project that intent into CCSDS EDS, and a normal cFS application can consume the resulting native EdsLib interfaces without OrbitFabric taking ownership of the cFS application architecture.

The reference project is part of the accepted `0.1.0` evidence surface.

## The complete path

```text
OrbitFabric mission semantics
        |
        v
Core Integration Input Set
        |
        + EDS-cFS Projection Profile
        |
        v
OrbitFabric EDS-cFS Adapter
        |
        v
CCSDS EDS package: OF_DEMO
        |
        + mission-owned CFE_MISSION topic allocations
        |
        v
NASA EdsLib native processing
        |
        + generated OF_DEMO types
        + generated OF_DEMO dispatcher
        |
        v
fixed of_demo_app
        |
        v
cFS Software Bus
        |
        v
native command / telemetry runtime evidence
```

The important word in that path is **fixed**.

The adapter does not generate the application implementation. The application is product-owned reference code that must compile and run against the native interfaces produced from the EDS contract.

## Why a fixed cFS application matters

A projection can look convincing while still avoiding the real downstream integration boundary.

For example, a test could generate EDS XML and then validate only that XML, while the application continues to use unrelated hand-written command structures, message IDs or dispatch logic.

This reference project prevents that shortcut.

Its source directly includes generated OF_DEMO headers:

```c
#include "of_demo_eds_dictionary.h"
#include "of_demo_eds_dispatcher.h"
#include "of_demo_eds_typedefs.h"
```

The handlers receive generated typed payloads:

```text
OF_DEMO_PayloadEnableCmd_t
OF_DEMO_PayloadSetPeriodCmd_t
OF_DEMO_PayloadStatusTlm_t
```

and command routing goes through:

```text
EdsDispatch_EdsComponent_OF_DEMO_Application_Telecommand(...)
```

There is no parallel hand-written OF_DEMO message contract in this example.

If the EDS is removed from the native build lane, the application is required to stop building successfully. That negative dependency control is part of P1.

## Mission-owned topic allocation

The reference project also exercises the target-allocation ownership boundary.

The reusable Projection Profile binds the two interfaces to symbolic mission identities:

```text
CFE_MISSION/OF_DEMO_CMD_TOPICID
CFE_MISSION/OF_DEMO_STATUS_TLM_TOPICID
```

The generated EDS carries those symbolic design-parameter references. The selected cFS mission owns their concrete values.

For the retained SampleMission proof lane they resolve to:

```text
OF_DEMO_CMD_TOPICID        -> 160
OF_DEMO_STATUS_TLM_TOPICID -> 416
```

Those values are not embedded as local numeric policy in `of_demo_app`.

The application consumes the mission-generated EDS design parameters through:

```c
#include "cfe_mission_eds_designparameters.h"

EdsParam_CFE_MISSION_OF_DEMO_CMD_TOPICID
EdsParam_CFE_MISSION_OF_DEMO_STATUS_TLM_TOPICID
```

This means the authority chain remains:

```text
Profile
    -> allocation identity

selected cFS mission
    -> concrete TopicId

EDS design parameters
    -> application-visible value

MissionLib / cFE
    -> TopicId to MsgId realization
```

The application does not become a second authority for the allocation.

A separate native negative control removes one required mission allocation and requires EDS processing to fail closed.

## The reference mission slice

The retained OrbitFabric contract exercises two commands and one telemetry packet.

### `payload.enable`

The command has no application payload.

```text
OrbitFabric command
    payload.enable

Profile
    Function Code 0

EDS
    PayloadEnableCmd

of_demo_app
    OF_DEMO_APP_PayloadEnableCmd(...)
```

The handler changes the reference application state and emits `PayloadStatusTlm`.

### `payload.set_period(period_ms)`

The command carries a typed `uint32` argument:

```text
period_ms
```

with OrbitFabric semantic range:

```text
100..60000 inclusive
```

The adapter projects that constraint into EDS as a `ValidRange`, and the generated handler surface delivers:

```text
Msg->Payload.PeriodMs
```

The reference application records the exact typed value it receives.

### `payload_status`

The telemetry packet carries:

```text
payload.enabled
payload.sample_count
```

and is materialized as generated `OF_DEMO_PayloadStatusTlm_t` telemetry.

## P1: complete native build dependency

P1 answers a narrow question:

> Does a fixed cFS application really depend on interfaces generated from the OrbitFabric-derived EDS?

The proof stages the exact retained EDS artifact into a disposable external application workspace and runs the pinned cFS EDS-enabled build:

```text
native_eds.prep
native_eds.compile
native_eds.install
```

Acceptance requires evidence that:

1. `of_demo_app.c` participates in the native compile database.
2. the application is compiled and linked as `of_demo_app.so`;
3. the application is installed into the staged cFS mission;
4. `core-cpu1` is produced;
5. the generated OF_DEMO headers are actual build dependencies.

The negative control removes the staged OF_DEMO EDS and requires the native consumer build to fail.

This is what turns the EDS from a generated document into a real software integration boundary.

## P2: native runtime closed loop

P2 runs the same application inside the pinned cFS mission.

The nominal command/telemetry path is:

```text
payload.enable
    -> EDS-enabled cmd_send
    -> cFS / ci_lab
    -> Software Bus
    -> generated OF_DEMO dispatcher
    -> OF_DEMO_APP_PayloadEnableCmd
    -> generated PayloadStatusTlm
    -> to_lab
    -> EDS-enabled tlm_recv
    -> PayloadEnabled=true
```

The proof therefore crosses both sides of the generated contract:

```text
host encoder
    -> wire packet
    -> cFS ingress
    -> generated typed dispatch
    -> fixed application
    -> generated typed telemetry
    -> cFS egress
    -> host decoder
```

It is not a direct function call test.

## P2-B: range metadata versus runtime policy

`payload.set_period` is also used as a conformance probe.

The authoritative OrbitFabric argument constraint is projected into EDS as:

```text
PeriodMs
    type       uint32
    ValidRange 100..60000 inclusive
```

The frozen native runtime lane is then exercised with:

```text
1000   in range
99     below range
60001  above range
```

All three values are encoded, dispatched and delivered to the typed application handler on the validated lane.

That evidence establishes an important boundary:

```text
constraint represented in EDS
    !=
automatic runtime enforcement on this path
```

The reference handler intentionally does **not** add a duplicate local `100..60000` guard merely to force a different result.

This is not production flight-software guidance. A real target application remains responsible for the executable command acceptance policy required by its mission unless an appropriate target-native generic validator is separately selected and proven.

## P3: negative conformance characterization

P3 sends a structurally valid OF_DEMO command using undefined Function Code `127`.

The prospective property under test was:

```text
valid OF_DEMO command family
+ undefined Function Code 127
-> no valid generated typed handler
```

The observed frozen lane instead produces:

```text
Function Code 127
    -> target ingress
    -> generated EDS dispatch
    -> payload.enable typed handler
```

The adapter records that behavior as target characterization.

It does not add a handwritten Function Code table or application-local dispatcher guard merely to make the negative test reject the packet.

A dedicated EdsLib causal control is kept separate from the product application and is used only to localize the observed behavior.

## What changes and what stays owned

| Concern | Owner in this reference project |
| --- | --- |
| command and telemetry semantic identity | OrbitFabric |
| Integration Input Set contract | OrbitFabric Core |
| EDS-cFS target bindings | Projection Profile |
| CCSDS EDS realization | adapter |
| concrete TopicId allocation | selected cFS mission |
| TopicId to MsgId realization | MissionLib / cFE |
| generated C types and dispatcher | EdsLib toolchain |
| application behavior | `of_demo_app` |
| executable command acceptance policy | target application / runtime |
| native build and runtime semantics | cFS / EdsLib lane |

This separation is the point of the reference project.

## What this project proves

The retained proof suite establishes that, on the exact supported lane:

- an OrbitFabric-derived EDS is accepted by native EdsLib processing;
- the fixed cFS application has a real build dependency on generated OF_DEMO interfaces;
- mission-owned symbolic allocations resolve through native cFS EDS design parameters;
- generated command types reach fixed typed handlers at runtime;
- generated telemetry types return through the cFS Software Bus and EDS-enabled host decoder;
- typed command arguments survive the complete runtime path;
- observed constraint and unknown-Function-Code behavior is characterized rather than hidden;
- the same application can be used for positive, negative and causal evidence without moving the ownership boundary into OrbitFabric.

## What this project does not prove

It does not claim that:

- OrbitFabric generates a complete cFS mission;
- OrbitFabric owns cFS TopicId allocation;
- all cFS missions use SampleMission allocation rules;
- all EDS `ValidRange` constraints are automatically enforced at runtime;
- all unknown Function Codes are automatically rejected;
- the `0.1.0` adapter supports every CCSDS EDS or cFS integration pattern.

Those non-claims are deliberate. The reference project is designed to make the proven boundary strong without turning a narrow first release into a claim about the entire cFS/EDS design space.

## Reproducing the native proofs

The canonical CI harnesses are:

```text
.github/scripts/p1-native-eds-build.sh
.github/scripts/p2-generated-api-probe.sh
.github/scripts/p2-runtime-proof.sh
.github/scripts/p3-conformance-proof.sh
.github/scripts/b10-native-edslib.sh
```

They clone exact NASA baselines into disposable workspaces, stage the reference mission allocations and the retained EDS artifact, and keep NASA source code outside this repository.

The validated baseline is:

```text
NASA cFS v7.0.1
    088b2fa828db9ff7e00733f1908e0eeb59f66ce3

NASA EdsLib v7.0.1
    2acc963b34f77692c6396555dcfb10ef43eb1046

NASA cFE
    c5fb2b4d540bd55eb6c3707da7dd13eee679d4dd
```

Additional sample applications and command-line tools are pinned by exact commit inside the individual proof harnesses.

## Why this matters to a cFS / EDS integrator

The interesting property is not that OrbitFabric can emit XML.

It is that one mission-level contract can cross a standards-backed boundary and become a **real native dependency** of a conventional cFS application while preserving target ownership:

```text
stable mission meaning
    -> explicit EDS projection
    -> mission-owned allocation
    -> native generated API
    -> application-owned implementation
    -> observable runtime behavior
```

That is the boundary this reference project exists to make reviewable, repeatable and falsifiable.
