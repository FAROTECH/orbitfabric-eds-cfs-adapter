# P0 B1 Core fixture

This directory owns the minimal OrbitFabric Mission Model used to generate the retained P0/B1 Core Integration Input Set.

## Frozen proof semantics

```text
subsystem
    payload

telemetry
    payload.enabled        bool
    payload.sample_count   uint32

commands
    payload.enable
    payload.set_period(period_ms: uint32, 100..60000)

packet
    payload_status
        payload.enabled
        payload.sample_count
```

## Fixture scaffolding

OrbitFabric Core requires a canonical mission directory with all required domain files and mandatory fields. Fields such as spacecraft metadata, one initial mode, telemetry operational metadata, command risk/ack policy and packet transport metadata are present only to make the mission a valid Core model.

Their presence does **not** mean that the EDS-cFS adapter consumes them. B2 audits the generated Integration Input Set and freezes only the Core surfaces and fields actually required for deterministic EDS projection.

The mission intentionally contains no events, faults, optional payload contract, data products, contacts or commandability extensions.

## Core baseline

The fixture is generated only with OrbitFabric Core `v1.3.0` at commit:

```text
a25917e81c90396df2b189834e83cf852fa4da5f
```

Generated Core output is retained under `integration_input/` after B1 acceptance.
