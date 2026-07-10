"""Reusable interactive 3D visualizations for IFC and scenario data."""
from __future__ import annotations

from typing import Any, Dict, Iterable, Optional, Set, Tuple

try:
    import networkx as nx
    NETWORKX_AVAILABLE = True
except ImportError:  # pragma: no cover
    nx = None
    NETWORKX_AVAILABLE = False
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


def _element_color(space: Any) -> str:
    """Choose a readable color from semantic type or IFC class in the name."""
    name = space.name.lower()
    if "stair" in name or space.space_type == "stair":
        return "#8e24aa"
    if "wall" in name:
        return "#546e7a"
    if "slab" in name:
        return "#42a5f5"
    if "corridor" in name or space.space_type == "corridor":
        return "#00acc1"
    if "proxy" in name or space.space_type == "structural_proxy":
        return "#78909c"
    return "#1976d2"


def create_ifc_plan_figure(building: Any) -> go.Figure:
    """Render a high-contrast top-down IFC footprint and egress diagram."""
    figure = go.Figure()
    centers = _space_centers(building)

    for space_id, space in building.spaces.items():
        if not space.bounding_box:
            continue
        minimum, maximum = space.bounding_box
        color = _element_color(space)
        figure.add_trace(go.Scatter(
            x=[minimum.x, maximum.x, maximum.x, minimum.x, minimum.x],
            y=[minimum.y, minimum.y, maximum.y, maximum.y, minimum.y],
            mode="lines",
            fill="toself",
            fillcolor=color,
            opacity=0.48,
            line=dict(color=color, width=2),
            text=(
                f"{space.name}<br>Type: {space.space_type}<br>"
                f"Area: {space.area:.1f} m²<br>Elevation: {minimum.z:.2f}–{maximum.z:.2f}"
            ),
            hoverinfo="text",
            name=space.name,
            showlegend=False,
        ))

    connection_x, connection_y = [], []
    for door in building.doors.values():
        linked = [centers[item] for item in door.connected_spaces if item in centers]
        if len(linked) == 1:
            linked.append((door.location.x, door.location.y, door.location.z))
        for first, second in zip(linked, linked[1:]):
            connection_x.extend([first[0], second[0], None])
            connection_y.extend([first[1], second[1], None])
    if connection_x:
        figure.add_trace(go.Scatter(
            x=connection_x,
            y=connection_y,
            mode="lines",
            line=dict(color="#f9a825", width=3),
            name="Evacuation connectivity",
            hoverinfo="skip",
        ))

    if building.exits:
        figure.add_trace(go.Scatter(
            x=[door.location.x for door in building.exits.values()],
            y=[door.location.y for door in building.exits.values()],
            mode="markers+text",
            marker=dict(size=15, color="#00c853", symbol="diamond", line=dict(color="white", width=2)),
            text=[door.name for door in building.exits.values()],
            textposition="top center",
            name="Exits / inferred egress",
            hoverinfo="text",
        ))

    figure.update_layout(
        title="Uploaded IFC Top-Down Diagram",
        height=700,
        margin=dict(l=10, r=10, t=50, b=10),
        hovermode="closest",
        legend=dict(orientation="h", y=1.02),
        plot_bgcolor="#f7f9fc",
        xaxis=dict(title="X", scaleanchor="y", scaleratio=1),
        yaxis=dict(title="Y"),
    )
    return figure


def create_ifc_3d_figure(building: Any) -> go.Figure:
    """Render uploaded IFC bounding volumes, connections and exits in 3D."""
    figure = go.Figure()
    centers = _space_centers(building)
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
            color=_element_color(space),
            opacity=0.5,
            flatshading=True,
            name=space.name,
            text=f"{space.name}<br>Type: {space.space_type}<br>Area: {space.area:.1f} m²",
            hoverinfo="text",
            showscale=False,
        ))

    if centers:
        figure.add_trace(go.Scatter3d(
            x=[point[0] for point in centers.values()],
            y=[point[1] for point in centers.values()],
            z=[point[2] for point in centers.values()],
            mode="markers",
            marker=dict(size=5, color="#0d47a1", line=dict(color="white", width=1)),
            text=[building.spaces[item].name for item in centers],
            hoverinfo="text",
            name="Element / space centers",
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
