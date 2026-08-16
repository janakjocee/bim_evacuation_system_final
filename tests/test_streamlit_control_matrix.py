"""Executable coverage for every release-critical Streamlit control group."""
from pathlib import Path

from streamlit.testing.v1 import AppTest

from src.scenario.worst_case_engine import (
    WorstCaseScenarioEngine,
    load_worst_case_dataset,
)
from tests.test_streamlit_interactions import _main_pipeline_result


REPO_ROOT = Path(__file__).resolve().parents[1]


def _app(path: str) -> AppTest:
    return AppTest.from_file(str(REPO_ROOT / path), default_timeout=30)


def _control(elements, label: str):
    return next(element for element in elements if element.label == label)


def _button(app: AppTest, label: str):
    return _control(app.button, label)


def _assert_clean(app: AppTest) -> None:
    assert not app.exception, [exception.value for exception in app.exception]


def test_main_app_control_matrix_and_icon_labels():
    result = _main_pipeline_result()
    scenario = result.scenarios[0]
    app = _app("src/ui/streamlit_app.py")
    app.session_state["processing_done"] = True
    app.session_state["pipeline_result"] = result
    app.session_state["baseline_pipeline_result"] = result
    app.session_state["selected_scenario_id"] = scenario.scenario_id
    app.run(timeout=30)
    _assert_clean(app)

    expected_tabs = {
        "📊 Dashboard", "🏢 BIM Insights", "📜 Regulations", "🚨 Scenarios",
        "🧠 Explainability", "⚠️ Screening Analysis", "👤 Research Review", "📤 Export",
        "🔍 Extracted Spaces", "🚪 Doors & Exits", "🕸️ Connectivity Graph",
        "🗺️ Floor Plan Diagram", "🏙️ 3D Model & Egress", "🧾 Diagnostics Export",
        "Route Diagram", "Operational Actions", "Evidence & Export",
    }
    assert expected_tabs == {tab.label for tab in app.get("tab")}

    search = _control(app.text_input, "Search regulations by keyword")
    search.set_value("door width").run(timeout=30)
    _assert_clean(app)
    _control(app.text_input, "Search regulations by keyword").set_value(
        "not-a-real-rule"
    ).run(timeout=30)
    _assert_clean(app)

    for option in _control(app.selectbox, "Sort By").options:
        _control(app.selectbox, "Sort By").set_value(option).run(timeout=30)
        _assert_clean(app)

    for values in ([], ["low"], ["medium"], ["high"], ["low", "medium", "high"]):
        _control(app.multiselect, "Screening Priority").set_value(values).run(timeout=30)
        _assert_clean(app)

    if "Close Details" not in {button.label for button in app.button}:
        _button(app, "View Details").click().run(timeout=30)
        _assert_clean(app)
    _button(app, "Close Details").click().run(timeout=30)
    _assert_clean(app)
    _button(app, "View Details").click().run(timeout=30)
    _assert_clean(app)

    _button(app, "Apply manual corrections and rerun").click().run(timeout=30)
    _assert_clean(app)
    assert app.session_state["manual_corrections"] is not None
    _button(app, "Reset manual corrections").click().run(timeout=30)
    _assert_clean(app)
    assert app.session_state["manual_corrections"] is None

    acknowledgement = _control(
        app.checkbox,
        "I understand this review status is not professional approval or statutory sign-off.",
    )
    acknowledgement.check().run(timeout=30)
    review = _control(app.radio, "Research Review Status")
    for option in review.options:
        _control(app.radio, "Research Review Status").set_value(option).run(timeout=30)
        _control(app.text_area, "Review Comments").set_value(
            f"Automated QA: {option}"
        ).run(timeout=30)
        _button(app, "💾 Save Research Review").click().run(timeout=30)
        _assert_clean(app)

    _button(app, "📑 Generate Complete Evidence Report").click().run(timeout=30)
    _assert_clean(app)
    download_labels = {download.label for download in app.get("download_button")}
    assert "⬇️ Download Complete Report (JSON)" in download_labels
    assert all(download.url for download in app.get("download_button"))
    assert not any(
        getattr(markdown, "value", "").strip() == "</div>"
        for markdown in app.markdown
    )


