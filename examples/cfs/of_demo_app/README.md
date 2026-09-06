# of_demo_app

`of_demo_app` is the fixed cFS application consumer used by the EDS-cFS integration proof.

It is intentionally separate from adapter-generated output:

```text
OrbitFabric adapter
    -> generates the OF_DEMO EDS contract realization

of_demo_app
    -> consumes the native interfaces generated from that EDS
    -> provides fixed application behavior for build and runtime proofs
```

The application source includes the generated OF_DEMO dictionary and dispatcher headers. This makes its cFS build depend on the EDS boundary rather than on a parallel hand-written message definition.

No EDS XML is committed inside this example directory. Native proof harnesses stage the exact retained adapter B6 artifact into a disposable application workspace before invoking the pinned NASA build.

Current proof scope:

```text
P1
    compile and stage the application through native_eds

P2-A
    run payload.enable through generated EDS dispatch
    publish PayloadStatusTlm
    decode PayloadEnabled=true through the same EDS database host-side

P2-B
    run payload.set_period through generated EDS dispatch
    observe exact typed PeriodMs delivery for 1000, 99 and 60001
```

## P2-B range observation

The authoritative OrbitFabric command argument constraint is projected into EDS as:

```text
PeriodMs
    type       uint32
    ValidRange 100..60000 inclusive
```

The pinned P2-B runtime evidence shows that `cmd_send` and the generated dispatch path still deliver both `99` and `60001` to the typed application handler.

The current `PayloadSetPeriodCmd` handler therefore intentionally **does not add a local hard-coded range check**. Its purpose is to preserve the observed downstream behavior as evidence and make the runtime boundary measurable.

This is not production flight-software guidance.

A production target application remains responsible for the executable command acceptance policy required by its mission unless a target-native generic validation mechanism consuming authoritative generated metadata is separately selected and proven.

The reference proof must not silently duplicate the OrbitFabric `100..60000` constants merely to manufacture runtime rejection.

NASA cFS and EdsLib sources remain external pinned dependencies and are not vendored here.
