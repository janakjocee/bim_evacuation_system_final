"""
IFC Parser using IfcOpenShell.
"""
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from pathlib import Path
import numpy as np
import math

try:
    import ifcopenshell
    import ifcopenshell.geom
    from ifcopenshell import entity_instance
    IFC_AVAILABLE = True
except ImportError:
    IFC_AVAILABLE = False

from ..utils.logger import get_logger
from ..utils.config_loader import get_config

logger = get_logger("ifc_parser")


@dataclass
class Point3D:
    """3D coordinate point."""
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0


@dataclass
class DoorData:
    """Door data extracted from IFC."""
    id: str
    name: str
    width: float
    height: float
    location: Point3D
    is_external: bool = False
    is_exit: bool = False
    connected_spaces: List[str] = field(default_factory=list)


@dataclass
class SpaceData:
    """Space data extracted from IFC."""
    id: str
    name: str
    area: float
    level: str = ""
    space_type: str = "unknown"
    connected_doors: List[str] = field(default_factory=list)
    bounding_box: Optional[Tuple[Point3D, Point3D]] = None


@dataclass
class StairData:
    """Stair data extracted from IFC."""
    id: str
    name: str
    width: float
    riser_height: float
    tread_length: float
    connected_levels: List[str] = field(default_factory=list)


@dataclass
class BuildingData:
    """Complete building data."""
    id: str
    name: str
    spaces: Dict[str, SpaceData] = field(default_factory=dict)
    doors: Dict[str, DoorData] = field(default_factory=dict)
    stairs: Dict[str, StairData] = field(default_factory=dict)
    exits: Dict[str, DoorData] = field(default_factory=dict)
    levels: Dict[str, str] = field(default_factory=dict)
    extraction_mode: str = "semantic_ifc"
    geometry_source_types: List[str] = field(default_factory=list)
    geometry_elements_available: int = 0
    geometry_elements_used: int = 0


