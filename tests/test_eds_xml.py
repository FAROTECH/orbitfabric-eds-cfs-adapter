from __future__ import annotations

import hashlib
import xml.etree.ElementTree as ET
from dataclasses import replace
from pathlib import Path

from orbitfabric_eds_cfs_adapter.projection.eds_xml import (
    EDS_NAMESPACE,
    serialize_eds_xml,
    write_eds_xml,
)
from orbitfabric_eds_cfs_adapter.projection.model import (
    BOOLEAN8_SIZE_BITS,
    BOOLEAN8_TYPE,
    EdsContainerType,
    EdsEntry,
    EdsInterface,
    EdsParameterMap,
    EdsProjectionModel,
    EdsValidRange,
    EdsValueConstraint,
    EdsVariable,
)

ROOT = Path(__file__).resolve().parents[1]
GOLDEN = ROOT / "tests" / "fixtures" / "p0_b6" / "expected.xml"
EXPECTED_SHA256 = "e068223bd996321a46a9a276ed7cb64c215d04d11fccb1cf416eaf5225ad887b"


def _model() -> EdsProjectionModel:
    return EdsProjectionModel(
        package_name="OF_DEMO",
        component_name="Application",
        datatypes=(
            EdsContainerType(
                name="CommandBase",
                base_type="CFE_HDR/CommandHeader",
            ),
            EdsContainerType(
                name="PayloadEnableCmd",
                base_type="CommandBase",
                constraints=(
                    EdsValueConstraint(entry="Sec.FunctionCode", value=0),
                ),
            ),
            EdsContainerType(
                name="PayloadSetPeriod_Payload",
                entries=(
                    EdsEntry(
                        name="PeriodMs",
                        type_ref="BASE_TYPES/uint32",
                        valid_range=EdsValidRange(
                            minimum=100,
                            maximum=60000,
                            range_type="inclusiveMinInclusiveMax",
                        ),
                    ),
                ),
            ),
            EdsContainerType(
                name="PayloadSetPeriodCmd",
                base_type="CommandBase",
                entries=(
                    EdsEntry(
                        name="Payload",
                        type_ref="PayloadSetPeriod_Payload",
                    ),
                ),
                constraints=(
                    EdsValueConstraint(entry="Sec.FunctionCode", value=1),
                ),
            ),
            EdsContainerType(
                name="PayloadStatusTlm_Payload",
                entries=(
                    EdsEntry(
                        name="PayloadEnabled",
                        type_ref=BOOLEAN8_TYPE,
                    ),
                    EdsEntry(
                        name="PayloadSampleCount",
                        type_ref="BASE_TYPES/uint32",
                    ),
                ),
            ),
            EdsContainerType(
                name="PayloadStatusTlm",
                base_type="CFE_HDR/TelemetryHeader",
                entries=(
                    EdsEntry(
                        name="Payload",
                        type_ref="PayloadStatusTlm_Payload",
                    ),
                ),
            ),
        ),
        interfaces=(
            EdsInterface(
                name="CMD",
                interface_type="CFE_SB/Telecommand",
                generic_type_name="TelecommandDataType",
                generic_type_ref="CommandBase",
                topic_id=160,
                topic_variable="CMDTopicId",
            ),
            EdsInterface(
                name="STATUS_TLM",
                interface_type="CFE_SB/Telemetry",
                generic_type_name="TelemetryDataType",
                generic_type_ref="PayloadStatusTlm",
                topic_id=416,
                topic_variable="STATUSTLMTopicId",
            ),
        ),
        variables=(
            EdsVariable(
                name="CMDTopicId",
                type_ref="BASE_TYPES/uint16",
                read_only=True,
                initial_value=160,
            ),
            EdsVariable(
                name="STATUSTLMTopicId",
                type_ref="BASE_TYPES/uint16",
                read_only=True,
                initial_value=416,
            ),
        ),
        parameter_maps=(
            EdsParameterMap(
                interface="CMD",
                parameter="TopicId",
                variable_ref="CMDTopicId",
            ),
            EdsParameterMap(
                interface="STATUS_TLM",
                parameter="TopicId",
                variable_ref="STATUSTLMTopicId",
            ),
        ),
    )


def test_serializer_matches_retained_golden_bytes() -> None:
    actual = serialize_eds_xml(_model())
    expected = GOLDEN.read_bytes()

    assert actual == expected
    assert len(actual) == 2921
    assert hashlib.sha256(actual).hexdigest() == EXPECTED_SHA256


