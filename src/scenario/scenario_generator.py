"""
Evacuation scenario generator.
"""
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field

from ..utils.logger import get_logger
from ..utils.config_loader import get_config
from ..utils.helpers import RiskLevel, ComplianceStatus, generate_id
from ..bim_processing.ifc_parser import BuildingData, SpaceData, DoorData
from ..bim_processing.spatial_graph import SpatialGraphBuilder, Route
from ..nlp.regulation_parser import RegulationClause, RegulationRule
from .compliance_checker import ComplianceChecker, ComplianceCheck
from .risk_classifier import RiskClassifier, RiskFactors

logger = get_logger("scenario_generator")


@dataclass
class EvacuationScenario:
    """Evacuation scenario."""
    scenario_id: str
    name: str
    origin_space_id: str
    origin_space_name: str
    risk_level: RiskLevel
    evacuation_route: Route
    compliance_status: ComplianceStatus
    compliance_score: float
    violated_regulations: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    confidence_score: float = 0.0
    explanation: str = ""
    risk_score: float = 0.0
    risk_factors: Dict[str, Any] = field(default_factory=dict)
    decision_trace: List[Dict[str, Any]] = field(default_factory=list)
    data_quality_notes: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'scenario_id': self.scenario_id,
            'name': self.name,
            'origin_space_id': self.origin_space_id,
            'origin_space_name': self.origin_space_name,
            'risk_level': self.risk_level.value,
            'evacuation_route': {
                'origin': self.evacuation_route.origin,
                'destination': self.evacuation_route.destination,
                'distance_m': round(self.evacuation_route.distance, 2),
                'estimated_time_s': round(self.evacuation_route.estimated_time, 1),
                'path': self.evacuation_route.path,
                'verified_edge_count': self.evacuation_route.verified_edge_count,
                'inferred_edge_count': self.evacuation_route.inferred_edge_count,
                'route_confidence': round(self.evacuation_route.route_confidence, 2),
                'edge_sources': self.evacuation_route.edge_sources or [],
            },
            'compliance_status': self.compliance_status.value,
            'compliance_score': round(self.compliance_score, 2),
            'violated_regulations': self.violated_regulations,
            'recommendations': self.recommendations,
            'confidence_score': round(self.confidence_score, 2),
            'explanation': self.explanation,
            'risk_score': round(self.risk_score, 3),
            'risk_factors': self.risk_factors,
            'decision_trace': self.decision_trace,
            'data_quality_notes': self.data_quality_notes,
        }


