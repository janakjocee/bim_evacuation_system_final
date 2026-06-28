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


class RiskClassifier:
    """Classify risk level of evacuation scenarios."""
    
    def __init__(self):
        """Initialize risk classifier."""
        self.config = get_config()
        self.thresholds = self.config.get('scenario.risk_thresholds', {})
    
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
            ):
                return RiskLevel.MEDIUM
            return RiskLevel.LOW
        elif score >= medium_threshold:
            return RiskLevel.MEDIUM
        else:
            return RiskLevel.HIGH
    
    def calculate_score(self, factors: RiskFactors) -> float:
        """
        Calculate composite risk score.
        
        Args:
            factors: Risk factors
            
        Returns:
            Risk score (0.0 to 1.0, higher is better/lower risk)
        """
        scores = []
        
        # Compliance score (weight: 0.35)
        scores.append(factors.compliance_score * 0.35)
        
        # Exit capacity ratio (weight: 0.25)
        capacity_score = min(factors.exit_capacity_ratio, 1.0) * 0.25
        scores.append(capacity_score)
        
        # Evacuation time score (weight: 0.15)
        # Assume 300 seconds (5 minutes) is maximum acceptable
        time_score = max(0, 1 - (factors.evacuation_time / 300)) * 0.15
        scores.append(time_score)
        
        # Bottleneck penalty (weight: 0.1)
        bottleneck_score = max(0, 1 - (factors.bottleneck_count * 0.1)) * 0.1
        scores.append(bottleneck_score)

        # IFC topology/data quality (weight: 0.15)
        topology_score = max(0.0, min(factors.graph_confidence, 1.0)) * 0.1
        data_quality_score = max(0.0, min(factors.data_quality_confidence, 1.0)) * 0.05
        inferred_penalty = min(max(factors.inferred_edge_ratio, 0.0), 1.0) * 0.05
        assumption_penalty = min(factors.assumed_measurement_count * 0.02, 0.08)
        scores.append(max(0.0, topology_score + data_quality_score - inferred_penalty - assumption_penalty))
        
        return sum(scores)

    def risk_contribution_breakdown(self, factors: RiskFactors) -> Dict[str, Any]:
        """Return the weighted score components used for traceable risk decisions."""
        time_score = max(0, 1 - (factors.evacuation_time / 300)) * 0.15
        topology_score = max(0.0, min(factors.graph_confidence, 1.0)) * 0.1
        data_quality_score = max(0.0, min(factors.data_quality_confidence, 1.0)) * 0.05
        inferred_penalty = min(max(factors.inferred_edge_ratio, 0.0), 1.0) * 0.05
        assumption_penalty = min(factors.assumed_measurement_count * 0.02, 0.08)
        topology_component = max(0.0, topology_score + data_quality_score - inferred_penalty - assumption_penalty)
        return {
            "compliance_component": round(factors.compliance_score * 0.35, 3),
            "exit_capacity_component": round(min(factors.exit_capacity_ratio, 1.0) * 0.25, 3),
            "evacuation_time_component": round(time_score, 3),
            "bottleneck_component": round(max(0, 1 - (factors.bottleneck_count * 0.1)) * 0.1, 3),
            "topology_data_quality_component": round(topology_component, 3),
            "total_score": round(self.calculate_score(factors), 3),
            "interpretation": (
                "Higher score means lower risk; thresholds are low>=0.8, medium>=0.5, otherwise high. "
                "Low-confidence or heavily inferred IFC topology can cap the displayed level at medium/high."
            ),
        }
    
    def get_risk_description(self, level: RiskLevel) -> str:
        """Get human-readable risk description."""
        descriptions = {
            RiskLevel.LOW: "Low risk - evacuation routes meet safety requirements",
            RiskLevel.MEDIUM: "Medium risk - some improvements recommended",
            RiskLevel.HIGH: "High risk - significant safety concerns identified"
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
        }
