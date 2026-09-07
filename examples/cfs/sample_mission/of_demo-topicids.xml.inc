<!--
Reference-only cFS SampleMission allocation fragment for OrbitFabric EDS-cFS
native proof lanes.

The reusable adapter does not own these concrete allocations. The selected
mission does. This fragment exists only to make the pinned SampleMission proof
explicit and deterministic.
-->
<Define name="OF_DEMO_CMD_TOPICID"
        value="${CFE_MISSION/TELECOMMAND_BASE_TOPICID} + 151"/>
<Define name="OF_DEMO_STATUS_TLM_TOPICID"
        value="${CFE_MISSION/TELEMETRY_BASE_TOPICID} + 151"/>
