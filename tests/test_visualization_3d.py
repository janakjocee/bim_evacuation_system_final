"""Tests for the interactive 3D visualization layer."""

from src.bim_processing.ifc_parser import BuildingData, DoorData, Point3D, SpaceData
from src.scenario.worst_case_engine import WorstCaseScenarioEngine, load_worst_case_dataset
from src.ui.visualization_3d import (
    create_dataset_3d_figure,
    create_ifc_3d_figure,
    create_ifc_plan_figure,
)


def test_ifc_3d_figure_contains_geometry_connections_and_exit():
    building = BuildingData(id="B1", name="Visual Test")
    building.spaces["S1"] = SpaceData(
        id="S1",
        name="Room",
        area=20,
        bounding_box=(Point3D(0, 0, 0), Point3D(5, 4, 3)),
    )
    exit_door = DoorData(
        id="E1",
        name="Exit",
        width=1.2,
        height=2.1,
        location=Point3D(5, 2, 0),
        is_exit=True,
        connected_spaces=["S1"],
    )
    building.doors["E1"] = exit_door
    building.exits["E1"] = exit_door

    figure = create_ifc_3d_figure(building)

    assert len(figure.data) == 4
    assert figure.data[0].type == "mesh3d"
    assert figure.data[-1].name == "Exits / inferred egress"


def test_ifc_plan_figure_contains_footprint_route_and_exit():
    building = BuildingData(id="B1", name="Plan Test")
    building.spaces["S1"] = SpaceData(
        id="S1",
        name="IfcSlab: Ground Floor",
        area=20,
        bounding_box=(Point3D(0, 0, 0), Point3D(5, 4, 0.3)),
    )
    exit_door = DoorData(
        id="E1",
        name="Exit",
        width=1.2,
        height=2.1,
        location=Point3D(5, 2, 0),
        is_exit=True,
        connected_spaces=["S1"],
    )
    building.doors["E1"] = exit_door
    building.exits["E1"] = exit_door

    figure = create_ifc_plan_figure(building)

    assert len(figure.data) == 3
    assert figure.data[0].fill == "toself"
    assert figure.data[-1].marker.symbol == "diamond"


def test_demo_3d_figure_is_deterministic_schematic():
    engine = WorstCaseScenarioEngine(load_worst_case_dataset())

    first = create_dataset_3d_figure(engine, fire_origin="R5", smoke_nodes=["C1"])
    second = create_dataset_3d_figure(engine, fire_origin="R5", smoke_nodes=["C1"])

    assert len(first.data) == 2
    assert first.data[1].type == "scatter3d"
    assert list(first.data[1].x) == list(second.data[1].x)
    assert "not BIM geometry" in first.layout.title.text
