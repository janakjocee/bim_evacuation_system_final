"""Reusable interactive 3D visualizations for IFC and scenario data."""
from __future__ import annotations

from typing import Any, Dict, Iterable, Optional, Set, Tuple

import networkx as nx
import plotly.graph_objects as go


BOX_TRIANGLES = (
    (0, 1, 2), (0, 2, 3), (4, 5, 6), (4, 6, 7),
    (0, 1, 5), (0, 5, 4), (1, 2, 6), (1, 6, 5),
    (2, 3, 7), (2, 7, 6), (3, 0, 4), (3, 4, 7),
)


def _box_vertices(minimum: Any, maximum: Any) -> Tuple[list, list, list]:
    x0, y0, z0 = minimum.x, minimum.y, minimum.z
    x1, y1, z1 = maximum.x, maximum.y, maximum.z
    return (
        [x0, x1, x1, x0, x0, x1, x1, x0],
        [y0, y0, y1, y1, y0, y0, y1, y1],
        [z0, z0, z0, z0, z1, z1, z1, z1],
    )


def _space_centers(building: Any) -> Dict[str, Tuple[float, float, float]]:
    centers = {}
    for space_id, space in building.spaces.items():
        if not space.bounding_box:
            continue
        minimum, maximum = space.bounding_box
        centers[space_id] = (
            (minimum.x + maximum.x) / 2,
            (minimum.y + maximum.y) / 2,
            (minimum.z + maximum.z) / 2,
        )
    return centers


def create_ifc_3d_figure(building: Any) -> go.Figure:
    """Render uploaded IFC bounding volumes, connections and exits in 3D."""
    figure = go.Figure()
    centers = _space_centers(building)
    palette = {
        "structural_proxy": "#607d8b",
        "structural_element": "#78909c",
        "corridor": "#42a5f5",
        "stair": "#ab47bc",
        "unknown": "#90caf9",
    }

    for space_id, space in building.spaces.items():
        if not space.bounding_box:
            continue
        minimum, maximum = space.bounding_box
        xs, ys, zs = _box_vertices(minimum, maximum)
        figure.add_trace(go.Mesh3d(
            x=xs,
            y=ys,
            z=zs,
            i=[item[0] for item in BOX_TRIANGLES],
            j=[item[1] for item in BOX_TRIANGLES],
            k=[item[2] for item in BOX_TRIANGLES],
            color=palette.get(space.space_type, "#64b5f6"),
            opacity=0.32,
            flatshading=True,
            name=space.name,
            text=f"{space.name}<br>Type: {space.space_type}<br>Area: {space.area:.1f} m²",
            hoverinfo="text",
            showscale=False,
        ))

    connection_x, connection_y, connection_z = [], [], []
    for door in building.doors.values():
        linked = [centers[item] for item in door.connected_spaces if item in centers]
        if len(linked) == 1:
            linked.append((door.location.x, door.location.y, door.location.z))
        if len(linked) < 2:
            continue
        for first, second in zip(linked, linked[1:]):
            connection_x.extend([first[0], second[0], None])
            connection_y.extend([first[1], second[1], None])
            connection_z.extend([first[2], second[2], None])
    if connection_x:
        figure.add_trace(go.Scatter3d(
            x=connection_x,
            y=connection_y,
            z=connection_z,
            mode="lines",
            line=dict(color="#ffb300", width=5),
            name="Connectivity / routes",
            hoverinfo="skip",
        ))

    if building.exits:
        figure.add_trace(go.Scatter3d(
            x=[door.location.x for door in building.exits.values()],
            y=[door.location.y for door in building.exits.values()],
            z=[door.location.z for door in building.exits.values()],
            mode="markers+text",
            marker=dict(size=8, color="#00c853", symbol="diamond"),
            text=[door.name for door in building.exits.values()],
            textposition="top center",
            name="Exits / inferred egress",
            hoverinfo="text",
        ))

    figure.update_layout(
        title="Uploaded IFC 3D Screening View",
        height=700,
        margin=dict(l=0, r=0, t=45, b=0),
        legend=dict(orientation="h", y=0),
        scene=dict(
            aspectmode="data",
            xaxis_title="X",
            yaxis_title="Y",
            zaxis_title="Z / elevation",
            bgcolor="#f7f9fc",
        ),
    )
    return figure


def create_dataset_3d_figure(
    engine: Any,
    *,
    fire_origin: Optional[str] = None,
    smoke_nodes: Iterable[str] = (),
    blocked_nodes: Iterable[str] = (),
    high_risk_nodes: Iterable[str] = (),
) -> go.Figure:
    """Render a deterministic 3D schematic of a scenario graph."""
    graph = engine.graph
    positions = nx.spring_layout(graph, seed=42, dim=3, weight="distance_m")
    smoke: Set[str] = set(smoke_nodes)
    blocked: Set[str] = set(blocked_nodes)
    high_risk: Set[str] = set(high_risk_nodes)
    exits: Set[str] = set(engine.exit_ids)

    edge_x, edge_y, edge_z = [], [], []
    for source, target in graph.edges():
        first, second = positions[source], positions[target]
        edge_x.extend([first[0], second[0], None])
        edge_y.extend([first[1], second[1], None])
        edge_z.extend([first[2], second[2], None])

    figure = go.Figure(go.Scatter3d(
        x=edge_x,
        y=edge_y,
        z=edge_z,
        mode="lines",
        line=dict(color="#b0bec5", width=4),
        hoverinfo="skip",
        name="Connections",
    ))

    colors, sizes, labels = [], [], []
    for node in graph.nodes():
        details = engine.space_by_id.get(node, {})
        labels.append(
            f"{node}: {details.get('name', node)}"
            f"<br>Type: {details.get('type', 'unknown')}"
            f"<br>Occupancy: {details.get('occupancy', 0)}"
        )
        if node == fire_origin:
            colors.append("#c62828")
            sizes.append(14)
        elif node in blocked:
            colors.append("#212121")
            sizes.append(12)
        elif node in high_risk:
            colors.append("#6a1b9a")
            sizes.append(12)
        elif node in smoke:
            colors.append("#fb8c00")
            sizes.append(11)
        elif node in exits:
            colors.append("#00c853")
            sizes.append(13)
        else:
            colors.append("#1976d2")
            sizes.append(9)

    nodes = list(graph.nodes())
    figure.add_trace(go.Scatter3d(
        x=[positions[node][0] for node in nodes],
        y=[positions[node][1] for node in nodes],
        z=[positions[node][2] for node in nodes],
        mode="markers+text",
        marker=dict(size=sizes, color=colors, line=dict(color="white", width=1)),
        text=nodes,
        textposition="top center",
        hovertext=labels,
        hoverinfo="text",
        name="Spaces and exits",
    ))
    figure.update_layout(
        title="3D Scenario Schematic (not BIM geometry)",
        height=650,
        margin=dict(l=0, r=0, t=45, b=0),
        showlegend=False,
        scene=dict(
            aspectmode="cube",
            xaxis=dict(visible=False),
            yaxis=dict(visible=False),
            zaxis=dict(visible=False),
            bgcolor="#f7f9fc",
        ),
    )
    return figure
