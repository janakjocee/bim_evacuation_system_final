"""
Feature extraction from building data.
"""
from typing import Dict, List, Any
from dataclasses import dataclass, field

from ..utils.logger import get_logger
from ..utils.config_loader import get_config
from .ifc_parser import BuildingData, SpaceData, DoorData

logger = get_logger("feature_extractor")


@dataclass
class ExtractedFeatures:
    """Extracted features from building."""
    total_area: float = 0.0
    total_occupancy: int = 0
    space_count: int = 0
    door_count: int = 0
    exit_count: int = 0
    stair_count: int = 0
    
    # Space type distribution
    space_types: Dict[str, int] = field(default_factory=dict)
    
    # Exit capacity
    total_exit_width: float = 0.0
    total_exit_capacity: float = 0.0
    
    # Average metrics
    avg_space_area: float = 0.0
    avg_door_width: float = 0.0
    
    # Features per space
    space_features: List[Dict[str, Any]] = field(default_factory=list)


class FeatureExtractor:
    """Extract relevant features from building data."""
    
    def __init__(self):
        """Initialize feature extractor."""
        self.config = get_config()
        self.occupancy_density = self.config.get('bim.occupancy_density', {})
    
    def extract(self, building: BuildingData) -> ExtractedFeatures:
        """
        Extract features from building.
        
        Args:
            building: Building data
            
        Returns:
            ExtractedFeatures object
        """
        logger.info("Extracting features from building")
        
        features = ExtractedFeatures()
        
        # Basic counts
        features.space_count = len(building.spaces)
        features.door_count = len(building.doors)
        features.exit_count = len(building.exits)
        features.stair_count = len(building.stairs)
        
        # Extract space features
        for space_id, space in building.spaces.items():
            self._process_space(space, features)
        
        # Extract door features
        for door_id, door in building.doors.items():
            self._process_door(door, features)
        
        # Calculate averages
        if features.space_count > 0:
            features.avg_space_area = features.total_area / features.space_count
        
        if features.door_count > 0:
            door_widths = [d.width for d in building.doors.values()]
            features.avg_door_width = sum(door_widths) / len(door_widths)
        
        # Calculate exit capacity
        exit_capacity_per_minute = self.config.get('regulations.exit_capacity_per_minute', 90)
        features.total_exit_capacity = features.total_exit_width * exit_capacity_per_minute
        
        logger.info(f"Feature extraction complete:")
        logger.info(f"  Total area: {features.total_area:.1f} m²")
        logger.info(f"  Total occupancy: {features.total_occupancy}")
        logger.info(f"  Exit capacity: {features.total_exit_capacity:.0f} persons/min")
        
        return features
    
    def _process_space(self, space: SpaceData, features: ExtractedFeatures) -> None:
        """Process individual space."""
        # Total area
        features.total_area += space.area
        
        # Space type distribution
        space_type = space.space_type
        features.space_types[space_type] = features.space_types.get(space_type, 0) + 1
        
        # Occupancy calculation
        if space_type in {"structural_proxy", "structural_element"}:
            occupancy = 0
        else:
            density = self.occupancy_density.get(space_type, 0.1)
            occupancy = int(space.area * density)
        features.total_occupancy += occupancy
        
        # Store space features
        space_feature = {
            'id': space.id,
            'name': space.name,
            'area': space.area,
            'type': space.space_type,
            'occupancy': occupancy,
            'level': space.level
        }
        features.space_features.append(space_feature)
    
    def _process_door(self, door: DoorData, features: ExtractedFeatures) -> None:
        """Process individual door."""
        # Exit width
        if door.is_exit:
            features.total_exit_width += door.width
    
    def get_summary_dict(self, features: ExtractedFeatures) -> Dict[str, Any]:
        """Get features as summary dictionary."""
        return {
            'total_area_m2': round(features.total_area, 2),
            'total_occupancy': features.total_occupancy,
            'space_count': features.space_count,
            'door_count': features.door_count,
            'exit_count': features.exit_count,
            'stair_count': features.stair_count,
            'exit_capacity_per_min': round(features.total_exit_capacity, 0),
            'avg_space_area_m2': round(features.avg_space_area, 2),
            'avg_door_width_m': round(features.avg_door_width, 2),
            'space_type_distribution': features.space_types
        }
