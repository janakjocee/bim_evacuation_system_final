"""Static regression checks for critical Streamlit workflows."""

from pathlib import Path


def test_scenario_details_use_inline_inspection_workspace():
    source = (Path(__file__).resolve().parents[1] / "src/ui/streamlit_app.py").read_text()

    assert "render_selected_scenario_details" in source
    assert "Scenario Inspection Workspace" in source
    assert "View Details" in source
    assert "st.session_state.active_tab = 4" not in source


def test_dark_mode_uses_adaptive_theme_variables():
    source = (Path(__file__).resolve().parents[1] / "src/ui/streamlit_app.py").read_text()

    assert "@media (prefers-color-scheme: dark)" in source
    assert "--app-panel-strong" in source
    assert "--app-heading" in source
