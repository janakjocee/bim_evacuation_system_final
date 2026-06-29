"""
Compliance checker for validating scenarios against regulations.
"""
from typing import Callable, Dict, List, Any, Optional
from dataclasses import dataclass, field

from ..utils.logger import get_logger
from ..utils.config_loader import get_config
from ..utils.helpers import ComplianceStatus
from ..bim_processing.ifc_parser import BuildingData, SpaceData, DoorData, StairData
from ..bim_processing.spatial_graph import Route
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
        self.default_regulations = dict(self.regulations)
        self.rule_sources: Dict[str, RegulationRule] = {}
        self.unsupported_rules: List[RegulationRule] = []
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
        self.unsupported_rules = []
        for rule in rules:
            key = self._map_rule_to_rule_key(rule)
            if key:
                self.regulations[key] = rule.value
                self.rule_sources[key] = rule
                applied += 1
            else:
                self.unsupported_rules.append(rule)

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

    def get_rule_application_summary(self) -> Dict[str, Any]:
        """Return active thresholds and whether each came from upload or defaults."""
        active_thresholds = []
        for key, value in sorted(self.regulations.items()):
            rule = self.rule_sources.get(key)
            active_thresholds.append({
                "rule_key": key,
                "value": value,
                "source": "uploaded_regulation_rule" if rule else "default_config",
                "rule_id": rule.rule_id if rule else "",
                "source_text": rule.source_text[:300] if rule else "",
            })

        return {
            "active_threshold_count": len(active_thresholds),
            "uploaded_rule_count": len(self.rule_sources),
            "default_threshold_count": sum(1 for item in active_thresholds if item["source"] == "default_config"),
            "unsupported_rule_count": len(self.unsupported_rules),
            "active_thresholds": active_thresholds,
            "unsupported_rules": [
                {
                    "rule_id": rule.rule_id,
                    "metric": rule.metric,
                    "operator": rule.operator,
                    "value": rule.value,
                    "unit": rule.unit,
                    "source_text": rule.source_text[:300],
                    "reason": "Extracted, but this prototype does not currently enforce that metric.",
                }
                for rule in self.unsupported_rules
            ],
        }

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

    def check_route_redundancy(self, origin: SpaceData, route_count: int, exit_count: int) -> List[ComplianceCheck]:
        """Check whether a space has route/exit redundancy or needs review."""
        checks = []
        status = ComplianceStatus.COMPLIANT if route_count >= 2 else ComplianceStatus.REQUIRES_REVIEW
        checks.append(ComplianceCheck(
            element_id=origin.id,
            element_type="route",
            regulation_id="alternative_escape_route",
            regulation_text="Alternative escape route availability should be confirmed for practical evacuation review.",
            status=status,
            measured_value=route_count,
            required_value=2,
            unit="routes",
            message=(
                f"{route_count} route(s) to exits found."
                if status == ComplianceStatus.COMPLIANT
                else "Only one route to an exit was found; alternative escape availability requires expert review."
            ),
            evidence_source="ifc_graph_validation",
            evidence=[{
                "source": "ifc_graph_validation",
                "text": f"{route_count} route(s) and {exit_count} exit node(s) are available in the extracted graph.",
                "score": 1.0 if status == ComplianceStatus.COMPLIANT else 0.5,
            }],
        ))

        if exit_count <= 1:
            checks.append(ComplianceCheck(
                element_id=origin.id,
                element_type="route",
                regulation_id="only_one_exit_available",
                regulation_text="Evacuation strategy should not rely on a single available exit without review.",
                status=ComplianceStatus.REQUIRES_REVIEW,
                measured_value=exit_count,
                required_value=2,
                unit="exits",
                message="Only one exit node was detected; exit availability requires expert review.",
                evidence_source="ifc_graph_validation",
                evidence=[{
                    "source": "ifc_graph_validation",
                    "text": f"{exit_count} exit node(s) were detected from the IFC-derived graph.",
                    "score": 0.5,
                }],
            ))
        return checks

    def check_route_doors(self, route: Route, doors: Dict[str, DoorData]) -> List[ComplianceCheck]:
        """Check door widths along the selected route where route nodes are doors."""
        checks = []
        min_width = self.regulations.get("min_door_width", 0.75)
        for node_id in route.path:
            door = doors.get(node_id)
            if not door or door.is_exit:
                continue
            status = ComplianceStatus.REQUIRES_REVIEW if door.width_confidence < 1.0 or door.assumptions.get("width") else (
                ComplianceStatus.COMPLIANT if door.width >= min_width else ComplianceStatus.NON_COMPLIANT
            )
            evidence_source, evidence = self._evidence_for(
                "min_door_width",
                f"minimum door clear width {min_width} metres",
            )
            checks.append(ComplianceCheck(
                element_id=door.id,
                element_type="door",
                regulation_id="route_door_width",
                regulation_text=f"Route door width should be at least {min_width}m",
                status=status,
                measured_value=door.width,
                required_value=min_width,
                unit="m",
                message=(
                    f"Route door {door.name} is {door.width:.2f}m wide; required minimum is {min_width:.2f}m."
                    + (" Width is assumed or low-confidence and requires expert confirmation." if status == ComplianceStatus.REQUIRES_REVIEW else "")
                ),
                evidence_source=evidence_source,
                evidence=evidence,
            ))
        return checks

    def check_space_data_quality(self, space: SpaceData) -> List[ComplianceCheck]:
        """Flag low-confidence space measurements that affect occupancy/risk."""
        checks = []
        if space.area_confidence < 1.0 or space.assumptions.get("area"):
            checks.append(ComplianceCheck(
                element_id=space.id,
                element_type="space",
                regulation_id="space_area_confidence",
                regulation_text="Space area should come from reliable IFC quantities or geometry for occupancy screening.",
                status=ComplianceStatus.REQUIRES_REVIEW,
                measured_value=space.area_confidence,
                required_value=1.0,
                unit="confidence",
                message="Space area is estimated or low-confidence; occupancy and risk outputs require review.",
                evidence_source="ifc_data_quality",
                evidence=[{
                    "source": "ifc_data_quality",
                    "text": space.assumptions.get("area", "Space area confidence is below 1.0."),
                    "score": space.area_confidence,
                }],
            ))
        return checks

    def check_corridor(self, space: SpaceData) -> List[ComplianceCheck]:
        """Check corridor width when a corridor-like space has bounding-box geometry."""
        if space.space_type != "corridor":
            return []

        rule_key = "min_corridor_width"
        min_width = self.regulations.get(rule_key, 1.2)
        if not space.bounding_box:
            status = ComplianceStatus.REQUIRES_REVIEW
            measured_width = 0.0
            message = "Corridor width could not be measured from IFC geometry and requires review."
        else:
            minimum, maximum = space.bounding_box
            measured_width = min(abs(maximum.x - minimum.x), abs(maximum.y - minimum.y))
            status = ComplianceStatus.COMPLIANT if measured_width >= min_width else ComplianceStatus.NON_COMPLIANT
            message = f"Corridor width is {measured_width:.2f}m (required: {min_width:.2f}m)."

        evidence_source, evidence = self._evidence_for(rule_key, f"minimum corridor width {min_width} metres")
        return [ComplianceCheck(
            element_id=space.id,
            element_type="corridor",
            regulation_id=rule_key,
            regulation_text=f"Minimum corridor width: {min_width}m",
            status=status,
            measured_value=measured_width,
            required_value=min_width,
            unit="m",
            message=message,
            evidence_source=evidence_source,
            evidence=evidence,
        )]

    def check_stair(self, stair: StairData) -> List[ComplianceCheck]:
        """Check stair dimensions when stair elements exist."""
        checks = []
        rules = [
            ("min_stair_width", "width", stair.width, self.regulations.get("min_stair_width", 1.0), ">="),
            ("max_riser_height", "riser height", stair.riser_height, self.regulations.get("max_riser_height", 0.19), "<="),
            ("min_tread_length", "tread length", stair.tread_length, self.regulations.get("min_tread_length", 0.25), ">="),
        ]
        for rule_key, label, measured, required, operator in rules:
            if stair.assumptions.get(label.split()[0]) or (label == "width" and stair.assumptions.get("width")):
                status = ComplianceStatus.REQUIRES_REVIEW
            elif operator == ">=":
                status = ComplianceStatus.COMPLIANT if measured >= required else ComplianceStatus.NON_COMPLIANT
            else:
                status = ComplianceStatus.COMPLIANT if measured <= required else ComplianceStatus.NON_COMPLIANT
            evidence_source, evidence = self._evidence_for(rule_key, f"{label} stair requirement {required}")
            checks.append(ComplianceCheck(
                element_id=stair.id,
                element_type="stair",
                regulation_id=rule_key,
                regulation_text=f"Stair {label} requirement: {operator} {required}m",
                status=status,
                measured_value=measured,
                required_value=required,
                unit="m",
                message=f"Stair {label} is {measured:.2f}m; requirement is {operator} {required:.2f}m.",
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
