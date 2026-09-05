from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path

from orbitfabric_eds_cfs_adapter.projection.model import EdsProjectionModel

EDS_NAMESPACE = "http://www.ccsds.org/schema/sois/seds"
XML_DECLARATION = b'<?xml version="1.0" encoding="UTF-8"?>\n'


def _serialize_container(parent: ET.Element, container) -> None:
    attributes = {"name": container.name}
    if container.base_type is not None:
        attributes["baseType"] = container.base_type
    element = ET.SubElement(parent, "ContainerDataType", attributes)

    if container.constraints:
        constraint_set = ET.SubElement(element, "ConstraintSet")
        for constraint in container.constraints:
            ET.SubElement(
                constraint_set,
                "ValueConstraint",
                {
                    "entry": constraint.entry,
                    "value": str(constraint.value),
                },
            )

    if container.entries:
        entry_list = ET.SubElement(element, "EntryList")
        for entry in container.entries:
            entry_element = ET.SubElement(
                entry_list,
                "Entry",
                {
                    "name": entry.name,
                    "type": entry.type_ref,
                },
            )
            if entry.valid_range is not None:
                valid_range = ET.SubElement(entry_element, "ValidRange")
                range_attributes: dict[str, str] = {}
                if entry.valid_range.minimum is not None:
                    range_attributes["min"] = str(entry.valid_range.minimum)
                if entry.valid_range.maximum is not None:
                    range_attributes["max"] = str(entry.valid_range.maximum)
                range_attributes["rangeType"] = entry.valid_range.range_type
                ET.SubElement(valid_range, "MinMaxRange", range_attributes)


def serialize_eds_xml(model: EdsProjectionModel) -> bytes:
    """Serialize one accepted B5 model into deterministic P0 EDS XML bytes."""

    root = ET.Element("PackageFile", {"xmlns": EDS_NAMESPACE})
    package = ET.SubElement(root, "Package", {"name": model.package_name})

    data_type_set = ET.SubElement(package, "DataTypeSet")
    for container in model.datatypes:
        _serialize_container(data_type_set, container)

    component_set = ET.SubElement(package, "ComponentSet")
    component = ET.SubElement(
        component_set,
        "Component",
        {"name": model.component_name},
    )

    required_interfaces = ET.SubElement(component, "RequiredInterfaceSet")
    for interface in model.interfaces:
        interface_element = ET.SubElement(
            required_interfaces,
            "Interface",
            {
                "name": interface.name,
                "type": interface.interface_type,
            },
        )
        generic_maps = ET.SubElement(interface_element, "GenericTypeMapSet")
        ET.SubElement(
            generic_maps,
            "GenericTypeMap",
            {
                "name": interface.generic_type_name,
                "type": interface.generic_type_ref,
            },
        )

    implementation = ET.SubElement(component, "Implementation")
    variable_set = ET.SubElement(implementation, "VariableSet")
    for variable in model.variables:
        ET.SubElement(
            variable_set,
            "Variable",
            {
                "type": variable.type_ref,
                "readOnly": "true" if variable.read_only else "false",
                "name": variable.name,
                "initialValue": str(variable.initial_value),
            },
        )

    parameter_map_set = ET.SubElement(implementation, "ParameterMapSet")
    for parameter_map in model.parameter_maps:
        ET.SubElement(
            parameter_map_set,
            "ParameterMap",
            {
                "interface": parameter_map.interface,
                "parameter": parameter_map.parameter,
                "variableRef": parameter_map.variable_ref,
            },
        )

    ET.indent(root, space="  ")
    body = ET.tostring(
        root,
        encoding="utf-8",
        xml_declaration=False,
        short_empty_elements=True,
    )
    return XML_DECLARATION + body + b"\n"


def write_eds_xml(model: EdsProjectionModel, path: Path) -> None:
    """Write the exact deterministic bytes returned by `serialize_eds_xml`."""

    path.write_bytes(serialize_eds_xml(model))
