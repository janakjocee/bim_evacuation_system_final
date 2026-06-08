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
        score = self._calculate_risk_score(factors)
        
        low_threshold = self.thresholds.get('low', 0.8)
        medium_threshold = self.thresholds.get('medium', 0.5)
        
        if score >= low_threshold:
            return RiskLevel.LOW
        elif score >= medium_threshold:
            return RiskLevel.MEDIUM
        else:
            return RiskLevel.HIGH
    
    def _calculate_risk_score(self, factors: RiskFactors) -> float:
        """
        Calculate composite risk score.
        
        Args:
            factors: Risk factors
            
        Returns:
            Risk score (0.0 to 1.0, higher is better/lower risk)
        """
        scores = []
        
        # Compliance score (weight: 0.4)
        scores.append(factors.compliance_score * 0.4)
        
        # Exit capacity ratio (weight: 0.3)
        capacity_score = min(factors.exit_capacity_ratio, 1.0) * 0.3
        scores.append(capacity_score)
        
        # Evacuation time score (weight: 0.2)
        # Assume 300 seconds (5 minutes) is maximum acceptable
        time_score = max(0, 1 - (factors.evacuation_time / 300)) * 0.2
        scores.append(time_score)
        
        # Bottleneck penalty (weight: 0.1)
        bottleneck_score = max(0, 1 - (factors.bottleneck_count * 0.1)) * 0.1
        scores.append(bottleneck_score)
        
        return sum(scores)
    
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
            'bottleneck_count': factors.bottleneck_count
        }
