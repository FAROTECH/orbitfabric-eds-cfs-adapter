# Target Allocation

The EDS-cFS Projection Profile binds OrbitFabric interfaces to **mission-owned cFS TopicId allocation identities**.

It does not assign concrete TopicId values.

```text
OrbitFabric semantics
    -> Projection Profile topic_ref
    -> EDS CFE_MISSION design-parameter reference
    -> selected cFS mission allocation
    -> MissionLib / cFE realization
```

A Profile therefore uses references such as:

```yaml
settings:
  interfaces:
    command:
      name: CMD
      topic_ref: CFE_MISSION/OF_DEMO_CMD_TOPICID
    telemetry:
      name: STATUS_TLM
      topic_ref: CFE_MISSION/OF_DEMO_STATUS_TLM_TOPICID
```

The generated EDS retains these as native design-parameter expressions:

```text
${CFE_MISSION/OF_DEMO_CMD_TOPICID}
${CFE_MISSION/OF_DEMO_STATUS_TLM_TOPICID}
```

The selected cFS mission owns the definitions and values of those symbols.

The pinned SampleMission proof lane included in this repository uses an explicit reference-only allocation fragment under `examples/cfs/sample_mission/`. It realizes the established proof values 160 and 416, but those numbers are not generic adapter policy.

Projection validates the symbolic binding. Native target validation proves that the selected mission can actually resolve and realize it.

The adapter deliberately does not provide a TopicId allocator, a parallel allocation registry, SampleMission-specific universal bounds, or a reimplementation of MissionLib.
