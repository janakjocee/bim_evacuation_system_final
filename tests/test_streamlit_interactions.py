"""Executable Streamlit interaction tests for release-critical controls."""
import copy
from pathlib import Path

from streamlit.testing.v1 import AppTest

from src.bim_processing.feature_extractor import FeatureExtractor
from src.bim_processing.ifc_parser import BuildingData, DoorData, Point3D, SpaceData
from src.bim_processing.ifc_validation import validate_ifc_model
from src.bim_processing.spatial_graph import SpatialGraphBuilder
from src.pipeline.evacuation_pipeline import PipelineResult
from src.scenario.scenario_generator import ScenarioGenerator


REPO_ROOT = Path(__file__).resolve().parents[1]


def _app_test(path: str) -> AppTest:
    return AppTest.from_file(str(REPO_ROOT / path), default_timeout=30)


def _main_pipeline_result() -> PipelineResult:
    building = BuildingData(id="B1", name="Streamlit Interaction Test")
    building.spaces["S1"] = SpaceData(
        id="S1",
        name="Test Room",
        area=20,
        bounding_box=(Point3D(0, 0, 0), Point3D(4, 4, 3)),
    )
    exit_door = DoorData(
        id="E1",
        name="Final Exit",
        width=1.2,
        height=2.1,
        location=Point3D(4, 2, 0),
        is_exit=True,
        connected_spaces=["S1"],
    )
    building.doors = {"E1": exit_door}
    building.exits = {"E1": exit_door}
    graph = SpatialGraphBuilder(building)
    assert graph.build()
    scenarios = ScenarioGenerator(building, graph).generate(max_scenarios=1)
    readiness = validate_ifc_model(extracted_data={
        "schema": "IFC4",
        "space_count": 1,
        "door_count": 1,
        "stair_count": 0,
        "buildingstorey_count": 1,
        "possible_exits_count": 1,
        "graph_connectivity_complete": True,
    })
    return PipelineResult(
        success=True,
        building=building,
        features=FeatureExtractor().extract(building),
        scenarios=scenarios,
        readiness=readiness,
        graph_stats=graph.get_graph_stats(),
        source_file_name="interaction.ifc",
        source_file_sha256="a" * 64,
        ifc_schema="IFC4",
    )


def _button(app: AppTest, label: str):
    return next(button for button in app.button if button.label == label)


def test_main_scenario_details_close_reopen_review_and_exports():
    result = _main_pipeline_result()
    scenario = result.scenarios[0]
    app = _app_test("src/ui/streamlit_app.py")
    app.session_state["processing_done"] = True
    app.session_state["pipeline_result"] = result
    app.session_state["baseline_pipeline_result"] = result
    app.session_state["selected_scenario_id"] = scenario.scenario_id

    app.run(timeout=30)
    assert not app.exception
    assert _button(app, "Close Details")
    detail_markup = "\n".join(str(getattr(element, "value", "")) for element in app.markdown)
    assert "Route reliability:</strong> verified" in detail_markup
    assert "Edge evidence:</strong> verified=1, inferred=0" in detail_markup

    _button(app, "Close Details").click().run(timeout=30)
    assert not app.exception
    assert app.session_state["selected_scenario_id"] is None
    assert "Close Details" not in [button.label for button in app.button]

    _button(app, "View Details").click().run(timeout=30)
    assert not app.exception
    assert app.session_state["selected_scenario_id"] == scenario.scenario_id
    assert _button(app, "Close Details")

    acknowledgement = next(
        checkbox for checkbox in app.checkbox
        if checkbox.label == "I understand this review status is not professional approval or statutory sign-off."
    )
    acknowledgement.check().run(timeout=30)
    decision = next(radio for radio in app.radio if radio.label == "Research Review Status")
    decision.set_value("✅ Accepted for research follow-up")
    comments = next(area for area in app.text_area if area.label == "Review Comments")
    comments.set_value("Reviewed in automated interaction test.")
    _button(app, "💾 Save Research Review").click().run(timeout=30)
    assert not app.exception
    saved = app.session_state["expert_reviews"][f"expert_review_{scenario.scenario_id}"]
    assert saved["decision"] == "✅ Accepted for research follow-up"
    assert saved["comments"] == "Reviewed in automated interaction test."
    assert saved["limitations_acknowledged"] is True
    assert saved["record_scope"] == "session_scoped_research_review_not_professional_approval"

    download_labels = {element.label for element in app.get("download_button")}
    assert {
        "Download selected scenario evidence",
        "Download IFC diagnostic report",
        "Download manual corrections JSON",
        "Export IFC-derived graph as fire scenario dataset",
        "⬇️ Download JSON",
        "⬇️ Download CSV",
        "⬇️ Download XML",
    }.issubset(download_labels)


def test_selected_details_render_inside_the_selected_scenario_card():
    result = _main_pipeline_result()
    scenarios = []
    for index in range(3):
        scenario = copy.deepcopy(result.scenarios[0])
        scenario.scenario_id = f"SCEN_POSITION_{index}"
        scenario.name = f"Position Test {index}"
        scenarios.append(scenario)
    result.scenarios = scenarios

    app = _app_test("src/ui/streamlit_app.py")
    app.session_state["processing_done"] = True
    app.session_state["pipeline_result"] = result
    app.session_state["baseline_pipeline_result"] = result
    app.session_state["selected_scenario_id"] = scenarios[0].scenario_id
    app.run(timeout=30)
    assert not app.exception

    markdown = [str(getattr(element, "value", "")) for element in app.markdown]
    card_positions = [
        index for index, value in enumerate(markdown)
        if 'class="scenario-card"' in value
    ]
    detail_position = next(
        index for index, value in enumerate(markdown)
        if 'class="scenario-detail-card"' in value
    )
    assert card_positions[0] < detail_position < card_positions[1]


def test_fire_scenario_page_runs_and_exposes_result_exports():
    app = _app_test("src/ui/pages/Fire_Scenario_Testing.py")
    app.run(timeout=30)
    assert not app.exception

    _button(app, "Run Fire Scenario").click().run(timeout=30)

    assert not app.exception
    assert app.session_state["fire_scenario_result"]
    download_labels = {element.label for element in app.get("download_button")}
    assert {"Download Scenario JSON", "Download FDS Skeleton"}.issubset(download_labels)


def test_worst_case_page_runs_ranks_and_exposes_result_exports():
    app = _app_test("src/ui/pages/Worst_Case_Testing.py")
    app.run(timeout=30)
    assert not app.exception

    _button(app, "🔥 Run Worst-Case Simulation").click().run(timeout=30)
    assert not app.exception
    assert app.session_state["worst_case_result"]

    _button(app, "📊 Auto-rank worst fire origins").click().run(timeout=30)
    assert not app.exception
    assert app.session_state["worst_case_rankings"]
    download_labels = {element.label for element in app.get("download_button")}
    assert {"Download JSON", "Download CSV", "Download HTML report"}.issubset(download_labels)
