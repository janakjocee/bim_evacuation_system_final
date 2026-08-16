"""
Main evacuation pipeline orchestrator.
"""
import json
import hashlib
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from pathlib import Path

from ..utils.logger import get_logger
from ..utils.config_loader import get_config
from ..utils.model_transparency import (
    ACADEMIC_USE_NOTICE,
    screening_index_semantics,
    standard_assumption_registry,
)
from ..bim_processing.ifc_parser import IFCParser, BuildingData
from ..bim_processing.ifc_validation import validate_ifc_model
from ..bim_processing.feature_extractor import FeatureExtractor, ExtractedFeatures
from ..bim_processing.spatial_graph import SpatialGraphBuilder
from ..nlp.regulation_parser import RegulationParser
from ..nlp.rag_engine import RAGEngine
from ..scenario.scenario_generator import ScenarioGenerator, EvacuationScenario

logger = get_logger("evacuation_pipeline")


@dataclass
class PipelineResult:
    """Result of pipeline execution."""
    success: bool
    building: Optional[BuildingData] = None
    features: Optional[ExtractedFeatures] = None
    scenarios: List[EvacuationScenario] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    processing_time: float = 0.0
    readiness: Dict[str, Any] = field(default_factory=dict)
    graph_stats: Dict[str, Any] = field(default_factory=dict)
    source_mode: str = "uploaded_ifc"
    source_file_name: str = ""
    source_file_sha256: str = ""
    ifc_schema: str = "UNKNOWN"
    regulation_source: str = "default_rules"
    regulation_clause_count: int = 0
    regulation_rule_count: int = 0
    regulation_application: Dict[str, Any] = field(default_factory=dict)
    rag_enabled: bool = False


