"""
Spatial graph construction using NetworkX.
"""
from typing import Any, Dict, List, Optional, Tuple, Set
from dataclasses import dataclass
import math

try:
    import networkx as nx
    NETWORKX_AVAILABLE = True
except ImportError:
    NETWORKX_AVAILABLE = False

from ..utils.logger import get_logger
from ..utils.config_loader import get_config
from .ifc_parser import BuildingData, SpaceData, DoorData, Point3D

logger = get_logger("spatial_graph")


@dataclass
class Route:
    """Evacuation route."""
    origin: str
    destination: str
    path: List[str]
    distance: float
    estimated_time: float
    verified_edge_count: int = 0
    inferred_edge_count: int = 0
    route_confidence: float = 1.0
    edge_sources: List[str] = None


class SpatialGraphBuilder:
    """Build spatial connectivity graph from building data."""
    
    def __init__(self, building: BuildingData):
        """Initialize graph builder."""
        self.building = building
        self.config = get_config()
        
        self.graph = None
        self.exit_nodes: Set[str] = set()
        self.validation: Dict[str, Any] = {}
        
        if not NETWORKX_AVAILABLE:
            logger.warning("NetworkX not available. Graph features will be limited.")
    
    def build(self) -> bool:
        """
        Build spatial graph.
        
        Returns:
            True if successful
        """
        logger.info("Building spatial graph")
        
        if not NETWORKX_AVAILABLE:
            logger.warning("NetworkX not available")
            return False
        
        try:
            self.graph = nx.Graph()
            
            # Add space nodes
            for space_id, space in self.building.spaces.items():
                self.graph.add_node(
                    space_id,
                    node_type='space',
                    name=space.name,
                    area=space.area
                )
            
            # Add door nodes
            for door_id, door in self.building.doors.items():
                self.graph.add_node(
                    door_id,
                    node_type='door',
                    name=door.name,
                    width=door.width,
                    is_exit=door.is_exit
                )
                
                if door.is_exit:
                    self.exit_nodes.add(door_id)
            
            # In geometry-derived mode, stair geometry is already represented
            # among the screened element nodes. Separate stair nodes would be
            # disconnected because the source IFC has no semantic route links.
            if self.building.extraction_mode != "geometry_derived":
                for stair_id, stair in self.building.stairs.items():
                    if not stair.connected_spaces:
                        continue
                    self.graph.add_node(
                        stair_id,
                        node_type='stair',
                        name=stair.name,
                        width=stair.width
                    )
            
            # Add edges from verified or explicitly inferred connectivity only.
            self._add_connectivity_edges()
            self._add_stair_edges()
            self.validation = self.validate_graph()
            
            logger.info(f"Graph built: {self.graph.number_of_nodes()} nodes, "
                       f"{self.graph.number_of_edges()} edges")
            
            return True
            
        except Exception as e:
            logger.error(f"Error building graph: {e}")
            return False
    
    def _add_connectivity_edges(self) -> None:
        """Add connectivity edges between spaces and doors."""
        explicit_connections = [
            (door_id, door)
            for door_id, door in self.building.doors.items()
            if door.connected_spaces
        ]
        if explicit_connections:
            for door_id, door in explicit_connections:
                for space_id in door.connected_spaces:
                    if space_id in self.graph:
                        distance = self._space_to_door_distance(space_id, door)
                        edge_type = door.connection_sources.get(
                            space_id,
                            door.connection_source or "explicit_connection",
                        )
                        self.graph.add_edge(
                            space_id,
                            door_id,
                            weight=distance,
                            edge_type=edge_type,
                            inferred=edge_type.startswith("inferred"),
                        )
            return
        logger.warning("No verified or explicitly inferred door-space connectivity found; graph edges were not fabricated.")

    def _add_stair_edges(self) -> None:
        """Add labelled stair-space edges when the parser found touching geometry."""
        for stair_id, stair in self.building.stairs.items():
            if stair_id not in self.graph:
                continue
            for space_id in stair.connected_spaces:
                if space_id not in self.graph:
                    continue
                edge_type = stair.connection_source or "inferred_stair_geometry"
                self.graph.add_edge(
                    space_id,
                    stair_id,
                    weight=self._space_to_stair_distance(space_id, stair),
                    edge_type=edge_type,
                    inferred=edge_type.startswith("inferred"),
                )

    def _space_to_door_distance(self, space_id: str, door: DoorData) -> float:
        """Calculate distance from a file-derived space center to a connection."""
        space = self.building.spaces[space_id]
        if not space.bounding_box:
            return 5.0
        minimum, maximum = space.bounding_box
        center = Point3D(
            (minimum.x + maximum.x) / 2,
            (minimum.y + maximum.y) / 2,
            (minimum.z + maximum.z) / 2,
        )
        return max(
            0.1,
            math.sqrt(
                (center.x - door.location.x) ** 2
                + (center.y - door.location.y) ** 2
                + (center.z - door.location.z) ** 2
            ),
        )

    def _space_to_stair_distance(self, space_id: str, stair) -> float:
        """Estimate travel distance between a space and touching stair geometry."""
        space_bounds = self.building.spaces[space_id].bounding_box
        stair_bounds = stair.bounding_box
        if not space_bounds or not stair_bounds:
            return 5.0
        space_min, space_max = space_bounds
        stair_min, stair_max = stair_bounds
        space_center = Point3D(
            (space_min.x + space_max.x) / 2,
            (space_min.y + space_max.y) / 2,
            (space_min.z + space_max.z) / 2,
        )
        stair_center = Point3D(
            (stair_min.x + stair_max.x) / 2,
            (stair_min.y + stair_max.y) / 2,
            (stair_min.z + stair_max.z) / 2,
        )
        return max(
            0.1,
            math.sqrt(
                (space_center.x - stair_center.x) ** 2
                + (space_center.y - stair_center.y) ** 2
                + (space_center.z - stair_center.z) ** 2
            ),
        )
    
    def find_shortest_path(self, origin: str, destination: str) -> Optional[Route]:
        """
        Find shortest path between two nodes.
        
        Args:
            origin: Origin node ID
            destination: Destination node ID
            
        Returns:
            Route object or None
        """
        if not NETWORKX_AVAILABLE or self.graph is None:
            return None
        
        try:
            if origin not in self.graph or destination not in self.graph:
                return None
            
            path = nx.shortest_path(
                self.graph, origin, destination, weight='weight'
            )
            
            distance = nx.shortest_path_length(
                self.graph, origin, destination, weight='weight'
            )
            
            # Calculate estimated time
            travel_speed = self.config.get('bim.travel_speed.level', 1.2)
            estimated_time = distance / travel_speed
            verified_edges, inferred_edges, edge_sources = self._route_edge_quality(path)
            total_edges = max(verified_edges + inferred_edges, 1)
            route_confidence = max(0.15, verified_edges / total_edges)
            if self.building.extraction_mode == "geometry_derived":
                route_confidence = min(route_confidence, 0.35)
            elif self.building.extraction_mode == "semantic_spaces_inferred_topology":
                route_confidence = min(route_confidence, 0.55)
            
            return Route(
                origin=origin,
                destination=destination,
                path=path,
                distance=distance,
                estimated_time=estimated_time,
                verified_edge_count=verified_edges,
                inferred_edge_count=inferred_edges,
                route_confidence=route_confidence,
                edge_sources=edge_sources,
            )
            
        except nx.NetworkXNoPath:
            logger.debug(f"No path found from {origin} to {destination}")
            return None
        except Exception as e:
            logger.error(f"Error finding path: {e}")
            return None

    def _route_edge_quality(self, path: List[str]) -> Tuple[int, int, List[str]]:
        """Summarize verified/inferred edge quality along a path."""
        verified_edges = 0
        inferred_edges = 0
        edge_sources: List[str] = []
        for first, second in zip(path, path[1:]):
            edge_data = self.graph.get_edge_data(first, second, default={}) if self.graph else {}
            source = str(edge_data.get("edge_type", "unknown"))
            edge_sources.append(source)
            if edge_data.get("inferred") or source.startswith("inferred"):
                inferred_edges += 1
            else:
                verified_edges += 1
        return verified_edges, inferred_edges, edge_sources
    
    def find_paths_to_exits(self, origin: str) -> List[Route]:
        """
        Find all paths from origin to exits.
        
        Args:
            origin: Origin space ID
            
        Returns:
            List of routes to exits
        """
        routes = []
        
        for exit_id in self.exit_nodes:
            route = self.find_shortest_path(origin, exit_id)
            if route:
                routes.append(route)
        
        # Sort by distance
        routes.sort(key=lambda r: r.distance)
        
        return routes
    
    def identify_bottlenecks(self, top_n: int = 5) -> List[Dict]:
        """
        Identify bottleneck nodes using betweenness centrality.
        
        Args:
            top_n: Number of top bottlenecks to return
            
        Returns:
            List of bottleneck information
        """
        if not NETWORKX_AVAILABLE or self.graph is None:
            return []
        
        try:
            centrality = nx.betweenness_centrality(self.graph)
            
            # Sort by centrality
            sorted_nodes = sorted(
                centrality.items(),
                key=lambda x: x[1],
                reverse=True
            )
            
            bottlenecks = []
            for node_id, score in sorted_nodes[:top_n]:
                node_data = self.graph.nodes[node_id]
                bottlenecks.append({
                    'node_id': node_id,
                    'name': node_data.get('name', 'Unknown'),
                    'type': node_data.get('node_type', 'unknown'),
                    'centrality': round(score, 4)
                })
            
            return bottlenecks
            
        except Exception as e:
            logger.error(f"Error identifying bottlenecks: {e}")
            return []
    
    def get_graph_stats(self) -> Dict:
        """Get graph statistics."""
        if not NETWORKX_AVAILABLE or self.graph is None:
            return {}

        stats = {
            'node_count': self.graph.number_of_nodes(),
            'edge_count': self.graph.number_of_edges(),
            'exit_count': len(self.exit_nodes),
            'is_connected': nx.is_connected(self.graph) if self.graph.number_of_nodes() > 0 else False
        }
        stats.update(self.validation or self.validate_graph())
        return stats

    def validate_graph(self) -> Dict[str, Any]:
        """Validate route graph completeness and confidence."""
        if not NETWORKX_AVAILABLE or self.graph is None:
            return {}

        space_ids = set(self.building.spaces)
        door_ids = set(self.building.doors)
        inferred_edges = 0
        verified_edges = 0
        for _, _, data in self.graph.edges(data=True):
            if data.get("inferred") or str(data.get("edge_type", "")).startswith("inferred"):
                inferred_edges += 1
            else:
                verified_edges += 1

        disconnected_spaces = sorted(space_id for space_id in space_ids if self.graph.degree(space_id) == 0)
        doors_without_spaces = sorted(
            door_id for door_id in door_ids if not self.building.doors[door_id].connected_spaces
        )
        stairs_without_spaces = sorted(
            stair_id
            for stair_id, stair in self.building.stairs.items()
            if not stair.connected_spaces
        )
        spaces_without_exit_route = []
        for space_id in space_ids:
            if not self.find_paths_to_exits(space_id):
                spaces_without_exit_route.append(space_id)

        total_spaces = max(len(space_ids), 1)
        total_doors = max(len(door_ids), 1)
        total_edges = verified_edges + inferred_edges
        routed_space_ratio = max(0.0, 1.0 - (len(spaces_without_exit_route) / total_spaces))
        connected_space_ratio = max(0.0, 1.0 - (len(disconnected_spaces) / total_spaces))
        connected_door_ratio = max(0.0, 1.0 - (len(doors_without_spaces) / total_doors))
        evidence_ratio = (
            verified_edges / total_edges
            if total_edges
            else 0.0
        )

        topology_confidence = (
            (routed_space_ratio * 0.45)
            + (connected_space_ratio * 0.30)
            + (connected_door_ratio * 0.10)
            + (evidence_ratio * 0.15)
        )
        if self.building.extraction_mode == "geometry_derived":
            topology_confidence = min(topology_confidence * 0.55, 0.55)
        elif self.building.extraction_mode == "semantic_spaces_inferred_topology":
            topology_confidence = min(topology_confidence * 0.75, 0.75)

        if not self.exit_nodes:
            topology_confidence = 0.0
        topology_confidence = max(0.0, min(topology_confidence, 1.0))

        return {
            "verified_edges_count": verified_edges,
            "inferred_edges_count": inferred_edges,
            "disconnected_spaces": disconnected_spaces,
            "doors_without_connected_spaces": doors_without_spaces,
            "stairs_without_connected_spaces": stairs_without_spaces,
            "spaces_without_exit_route": sorted(spaces_without_exit_route),
            "routed_space_ratio": round(routed_space_ratio, 2),
            "connected_space_ratio": round(connected_space_ratio, 2),
            "connected_door_ratio": round(connected_door_ratio, 2),
            "edge_evidence_ratio": round(evidence_ratio, 2),
            "graph_confidence_score": round(topology_confidence, 2),
        }
