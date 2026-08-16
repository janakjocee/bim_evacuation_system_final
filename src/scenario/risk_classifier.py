"""
Risk classifier for evacuation scenarios.
"""
from typing import Dict, Any
from dataclasses import dataclass

from ..utils.logger import get_logger
from ..utils.config_loader import get_config
from ..utils.helpers import RiskLevel

logger = get_logger("risk_classifier")


@dataclass
class RiskFactors:
    """Risk factors for a scenario."""
    travel_distance: float = 0.0
    evacuation_time: float = 0.0
    compliance_score: float = 1.0
    exit_capacity_ratio: float = 1.0
    bottleneck_count: int = 0
    graph_confidence: float = 1.0
    data_quality_confidence: float = 1.0
    inferred_edge_ratio: float = 0.0
    missing_exit_count: int = 0
    assumed_measurement_count: int = 0
    narrow_door_count: int = 0
    no_alternative_route_count: int = 0
    missing_area_count: int = 0


class RiskClassifier:
    """Classify prototype screening priority using a deterministic index."""
    
    def __init__(self):
        """Initialize risk classifier."""
        self.config = get_config()
        self.thresholds = self.config.get('scenario.risk_thresholds', {})
        self.index_config = self.config.get('scenario.screening_index', {})
        self.weights = self.index_config.get('weights', {})
        self.penalties = self.index_config.get('penalties', {})
    
    def classify(self, factors: RiskFactors) -> RiskLevel:
        """
        Classify risk level based on factors.
        
        Args:
            factors: Risk factors
            
        Returns:
            Risk level
        """
        score = self.calculate_score(factors)

        if factors.missing_exit_count > 0 or factors.graph_confidence < 0.25:
            return RiskLevel.HIGH
        
        low_threshold = self.thresholds.get('low', 0.8)
        medium_threshold = self.thresholds.get('medium', 0.5)
        
        if score >= low_threshold:
            if (
                factors.graph_confidence < 0.5
                or factors.data_quality_confidence < 0.5
                or factors.inferred_edge_ratio > 0.75
                or factors.assumed_measurement_count > 0
                or factors.narrow_door_count > 0
                or factors.no_alternative_route_count > 0
                or factors.missing_area_count > 0
            ):
                return RiskLevel.MEDIUM
            return RiskLevel.LOW
        elif score >= medium_threshold:
            return RiskLevel.MEDIUM
        else:
            return RiskLevel.HIGH
    
    def calculate_score(self, factors: RiskFactors) -> float:
        """
        Calculate the composite screening index.
        
        Args:
            factors: Risk factors
            
        Returns:
            Screening index (0.0 to 1.0, higher is lower screening priority)
        """
        scores = []
        
        compliance_weight = self.weights.get('compliance', 0.35)
        exit_capacity_weight = self.weights.get('exit_capacity', 0.25)
        evacuation_time_weight = self.weights.get('evacuation_time', 0.15)
        bottleneck_weight = self.weights.get('bottleneck', 0.10)
        topology_weight = self.weights.get('topology', 0.10)
        data_quality_weight = self.weights.get('data_quality', 0.05)
        time_reference = max(1.0, float(self.index_config.get('time_reference_s', 300)))

        scores.append(factors.compliance_score * compliance_weight)
        
        # Exit capacity ratio (weight: 0.25)
        capacity_score = min(factors.exit_capacity_ratio, 1.0) * exit_capacity_weight
        scores.append(capacity_score)
        
        # This reference normalises a prototype score; it is not an ASET limit.
        time_score = max(0, 1 - (factors.evacuation_time / time_reference)) * evacuation_time_weight
        scores.append(time_score)
        
        # Bottleneck penalty (weight: 0.1)
        bottleneck_score = max(0, 1 - (factors.bottleneck_count * 0.1)) * bottleneck_weight
        scores.append(bottleneck_score)

        # IFC topology/data quality (weight: 0.15)
        topology_score = max(0.0, min(factors.graph_confidence, 1.0)) * topology_weight
        data_quality_score = max(0.0, min(factors.data_quality_confidence, 1.0)) * data_quality_weight
        inferred_penalty = min(max(factors.inferred_edge_ratio, 0.0), 1.0) * self.penalties.get('inferred_route_max', 0.05)
        assumption_penalty = min(
            factors.assumed_measurement_count * self.penalties.get('assumption_each', 0.02),
            self.penalties.get('assumption_max', 0.08),
        )
        practical_penalty = self._practical_data_penalty(factors)
        scores.append(max(0.0, topology_score + data_quality_score - inferred_penalty - assumption_penalty - practical_penalty))
        
        return sum(scores)

    def risk_contribution_breakdown(self, factors: RiskFactors) -> Dict[str, Any]:
        """Return the weighted score components used for traceable risk decisions."""
        compliance_weight = self.weights.get('compliance', 0.35)
        exit_capacity_weight = self.weights.get('exit_capacity', 0.25)
        evacuation_time_weight = self.weights.get('evacuation_time', 0.15)
        bottleneck_weight = self.weights.get('bottleneck', 0.10)
        topology_weight = self.weights.get('topology', 0.10)
        data_quality_weight = self.weights.get('data_quality', 0.05)
        time_reference = max(1.0, float(self.index_config.get('time_reference_s', 300)))
        time_score = max(0, 1 - (factors.evacuation_time / time_reference)) * evacuation_time_weight
        topology_score = max(0.0, min(factors.graph_confidence, 1.0)) * topology_weight
        data_quality_score = max(0.0, min(factors.data_quality_confidence, 1.0)) * data_quality_weight
        inferred_penalty = min(max(factors.inferred_edge_ratio, 0.0), 1.0) * self.penalties.get('inferred_route_max', 0.05)
        assumption_penalty = min(
            factors.assumed_measurement_count * self.penalties.get('assumption_each', 0.02),
            self.penalties.get('assumption_max', 0.08),
        )
        practical_penalty = self._practical_data_penalty(factors)
        topology_component = max(0.0, topology_score + data_quality_score - inferred_penalty - assumption_penalty - practical_penalty)
        return {
            "compliance_component": round(factors.compliance_score * compliance_weight, 3),
            "exit_capacity_component": round(min(factors.exit_capacity_ratio, 1.0) * exit_capacity_weight, 3),
            "evacuation_time_component": round(time_score, 3),
            "bottleneck_component": round(max(0, 1 - (factors.bottleneck_count * 0.1)) * bottleneck_weight, 3),
            "topology_data_quality_component": round(topology_component, 3),
            "inferred_route_penalty": round(inferred_penalty, 3),
            "assumed_measurement_penalty": round(assumption_penalty, 3),
            "practical_data_penalty": round(practical_penalty, 3),
            "screening_index": round(self.calculate_score(factors), 3),
            "total_score": round(self.calculate_score(factors), 3),
            "calibration_status": "unvalidated_research_assumption",
            "interpretation": (
                "Higher index means lower screening priority within implemented prototype checks; it does not mean proven safety. "
                "Low-confidence or heavily inferred IFC topology can cap the displayed priority at medium/high."
            ),
        }
    
    def get_risk_description(self, level: RiskLevel) -> str:
        """Get human-readable risk description."""
        descriptions = {
            RiskLevel.LOW: "Lower screening priority within implemented checks; professional review still required",
            RiskLevel.MEDIUM: "Medium screening priority; assumptions or findings require review",
            RiskLevel.HIGH: "High screening priority; significant findings or insufficient evidence require review"
        }
        return descriptions.get(level, "Unknown risk level")
    
    def get_risk_factors_dict(self, factors: RiskFactors) -> Dict[str, Any]:
        """Get risk factors as dictionary."""
        return {
            'travel_distance_m': round(factors.travel_distance, 1),
            'evacuation_time_s': round(factors.evacuation_time, 1),
            'compliance_score': round(factors.compliance_score, 2),
            'exit_capacity_ratio': round(factors.exit_capacity_ratio, 2),
            'bottleneck_count': factors.bottleneck_count,
            'graph_confidence': round(factors.graph_confidence, 2),
            'data_quality_confidence': round(factors.data_quality_confidence, 2),
            'inferred_edge_ratio': round(factors.inferred_edge_ratio, 2),
            'missing_exit_count': factors.missing_exit_count,
            'assumed_measurement_count': factors.assumed_measurement_count,
            'narrow_door_count': factors.narrow_door_count,
            'no_alternative_route_count': factors.no_alternative_route_count,
            'missing_area_count': factors.missing_area_count,
        }

    def _practical_data_penalty(self, factors: RiskFactors) -> float:
        """Penalty for practical evacuation weaknesses visible in the extracted IFC."""
        return min(
            factors.narrow_door_count * self.penalties.get('narrow_door_each', 0.03)
            + factors.no_alternative_route_count * self.penalties.get('no_alternative_route_each', 0.04)
            + factors.missing_area_count * self.penalties.get('missing_area_each', 0.02),
            self.penalties.get('practical_max', 0.10),
        )
