"""Generate a small IFC4 model with known evacuation topology.

The fixture contains three spaces, two internal doors, and one final exit. It is
generated rather than committed because IFC payloads are intentionally ignored by
the repository. Stable GUIDs keep entity identity consistent between runs.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import ifcopenshell
from ifcopenshell import guid


NAMESPACE = "https://github.com/janakjocee/bim_evacuation_system_final/controlled-ifc/v1"


def stable_guid(label: str) -> str:
    """Return a valid compressed IFC GUID derived from a stable label."""
    value = uuid5(NAMESPACE_URL, f"{NAMESPACE}:{label}")
    return guid.compress(value.hex)


def _aggregate(model, parent, children, label: str) -> None:
    model.create_entity(
        "IfcRelAggregates",
        GlobalId=stable_guid(f"aggregate:{label}"),
        OwnerHistory=None,
        Name=None,
        Description=None,
        RelatingObject=parent,
        RelatedObjects=children,
    )


def _add_area(model, space, area: float) -> None:
    quantity = model.create_entity(
        "IfcQuantityArea",
        Name="NetFloorArea",
        Description="Controlled ground-truth area",
        Unit=None,
        AreaValue=area,
        Formula=None,
    )
    quantities = model.create_entity(
        "IfcElementQuantity",
        GlobalId=stable_guid(f"quantity-set:{space.GlobalId}"),
        OwnerHistory=None,
        Name="BaseQuantities",
        Description="Controlled evaluation quantities",
        MethodOfMeasurement=None,
        Quantities=[quantity],
    )
    model.create_entity(
        "IfcRelDefinesByProperties",
        GlobalId=stable_guid(f"quantity-relation:{space.GlobalId}"),
        OwnerHistory=None,
        Name=None,
        Description=None,
        RelatedObjects=[space],
        RelatingPropertyDefinition=quantities,
    )


def _boundary(model, space, door, label: str, boundary_type: str = "INTERNAL") -> None:
    model.create_entity(
        "IfcRelSpaceBoundary",
        GlobalId=stable_guid(f"boundary:{label}"),
        OwnerHistory=None,
        Name=label,
        Description="Controlled door-space relationship",
        RelatingSpace=space,
        RelatedBuildingElement=door,
        ConnectionGeometry=None,
        PhysicalOrVirtualBoundary="PHYSICAL",
        InternalOrExternalBoundary=boundary_type,
    )


def build_controlled_ifc(output_path: Path) -> Path:
    """Build and write the controlled semantic IFC fixture."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    model = ifcopenshell.file(schema="IFC4")
    model.header.file_name.name = "controlled_semantic_evacuation.ifc"
    model.header.file_name.time_stamp = "2026-01-01T00:00:00"
    model.header.file_name.author = ("Janak Raj Joshi",)
    model.header.file_name.organization = ("University of Greenwich",)
    model.header.file_name.preprocessor_version = "BIM Evacuation controlled fixture v1"
    model.header.file_name.originating_system = "BIM Evacuation controlled fixture v1"

    metre = model.create_entity("IfcSIUnit", UnitType="LENGTHUNIT", Prefix=None, Name="METRE")
    square_metre = model.create_entity("IfcSIUnit", UnitType="AREAUNIT", Prefix=None, Name="SQUARE_METRE")
    units = model.create_entity("IfcUnitAssignment", Units=[metre, square_metre])

    project = model.create_entity(
        "IfcProject",
        GlobalId=stable_guid("project"),
        OwnerHistory=None,
        Name="Controlled Evacuation Evaluation",
        Description="Project-generated IFC for parser and route ground-truth evaluation",
        ObjectType=None,
        LongName=None,
        Phase=None,
        RepresentationContexts=None,
        UnitsInContext=units,
    )
    site = model.create_entity(
        "IfcSite",
        GlobalId=stable_guid("site"),
        OwnerHistory=None,
        Name="Evaluation Site",
        Description=None,
        ObjectType=None,
        ObjectPlacement=None,
        Representation=None,
        LongName=None,
        CompositionType="ELEMENT",
        RefLatitude=None,
        RefLongitude=None,
        RefElevation=None,
        LandTitleNumber=None,
        SiteAddress=None,
    )
    building = model.create_entity(
        "IfcBuilding",
        GlobalId=stable_guid("building"),
        OwnerHistory=None,
        Name="Controlled Semantic Building",
        Description=None,
        ObjectType=None,
        ObjectPlacement=None,
        Representation=None,
        LongName=None,
        CompositionType="ELEMENT",
        ElevationOfRefHeight=None,
        ElevationOfTerrain=None,
        BuildingAddress=None,
    )
    storey = model.create_entity(
        "IfcBuildingStorey",
        GlobalId=stable_guid("storey"),
        OwnerHistory=None,
        Name="Ground Floor",
        Description=None,
        ObjectType=None,
        ObjectPlacement=None,
        Representation=None,
        LongName=None,
        CompositionType="ELEMENT",
        Elevation=0.0,
    )
    _aggregate(model, project, [site], "project-site")
    _aggregate(model, site, [building], "site-building")
    _aggregate(model, building, [storey], "building-storey")

    space_specs = [
        ("office", "S-OFFICE", "Office 101", 20.0),
        ("corridor", "S-CORRIDOR", "Main Corridor", 30.0),
        ("kitchen", "S-KITCHEN", "Kitchen", 15.0),
    ]
    spaces = {}
    for key, name, long_name, area in space_specs:
        space = model.create_entity(
            "IfcSpace",
            GlobalId=stable_guid(f"space:{key}"),
            OwnerHistory=None,
            Name=name,
            Description="Controlled evaluation space",
            ObjectType=None,
            ObjectPlacement=None,
            Representation=None,
            LongName=long_name,
            CompositionType="ELEMENT",
            PredefinedType="INTERNAL",
            ElevationWithFlooring=None,
        )
        spaces[key] = space
        _add_area(model, space, area)
    _aggregate(model, storey, list(spaces.values()), "storey-spaces")

    door_specs = [
        ("office", "Office Door", 0.9),
        ("kitchen", "Kitchen Door", 0.9),
        ("exit", "Final Exit", 1.2),
    ]
    doors = {}
    for key, name, width in door_specs:
        doors[key] = model.create_entity(
            "IfcDoor",
            GlobalId=stable_guid(f"door:{key}"),
            OwnerHistory=None,
            Name=name,
            Description="Controlled evaluation door",
            ObjectType=None,
            ObjectPlacement=None,
            Representation=None,
            Tag=None,
            OverallHeight=2.1,
            OverallWidth=width,
            PredefinedType="DOOR",
            OperationType="NOTDEFINED",
            UserDefinedOperationType=None,
        )
    model.create_entity(
        "IfcRelContainedInSpatialStructure",
        GlobalId=stable_guid("contained:doors"),
        OwnerHistory=None,
        Name=None,
        Description=None,
        RelatedElements=list(doors.values()),
        RelatingStructure=storey,
    )

    _boundary(model, spaces["office"], doors["office"], "office-office-door")
    _boundary(model, spaces["corridor"], doors["office"], "corridor-office-door")
    _boundary(model, spaces["kitchen"], doors["kitchen"], "kitchen-kitchen-door")
    _boundary(model, spaces["corridor"], doors["kitchen"], "corridor-kitchen-door")
    _boundary(model, spaces["corridor"], doors["exit"], "corridor-final-exit", "EXTERNAL")

    model.write(str(output_path))
    return output_path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/generated/controlled_semantic_evacuation.ifc"),
    )
    args = parser.parse_args()
    generated = build_controlled_ifc(args.output)
    print(generated.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
