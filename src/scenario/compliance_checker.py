"""
Compliance checker for validating scenarios against regulations.
"""
from typing import Callable, Dict, List, Any, Optional
from dataclasses import dataclass, field

from ..utils.logger import get_logger
from ..utils.config_loader import get_config
from ..utils.helpers import ComplianceStatus
from ..bim_processing.ifc_parser import BuildingData, SpaceData, DoorData
from ..nlp.regulation_parser import RegulationClause, RegulationRule

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
    evidence_source: str = "default_rules"
    evidence: List[Dict[str, Any]] = field(default_factory=list)


class ComplianceChecker:
    """Check building elements against regulations."""
    
    def __init__(self):
        """Initialize compliance checker."""
        self.config = get_config()
        self.regulations = self._load_default_regulations()
        self.rule_sources: Dict[str, RegulationRule] = {}
        self.evidence_provider: Optional[Callable[[str, int], List[Any]]] = None
    
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
        applied = 0
        for clause in clauses:
            if clause.value is not None:
                key = self._map_clause_to_rule_key(clause)
                if key:
                    self.regulations[key] = clause.value
                    self.rule_sources[key] = RegulationRule(
                        rule_id=clause.clause_id,
                        source_section=clause.section or clause.clause_id,
                        source_text=clause.text,
                        applies_to=clause.applies_to,
                        condition="general",
                        metric=key,
                        operator="<=" if key.startswith("max_") else ">=",
                        value=clause.value,
                        unit=clause.unit,
                        confidence=0.6,
                        extracted_by="legacy_clause_parser",
                    )
                    applied += 1

        logger.info(f"Updated regulations with {len(clauses)} clauses; applied {applied} numeric constraints")

    def update_regulation_rules(self, rules: List[RegulationRule]) -> None:
        """
        Update regulations from structured uploaded rules.

        Structured rules are preferred over legacy clauses because they preserve
        multiple measurements from the same paragraph and carry source evidence.
        """
        applied = 0
        for rule in rules:
            key = self._map_rule_to_rule_key(rule)
            if key:
                self.regulations[key] = rule.value
                self.rule_sources[key] = rule
                applied += 1

        logger.info(f"Updated regulations with {len(rules)} structured rules; applied {applied} constraints")

    def set_evidence_provider(self, provider: Callable[[str, int], List[Any]]) -> None:
        """Set retrieval provider used to ground compliance checks in uploaded text."""
        self.evidence_provider = provider

    def _map_clause_to_rule_key(self, clause: RegulationClause) -> str:
        """Map parsed regulation clauses onto the checker rule keys actually used."""
        text = clause.text.lower()
        constraint = clause.constraint_type
        applies_to = clause.applies_to

        if constraint == "max_distance" and ("travel" in text or applies_to == "route"):
            return "max_travel_distance"
        if constraint == "min_width":
            if "final exit" in text or ("exit" in text and applies_to == "door"):
                return "min_exit_width"
            if "corridor" in text or applies_to == "corridor":
                return "min_corridor_width"
            if "stair" in text or applies_to == "stair":
                return "min_stair_width"
            if "door" in text or applies_to == "door":
                return "min_door_width"
        if constraint == "max_height" and "riser" in text:
            return "max_riser_height"
        if constraint in {"min_width", "min_height"} and "tread" in text:
            return "min_tread_length"

        return ""

    def _map_rule_to_rule_key(self, rule: RegulationRule) -> str:
        """Map structured regulation rules onto checker rule keys."""
        if rule.metric in {
            "max_travel_distance",
            "max_single_direction_travel_distance",
            "max_alternative_travel_distance",
            "min_door_width",
            "min_exit_width",
            "min_corridor_width",
            "min_stair_width",
            "max_riser_height",
            "min_tread_length",
            "max_occupancy",
            "max_area",
        }:
            if rule.metric.startswith("max_") and rule.operator == "<=":
                return rule.metric
            if rule.metric.startswith("min_") and rule.operator == ">=":
                return rule.metric

        return ""

    def _evidence_for(self, rule_key: str, query: str) -> tuple:
        """Return evidence source label and compact source snippets for a rule."""
        evidence = []
        rule = self.rule_sources.get(rule_key)
        if rule:
            evidence.append({
                "rule_id": rule.rule_id,
                "source_section": rule.source_section,
                "text": rule.source_text[:300],
                "score": rule.confidence,
                "source": "uploaded_regulation_rule",
            })

        if self.evidence_provider:
            for item in self.evidence_provider(query, 3):
                clause = None
                score = 0.0
                if isinstance(item, tuple) and len(item) >= 2:
                    clause, score = item[0], item[1]
                if clause:
                    evidence.append({
                        "clause_id": getattr(clause, "clause_id", ""),
                        "text": getattr(clause, "text", "")[:300],
                        "score": float(score),
                        "source": "rag_uploaded_regulation",
                    })

        if rule:
            source = "uploaded_regulation_rule"
        elif any(e.get("source") == "rag_uploaded_regulation" for e in evidence):
            source = "rag_uploaded_regulation"
        else:
            source = "default_rules"

        return source, evidence
    
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
            rule_key = "min_exit_width"
            min_width = self.regulations.get(rule_key, 1.05)
        else:
            rule_key = "min_door_width"
        
        if door.width_confidence < 1.0 or door.assumptions.get("width"):
            status = ComplianceStatus.REQUIRES_REVIEW
        else:
            status = ComplianceStatus.COMPLIANT if door.width >= min_width else ComplianceStatus.NON_COMPLIANT
        
        evidence_source, evidence = self._evidence_for(
            rule_key,
            f"{'final exit' if door.is_exit else 'door'} minimum clear width {min_width} metres",
        )

        checks.append(ComplianceCheck(
            element_id=door.id,
            element_type='door',
            regulation_id=rule_key,
            regulation_text=f"Minimum door width: {min_width}m",
            status=status,
            measured_value=door.width,
            required_value=min_width,
            unit='m',
            message=f"Door width is {door.width:.2f}m (required: {min_width}m)"
            + ("; width is assumed or low-confidence and requires expert confirmation" if status == ComplianceStatus.REQUIRES_REVIEW else ""),
            evidence_source=evidence_source,
            evidence=evidence,
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
        rule_key = 'max_travel_distance'
        max_distance = self.regulations.get(rule_key, 45.0)
        
        status = ComplianceStatus.COMPLIANT if distance <= max_distance else ComplianceStatus.NON_COMPLIANT
        evidence_source, evidence = self._evidence_for(
            rule_key,
            f"maximum travel distance to exit {max_distance} metres",
        )
        
        checks.append(ComplianceCheck(
            element_id=origin.id,
            element_type='route',
            regulation_id=rule_key,
            regulation_text=f"Maximum travel distance: {max_distance}m",
            status=status,
            measured_value=distance,
            required_value=max_distance,
            unit='m',
            message=f"Travel distance is {distance:.1f}m (maximum: {max_distance}m)",
            evidence_source=evidence_source,
            evidence=evidence,
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
            return 0.0
        
        compliant_count = sum(1 for c in checks if c.status == ComplianceStatus.COMPLIANT)
        return compliant_count / len(checks)
    
    def get_violations(self, checks: List[ComplianceCheck]) -> List[ComplianceCheck]:
        """Get only non-compliant checks."""
        return [c for c in checks if c.status != ComplianceStatus.COMPLIANT]
    
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
            if v.status == ComplianceStatus.REQUIRES_REVIEW:
                recommendations.append(
                    f"Expert review required for {v.element_id}: {v.message}"
                )
            elif 'width' in v.regulation_id:
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