class ScenarioGenerator:
    """Generate evacuation scenarios from building data."""
    
    def __init__(self, building: BuildingData, graph_builder: SpatialGraphBuilder):
        """Initialize scenario generator."""
        self.building = building
        self.graph_builder = graph_builder
        self.config = get_config()
        
        self.compliance_checker = ComplianceChecker()
        self.risk_classifier = RiskClassifier()
        
        self.scenarios: List[EvacuationScenario] = []
    
    def set_regulations(
        self,
        clauses: List[RegulationClause],
        rules: Optional[List[RegulationRule]] = None,
        rag_engine: Any = None,
    ) -> None:
        """Set regulations from parsed clauses."""
        self.compliance_checker.update_regulations(clauses)
        if rules:
            self.compliance_checker.update_regulation_rules(rules)
        if rag_engine:
            self.compliance_checker.set_evidence_provider(rag_engine.retrieve)
    
    def generate(self, max_scenarios: int = None) -> List[EvacuationScenario]:
        """
        Generate evacuation scenarios.
        
        Args:
            max_scenarios: Maximum number of scenarios to generate
            
        Returns:
            List of evacuation scenarios
        """
        if max_scenarios is None:
            max_scenarios = self.config.get('scenario.max_scenarios', 10)
        
        logger.info(f"Generating up to {max_scenarios} scenarios")
        
        self.scenarios = []
        
        # Generate scenario for each space
        for space_id, space in self.building.spaces.items():
            if len(self.scenarios) >= max_scenarios:
                break
            
            scenario = self._generate_space_scenario(space)
            if scenario:
                self.scenarios.append(scenario)
        
        # Sort by confidence score
        self.scenarios.sort(key=lambda s: s.confidence_score, reverse=True)
        
        logger.info(f"Generated {len(self.scenarios)} scenarios")
        return self.scenarios
    
    def _generate_space_scenario(self, space: SpaceData) -> Optional[EvacuationScenario]:
        """Generate scenario for a single space."""
        # Find paths to exits
        routes = self.graph_builder.find_paths_to_exits(space.id)
        
        if not routes:
            logger.warning(f"No evacuation routes found for {space.name}")
            return None
        
        # Use shortest route
        best_route = routes[0]
        
        # Run compliance checks
        compliance_checks = []
        
        # Check route distance
        route_checks = self.compliance_checker.check_route(space, best_route.distance)
        compliance_checks.extend(route_checks)

        if best_route.inferred_edge_count:
            compliance_checks.append(ComplianceCheck(
                element_id=space.id,
                element_type="route",
                regulation_id="route_connectivity_confidence",
                regulation_text="Route connectivity must be based on verifiable IFC topology for automated compliance claims.",
                status=ComplianceStatus.REQUIRES_REVIEW,
                measured_value=best_route.route_confidence,
                required_value=1.0,
                unit="confidence",
                message=(
                    f"Route uses {best_route.inferred_edge_count} inferred edge(s); "
                    "expert review is required before treating it as a verified evacuation path."
                ),
                evidence_source="ifc_graph_validation",
                evidence=[{
                    "source": "ifc_graph_validation",
                    "text": f"Route edge sources: {', '.join(best_route.edge_sources or [])}",
                    "score": best_route.route_confidence,
                }],
            ))
        
        # Check exit door
        exit_door = self.building.exits.get(best_route.destination)
        if exit_door:
            door_checks = self.compliance_checker.check_door(exit_door)
            compliance_checks.extend(door_checks)
        
        # Calculate compliance score
        compliance_score = self.compliance_checker.calculate_compliance_score(compliance_checks)
        
        # Determine compliance status
        violations = self.compliance_checker.get_violations(compliance_checks)
        if any(v.status == ComplianceStatus.INSUFFICIENT_DATA for v in violations):
            compliance_status = ComplianceStatus.INSUFFICIENT_DATA
        elif any(v.status == ComplianceStatus.REQUIRES_REVIEW for v in violations):
            compliance_status = ComplianceStatus.REQUIRES_REVIEW
        else:
            compliance_status = ComplianceStatus.COMPLIANT if not violations else ComplianceStatus.NON_COMPLIANT
        
        # Generate recommendations
        recommendations = self.compliance_checker.generate_recommendations(violations)
        
        graph_stats = self.graph_builder.get_graph_stats() if self.graph_builder else {}
        data_quality_factors = self._build_data_quality_risk_factors(graph_stats)

        # Classify risk
        risk_factors = RiskFactors(
            travel_distance=best_route.distance,
            evacuation_time=best_route.estimated_time,
            compliance_score=compliance_score,
            exit_capacity_ratio=self._estimate_exit_capacity_ratio(),
            bottleneck_count=self._estimate_bottleneck_count(),
            **data_quality_factors,
        )
        
        risk_level = self.risk_classifier.classify(risk_factors)
        risk_score = self.risk_classifier.calculate_score(risk_factors)
        risk_factor_dict = self.risk_classifier.get_risk_factors_dict(risk_factors)
        risk_factor_dict["weighted_breakdown"] = self.risk_classifier.risk_contribution_breakdown(risk_factors)
        
        # Calculate confidence
        confidence = self._calculate_confidence(compliance_score, best_route)
        confidence = min(confidence, best_route.route_confidence)
        data_quality_notes = []
        if self.building.extraction_mode == "geometry_derived":
            confidence = min(confidence, 0.5)
            data_quality_notes.append(
                "Geometry-derived mode caps confidence at 50% because semantic IfcSpace/IfcDoor data is incomplete."
            )
        elif self.building.extraction_mode == "semantic_spaces_inferred_topology":
            confidence = min(confidence, 0.65)
            data_quality_notes.append(
                "IfcSpace-inferred topology caps confidence at 65% because route links and exits were inferred from room geometry."
            )
        if not violations:
            data_quality_notes.append("No regulatory violations were detected by the active rule set.")
        else:
            data_quality_notes.append(f"{len(violations)} regulatory violation(s) affected compliance scoring.")
        if graph_stats:
            data_quality_notes.append(
                f"Graph confidence {graph_stats.get('graph_confidence_score', 0):.2f}; "
                f"verified edges={graph_stats.get('verified_edges_count', 0)}, "
                f"inferred edges={graph_stats.get('inferred_edges_count', 0)}."
            )
        
        # Generate explanation
        explanation = self._generate_explanation(
            space, best_route, compliance_checks, violations, risk_level
        )
        
        # Create scenario
        scenario = EvacuationScenario(
            scenario_id=generate_id("SCEN"),
            name=f"Evacuation from {space.name}",
            origin_space_id=space.id,
            origin_space_name=space.name,
            risk_level=risk_level,
            evacuation_route=best_route,
            compliance_status=compliance_status,
            compliance_score=compliance_score,
            violated_regulations=[v.regulation_id for v in violations],
            recommendations=recommendations,
            confidence_score=confidence,
            explanation=explanation,
            risk_score=risk_score,
            risk_factors=risk_factor_dict,
            decision_trace=self._build_decision_trace(
                space=space,
                route=best_route,
                compliance_checks=compliance_checks,
                violations=violations,
                risk_level=risk_level,
                risk_score=risk_score,
                confidence=confidence,
            ),
            data_quality_notes=data_quality_notes,
        )
        
        return scenario

    def _build_decision_trace(self, space: SpaceData, route: Route,
                              compliance_checks: List[ComplianceCheck],
                              violations: List[ComplianceCheck],
                              risk_level: RiskLevel, risk_score: float,
                              confidence: float) -> List[Dict[str, Any]]:
        """Build a transparent audit trail for why the scenario was produced."""
        if self.building.extraction_mode == "geometry_derived":
            extraction_basis = "geometry-derived IFC element topology"
        elif self.building.extraction_mode == "semantic_spaces_inferred_topology":
            extraction_basis = "semantic IfcSpace geometry with inferred route links and egress points"
        else:
            extraction_basis = "semantic IFC spaces, doors and exits"
        return [
            {
                "step": "IFC extraction",
                "input": space.id,
                "method": extraction_basis,
                "output": f"Origin candidate '{space.name}' with area {space.area:.1f} m2.",
            },
            {
                "step": "Route search",
                "input": route.origin,
                "method": "Shortest path to available exit using the spatial graph.",
                "output": {
                    "destination": route.destination,
                    "path": route.path,
                    "distance_m": round(route.distance, 2),
                    "estimated_time_s": round(route.estimated_time, 1),
                    "verified_edge_count": route.verified_edge_count,
                    "inferred_edge_count": route.inferred_edge_count,
                    "route_confidence": round(route.route_confidence, 2),
                    "edge_sources": route.edge_sources or [],
                },
            },
            {
                "step": "Compliance checks",
                "input": len(compliance_checks),
                "method": "Rule checks for route distance and selected exit/door width.",
                "output": {
                    "passed": len(compliance_checks) - len(violations),
                    "failed": len(violations),
                    "violations": [v.message for v in violations],
                    "checks": [
                        {
                            "element_id": check.element_id,
                            "regulation_id": check.regulation_id,
                            "status": check.status.value,
                            "measured_value": round(check.measured_value, 3),
                            "required_value": round(check.required_value, 3),
                            "evidence_source": check.evidence_source,
                            "evidence": check.evidence[:3],
                        }
                        for check in compliance_checks
                    ],
                },
            },
            {
                "step": "Risk classification",
                "input": self.risk_classifier.get_risk_factors_dict(RiskFactors(
                    travel_distance=route.distance,
                    evacuation_time=route.estimated_time,
                    compliance_score=self.compliance_checker.calculate_compliance_score(compliance_checks),
                    exit_capacity_ratio=self._estimate_exit_capacity_ratio(),
                    bottleneck_count=self._estimate_bottleneck_count(),
                    **self._build_data_quality_risk_factors(
                        self.graph_builder.get_graph_stats() if self.graph_builder else {}
                    ),
                )),
                "method": "Weighted deterministic score, not an opaque machine-learning prediction.",
                "output": {
                    "risk_score": round(risk_score, 3),
                    "risk_level": risk_level.value,
                    "confidence": round(confidence, 3),
                },
            },
        ]
    
    def _calculate_confidence(self, compliance_score: float, route: Route) -> float:
        """Calculate confidence score."""
        # Base confidence on compliance
        confidence = compliance_score
        
        # Penalize long routes
        if route.distance > 100:
            confidence *= 0.9
        
        # Penalize long evacuation times
        if route.estimated_time > 300:
            confidence *= 0.8
        
        return min(confidence, 1.0)

    def _build_data_quality_risk_factors(self, graph_stats: Dict[str, Any]) -> Dict[str, Any]:
        """Build risk model inputs from IFC extraction and graph validation quality."""
        total_edges = graph_stats.get("edge_count", 0)
        inferred_edges = graph_stats.get("inferred_edges_count", 0)
        inferred_edge_ratio = inferred_edges / total_edges if total_edges else 0.0

        assumed_measurements = 0
        for door in self.building.doors.values():
            assumed_measurements += len(door.assumptions)
        for space in self.building.spaces.values():
            assumed_measurements += len(space.assumptions)

        if self.building.extraction_mode == "geometry_derived":
            data_quality_confidence = 0.4
        elif self.building.extraction_mode == "semantic_spaces_inferred_topology":
            data_quality_confidence = 0.45
        else:
            data_quality_confidence = 1.0

        if assumed_measurements:
            data_quality_confidence = min(data_quality_confidence, 0.65)

        return {
            "graph_confidence": graph_stats.get("graph_confidence_score", 1.0),
            "data_quality_confidence": data_quality_confidence,
            "inferred_edge_ratio": inferred_edge_ratio,
            "missing_exit_count": 0 if self.building.exits else 1,
            "assumed_measurement_count": assumed_measurements,
        }

    def _estimate_exit_capacity_ratio(self) -> float:
        """Estimate exit capacity against area-derived occupancy when available."""
        total_exit_width = sum(door.width for door in self.building.exits.values())
        occupancy = self._estimate_total_occupancy()
        if occupancy <= 0:
            return 0.5
        exit_capacity_per_minute = self.config.get('regulations.exit_capacity_per_minute', 90)
        return max(0.0, min((total_exit_width * exit_capacity_per_minute) / occupancy, 1.5))

    def _estimate_total_occupancy(self) -> int:
        """Estimate occupancy from space area/type using configured densities."""
        densities = self.config.get('bim.occupancy_density', {})
        total = 0
        for space in self.building.spaces.values():
            if space.space_type in {"structural_proxy", "structural_element"}:
                continue
            total += int(space.area * densities.get(space.space_type, 0.1))
        return total

    def _estimate_bottleneck_count(self) -> int:
        """Count meaningful graph bottlenecks from betweenness centrality."""
        if not self.graph_builder:
            return 0
        bottlenecks = self.graph_builder.identify_bottlenecks(top_n=10)
        return sum(1 for item in bottlenecks if item.get("centrality", 0) >= 0.2)
    
    def _generate_explanation(self, space: SpaceData, route: Route,
                              checks: List[ComplianceCheck], violations: List[ComplianceCheck],
                              risk_level: RiskLevel) -> str:
        """Generate natural language explanation."""
        parts = []
        
        # Introduction
        parts.append(f"Evacuation scenario for {space.name}.")
        if self.building.extraction_mode == "geometry_derived":
            parts.append(
                "This is geometry-derived structural screening, not a verified room-level route."
            )
        elif self.building.extraction_mode == "semantic_spaces_inferred_topology":
            parts.append(
                "This uses real IfcSpace geometry with inferred route links and egress points, not verified IfcDoor connectivity."
            )
        parts.append(f"Route to exit: {route.distance:.1f} meters, "
                    f"estimated evacuation time: {route.estimated_time:.1f} seconds.")
        
        # Compliance
        compliant_count = sum(1 for c in checks if c.status == ComplianceStatus.COMPLIANT)
        total_checks = len(checks)
        parts.append(f"Compliance: {compliant_count}/{total_checks} checks passed.")
        
        # Violations
        if violations:
            parts.append("Violations identified:")
            for v in violations:
                parts.append(f"  - {v.message}")
        
        # Risk level
        parts.append(f"Risk level: {risk_level.value.upper()}.")
        
        return " ".join(parts)
    
    def get_scenarios_by_risk(self, risk_level: RiskLevel) -> List[EvacuationScenario]:
        """Filter scenarios by risk level."""
        return [s for s in self.scenarios if s.risk_level == risk_level]
    
    def get_summary(self) -> Dict[str, Any]:
        """Get summary of generated scenarios."""
        if not self.scenarios:
            return {'total': 0}
        
        risk_counts = {
            'low': len(self.get_scenarios_by_risk(RiskLevel.LOW)),
            'medium': len(self.get_scenarios_by_risk(RiskLevel.MEDIUM)),
            'high': len(self.get_scenarios_by_risk(RiskLevel.HIGH))
        }
        
        avg_compliance = sum(s.compliance_score for s in self.scenarios) / len(self.scenarios)
        avg_confidence = sum(s.confidence_score for s in self.scenarios) / len(self.scenarios)
        
        return {
            'total': len(self.scenarios),
            'risk_distribution': risk_counts,
            'avg_compliance_score': round(avg_compliance, 2),
            'avg_confidence_score': round(avg_confidence, 2)
        }
