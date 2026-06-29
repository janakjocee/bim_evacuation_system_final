"""
Fire-Origin Worst-Case Scenario Testing page.

This Streamlit multipage entry can be launched from the sidebar when running
`streamlit run src/ui/streamlit_app.py`. It uses a bundled demonstration dataset
so the marker can test the worst-case engine even without a fully classified IFC.
"""
import json
import hashlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src.scenario.worst_case_engine import (
    DEFAULT_DATASET_PATH,
    WorstCaseScenarioEngine,
    dataset_summary,
    load_worst_case_dataset,
    validate_scenario_dataset,
)
from src.scenario.ifc_dataset_exporter import building_to_worst_case_dataset
from src.ui.visualization_3d import create_dataset_3d_figure


st.set_page_config(
    page_title="Fire-Origin Worst-Case Testing",
    page_icon="🔥",
    layout="wide",
)


def _risk_color(risk: str) -> str:
    return {
        "Low": "#2e7d32",
        "Medium": "#f9a825",
        "High": "#ef6c00",
        "Critical": "#c62828",
    }.get(risk, "#607d8b")


def _draw_graph(engine: WorstCaseScenarioEngine, result=None):
    graph = engine.graph
    nodes = list(graph.nodes())
    angle_step = 360 / max(len(nodes), 1)
    positions = {}
    for idx, node in enumerate(nodes):
        # fixed light layout to avoid extra dependencies/slow rendering
        import math
        angle = math.radians(idx * angle_step)
        positions[node] = (math.cos(angle), math.sin(angle))

    blocked_nodes = set(result.blocked_nodes if result else [])
    smoke_nodes = set(result.smoke_affected_nodes if result else [])
    exits = set(engine.exit_ids)
    fire_origin = result.fire_origin if result else None

    edge_x = []
    edge_y = []
    for u, v, data in graph.edges(data=True):
        x0, y0 = positions[u]
        x1, y1 = positions[v]
        edge_x.extend([x0, x1, None])
        edge_y.extend([y0, y1, None])

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=edge_x,
        y=edge_y,
        mode="lines",
        line=dict(width=1, color="#9e9e9e"),
        hoverinfo="none",
        name="Connections",
    ))

    node_x = []
    node_y = []
    labels = []
    colors = []
    sizes = []
    for node in nodes:
        x, y = positions[node]
        node_x.append(x)
        node_y.append(y)
        labels.append(f"{node}: {engine.space_by_id.get(node, {}).get('name', node)}")
        if node == fire_origin:
            colors.append("#b71c1c")
            sizes.append(24)
        elif node in blocked_nodes:
            colors.append("#212121")
            sizes.append(20)
        elif node in smoke_nodes:
            colors.append("#ff9800")
            sizes.append(18)
        elif node in exits:
            colors.append("#2e7d32")
            sizes.append(18)
        else:
            colors.append("#1565c0")
            sizes.append(14)

    fig.add_trace(go.Scatter(
        x=node_x,
        y=node_y,
        mode="markers+text",
        text=nodes,
        textposition="top center",
        marker=dict(size=sizes, color=colors, line=dict(width=1, color="white")),
        hovertext=labels,
        hoverinfo="text",
        name="Spaces / Exits",
    ))
    fig.update_layout(
        height=520,
        showlegend=False,
        margin=dict(l=10, r=10, t=30, b=10),
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
        title="Building graph: fire origin, smoke-affected areas, blocked nodes and exits",
    )
    return fig


st.title("🔥 Fire-Origin Worst-Case Scenario Testing")
st.caption("Indicative decision-support result only. This is not certified fire engineering, physical fire simulation or final legal compliance approval.")

demo_dataset_text = DEFAULT_DATASET_PATH.read_text(encoding="utf-8")
latest_pipeline_result = st.session_state.get("pipeline_result")
dataset_options = ["Bundled demonstration dataset", "Upload custom JSON dataset"]
if latest_pipeline_result and getattr(latest_pipeline_result, "building", None):
    dataset_options.insert(0, "Latest uploaded IFC-derived dataset")
