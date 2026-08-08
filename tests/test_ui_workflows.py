"""Static regression checks for critical Streamlit workflows."""

from pathlib import Path


def test_scenario_details_use_stable_inspection_workspace():
    source = (Path(__file__).resolve().parents[1] / "src/ui/streamlit_app.py").read_text()

    assert "render_selected_scenario_details" in source
    assert "Selected Scenario Inspection Workspace" in source
    assert "View Details" in source
    assert '"Close Details", key="close_selected_scenario_details"' in source
    assert "scenario_by_id = {scenario.scenario_id: scenario for scenario in scenarios}" in source
    assert "selected_scenario = scenario_by_id.get" in source
    assert "st.session_state.active_tab = 4" not in source
    assert "render_selected_scenario_details(result, selected_scenario)" in source
    scenario_tab_source = source[source.index("def render_evacuation_scenarios"):source.index("def render_explainability")]
    assert "render_selected_scenario_details(result, scenario)" not in scenario_tab_source
    assert "selected_scenario = next(" not in source
    assert "Download selected scenario evidence" in source
    assert "scenario.decision_trace" in source


def test_dark_mode_uses_adaptive_theme_variables():
    source = (Path(__file__).resolve().parents[1] / "src/ui/streamlit_app.py").read_text()

    assert "@media (prefers-color-scheme: dark)" in source
    assert "--app-panel-strong" in source
    assert "--app-heading" in source
    assert 'background-color: white; border: 1px solid #e0e0e0' not in source
    assert 'background-color: #f8f9fa; padding: 12px' not in source


def test_badges_do_not_use_fragile_multiline_html():
    source = (Path(__file__).resolve().parents[1] / "src/ui/ui_components.py").read_text()

    assert "return f\\\"\\\"\\\"" not in source[source.index("def get_risk_badge"):source.index("def create_risk_pie_chart")]


def test_explainability_ui_is_not_black_box_or_overclaiming_rag():
    source = (Path(__file__).resolve().parents[1] / "src/ui/streamlit_app.py").read_text()

    assert "Anti-Black-Box Decision Trace" in source
    assert "deterministic weighted score" in source
    assert "Retrieved relevant building safety regulations via RAG" not in source
    assert "not as final regulatory approval" in source


def test_bim_insights_has_exportable_diagnostics():
    source = (Path(__file__).resolve().parents[1] / "src/ui/streamlit_app.py").read_text()
    pipeline = (Path(__file__).resolve().parents[1] / "src/pipeline/evacuation_pipeline.py").read_text()

    assert "Diagnostics Export" in source
    assert "Download IFC diagnostic report" in source
    assert "graph_stats" in pipeline


def test_bim_insights_has_manual_corrections_and_fire_dataset_bridge():
    source = (Path(__file__).resolve().parents[1] / "src/ui/streamlit_app.py").read_text()

    assert "Manual IFC Review & Correction" in source
    assert "Apply manual corrections and rerun" in source
    assert "Reset manual corrections" in source
    assert "'baseline_pipeline_result': None" in source
    assert "st.session_state.baseline_pipeline_result = copy.deepcopy(result)" in source
    assert "correction_base = copy.deepcopy" in source
    assert "Download manual corrections JSON" in source
    assert "Fire/Worst-Case Dataset Bridge" in source
    assert "Export IFC-derived graph as fire scenario dataset" in source


def test_fire_and_worst_case_pages_can_use_latest_ifc_dataset():
    root = Path(__file__).resolve().parents[1]
    fire_source = (root / "src/ui/pages/Fire_Scenario_Testing.py").read_text()
    worst_source = (root / "src/ui/pages/Worst_Case_Testing.py").read_text()

    for source in (fire_source, worst_source):
        assert "Latest uploaded IFC-derived dataset" in source
        assert "building_to_worst_case_dataset" in source
        assert "latest_pipeline_result = st.session_state.get(\"pipeline_result\")" in source
        assert "IFC-DERIVED DATASET" in source
        assert "IFC provenance" in source
        assert "This page does not silently use the IFC uploaded" not in source


def test_main_export_uses_complete_evidence_payload():
    source = (Path(__file__).resolve().parents[1] / "src/ui/streamlit_app.py").read_text()

    assert "def build_complete_export_payload" in source
    assert "\"export_version\": \"submission-evidence-v1\"" in source
    assert "\"ifc_readiness\": result.readiness" in source
    assert "\"graph_stats\": result.graph_stats" in source
    assert "\"manual_corrections\": st.session_state.get(\"manual_corrections\")" in source
    assert "export_data = build_complete_export_payload(result)" in source
