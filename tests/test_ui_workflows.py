"""Static regression checks for critical Streamlit workflows."""

from pathlib import Path

from src.ui.accessibility import palette_contrast_report
from src.ui.streamlit_app import analysis_control_state
from src.ui.theme import APP_CSS


def test_scenario_details_use_stable_inspection_workspace():
    source = (Path(__file__).resolve().parents[1] / "src/ui/streamlit_app.py").read_text()

    assert "render_selected_scenario_details" in source
    assert "Selected Scenario Inspection Workspace" in source
    assert "View Details" in source
    assert '"Close Details" if is_selected else "View Details"' in source
    assert "on_click=toggle_scenario_details" in source
    assert "visible_scenario_ids = {scenario.scenario_id for scenario in filtered}" in source
    assert "st.session_state.active_tab = 4" not in source
    assert "render_selected_scenario_details(result, scenario)" in source
    scenario_tab_source = source[source.index("def render_evacuation_scenarios"):source.index("def render_explainability")]
    assert "if st.session_state.selected_scenario_id == scenario.scenario_id:" in scenario_tab_source
    assert "selected_scenario = next(" not in source
    assert "Download selected scenario evidence" in source
    assert "scenario.decision_trace" in source


def test_theme_tracks_streamlit_light_and_dark_variables_without_split_mode():
    source = (Path(__file__).resolve().parents[1] / "src/ui/theme.py").read_text()

    assert "--app-background: var(--background-color" in source
    assert "--app-text: var(--text-color" in source
    assert "--app-panel-strong" in source
    assert "--app-heading" in source
    assert "@media (prefers-color-scheme: dark)" not in source
    assert "color-mix(in srgb" in source


def test_custom_theme_palette_meets_normal_text_contrast_target():
    report = palette_contrast_report()

    assert report
    assert min(report.values()) >= 4.5, report


def test_custom_motion_respects_reduced_motion_preference():
    source = (Path(__file__).resolve().parents[1] / "src/ui/theme.py").read_text()

    assert "@media (prefers-reduced-motion: reduce)" in source
    assert "transition-duration: .01ms !important" in source


def test_analysis_control_has_clear_waiting_ready_processing_and_retry_states():
    waiting = analysis_control_state(False, "ready")
    ready = analysis_control_state(True, "ready")
    processing = analysis_control_state(True, "processing")
    complete = analysis_control_state(True, "complete")
    error = analysis_control_state(True, "error")

    assert waiting["disabled"] is True
    assert waiting["button_label"] == "Upload IFC to enable analysis"
    assert ready["disabled"] is False
    assert ready["variant"] == "ready"
    assert processing["disabled"] is True
    assert processing["button_label"] == "Analysis in progress..."
    assert complete["button_label"] == "Run Analysis Again"
    assert error["button_label"] == "Retry Analysis"


def test_analysis_ui_acknowledges_click_before_loading_pipeline():
    source = (Path(__file__).resolve().parents[1] / "src/ui/streamlit_app.py").read_text()
    process_source = source[source.index("def process_files"):source.index("def render_dashboard")]

    assert "on_click=queue_analysis_request" in source
    assert 'analysis_ui_state = "processing"' in source
    assert 'st.status("Analysis request received"' in process_source
    assert process_source.index('st.status("Analysis request received"') < process_source.index(
        "from src.pipeline.evacuation_pipeline import EvacuationPipeline"
    )
    assert "analysis-state--{control['variant']}" in source
    assert 'aria-live="polite"' in source
    assert "st.rerun()" in source[source.index("def main"):]


def test_theme_uses_semantic_safety_states_and_compact_responsive_layout():
    source = (Path(__file__).resolve().parents[1] / "src/ui/theme.py").read_text()

    assert "--app-fire-red: #B42318" in source
    assert "--app-caution: #B54708" in source
    assert "--app-escape-green: #147A50" in source
    assert ".analysis-state--processing" in source
    assert ".st-key-analysis-action-ready" in source
    assert ".st-key-app-header" in source
    assert "width: min(100%, 1480px)" in source
    assert APP_CSS.count("{") == APP_CSS.count("}")


def test_submission_theme_is_shared_by_every_streamlit_entrypoint():
    root = Path(__file__).resolve().parents[1]
    main_source = (root / "src/ui/streamlit_app.py").read_text()
    fire_source = (root / "src/ui/pages/Fire_Scenario_Testing.py").read_text()
    worst_source = (root / "src/ui/pages/Worst_Case_Testing.py").read_text()
    config = (root / ".streamlit/config.toml").read_text()

    for source in (main_source, fire_source, worst_source):
        assert "apply_app_theme()" in source
    assert 'primaryColor = "#0B5F6B"' in config
    assert "workflow-grid" in main_source
    assert "system-status-row" in main_source


def test_badges_do_not_use_fragile_multiline_html():
    source = (Path(__file__).resolve().parents[1] / "src/ui/ui_components.py").read_text()

    assert "return f\\\"\\\"\\\"" not in source[source.index("def get_risk_badge"):source.index("def create_risk_pie_chart")]


def test_explainability_ui_is_not_black_box_or_overclaiming_rag():
    source = (Path(__file__).resolve().parents[1] / "src/ui/streamlit_app.py").read_text()

    assert "Anti-Black-Box Decision Trace" in source
    assert "deterministic weighted score" in source
    assert "Retrieved relevant building safety regulations via RAG" not in source
    assert "not fire-strategy approval or statutory sign-off" in source
    assert "Example Reasoning Format" not in source
    assert "Approved Document B Section 2.2.1" not in source
    assert "ASET (300s)" not in source
    assert "Safety Margin" not in source
    assert "Scenarios meet basic safety requirements" not in source
    assert "Generate Fire Strategy Scenarios" not in source
    assert "complete fire strategy report" not in source


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
    assert "\"export_version\": \"submission-evidence-v2\"" in source
    assert "\"score_semantics\": screening_index_semantics()" in source
    assert "\"assumption_registry\": standard_assumption_registry()" in source
    assert "\"ifc_readiness\": result.readiness" in source
    assert "\"graph_stats\": result.graph_stats" in source
    assert "\"retrieval_mode\": result.retrieval_mode" in source
    assert "\"document\": result.regulation_document" in source
    assert "\"manual_corrections\": st.session_state.get(\"manual_corrections\")" in source
    assert "\"research_review_records\":" in source
    assert "\"preliminary_domain_review_records\":" in source
    assert "\"manual_accessibility_audit_records\":" in source
    assert "\"space_label_review_validation\":" in source
    assert "export_data = build_complete_export_payload(result)" in source


def test_uploader_supports_compressed_ifc_and_regulation_provenance():
    source = (Path(__file__).resolve().parents[1] / "src/ui/streamlit_app.py").read_text()

    assert "type=['ifc', 'ifczip']" in source
    assert "from src.utils.helpers import RiskLevel, ComplianceStatus, sha256_file" not in source
    assert "hashlib.sha256(regulation_file.getbuffer()).hexdigest()" in source
    assert "inside an IFCZIP are limited to 200 MB" in source
    assert "512 MB" not in source
    assert "Regulation source provenance" in source
    assert "user_declared_not_legally_validated" in source
    assert "does not determine legal applicability" in source
