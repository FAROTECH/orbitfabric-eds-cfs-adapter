# Changelog

All notable product changes will be documented here.

## Unreleased

### P3 negative/conformance characterization complete

- added a dedicated unknown Function Code runtime falsification on the frozen EDS-cFS lane;
- proved that undefined FC 127 can reach the valid generated `payload.enable` typed handler on the pinned runtime;
- added NASA sample_app and EdsLib derived-dispatch controls;
- added an evidence-only EdsLib intervention that fails closed for an unmatched derived selector while preserving FC 0, FC 1 and a genuinely non-derived NASA command;
- closed P3 as an evidence-backed characterization rather than claiming automatic unknown-command rejection;
- added no adapter-local Function Code guard and made no Core or Projection Profile change.

### P2 runtime proof complete

- evolved the fixed `of_demo_app` from build consumer to EDS-backed runtime consumer;
- added pinned generated-API and runtime proof harnesses;
- proved `payload.enable` command dispatch and `PayloadStatusTlm` EDS encode/decode through the native cFS runtime lane;
- proved typed `payload.set_period(PeriodMs)` delivery;
- characterized projected `ValidRange 100..60000` versus runtime behavior, including retained `1000`, `99` and `60001` observations;
- retained the ownership rule that projected constraints do not imply automatic runtime enforcement.

### P1 complete native build

- added a product-owned fixed cFS application that consumes generated OF_DEMO interfaces;
- proved exact pinned `native_eds.prep`, `native_eds.compile` and `native_eds.install` participation;
- proved fixed-app source participation through the composed native build compile databases;
- proved staged `of_demo_app.so` and `core-cpu1` artifacts;
- added a dependency negative control showing the fixed app fails when the OF_DEMO EDS source is removed.

### P0 projection proof complete

- froze the Core Integration Input Set consumption boundary and EDS-cFS Projection Profile;
- implemented deterministic internal projection, EDS XML, machine-readable traceability and Core-conformant Integration Result generation;
- implemented deterministic failure semantics and rollback behavior;
- validated the retained EDS artifact through the exact pinned NASA cFS / EdsLib native lane;
- corrected the adapter-owned Core `bool` target realization to byte-aligned EDS `Boolean8` after native evidence falsified the initial one-bit realization.

### Bootstrap

- established final repository/package identity and clean bootstrap conformity;
- added the Integration Package Manifest, CLI execution identity, packaging, tests and repository conformance controls.

No public versioned release has been published yet.
