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

P2
    start the application and exercise command and telemetry behavior
```

NASA cFS and EdsLib sources remain external pinned dependencies and are not vendored here.
