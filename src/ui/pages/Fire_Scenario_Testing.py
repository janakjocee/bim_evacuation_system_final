"""Interactive ASET/RSET fire scenario testing page."""
from __future__ import annotations

import json
import hashlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

import pandas as pd
import plotly.express as px
import streamlit as st

from src.fire.fire_scenario_engine import FireScenarioEngine
from src.ui.visualization_3d import create_dataset_3d_figure
from src.scenario.worst_case_engine import (
    DEFAULT_DATASET_PATH,
    dataset_summary,
    load_worst_case_dataset,
    validate_scenario_dataset,
)


st.set_page_config(page_title="Fire Scenario Testing", page_icon="🔥", layout="wide")
st.title("🔥 ASET/RSET Fire Scenario Testing")
st.warning(
    "Indicative academic decision support only. Results require validation by "
    "a qualified fire-safety professional."
)

demo_dataset_text = DEFAULT_DATASET_PATH.read_text(encoding="utf-8")
with st.sidebar:
    st.header("Dataset Source")
    dataset_source = st.radio(
        "Choose simulation dataset",
        ["Bundled demonstration dataset", "Upload custom JSON dataset"],
        help="This choice controls only this Fire Scenario Testing page.",
    )
    st.download_button(
        "Download bundled demo dataset",
        demo_dataset_text,
        "demo_worst_case_building.json",
        "application/json",
        width="stretch",
    )
    uploaded_dataset = None
    if dataset_source == "Upload custom JSON dataset":
        uploaded_dataset = st.file_uploader("Upload scenario dataset", type=["json"])

try:
    if dataset_source == "Upload custom JSON dataset":
        if uploaded_dataset is None:
            st.info("Upload a JSON scenario dataset to enable Fire Scenario Testing.")
            st.stop()
        dataset = json.loads(uploaded_dataset.getvalue().decode("utf-8"))
        validate_scenario_dataset(dataset)
        dataset_label = f"UPLOADED CUSTOM DATASET: {uploaded_dataset.name}"
    else:
        dataset = load_worst_case_dataset()
        dataset_label = "BUNDLED DEMONSTRATION DATASET"
except (ValueError, json.JSONDecodeError, UnicodeDecodeError) as exc:
    st.error(f"Dataset validation failed: {exc}")
    st.stop()

engine = FireScenarioEngine(dataset)
dataset_token = hashlib.sha256(
    json.dumps(dataset, sort_keys=True).encode("utf-8")
).hexdigest()
if st.session_state.get("fire_dataset_token") != dataset_token:
    st.session_state.fire_dataset_token = dataset_token
    st.session_state.fire_scenario_result = None
scenarios = engine.get_scenarios()
scenario_by_label = {
    f"{scenario['scenario_id']} — {scenario['scenario_name']}": scenario
    for scenario in scenarios
}

with st.sidebar:
    st.header("Fire Scenario Controls")
    selected_label = st.selectbox("Predefined scenario", list(scenario_by_label))
    growth_class = st.selectbox(
        "Fire growth class",
        ["slow", "medium", "fast", "ultra_fast"],
        index=2,
    )
    duration = st.slider("Simulation duration (seconds)", 60, 900, 360, 30)
    time_step = st.slider("Time step (seconds)", 10, 120, 30, 10)
    pre_movement = st.slider("Pre-movement delay (seconds)", 0, 300, 60, 15)
    ventilation = st.slider("Ventilation factor", 0.5, 2.0, 1.0, 0.1)
    suppression = st.checkbox("Suppression / sprinkler enabled")
    run_scenario = st.button("Run Fire Scenario", type="primary")

scenario = scenario_by_label[selected_label]
summary = dataset_summary(dataset)
st.warning(
    f"Active source: **{dataset_label}**. This page does not silently use the IFC uploaded "
    "on the main page."
)
with st.expander("Active dataset provenance and structure", expanded=True):
    st.json(summary)
    st.caption("Review or download the dataset before using its results in an assessment.")
with st.expander("Explore 3D dataset overview", expanded=True):
    st.plotly_chart(create_dataset_3d_figure(engine))
    st.caption(
        "Schematic connectivity overview, not BIM geometry. Hover to inspect room "
        "names, types and occupancies; green nodes are exits."
    )
st.subheader(selected_label)
st.write(
    f"Fire origin: **{scenario.get('fire_origin_name', scenario['fire_origin'])}**  |  "
    f"Modelled growth: **{growth_class}**"
)

if run_scenario:
    with st.spinner("Running fire growth, smoke spread, and ASET/RSET screening..."):
        st.session_state.fire_scenario_result = engine.run_fire_scenario(
            scenario,
            {
                "fire_growth_class": growth_class,
                "simulation_duration_seconds": duration,
                "time_step_seconds": time_step,
                "pre_movement_delay": pre_movement,
                "ventilation_factor": ventilation,
                "suppression_enabled": suppression,
            },
        )

result = st.session_state.get("fire_scenario_result")
if not result:
    st.info("Choose assumptions in the sidebar and click **Run Fire Scenario**.")
    st.stop()

impact = result["life_safety_impact"]
k1, k2, k3, k4 = st.columns(4)
k1.metric("Overall Risk", result["overall_risk_level"])
k2.metric("Risk Score", result["overall_risk_score"])
k3.metric("Potentially Affected", impact.get("potentially_affected_occupants", 0))
k4.metric("Trapped Occupants", impact.get("trapped_occupants", 0))

st.write(result["explanation"])

growth_tab, aset_tab, checks_tab, visual_tab, export_tab = st.tabs(
    ["Fire Growth", "ASET / RSET", "Compliance Screening", "3D Scenario View", "Export"]
)

with growth_tab:
    growth_df = pd.DataFrame(result["fire_growth"]["time_series"])
    figure = px.line(growth_df, x="time_s", y="hrr_kw", color="intensity")
    figure.update_layout(xaxis_title="Time (seconds)", yaxis_title="HRR (kW)")
    st.plotly_chart(figure)
    st.dataframe(growth_df)

with aset_tab:
    aset_df = pd.DataFrame(result["aset_rset_results"])
    st.dataframe(aset_df, height=460)

with checks_tab:
    st.dataframe(pd.DataFrame(result["compliance_oriented_checks"]))

with visual_tab:
    smoke = result.get("smoke_spread", {})
    st.plotly_chart(create_dataset_3d_figure(
        engine,
        fire_origin=result.get("fire_origin"),
        smoke_nodes=smoke.get("final_smoke_affected_nodes", []),
        high_risk_nodes=(
            smoke.get("final_high_risk_nodes", [])
            + smoke.get("final_untenable_nodes", [])
        ),
    ))
    st.caption(
        "Schematic only, not BIM geometry. Red = fire origin, orange = smoke affected, "
        "purple = high risk/untenable, green = exit."
    )

with export_tab:
    st.download_button(
        "Download Scenario JSON",
        json.dumps(result, indent=2),
        "fire_scenario_result.json",
        "application/json",
        width="stretch",
    )
    st.download_button(
        "Download FDS Skeleton",
        engine.export_fds_skeleton(result),
        "fire_scenario_skeleton.fds",
        "text/plain",
        width="stretch",
    )
