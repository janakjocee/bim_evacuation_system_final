"""
Compliance checker for validating scenarios against regulations.
"""
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field

from ..utils.logger import get_logger
from ..utils.config_loader import get_config
from ..utils.helpers import ComplianceStatus
from ..bim_processing.ifc_parser import BuildingData, SpaceData, DoorData
from ..nlp.regulation_parser import RegulationClause

logger = get_logger("compliance_checker")


@dataclass
class ComplianceCheck:
    """Result of a compliance check."""
    element_id: str
    element_type: str
    regulation_id: str
    regulation_text: str
    status: ComplianceStatus
    measured_value: float
    required_value: float
    unit: str
    message: str = ""


class ComplianceChecker:
    """Check building elements against regulations."""
    
    def __init__(self):
        """Initialize compliance checker."""
        self.config = get_config()
        self.regulations = self._load_default_regulations()
    
    def _load_default_regulations(self) -> Dict[str, Any]:
        """Load default regulations from config."""
        return {
            'max_travel_distance': self.config.get('regulations.max_travel_distance', 45.0),
            'min_door_width': self.config.get('regulations.min_door_width', 0.75),
            'min_exit_width': self.config.get('regulations.min_exit_width', 1.05),
            'min_corridor_width': self.config.get('regulations.min_corridor_width', 1.2),
            'max_riser_height': self.config.get('regulations.max_riser_height', 0.19),
            'min_tread_length': self.config.get('regulations.min_tread_length', 0.25),
        }
    
    def update_regulations(self, clauses: List[RegulationClause]) -> None:
        """
        Update regulations from parsed clauses.
        
        Args:
            clauses: Parsed regulation clauses
        """
        for clause in clauses:
            if clause.value is not None:
                key = f"{clause.applies_to}_{clause.constraint_type}"
                self.regulations[key] = {
                    'value': clause.value,
                    'unit': clause.unit,
                    'clause_id': clause.clause_id
                }
        
        logger.info(f"Updated regulations with {len(clauses)} clauses")
    
    def check_door(self, door: DoorData) -> List[ComplianceCheck]:
        """
        Check door compliance.
        
        Args:
            door: Door data
            
        Returns:
            List of compliance checks
        """
        checks = []
        
        # Check minimum width
        min_width = self.regulations.get('min_door_width', 0.75)
        if door.is_exit:
            min_width = self.regulations.get('min_exit_width', 1.05)
        
        status = ComplianceStatus.COMPLIANT if door.width >= min_width else ComplianceStatus.NON_COMPLIANT
        
        checks.append(ComplianceCheck(
            element_id=door.id,
            element_type='door',
            regulation_id='min_width',
            regulation_text=f"Minimum door width: {min_width}m",
            status=status,
            measured_value=door.width,
            required_value=min_width,
            unit='m',
            message=f"Door width is {door.width:.2f}m (required: {min_width}m)"
        ))
        
        return checks
    
    def check_route(self, origin: SpaceData, distance: float) -> List[ComplianceCheck]:
        """
        Check evacuation route compliance.
        
        Args:
            origin: Origin space
            distance: Travel distance to exit
            
        Returns:
            List of compliance checks
        """
        checks = []
        
        # Check maximum travel distance
        max_distance = self.regulations.get('max_travel_distance', 45.0)
        
        status = ComplianceStatus.COMPLIANT if distance <= max_distance else ComplianceStatus.NON_COMPLIANT
        
        checks.append(ComplianceCheck(
            element_id=origin.id,
            element_type='route',
            regulation_id='max_travel_distance',
            regulation_text=f"Maximum travel distance: {max_distance}m",
            status=status,
            measured_value=distance,
            required_value=max_distance,
            unit='m',
            message=f"Travel distance is {distance:.1f}m (maximum: {max_distance}m)"
        ))
        
        return checks
    
    def calculate_compliance_score(self, checks: List[ComplianceCheck]) -> float:
        """
        Calculate overall compliance score.
        
        Args:
            checks: List of compliance checks
            
        Returns:
            Compliance score (0.0 to 1.0)
        """
        if not checks:
            return 1.0
        
        compliant_count = sum(1 for c in checks if c.status == ComplianceStatus.COMPLIANT)
        return compliant_count / len(checks)
    
    def get_violations(self, checks: List[ComplianceCheck]) -> List[ComplianceCheck]:
        """Get only non-compliant checks."""
        return [c for c in checks if c.status == ComplianceStatus.NON_COMPLIANT]
    
    def generate_recommendations(self, violations: List[ComplianceCheck]) -> List[str]:
        """
        Generate improvement recommendations from violations.
        
        Args:
            violations: List of violations
            
        Returns:
            List of recommendations
        """
        recommendations = []
        
        for v in violations:
            if 'width' in v.regulation_id:
                recommendations.append(
                    f"Increase width of {v.element_id} from {v.measured_value:.2f}m "
                    f"to at least {v.required_value:.2f}m"
                )
            elif 'distance' in v.regulation_id:
                recommendations.append(
                    f"Provide additional exit closer to {v.element_id} to reduce "
                    f"travel distance from {v.measured_value:.1f}m to under {v.required_value:.1f}m"
                )
        
        if not recommendations:
            recommendations.append("No improvements required - all checks passed")
        
        return recommendations
