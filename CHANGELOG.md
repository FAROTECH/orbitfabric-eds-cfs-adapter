# Changelog

All notable product changes will be documented here.

## Unreleased

### C2 public release readiness

- rebaselined the product identity from `0.1.0.dev0` to release candidate `0.1.0` without changing projection semantics;
- added one canonical Adapter Source Coordinate: `github.com/FAROTECH:orbitfabric/eds-cfs`;
- bound release construction to the canonical product identity instead of caller-supplied authority/publisher/name values;
- added deterministic Release Descriptor and Project Lock construction for the canonical adapter release;
- added Project Lock lifecycle proof for `MISSING -> INSTALLED -> MATCH -> NOOP`, verify and removal;
- added publisher-only release material that deliberately excludes consumer-owned Project Lock state;
- added public Getting Started documentation and `v0.1.0` release notes;
- added a tag-triggered draft-release workflow that downloads and verifies published bytes before making the GitHub Release public;
- retained Catalog registration as a post-publication C2-B step so the Catalog digest can be taken from the actual published `adapter-release.json` bytes.

### C1 installed lifecycle readiness

- added provider-neutral Release Descriptor construction for the adapter wheel;
- added an OrbitFabric Adapter Manager installed-lifecycle proof;
- proved install and managed-environment verification independently of the checkout package source;
- removed wheel, acquisition wheelhouse and repository `src/` before installed execution;
- executed `eds_cfs_projection` through the installed adapter instance;
- required installed B6 EDS XML, B7 traceability and B8 Integration Result bytes to match the retained accepted goldens exactly;
- retained Project Lock and published-byte release controls for the later C2 gate.

### Mission-owned symbolic target allocation

- replaced Profile-authored numeric cFS TopicIds with mission-owned symbolic `CFE_MISSION/<symbol>` bindings;
- projected symbolic references through native EDS design-parameter syntax;
- retained selected cFS mission ownership of concrete TopicId values and MissionLib ownership of target-specific TopicId-to-MsgId realization;
- retained the pinned SampleMission reference allocations `160` and `416` only as mission fixture evidence;
- added a native fail-closed control for missing mission allocation symbols;
- revalidated CI, B8, B9, B10, P1, P2 and P3 on the promoted symbolic allocation product;
- added no OrbitFabric TopicId registry, automatic allocator, hardcoded SampleMission universal range policy or MissionLib reimplementation.

### P3 negative/conformance characterization complete

- added a dedicated unknown Function Code runtime falsification on the frozen EDS-cFS lane;
- proved that undefined FC 127 can reach the valid generated `payload.enable` typed handler on the pinned runtime;
- added NASA sample_app and EdsLib derived-dispatch controls;
- added an evidence-only EdsLib intervention that fails closed for an unmatched derived selector while preserving FC 0, FC 1 and a genuinely non-derived NASA command;
- closed P3 as an evidence-backed characterization rather than claiming automatic unknown-command rejection;
- added no adapter-local Function Code guard and made no Core semantic change.

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