with st.sidebar:
    st.header("Dataset Source")
    dataset_source = st.radio(
        "Choose simulation dataset",
        dataset_options,
        help="This choice controls only this Worst Case Testing page.",
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
    if dataset_source == "Latest uploaded IFC-derived dataset":
        dataset = building_to_worst_case_dataset(
            latest_pipeline_result.building,
            graph_builder=None,
            features=getattr(latest_pipeline_result, "features", None),
            source_file_name=getattr(latest_pipeline_result, "source_file_name", ""),
            ifc_schema=getattr(latest_pipeline_result, "ifc_schema", "UNKNOWN"),
        )
        validate_scenario_dataset(dataset)
        dataset_label = f"IFC-DERIVED DATASET: {getattr(latest_pipeline_result, 'source_file_name', 'current upload')}"
    elif dataset_source == "Upload custom JSON dataset":
        if uploaded_dataset is None:
            st.info("Upload a JSON scenario dataset to enable Worst Case Testing.")
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

engine = WorstCaseScenarioEngine(dataset)
dataset_token = hashlib.sha256(
    json.dumps(dataset, sort_keys=True).encode("utf-8")
).hexdigest()
if st.session_state.get("worst_case_dataset_token") != dataset_token:
    st.session_state.worst_case_dataset_token = dataset_token
    st.session_state.worst_case_result = None
    st.session_state.worst_case_rankings = []
scenarios = engine.get_scenarios()
scenario_options = {f"{s['scenario_id']} — {s['scenario_name']}": s for s in scenarios}

with st.sidebar:
    st.header("Worst-Case Controls")
    selected_label = st.selectbox("Predefined scenario", list(scenario_options.keys()))
    base_scenario = dict(scenario_options[selected_label])

    st.subheader("Custom override")
    custom_fire_origin = st.selectbox(
        "Custom fire origin room",
        engine.get_node_options(),
        index=engine.get_node_options().index(base_scenario["fire_origin"]),
        format_func=lambda node: f"{node} — {engine.space_by_id.get(node, {}).get('name', node)}",
    )
    smoke_nodes = st.multiselect("Smoke affected nodes", engine.get_node_options(), default=base_scenario.get("smoke_spread_nodes", []))
    blocked_nodes = st.multiselect("Blocked nodes", engine.get_node_options(), default=base_scenario.get("blocked_nodes", []))
    blocked_edges = st.multiselect("Blocked edges / doors", engine.get_edge_options(), default=base_scenario.get("blocked_edges", []))
    high_risk_edges = st.multiselect("High-risk edges", engine.get_edge_options(), default=base_scenario.get("high_risk_edges", []))
    occupancy_multiplier = st.slider("Occupancy multiplier", 0.5, 2.5, float(base_scenario.get("occupancy_multiplier", 1.0)), 0.05)
    pre_movement_delay = st.slider("Pre-movement delay (seconds)", 0, 240, int(base_scenario.get("pre_movement_delay_seconds", 60)), 5)
    block_nearest_exit = st.checkbox("Block nearest / affected exit", value=bool(base_scenario.get("affected_exit")))

    run_button = st.button("🔥 Run Worst-Case Simulation", type="primary")
    rank_button = st.button("📊 Auto-rank worst fire origins")

scenario = base_scenario.copy()
scenario["fire_origin"] = custom_fire_origin
scenario["fire_origin_name"] = engine.space_by_id.get(custom_fire_origin, {}).get("name", custom_fire_origin)
scenario["smoke_spread_nodes"] = smoke_nodes
scenario["blocked_nodes"] = list(dict.fromkeys(blocked_nodes + [custom_fire_origin]))
scenario["blocked_edges"] = blocked_edges
scenario["high_risk_edges"] = high_risk_edges
scenario["occupancy_multiplier"] = occupancy_multiplier
scenario["pre_movement_delay_seconds"] = pre_movement_delay
if not block_nearest_exit:
    scenario["affected_exit"] = None

if "worst_case_result" not in st.session_state:
    st.session_state.worst_case_result = None
if "worst_case_rankings" not in st.session_state:
    st.session_state.worst_case_rankings = []

if run_button:
    try:
        st.session_state.worst_case_result = engine.run_scenario(scenario)
        st.success("Worst-case simulation completed.")
    except Exception as exc:
        st.error(f"Worst-case simulation failed: {exc}")

if rank_button:
    with st.spinner("Testing every room/corridor as a possible fire origin..."):
        st.session_state.worst_case_rankings = engine.auto_rank_fire_origins()
    st.success("Auto-ranking completed.")

result = st.session_state.worst_case_result

st.markdown("---")
summary = dataset_summary(dataset)
st.warning(
    f"Active source: **{dataset_label}**. IFC-derived datasets are converted from the "
    "main analysis graph and remain marked for expert review when inference was needed."
)
with st.expander("Active dataset provenance and structure", expanded=True):
    st.json(summary)
    if dataset.get("provenance"):
        st.markdown("#### IFC provenance")
        st.json(dataset["provenance"])
    st.caption("Review or download the dataset before using its results in an assessment.")
with st.expander("Explore 3D dataset overview", expanded=True):
    st.plotly_chart(create_dataset_3d_figure(engine))
    st.caption(
        "Schematic connectivity overview, not BIM geometry. Hover to inspect room "
        "names, types and occupancies; green nodes are exits."
    )

col_intro1, col_intro2, col_intro3 = st.columns(3)
with col_intro1:
    st.metric("Spaces / Nodes", len(engine.space_by_id))
with col_intro2:
    st.metric("Connections", len(engine.connection_by_id))
with col_intro3:
    st.metric("Exits", len(engine.exit_ids))

st.info(
    "This page runs a fire-origin-based worst-case scenario engine using the selected dataset. "
    "It models smoke-affected routes, blocked evacuation routes, trapped rooms, bottlenecks and alternative route availability."
)

if result:
    st.subheader("Worst-Case Scenario Summary")
    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric("Overall Risk", result.overall_risk)
    k2.metric("Risk Score", result.risk_score)
    k3.metric("Affected Occupants", result.affected_occupants)
    k4.metric("Trapped Occupants", result.trapped_occupants)
    k5.metric("Avg Delay Increase", f"{result.average_delay_increase_s:.1f}s")

    risk_color = _risk_color(result.overall_risk)
    st.markdown(
        f"""
        <div style="border-left: 6px solid {risk_color}; background: {risk_color}15; padding: 1rem; border-radius: 6px;">
        <strong>Fire Origin:</strong> {result.fire_origin_name} ({result.fire_origin})<br>
        <strong>Blocked nodes:</strong> {', '.join(result.blocked_nodes) or 'None'}<br>
        <strong>Blocked edges:</strong> {', '.join(result.blocked_edges) or 'None'}<br>
        <strong>Affected exits:</strong> {', '.join(result.affected_exits) or 'None'}
        </div>
        """,
        unsafe_allow_html=True,
    )

    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "Room-by-room results",
        "Route comparison",
        "Compliance screening",
        "Graph visualisation",
        "Export",
    ])

    with tab1:
        st.subheader("Room-by-Room Evacuation Result")
        df = pd.DataFrame(result.room_results)
        display_cols = [
            "start_room_name", "occupancy", "available_exit", "trapped", "rerouted",
            "worst_case_distance_m", "delay_increase_s", "risk_score", "risk_level", "explanation"
        ]
        st.dataframe(df[display_cols], height=420)
        if result.trapped_rooms:
            st.error("Trapped rooms detected: " + ", ".join(result.trapped_rooms))
        if result.rerouted_rooms:
            st.warning("Rooms forced to reroute: " + ", ".join(result.rerouted_rooms))

    with tab2:
        st.subheader("Normal Route vs Worst-Case Route")
        route_rows = []
        for row in result.room_results:
            route_rows.append({
                "Room": row["start_room_name"],
                "Normal route": " → ".join(row["normal_route"] or []),
                "Worst-case route": " → ".join(row["worst_case_route"] or []),
                "Normal distance (m)": row["normal_distance_m"],
                "Worst-case distance (m)": row["worst_case_distance_m"],
                "Delay increase (s)": row["delay_increase_s"],
                "Risk": row["risk_level"],
            })
        st.dataframe(pd.DataFrame(route_rows), height=420)
        st.markdown("### Explanation Panel")
        st.write(result.explanation)

    with tab3:
        st.subheader("Compliance-Oriented Screening")
        st.warning("Indicative compliance-oriented screening only. Requires expert review.")
        st.dataframe(pd.DataFrame(result.compliance_checks), height=360)

    with tab4:
        graph_2d, graph_3d = st.tabs(["2D graph", "3D schematic"])
        with graph_2d:
            st.plotly_chart(_draw_graph(engine, result))
            st.caption("Legend: dark red = fire origin, black = blocked, orange = smoke affected, green = exits, blue = other rooms/spaces.")
        with graph_3d:
            st.plotly_chart(create_dataset_3d_figure(
                engine,
                fire_origin=result.fire_origin,
                smoke_nodes=result.smoke_affected_nodes,
                blocked_nodes=result.blocked_nodes,
            ))
            st.caption(
                "Schematic only, not BIM geometry. Rotate and zoom to understand "
                "scenario connectivity and hazard states."
            )

    with tab5:
        st.subheader("Export Worst-Case Results")
        rankings = st.session_state.get("worst_case_rankings", [])
        json_data = engine.to_json(result, rankings, st.session_state.get("expert_reviews", []))
        csv_data = engine.to_csv(result)
        html_data = engine.to_html_report(result, rankings, st.session_state.get("expert_reviews", []))
        col_a, col_b, col_c = st.columns(3)
        with col_a:
            st.download_button("Download JSON", json_data, "worst_case_fire_scenario.json", "application/json")
        with col_b:
            st.download_button("Download CSV", csv_data, "worst_case_room_results.csv", "text/csv")
        with col_c:
            st.download_button("Download HTML report", html_data, "worst_case_fire_report.html", "text/html")
else:
    st.warning("Select a scenario and click 'Run Worst-Case Simulation' to generate results.")
    st.plotly_chart(_draw_graph(engine))

if st.session_state.worst_case_rankings:
    st.markdown("---")
    st.subheader("Auto-ranked Worst Fire Origins")
    rankings_df = pd.DataFrame(st.session_state.worst_case_rankings)
    visible_cols = [
        "rank", "fire_origin_name", "affected_occupants", "trapped_rooms",
        "unavailable_exits", "average_delay_increase_s", "overall_risk", "main_reason"
    ]
    st.dataframe(rankings_df[visible_cols], height=460)

st.markdown("---")
st.caption(
    "Academic wording: fire-origin-based worst-case scenario, smoke-affected route, blocked evacuation route, trapped room, "
    "alternative route availability, human-in-the-loop expert review, compliance-oriented screening, indicative decision-support result."
)
