# Changelog

All notable product changes will be documented here.

## Unreleased

### P2 runtime proof in progress

- evolved the fixed `of_demo_app` from build consumer to EDS-backed runtime consumer;
- added pinned generated-API and runtime proof harnesses;
- runtime acceptance remains open and is not claimed complete yet.

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