class EvacuationPipeline:
    """Main evacuation scenario generation pipeline."""
    
    def __init__(self):
        """Initialize pipeline."""
        self.config = get_config()
        
        # Components
        self.ifc_parser = IFCParser()
        self.feature_extractor = FeatureExtractor()
        self.regulation_parser = RegulationParser()
        self.rag_engine = RAGEngine()
        
        # State
        self.building: Optional[BuildingData] = None
        self.graph_builder: Optional[SpatialGraphBuilder] = None
        self.scenario_generator: Optional[ScenarioGenerator] = None

    def _build_readiness(self, graph_stats: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Assess both operational processing and engineering evidence quality."""
        building = self.building
        graph_stats = graph_stats or {}
        if building is None:
            return validate_ifc_model(self.ifc_parser.ifc_file)

        def model_count(entity_name: str) -> int:
            try:
                return len(self.ifc_parser.ifc_file.by_type(entity_name))
            except Exception:
                return 0

        inferred_exits = sum(
            1
            for door in building.exits.values()
            if str(door.connection_source).startswith("inferred")
            or "exit_detection" in door.assumptions
            or "topology" in door.assumptions
        )
        missing_door_widths = sum(
            1 for door in building.doors.values() if door.assumptions.get("width")
        )
        missing_space_areas = sum(
            1 for space in building.spaces.values() if space.assumptions.get("area")
        )
        missing_storey_placement = sum(
            1 for space in building.spaces.values() if not space.level
        )
        semantic_rooms = model_count("IfcSpace")
        missing_occupancy = semantic_rooms
        graph_complete = bool(
            graph_stats.get("is_connected")
            and building.exits
            and not graph_stats.get("disconnected_spaces")
            and not graph_stats.get("spaces_without_exit_route")
        )

        return validate_ifc_model(
            self.ifc_parser.ifc_file,
            extracted_data={
                "space_count": semantic_rooms,
                "door_count": model_count("IfcDoor"),
                "stair_count": model_count("IfcStair"),
                "buildingstorey_count": model_count("IfcBuildingStorey"),
                "possible_exits_count": len(building.exits),
                "analysis_space_count": len(building.spaces),
                "analysis_door_count": len(building.doors),
                "analysis_mode": building.extraction_mode,
                "missing_door_widths": missing_door_widths,
                "missing_space_areas": missing_space_areas,
                "missing_storey_placement": missing_storey_placement,
                "missing_exit_identification": bool(inferred_exits),
                "missing_occupancy": missing_occupancy,
                "graph_connectivity_complete": graph_complete,
                "verified_edge_count": graph_stats.get("verified_edges_count", 0),
                "inferred_edge_count": graph_stats.get("inferred_edges_count", 0),
                "inferred_exit_count": inferred_exits,
                "graph_confidence_score": graph_stats.get("graph_confidence_score", 0),
            },
        )
    
    def run(
        self,
        ifc_path: str,
        regulation_text: str = None,
        max_scenarios: int = None,
        enable_rag: bool = True,
    ) -> PipelineResult:
        """
        Run the complete pipeline.
        
        Args:
            ifc_path: Path to IFC file
            regulation_text: Optional regulation text
            
        Returns:
            PipelineResult
        """
        import time
        start_time = time.time()
        source_path = Path(ifc_path)
        source_file_name = source_path.name
        try:
            source_file_sha256 = hashlib.sha256(source_path.read_bytes()).hexdigest()
        except OSError:
            source_file_sha256 = ""
        
        logger.info("=" * 60)
        logger.info("Starting Evacuation Pipeline")
        logger.info("=" * 60)
        
        errors = []
        
        if _looks_like_git_lfs_pointer(source_path):
            errors.append(
                "The uploaded .ifc file is a Git LFS pointer, not the actual IFC model. "
                "Download the real LFS file contents and upload that IFC again."
            )
            return PipelineResult(
                success=False,
                errors=errors,
                source_file_name=source_file_name,
                source_file_sha256=source_file_sha256,
            )

        # Step 1: Parse IFC
        logger.info("Step 1: Parsing IFC file")
        self.building = self.ifc_parser.parse(ifc_path)
        
        if not self.building:
            errors.append("Failed to parse IFC file")
            return PipelineResult(
                success=False,
                errors=errors,
                source_file_name=source_file_name,
                source_file_sha256=source_file_sha256,
            )

        source_mode = self.building.extraction_mode or "semantic_ifc"
        readiness = self._build_readiness()

        if self.building.extraction_mode == "geometry_derived":
            source_mode = "geometry_derived"
        elif self.building.extraction_mode == "semantic_spaces_inferred_topology":
            source_mode = "semantic_spaces_inferred_topology"
        elif readiness["critical_issues"]:
            errors.extend(readiness["critical_issues"])
            errors.append(
                "The uploaded IFC has no usable semantic or geometry-derived topology."
            )
            return PipelineResult(
                success=False,
                building=self.building,
                errors=errors,
                processing_time=time.time() - start_time,
                readiness=readiness,
                source_mode=source_mode,
                source_file_name=source_file_name,
                source_file_sha256=source_file_sha256,
                ifc_schema=readiness["schema"],
            )
        
        # Step 2: Extract features
        logger.info("Step 2: Extracting features")
        features = self.feature_extractor.extract(self.building)
        
        # Step 3: Build spatial graph
        logger.info("Step 3: Building spatial graph")
        self.graph_builder = SpatialGraphBuilder(self.building)
        graph_success = self.graph_builder.build()
        
        if not graph_success:
            logger.warning("Graph building had issues, continuing with limited functionality")
        graph_stats = self.graph_builder.get_graph_stats() if self.graph_builder else {}
        readiness = self._build_readiness(graph_stats)
        
        # Step 4: Parse regulations (if provided)
        regulation_clauses = []
        regulation_rules = []
        if regulation_text:
            logger.info("Step 4: Parsing regulations")
            regulation_clauses = self.regulation_parser.parse(regulation_text)
            regulation_rules = self.regulation_parser.rules
            
            # Build the optional retrieval index only when enabled.
            if regulation_clauses and enable_rag:
                self.rag_engine.build_index(regulation_clauses)
            elif regulation_clauses:
                logger.info("RAG grounding disabled; using parsed regulation constraints only")
        else:
            logger.info("Step 4: No regulations provided, using defaults")
        
        # Step 5: Generate scenarios
        logger.info("Step 5: Generating evacuation scenarios")
        self.scenario_generator = ScenarioGenerator(self.building, self.graph_builder)
        
        if regulation_clauses:
            self.scenario_generator.set_regulations(
                regulation_clauses,
                rules=regulation_rules,
                rag_engine=self.rag_engine if enable_rag else None,
            )
        regulation_application = self.scenario_generator.compliance_checker.get_rule_application_summary()
        
        scenarios = self.scenario_generator.generate(max_scenarios=max_scenarios)
        regulation_source = "uploaded_regulations" if regulation_clauses else "default_rules"
        
        if not scenarios:
            errors.append("No scenarios generated")
        
        processing_time = time.time() - start_time
        
        logger.info("=" * 60)
        logger.info(f"Pipeline completed in {processing_time:.2f}s")
        logger.info(f"Generated {len(scenarios)} scenarios")
        logger.info("=" * 60)
        
        return PipelineResult(
            success=len(scenarios) > 0,
            building=self.building,
            features=features,
            scenarios=scenarios,
            errors=errors,
            processing_time=processing_time,
            readiness=readiness,
            graph_stats=graph_stats,
            source_mode=source_mode,
            source_file_name=source_file_name,
            source_file_sha256=source_file_sha256,
            ifc_schema=readiness["schema"],
            regulation_source=regulation_source,
            regulation_clause_count=len(regulation_clauses),
            regulation_rule_count=len(regulation_rules),
            regulation_application=regulation_application,
            rag_enabled=bool(regulation_clauses and enable_rag),
        )

    
    def export_results(self, result: PipelineResult, output_dir: str,
                       formats: List[str] = None) -> Dict[str, str]:
        """
        Export pipeline results.
        
        Args:
            result: Pipeline result
            output_dir: Output directory
            formats: Export formats
            
        Returns:
            Dictionary of exported file paths
        """
        if formats is None:
            formats = ['json', 'csv']
        
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        exported = {}
        
        # Export to JSON
        if 'json' in formats:
            json_path = output_path / 'scenarios.json'
            data = {
                'export_version': 'submission-evidence-v2',
                'academic_use_notice': ACADEMIC_USE_NOTICE,
                'score_semantics': screening_index_semantics(),
                'assumption_registry': standard_assumption_registry(),
                'building_name': result.building.name if result.building else 'Unknown',
                'source_file_name': result.source_file_name,
                'source_file_sha256': result.source_file_sha256,
                'ifc_schema': result.ifc_schema,
                'source_mode': result.source_mode,
                'regulation_source': result.regulation_source,
                'regulation_clause_count': result.regulation_clause_count,
                'regulation_rule_count': result.regulation_rule_count,
                'regulation_application': result.regulation_application,
                'graph_stats': result.graph_stats,
                'rag_enabled': result.rag_enabled,
                'scenarios': [s.to_dict() for s in result.scenarios],
                'summary': self.scenario_generator.get_summary() if self.scenario_generator else {}
            }
            
            with open(json_path, 'w') as f:
                json.dump(data, f, indent=2)
            
            exported['json'] = str(json_path)
            logger.info(f"Exported JSON: {json_path}")
        
        # Export to CSV
        if 'csv' in formats and result.scenarios:
            csv_path = output_path / 'scenarios.csv'
            
            import csv
            with open(csv_path, 'w', newline='') as f:
                if result.scenarios:
                    writer = csv.DictWriter(f, fieldnames=result.scenarios[0].to_dict().keys())
                    writer.writeheader()
                    for scenario in result.scenarios:
                        writer.writerow(scenario.to_dict())
            
            exported['csv'] = str(csv_path)
            logger.info(f"Exported CSV: {csv_path}")
        
        return exported


def _looks_like_git_lfs_pointer(path: Path) -> bool:
    """Return True when a file is a Git LFS pointer instead of real IFC SPF text."""
    try:
        header = path.read_text(encoding="utf-8", errors="ignore")[:200]
    except OSError:
        return False
    return (
        "version https://git-lfs.github.com/spec/v1" in header
        and "oid sha256:" in header
    )
