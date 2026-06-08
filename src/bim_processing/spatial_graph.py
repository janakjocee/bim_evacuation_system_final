"""
Spatial graph construction using NetworkX.
"""
from typing import Dict, List, Optional, Tuple, Set
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


class SpatialGraphBuilder:
    """Build spatial connectivity graph from building data."""
    
    def __init__(self, building: BuildingData):
        """Initialize graph builder."""
        self.building = building
        self.config = get_config()
        
        self.graph = None
        self.exit_nodes: Set[str] = set()
        
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
                    self.graph.add_node(
                        stair_id,
                        node_type='stair',
                        name=stair.name,
                        width=stair.width
                    )
            
            # Add edges (simplified connectivity)
            self._add_connectivity_edges()
            
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
                        self.graph.add_edge(
                            space_id,
                            door_id,
                            weight=distance,
                            edge_type="file_geometry_connection",
                        )
            return

        # Simple heuristic: connect spaces to nearby doors
        spaces = list(self.building.spaces.keys())
        doors = list(self.building.doors.keys())
        
        # Connect each space to at least one door
        for i, space_id in enumerate(spaces):
            if doors:
                # Connect to a door (cyclic for simplicity)
                door_id = doors[i % len(doors)]
                self.graph.add_edge(
                    space_id, door_id,
                    weight=5.0,  # Default distance in meters
                    edge_type='space_door'
                )
        
        # Connect doors to each other (for corridors)
        for i in range(len(doors) - 1):
            self.graph.add_edge(
                doors[i], doors[i + 1],
                weight=10.0,
                edge_type='door_door'
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
            
            return Route(
                origin=origin,
                destination=destination,
                path=path,
                distance=distance,
                estimated_time=estimated_time
            )
            
        except nx.NetworkXNoPath:
            logger.warning(f"No path found from {origin} to {destination}")
            return None
        except Exception as e:
            logger.error(f"Error finding path: {e}")
            return None
    
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
        
        return {
            'node_count': self.graph.number_of_nodes(),
            'edge_count': self.graph.number_of_edges(),
            'exit_count': len(self.exit_nodes),
            'is_connected': nx.is_connected(self.graph) if self.graph.number_of_nodes() > 0 else False
        }