class IFCParser:
    """Parser for IFC building models."""
    
    def __init__(self):
        """Initialize parser."""
        self.config = get_config()
        self.ifc_file = None
        self.building = None
        
        if not IFC_AVAILABLE:
            logger.error("IfcOpenShell not available. Uploaded IFC files cannot be parsed.")
    
    def parse(self, file_path: str) -> Optional[BuildingData]:
        """
        Parse IFC file and extract building data.
        
        Args:
            file_path: Path to IFC file
            
        Returns:
            BuildingData object or None if parsing fails
        """
        try:
            logger.info(f"Parsing IFC file: {file_path}")
            
            if not IFC_AVAILABLE:
                logger.error("IfcOpenShell not available; cannot parse the uploaded IFC")
                return None
            
            if not Path(file_path).exists():
                logger.error(f"File not found: {file_path}")
                return None
            
            self.ifc_file = ifcopenshell.open(file_path)
            
            # Extract building
            building = self._extract_building()
            if building.name.lower() in {"unknown", "unnamed building", "extracted building"}:
                building.name = Path(file_path).stem
            
            # Extract levels
            self._extract_levels(building)
            
            # Extract spaces
            self._extract_spaces(building)
            
            # Extract doors
            self._extract_doors(building)
            
            # Extract stairs
            self._extract_stairs(building)
            
            # Identify exits
            self._identify_exits(building)

            # Structural/specialist exports often omit IfcSpace and IfcDoor.
            # Derive a bounded topology only from real elements in the file.
            if not building.spaces:
                self._extract_geometry_topology(building)
            elif not building.doors or not building.exits:
                self._infer_space_topology(building)
            
            logger.info(f"Successfully parsed building: {building.name}")
            logger.info(f"  Spaces: {len(building.spaces)}")
            logger.info(f"  Doors: {len(building.doors)}")
            logger.info(f"  Stairs: {len(building.stairs)}")
            logger.info(f"  Exits: {len(building.exits)}")
            
            return building
            
        except Exception as e:
            logger.error(f"Error parsing IFC: {e}")
            return None
    
    def _extract_building(self) -> BuildingData:
        """Extract building information."""
        buildings = self.ifc_file.by_type("IfcBuilding")
        
        if buildings:
            ifc_building = buildings[0]
            return BuildingData(
                id=ifc_building.GlobalId,
                name=ifc_building.Name or "Unnamed Building"
            )
        
        return BuildingData(
            id="BUILDING_001",
            name="Extracted Building"
        )
    
    def _extract_levels(self, building: BuildingData) -> None:
        """Extract building levels."""
        storeys = self.ifc_file.by_type("IfcBuildingStorey")
        
        for storey in storeys:
            building.levels[storey.GlobalId] = storey.Name or f"Level_{storey.Elevation}"
    
    def _extract_spaces(self, building: BuildingData) -> None:
        """Extract spaces from IFC."""
        spaces = self.ifc_file.by_type("IfcSpace")
        
        for ifc_space in spaces:
            try:
                space = SpaceData(
                    id=ifc_space.GlobalId,
                    name=ifc_space.Name or "Unnamed Space",
                    area=self._calculate_area(ifc_space),
                    level=self._get_level(ifc_space),
                    space_type=self._get_space_type(ifc_space),
                    bounding_box=self._get_bounding_box(ifc_space),
                )
                building.spaces[space.id] = space
            except Exception as e:
                logger.warning(f"Error extracting space {ifc_space.GlobalId}: {e}")
    
    def _extract_doors(self, building: BuildingData) -> None:
        """Extract doors from IFC."""
        doors = self.ifc_file.by_type("IfcDoor")
        
        for ifc_door in doors:
            try:
                door = DoorData(
                    id=ifc_door.GlobalId,
                    name=ifc_door.Name or "Unnamed Door",
                    width=getattr(ifc_door, 'OverallWidth', 0.9) or 0.9,
                    height=getattr(ifc_door, 'OverallHeight', 2.1) or 2.1,
                    location=self._get_location(ifc_door)
                )
                building.doors[door.id] = door
            except Exception as e:
                logger.warning(f"Error extracting door {ifc_door.GlobalId}: {e}")
    
    def _extract_stairs(self, building: BuildingData) -> None:
        """Extract stairs from IFC."""
        stairs = self.ifc_file.by_type("IfcStair")
        
        for ifc_stair in stairs:
            try:
                stair = StairData(
                    id=ifc_stair.GlobalId,
                    name=ifc_stair.Name or "Unnamed Stair",
                    width=1.2,  # Default width
                    riser_height=0.17,  # Default
                    tread_length=0.25  # Default
                )
                building.stairs[stair.id] = stair
            except Exception as e:
                logger.warning(f"Error extracting stair {ifc_stair.GlobalId}: {e}")
    
    def _identify_exits(self, building: BuildingData) -> None:
        """Identify exit doors."""
        for door_id, door in building.doors.items():
            # Simple heuristic: external doors are exits
            if door.is_external or "exit" in door.name.lower():
                door.is_exit = True
                building.exits[door_id] = door
    
    def _calculate_area(self, ifc_space) -> float:
        """Calculate space area."""
        try:
            # Try to get from quantity sets
            for rel in getattr(ifc_space, 'IsDefinedBy', []):
                if hasattr(rel, 'RelatingPropertyDefinition'):
                    prop_set = rel.RelatingPropertyDefinition
                    if hasattr(prop_set, 'Quantities'):
                        for quantity in prop_set.Quantities:
                            if hasattr(quantity, 'AreaValue'):
                                return float(quantity.AreaValue)
            
            # Default area
            return 20.0
        except:
            return 20.0
    
    def _get_level(self, ifc_space) -> str:
        """Get space level."""
        try:
            for rel in getattr(ifc_space, 'Decomposes', []):
                if hasattr(rel, 'RelatingObject'):
                    return rel.RelatingObject.GlobalId
        except:
            pass
        return ""
    
    def _get_space_type(self, ifc_space) -> str:
        """Determine space type from name."""
        name = (ifc_space.Name or "").lower()
        
        if "office" in name:
            return "office"
        elif "corridor" in name or "hall" in name:
            return "corridor"
        elif "stair" in name:
            return "stair"
        elif "lobby" in name:
            return "lobby"
        elif "toilet" in name or "wc" in name:
            return "toilet"
        
        return "unknown"
    
    def _get_location(self, element) -> Point3D:
        """Get element location."""
        try:
            placement = getattr(element, 'ObjectPlacement', None)
            if placement and hasattr(placement, 'RelativePlacement'):
                coords = placement.RelativePlacement.Location.Coordinates
                return Point3D(x=coords[0], y=coords[1], z=coords[2] if len(coords) > 2 else 0)
        except:
            pass
        return Point3D()

    def _get_bounding_box(self, element) -> Optional[Tuple[Point3D, Point3D]]:
        """Extract a world-coordinate bounding box when IFC geometry is available."""
        try:
            settings = ifcopenshell.geom.settings()
            settings.set(settings.USE_WORLD_COORDS, True)
            shape = ifcopenshell.geom.create_shape(settings, element)
            vertices = shape.geometry.verts
            points = list(zip(vertices[0::3], vertices[1::3], vertices[2::3]))
            if not points:
                return None
            xs, ys, zs = zip(*points)
            return Point3D(min(xs), min(ys), min(zs)), Point3D(max(xs), max(ys), max(zs))
        except Exception:
            return None
    
    def _extract_geometry_topology(self, building: BuildingData) -> None:
        """Derive a bounded analysis topology from real geometry-only IFC elements."""
        proxies = self.ifc_file.by_type("IfcBuildingElementProxy")
        if proxies:
            candidates = proxies
            source_types = ["IfcBuildingElementProxy"]
            space_type = "structural_proxy"
        else:
            stairs = self.ifc_file.by_type("IfcStair")
            slabs = self.ifc_file.by_type("IfcSlab")
            walls = self.ifc_file.by_type("IfcWall")
            candidates = stairs + slabs
            if len(candidates) < 2:
                candidates += walls
            source_types = [
                name
                for name, values in (
                    ("IfcStair", stairs),
                    ("IfcSlab", slabs),
                    ("IfcWall", walls if len(stairs + slabs) < 2 else []),
                )
                if values
            ]
            space_type = "structural_element"

        if not candidates:
            return

        building.geometry_elements_available = len(candidates)
        candidates = self._evenly_sample(candidates, 60)
        building.geometry_source_types = source_types

        settings = ifcopenshell.geom.settings()
        settings.set(settings.USE_WORLD_COORDS, True)
        geometry_rows = []

        for element in candidates:
            try:
                shape = ifcopenshell.geom.create_shape(settings, element)
                verts = shape.geometry.verts
                points = list(zip(verts[0::3], verts[1::3], verts[2::3]))
                if not points:
                    continue
                xs = [point[0] for point in points]
                ys = [point[1] for point in points]
                zs = [point[2] for point in points]
                minimum = Point3D(min(xs), min(ys), min(zs))
                maximum = Point3D(max(xs), max(ys), max(zs))
                center = Point3D(
                    (minimum.x + maximum.x) / 2,
                    (minimum.y + maximum.y) / 2,
                    (minimum.z + maximum.z) / 2,
                )
                properties = self._get_properties(element)
                element_number = properties.get("13:Elem nr")
                element_type = element.is_a()
                name = element_number or element.Name or f"{element_type} {element.GlobalId[:8]}"
                area = max(1.0, (maximum.x - minimum.x) * (maximum.y - minimum.y))
                geometry_rows.append((element, name, area, center, minimum, maximum))
            except Exception as exc:
                logger.warning(f"Could not derive geometry for {element.GlobalId}: {exc}")

        if len(geometry_rows) < 2:
            return

        # Keep distinct geometry objects only; several exports duplicate helper
        # geometry with exactly the same bounds.
        unique_rows = []
        seen_bounds = set()
        for row in geometry_rows:
            bounds = tuple(round(value, 4) for value in (
                row[4].x, row[4].y, row[4].z, row[5].x, row[5].y, row[5].z
            ))
            if bounds not in seen_bounds:
                seen_bounds.add(bounds)
                unique_rows.append(row)

        for index, (element, name, area, center, minimum, maximum) in enumerate(unique_rows, 1):
            display_name = f"{name} [{element.is_a()} #{index}]"
            building.spaces[element.GlobalId] = SpaceData(
                id=element.GlobalId,
                name=display_name,
                area=area,
                level=self._get_containing_level(element),
                space_type=space_type,
                bounding_box=(minimum, maximum),
            )

        centers = {row[0].GlobalId: row[3] for row in unique_rows}
        self._add_proxy_connectivity(building, centers)
        self._add_inferred_proxy_exits(building, centers)
        building.extraction_mode = "geometry_derived"
        building.geometry_elements_used = len(unique_rows)
        logger.info(
            f"Derived file geometry topology from {', '.join(source_types)}: "
            f"{len(building.spaces)} elements, "
            f"{len(building.doors)} inferred connections, {len(building.exits)} inferred exits"
        )

    def _infer_space_topology(self, building: BuildingData) -> None:
        """Infer route links for IFCs that include spaces but omit door semantics."""
        centers = {}
        missing_geometry = 0
        for space_id, space in building.spaces.items():
            if not space.bounding_box:
                missing_geometry += 1
                continue
            minimum, maximum = space.bounding_box
            centers[space_id] = Point3D(
                (minimum.x + maximum.x) / 2,
                (minimum.y + maximum.y) / 2,
                (minimum.z + maximum.z) / 2,
            )

        if len(centers) < 2:
            return

        existing_door_count = len(building.doors)
        if not building.doors:
            self._add_proxy_connectivity(building, centers)
        if not building.exits:
            self._add_inferred_proxy_exits(building, centers)

        if len(building.doors) > existing_door_count or building.exits:
            building.extraction_mode = "semantic_spaces_inferred_topology"
            building.geometry_source_types = ["IfcSpace"]
            building.geometry_elements_available = len(building.spaces)
            building.geometry_elements_used = len(centers)
            logger.info(
                "Inferred route topology from IfcSpace geometry: "
                f"{len(centers)} spaces with usable bounds, "
                f"{len(building.doors) - existing_door_count} inferred connections/exits, "
                f"{missing_geometry} spaces without bounds"
            )

    @staticmethod
    def _evenly_sample(elements: List[Any], limit: int) -> List[Any]:
        """Keep deterministic coverage across a large IFC element collection."""
        if len(elements) <= limit:
            return elements
        return [elements[round(index * (len(elements) - 1) / (limit - 1))] for index in range(limit)]

    def _add_proxy_connectivity(self, building: BuildingData, centers: Dict[str, Point3D]) -> None:
        """Connect all proxy elements using a minimum-distance spanning tree."""
        ids = list(centers)
        connected = {ids[0]}
        remaining = set(ids[1:])
        edge_index = 1

        while remaining:
            distance, source, target = min(
                (
                    self._point_distance(centers[a], centers[b]),
                    a,
                    b,
                )
                for a in connected
                for b in remaining
            )
            midpoint = Point3D(
                (centers[source].x + centers[target].x) / 2,
                (centers[source].y + centers[target].y) / 2,
                (centers[source].z + centers[target].z) / 2,
            )
            door_id = f"INFERRED_CONNECTION_{edge_index:03d}"
            building.doors[door_id] = DoorData(
                id=door_id,
                name=f"Inferred geometry connection {edge_index}",
                width=0.9,
                height=2.1,
                location=midpoint,
                connected_spaces=[source, target],
            )
            building.spaces[source].connected_doors.append(door_id)
            building.spaces[target].connected_doors.append(door_id)
            connected.add(target)
            remaining.remove(target)
            edge_index += 1

    def _add_inferred_proxy_exits(self, building: BuildingData, centers: Dict[str, Point3D]) -> None:
        """Add two egress points at the most distant boundary elements."""
        ids = list(centers)
        first, second = max(
            ((a, b) for index, a in enumerate(ids) for b in ids[index + 1:]),
            key=lambda pair: self._point_distance(centers[pair[0]], centers[pair[1]]),
        )
        for index, space_id in enumerate((first, second), 1):
            exit_id = f"INFERRED_EXIT_{index:03d}"
            exit_door = DoorData(
                id=exit_id,
                name=f"Inferred boundary egress {index}",
                width=1.2,
                height=2.1,
                location=centers[space_id],
                is_external=True,
                is_exit=True,
                connected_spaces=[space_id],
            )
            building.doors[exit_id] = exit_door
            building.exits[exit_id] = exit_door
            building.spaces[space_id].connected_doors.append(exit_id)

    def _get_properties(self, element) -> Dict[str, Any]:
        properties = {}
        for relation in getattr(element, "IsDefinedBy", []):
            prop_set = getattr(relation, "RelatingPropertyDefinition", None)
            for prop in getattr(prop_set, "HasProperties", []):
                value = getattr(getattr(prop, "NominalValue", None), "wrappedValue", None)
                properties[getattr(prop, "Name", "")] = value
        return properties

    def _get_containing_level(self, element) -> str:
        for relation in getattr(element, "ContainedInStructure", []):
            structure = getattr(relation, "RelatingStructure", None)
            if structure:
                return structure.GlobalId
        return ""

    @staticmethod
    def _point_distance(first: Point3D, second: Point3D) -> float:
        return math.sqrt(
            (first.x - second.x) ** 2
            + (first.y - second.y) ** 2
            + (first.z - second.z) ** 2
        )
