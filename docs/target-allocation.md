# Target Allocation

The EDS-cFS Projection Profile binds OrbitFabric interfaces to mission-owned cFS topic allocation identities. It does not own the concrete TopicId values used by a selected cFS mission.

## Ownership

```text
OrbitFabric Core
    mission semantics

EDS-cFS Projection Profile
    interface -> CFE_MISSION allocation identity

selected cFS mission
    concrete TopicId allocation

MissionLib / cFE
    mission-specific TopicId -> MsgId realization

native selected-mission proof
    final realization authority
```

For the retained reference slice, the Profile uses:

```yaml
interfaces:
  command:
    name: CMD
    topic_ref: CFE_MISSION/OF_DEMO_CMD_TOPICID
  telemetry:
    name: STATUS_TLM
    topic_ref: CFE_MISSION/OF_DEMO_STATUS_TLM_TOPICID
```

The generated EDS therefore carries native design-parameter references:

```text
${CFE_MISSION/OF_DEMO_CMD_TOPICID}
${CFE_MISSION/OF_DEMO_STATUS_TLM_TOPICID}
```

The reusable adapter does not assign numeric values to these identities.

## Reference mission

The disposable pinned SampleMission proof lane defines the two required identities in its mission-owned `CFE_MISSION` topic registry. For that selected mission they resolve to:

```text
OF_DEMO_CMD_TOPICID         -> 160
OF_DEMO_STATUS_TLM_TOPICID  -> 416
```

Those values are reference-mission evidence, not universal cFS constraints.

## Failure semantics

A Profile that uses the old numeric `topic_id` form is rejected by the pre-v0.1 Profile schema.

A selected cFS mission that does not define a required symbolic allocation must fail native EDS processing. The adapter does not invent a fallback TopicId and does not reimplement MissionLib allocation rules.

## Deliberate non-goals for v0.1

The adapter does not provide:

- an OrbitFabric-owned topic allocation registry;
- automatic TopicId allocation;
- a generic MissionLib resolver;
- SampleMission range rules as universal cFS validation;
- parallel numeric and symbolic Profile modes;
- authoritative mutation of a user's cFS mission configuration.

Native validation against the selected mission remains required release evidence.
