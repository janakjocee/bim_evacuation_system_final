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
    properties: Dict[str, Any] = field(default_factory=dict)
    data_quality_flags: List[str] = field(default_factory=list)
    assumptions: Dict[str, str] = field(default_factory=dict)
    connection_source: str = "unconnected"
    width_confidence: float = 1.0
    is_fire_door: Optional[bool] = None
    is_smoke_stop: Optional[bool] = None


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
    data_quality_flags: List[str] = field(default_factory=list)
    assumptions: Dict[str, str] = field(default_factory=dict)
    area_confidence: float = 1.0


@dataclass
class StairData:
    """Stair data extracted from IFC."""
    id: str
    name: str
    width: float
    riser_height: float
    tread_length: float
    connected_levels: List[str] = field(default_factory=list)
    data_quality_flags: List[str] = field(default_factory=list)
    assumptions: Dict[str, str] = field(default_factory=dict)


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
    data_quality_flags: List[str] = field(default_factory=list)


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

            # Connect doors to spaces using IFC semantic relationships where available.
            self._connect_doors_to_spaces_from_boundaries(building)
            self._connect_doors_to_spaces_by_proximity(building)
            
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
                area, area_source, area_confidence, area_flags = self._extract_space_area(ifc_space)
                space = SpaceData(
                    id=ifc_space.GlobalId,
                    name=ifc_space.Name or "Unnamed Space",
                    area=area,
                    level=self._get_level(ifc_space),
                    space_type=self._get_space_type(ifc_space),
                    bounding_box=self._get_bounding_box(ifc_space),
                    data_quality_flags=area_flags,
                    assumptions={} if area_confidence >= 1 else {"area": area_source},
                    area_confidence=area_confidence,
                )
                building.spaces[space.id] = space
            except Exception as e:
                logger.warning(f"Error extracting space {ifc_space.GlobalId}: {e}")
    
    def _extract_doors(self, building: BuildingData) -> None:
        """Extract doors from IFC."""
        doors = self.ifc_file.by_type("IfcDoor")
        
        for ifc_door in doors:
            try:
                properties = self._get_properties(ifc_door)
                width, height, assumptions, confidence, flags = self._extract_door_dimensions(ifc_door, properties)
                door = DoorData(
                    id=ifc_door.GlobalId,
                    name=ifc_door.Name or "Unnamed Door",
                    width=width,
                    height=height,
                    location=self._get_location(ifc_door),
                    is_external=self._property_bool(properties, "IsExternal"),
                    properties=properties,
                    data_quality_flags=flags,
                    assumptions=assumptions,
                    width_confidence=confidence,
                    is_fire_door=self._property_bool(properties, "FireRating") or self._property_bool(properties, "FireExit"),
                    is_smoke_stop=self._property_bool(properties, "SmokeStop") or self._property_bool(properties, "SmokeSeal"),
                )
                building.doors[door.id] = door
            except Exception as e:
                logger.warning(f"Error extracting door {ifc_door.GlobalId}: {e}")
    
    def _extract_stairs(self, building: BuildingData) -> None:
        """Extract stairs from IFC."""
        stairs = self.ifc_file.by_type("IfcStair")
        
        for ifc_stair in stairs:
            try:
                properties = self._get_properties(ifc_stair)
                width = self._first_numeric_property(properties, ["Width", "ClearWidth", "NominalWidth"])
                assumptions = {}
                flags = []
                if width is None:
                    width = 1.2
                    assumptions["width"] = "Assumed 1.2m because no stair width property was found."
                    flags.append("missing_stair_width_assumed")
                stair = StairData(
                    id=ifc_stair.GlobalId,
                    name=ifc_stair.Name or "Unnamed Stair",
                    width=width,
                    riser_height=0.17,
                    tread_length=0.25,
                    assumptions=assumptions,
                    data_quality_flags=flags,
                )
                building.stairs[stair.id] = stair
            except Exception as e:
                logger.warning(f"Error extracting stair {ifc_stair.GlobalId}: {e}")
    
    def _identify_exits(self, building: BuildingData) -> None:
        """Identify exit doors."""
        space_bounds = [space.bounding_box for space in building.spaces.values() if space.bounding_box]
        perimeter = self._combined_bounds(space_bounds)
        for door_id, door in building.doors.items():
            name = door.name.lower()
            keyword_exit = any(word in name for word in ["exit", "final exit", "egress", "external", "entrance", "entry"])
            property_exit = (
                self._property_bool(door.properties, "FireExit")
                or self._property_bool(door.properties, "Exit")
                or self._property_bool(door.properties, "EmergencyExit")
            )
            perimeter_exit = perimeter is not None and self._point_near_bounds_perimeter(door.location, perimeter)
            if door.is_external or keyword_exit or property_exit or perimeter_exit:
                door.is_exit = True
                if perimeter_exit and not (door.is_external or keyword_exit or property_exit):
                    door.data_quality_flags.append("exit_inferred_from_perimeter_location")
                    door.assumptions["exit_detection"] = (
                        "Door treated as a possible exit because it is near the building space perimeter."
                    )
                building.exits[door_id] = door
    
    def _extract_space_area(self, ifc_space) -> Tuple[float, str, float, List[str]]:
        """Extract space area with source/confidence metadata."""
        try:
            properties = self._get_properties(ifc_space)
            area_from_properties = self._first_numeric_property(properties, [
                "NetFloorArea",
                "GrossFloorArea",
                "NetPlannedArea",
                "GrossPlannedArea",
                "NetArea",
                "GrossArea",
                "Area",
            ])
            if area_from_properties:
                return float(area_from_properties), "IFC space property area", 1.0, []

            for rel in getattr(ifc_space, 'IsDefinedBy', []):
                if hasattr(rel, 'RelatingPropertyDefinition'):
                    prop_set = rel.RelatingPropertyDefinition
                    if hasattr(prop_set, 'Quantities'):
                        for quantity in prop_set.Quantities:
                            if hasattr(quantity, 'AreaValue') and str(getattr(quantity, "Name", "")).lower() in {
                                "netfloorarea", "grossfloorarea", "area", "netarea"
                            }:
                                return float(quantity.AreaValue), "IFC quantity AreaValue", 1.0, []

            bounding_box = self._get_bounding_box(ifc_space)
            if bounding_box:
                minimum, maximum = bounding_box
                area = max(1.0, (maximum.x - minimum.x) * (maximum.y - minimum.y))
                return area, "Estimated from geometry bounding box footprint", 0.6, [
                    "space_area_estimated_from_geometry"
                ]
        except Exception:
            pass

        return 20.0, "Assumed 20m2 because no area quantity or geometry was available", 0.25, [
            "missing_space_area_assumed"
        ]

    def _extract_door_dimensions(
        self, ifc_door, properties: Dict[str, Any]
    ) -> Tuple[float, float, Dict[str, str], float, List[str]]:
        """Extract door dimensions with assumption metadata."""
        assumptions: Dict[str, str] = {}
        flags: List[str] = []

        width = getattr(ifc_door, "OverallWidth", None)
        width_source = "IfcDoor.OverallWidth"
        if not width:
            width = self._first_numeric_property(properties, [
                "ClearWidth", "Width", "NominalWidth", "OverallWidth", "EffectiveWidth", "GrossWidth"
            ])
            width_source = "door property set"

        confidence = 1.0
        if not width:
            width = 0.9
            confidence = 0.35
            assumptions["width"] = "Assumed 0.9m because no IFC door width or property-set width was found."
            flags.append("missing_door_width_assumed")
        else:
            assumptions["width_source"] = width_source

        height = getattr(ifc_door, "OverallHeight", None)
        if not height:
            height = self._first_numeric_property(properties, ["Height", "NominalHeight", "OverallHeight"])
        if not height:
            height = 2.1
            assumptions["height"] = "Assumed 2.1m because no IFC door height was found."
            flags.append("missing_door_height_assumed")

        return float(width), float(height), assumptions, confidence, flags

    @staticmethod
    def _first_numeric_property(properties: Dict[str, Any], names: List[str]) -> Optional[float]:
        lower_map = {str(key).lower(): value for key, value in properties.items()}
        for name in names:
            value = lower_map.get(name.lower())
            if isinstance(value, (int, float)):
                return float(value)
            if isinstance(value, str):
                try:
                    return float(value)
                except ValueError:
                    continue
        return None

    @staticmethod
    def _property_bool(properties: Dict[str, Any], name: str) -> bool:
        value = next((v for k, v in properties.items() if str(k).lower() == name.lower()), None)
        if isinstance(value, bool):
            return value
        if isinstance(value, (int, float)):
            return bool(value)
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {"false", "f", "no", "0", "none", "n/a", ""}:
                return False
            return normalized in {"true", "t", "yes", "1", "external", "fire rated", "exit"} or bool(normalized)
        return False

    def _connect_doors_to_spaces_from_boundaries(self, building: BuildingData) -> None:
        """Connect doors to spaces using IfcRelSpaceBoundary / opening fillings."""
        for ifc_space in self.ifc_file.by_type("IfcSpace"):
            space_id = ifc_space.GlobalId
            for boundary in getattr(ifc_space, "BoundedBy", []) or []:
                element = getattr(boundary, "RelatedBuildingElement", None)
                for door_id in self._door_ids_from_boundary_element(element):
                    if door_id in building.doors and space_id in building.spaces:
                        door = building.doors[door_id]
                        if space_id not in door.connected_spaces:
                            door.connected_spaces.append(space_id)
                        if door_id not in building.spaces[space_id].connected_doors:
                            building.spaces[space_id].connected_doors.append(door_id)
                        door.connection_source = "IfcRelSpaceBoundary"

    def _connect_doors_to_spaces_by_proximity(self, building: BuildingData) -> None:
        """Infer door-space links from door locations and space bounding boxes."""
        if not building.spaces or not building.doors:
            return

        for door_id, door in building.doors.items():
            if door.connected_spaces:
                continue
            candidates = []
            for space_id, space in building.spaces.items():
                if not space.bounding_box:
                    continue
                distance = self._point_to_box_distance(door.location, space.bounding_box)
                if distance <= 2.5:
                    candidates.append((distance, space_id))

            candidates.sort(key=lambda item: item[0])
            for _, space_id in candidates[:2]:
                door.connected_spaces.append(space_id)
                building.spaces[space_id].connected_doors.append(door_id)
            if candidates:
                door.connection_source = "inferred_proximity"
                door.data_quality_flags.append("door_space_connection_inferred_by_proximity")
                door.assumptions["connectivity"] = (
                    "Door-space relationship inferred from door location and space bounding boxes."
                )

    def _door_ids_from_boundary_element(self, element) -> List[str]:
        """Resolve a boundary element or opening element to one or more door ids."""
        if element is None:
            return []
        try:
            if element.is_a("IfcDoor"):
                return [element.GlobalId]
            if element.is_a("IfcOpeningElement"):
                door_ids = []
                for filling in getattr(element, "HasFillings", []) or []:
                    related = getattr(filling, "RelatedBuildingElement", None)
                    if related is not None and related.is_a("IfcDoor"):
                        door_ids.append(related.GlobalId)
                return door_ids
        except Exception:
            return []
        return []
    
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
        name = " ".join(
            str(value or "")
            for value in (
                getattr(ifc_space, "Name", ""),
                getattr(ifc_space, "LongName", ""),
                getattr(ifc_space, "Description", ""),
                getattr(ifc_space, "PredefinedType", ""),
            )
        ).lower()
        
        if "office" in name:
            return "office"
        elif "corridor" in name or "hall" in name:
            return "corridor"
        elif "stair" in name:
            return "stair"
        elif "lobby" in name:
            return "lobby"
        elif "bedroom" in name or "dorm" in name or "residential" in name:
            return "residential"
        elif "storage" in name or "store" in name or "plant" in name:
            return "industrial"
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
                data_quality_flags=["inferred_topology_edge", "missing_door_width_assumed"],
                assumptions={
                    "topology": "Connection inferred from nearest-neighbour geometry, not verified IFC door semantics.",
                    "width": "Assumed 0.9m for inferred route connector.",
                },
                connection_source="inferred_geometry",
                width_confidence=0.25,
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
                data_quality_flags=["inferred_egress", "missing_exit_width_assumed"],
                assumptions={
                    "topology": "Boundary egress inferred from farthest geometry points, not verified final-exit semantics.",
                    "width": "Assumed 1.2m for inferred egress marker.",
                },
                connection_source="inferred_geometry",
                width_confidence=0.25,
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
            for quantity in getattr(prop_set, "Quantities", []):
                name = getattr(quantity, "Name", "")
                for attr in ("LengthValue", "AreaValue", "VolumeValue", "CountValue", "WeightValue"):
                    if hasattr(quantity, attr):
                        properties[name] = getattr(quantity, attr)
                        properties[f"{name}_{attr}"] = getattr(quantity, attr)
                        break
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

    @staticmethod
    def _point_to_box_distance(point: Point3D, bounds: Tuple[Point3D, Point3D]) -> float:
        minimum, maximum = bounds
        dx = max(minimum.x - point.x, 0, point.x - maximum.x)
        dy = max(minimum.y - point.y, 0, point.y - maximum.y)
        dz = max(minimum.z - point.z, 0, point.z - maximum.z)
        return math.sqrt(dx * dx + dy * dy + dz * dz)

    @staticmethod
    def _combined_bounds(bounds: List[Tuple[Point3D, Point3D]]) -> Optional[Tuple[Point3D, Point3D]]:
        if not bounds:
            return None
        mins, maxes = zip(*bounds)
        return (
            Point3D(min(point.x for point in mins), min(point.y for point in mins), min(point.z for point in mins)),
            Point3D(max(point.x for point in maxes), max(point.y for point in maxes), max(point.z for point in maxes)),
        )

    @staticmethod
    def _point_near_bounds_perimeter(point: Point3D, bounds: Tuple[Point3D, Point3D], tolerance: float = 1.0) -> bool:
        minimum, maximum = bounds
        within_xy = minimum.x - tolerance <= point.x <= maximum.x + tolerance and minimum.y - tolerance <= point.y <= maximum.y + tolerance
        if not within_xy:
            return False
        return (
            abs(point.x - minimum.x) <= tolerance
            or abs(point.x - maximum.x) <= tolerance
            or abs(point.y - minimum.y) <= tolerance
            or abs(point.y - maximum.y) <= tolerance
        )