def test_fire_page_all_scenarios_growth_classes_and_boundaries():
    app = _app("src/ui/pages/Fire_Scenario_Testing.py").run(timeout=30)
    _assert_clean(app)

    source = _control(app.radio, "Choose simulation dataset")
    source.set_value("Upload custom JSON dataset").run(timeout=30)
    _assert_clean(app)
    assert _control(app.get("file_uploader"), "Upload scenario dataset")

    source = _control(app.radio, "Choose simulation dataset")
    source.set_value("Bundled demonstration dataset").run(timeout=30)
    _assert_clean(app)

    scenarios = list(_control(app.selectbox, "Predefined scenario").options)
    for scenario in scenarios:
        _control(app.selectbox, "Predefined scenario").set_value(scenario).run(timeout=30)
        assert app.session_state["fire_scenario_result"] is None
        _button(app, "Run Fire Scenario").click().run(timeout=30)
        _assert_clean(app)
        assert app.session_state["fire_scenario_result"]

    growth_classes = list(_control(app.selectbox, "Fire growth class").options)
    for growth_class in growth_classes:
        _control(app.selectbox, "Fire growth class").set_value(growth_class).run(timeout=30)
        assert app.session_state["fire_scenario_result"] is None
        _button(app, "Run Fire Scenario").click().run(timeout=30)
        _assert_clean(app)

    slider_labels = [
        "Simulation duration (seconds)", "Time step (seconds)",
        "Pre-movement delay (seconds)", "Ventilation factor",
    ]
    for label in slider_labels:
        for endpoint in ("min", "max"):
            slider = _control(app.slider, label)
            slider.set_value(getattr(slider, endpoint)).run(timeout=30)
            assert app.session_state["fire_scenario_result"] is None
            _assert_clean(app)

    _control(app.checkbox, "Suppression / sprinkler enabled").check().run(timeout=30)
    assert app.session_state["fire_scenario_result"] is None
    _button(app, "Run Fire Scenario").click().run(timeout=30)
    _assert_clean(app)

    assert {"Fire Growth", "ASET / RSET", "Compliance Screening", "3D Scenario View", "Export"} == {
        tab.label for tab in app.get("tab")
    }
    assert {"Download Scenario JSON", "Download FDS Skeleton"}.issubset(
        {download.label for download in app.get("download_button")}
    )


def test_worst_case_page_all_scenarios_origins_and_boundaries():
    app = _app("src/ui/pages/Worst_Case_Testing.py").run(timeout=30)
    _assert_clean(app)

    scenarios = list(_control(app.selectbox, "Predefined scenario").options)
    for scenario in scenarios:
        _control(app.selectbox, "Predefined scenario").set_value(scenario).run(timeout=30)
        assert app.session_state["worst_case_result"] is None
        _button(app, "🔥 Run Worst-Case Simulation").click().run(timeout=30)
        _assert_clean(app)

    engine = WorstCaseScenarioEngine(load_worst_case_dataset())
    for origin in engine.get_node_options():
        _control(app.selectbox, "Custom fire origin room").set_value(origin).run(timeout=30)
        assert app.session_state["worst_case_result"] is None
        _button(app, "🔥 Run Worst-Case Simulation").click().run(timeout=30)
        _assert_clean(app)

    for label in ("Occupancy multiplier", "Pre-movement delay (seconds)"):
        for endpoint in ("min", "max"):
            slider = _control(app.slider, label)
            slider.set_value(getattr(slider, endpoint)).run(timeout=30)
            assert app.session_state["worst_case_result"] is None
            _button(app, "🔥 Run Worst-Case Simulation").click().run(timeout=30)
            _assert_clean(app)

    for label in (
        "Smoke affected nodes", "Blocked nodes", "Blocked edges / doors", "High-risk edges"
    ):
        _control(app.multiselect, label).set_value([]).run(timeout=30)
        assert app.session_state["worst_case_result"] is None
        _button(app, "🔥 Run Worst-Case Simulation").click().run(timeout=30)
        _assert_clean(app)

    _control(app.checkbox, "Block nearest / affected exit").uncheck().run(timeout=30)
    assert app.session_state["worst_case_result"] is None
    _button(app, "🔥 Run Worst-Case Simulation").click().run(timeout=30)
    _button(app, "📊 Auto-rank worst fire origins").click().run(timeout=30)
    _assert_clean(app)
    assert app.session_state["worst_case_rankings"]
    assert {"Download JSON", "Download CSV", "Download HTML report"}.issubset(
        {download.label for download in app.get("download_button")}
    )


def test_fire_pages_use_latest_ifc_derived_dataset():
    result = _main_pipeline_result()
    for path, run_label, result_key in (
        ("src/ui/pages/Fire_Scenario_Testing.py", "Run Fire Scenario", "fire_scenario_result"),
        (
            "src/ui/pages/Worst_Case_Testing.py",
            "🔥 Run Worst-Case Simulation",
            "worst_case_result",
        ),
    ):
        app = _app(path)
        app.session_state["pipeline_result"] = result
        app.run(timeout=30)
        _assert_clean(app)
        source = _control(app.radio, "Choose simulation dataset")
        assert source.value == "Latest uploaded IFC-derived dataset"
        _button(app, run_label).click().run(timeout=30)
        _assert_clean(app)
        assert app.session_state[result_key]