def test_repeated_serialization_is_byte_identical() -> None:
    model = _model()
    assert serialize_eds_xml(model) == serialize_eds_xml(model)


def test_file_wrapper_writes_exact_serializer_bytes(tmp_path: Path) -> None:
    model = _model()
    path = tmp_path / "mission.xml"

    write_eds_xml(model, path)

    assert path.read_bytes() == serialize_eds_xml(model)


def test_xml_is_namespace_aware_and_well_formed() -> None:
    root = ET.fromstring(serialize_eds_xml(_model()))
    ns = {"eds": EDS_NAMESPACE}

    assert root.tag == f"{{{EDS_NAMESPACE}}}PackageFile"
    package = root.find("eds:Package", ns)
    assert package is not None
    assert package.attrib == {"name": "OF_DEMO"}
    component = root.find("eds:Package/eds:ComponentSet/eds:Component", ns)
    assert component is not None
    assert component.attrib == {"name": "Application"}


def test_b5_concepts_are_preserved_in_xml() -> None:
    root = ET.fromstring(serialize_eds_xml(_model()))
    ns = {"eds": EDS_NAMESPACE}

    boolean_type = root.find(
        "eds:Package/eds:DataTypeSet/eds:BooleanDataType[@name='Boolean8']",
        ns,
    )
    assert boolean_type is not None
    boolean_encoding = boolean_type.find("eds:BooleanDataEncoding", ns)
    assert boolean_encoding is not None
    assert boolean_encoding.attrib == {"sizeInBits": str(BOOLEAN8_SIZE_BITS)}

    containers = root.findall("eds:Package/eds:DataTypeSet/eds:ContainerDataType", ns)
    assert [item.attrib["name"] for item in containers] == [
        "CommandBase",
        "PayloadEnableCmd",
        "PayloadSetPeriod_Payload",
        "PayloadSetPeriodCmd",
        "PayloadStatusTlm_Payload",
        "PayloadStatusTlm",
    ]

    enabled_entry = root.find(
        ".//eds:ContainerDataType[@name='PayloadStatusTlm_Payload']"
        "/eds:EntryList/eds:Entry[@name='PayloadEnabled']",
        ns,
    )
    assert enabled_entry is not None
    assert enabled_entry.attrib["type"] == BOOLEAN8_TYPE

    period_range = root.find(
        ".//eds:ContainerDataType[@name='PayloadSetPeriod_Payload']"
        "/eds:EntryList/eds:Entry/eds:ValidRange/eds:MinMaxRange",
        ns,
    )
    assert period_range is not None
    assert period_range.attrib == {
        "min": "100",
        "max": "60000",
        "rangeType": "inclusiveMinInclusiveMax",
    }

    constraints = root.findall(".//eds:ValueConstraint", ns)
    assert [item.attrib for item in constraints] == [
        {"entry": "Sec.FunctionCode", "value": "0"},
        {"entry": "Sec.FunctionCode", "value": "1"},
    ]

    variables = root.findall(".//eds:Variable", ns)
    assert [(item.attrib["name"], item.attrib["initialValue"]) for item in variables] == [
        ("CMDTopicId", "160"),
        ("STATUSTLMTopicId", "416"),
    ]


def test_telemetry_entry_order_follows_b5_model_order() -> None:
    model = _model()
    datatypes = list(model.datatypes)
    payload_index = next(
        index for index, item in enumerate(datatypes) if item.name == "PayloadStatusTlm_Payload"
    )
    payload = datatypes[payload_index]
    datatypes[payload_index] = replace(payload, entries=tuple(reversed(payload.entries)))

    root = ET.fromstring(serialize_eds_xml(replace(model, datatypes=tuple(datatypes))))
    ns = {"eds": EDS_NAMESPACE}
    entries = root.findall(
        ".//eds:ContainerDataType[@name='PayloadStatusTlm_Payload']/eds:EntryList/eds:Entry",
        ns,
    )
    assert [item.attrib["name"] for item in entries] == [
        "PayloadSampleCount",
        "PayloadEnabled",
    ]


def test_byte_contract_has_expected_declaration_and_final_newline() -> None:
    payload = serialize_eds_xml(_model())

    assert payload.startswith(b'<?xml version="1.0" encoding="UTF-8"?>\n')
    assert payload.endswith(b"\n")
    assert b"\r\n" not in payload
    assert not payload.startswith(b"\xef\xbb\xbf")
