"""Static regression checks for critical Streamlit workflows."""

from pathlib import Path


def test_scenario_details_use_inline_inspection_workspace():
    source = (Path(__file__).resolve().parents[1] / "src/ui/streamlit_app.py").read_text()

    assert "render_selected_scenario_details" in source
    assert "Scenario Inspection Workspace" in source
    assert "View Details" in source
    assert "st.session_state.active_tab = 4" not in source
    assert "render_selected_scenario_details(result, scenario)" in source
    assert "selected_scenario = next(" not in source


def test_dark_mode_uses_adaptive_theme_variables():
    source = (Path(__file__).resolve().parents[1] / "src/ui/streamlit_app.py").read_text()

    assert "@media (prefers-color-scheme: dark)" in source
    assert "--app-panel-strong" in source
    assert "--app-heading" in source


def test_badges_do_not_use_fragile_multiline_html():
    source = (Path(__file__).resolve().parents[1] / "src/ui/ui_components.py").read_text()

    assert "return f\\\"\\\"\\\"" not in source[source.index("def get_risk_badge"):source.index("def create_risk_pie_chart")]
