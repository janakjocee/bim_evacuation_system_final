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
    source_mode: str = "uploaded_ifc"
    source_file_name: str = ""
    source_file_sha256: str = ""
    ifc_schema: str = "UNKNOWN"
    regulation_source: str = "default_rules"
    regulation_clause_count: int = 0
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

        readiness = validate_ifc_model(
            self.ifc_parser.ifc_file,
            extracted_data={
                "space_count": len(self.building.spaces),
                "door_count": len(self.building.doors),
                "stair_count": len(self.building.stairs),
                "possible_exits_count": len(self.building.exits),
                "graph_connectivity_complete": bool(self.building.doors and self.building.exits),
            },
        )
        source_mode = "uploaded_ifc"

        if self.building.extraction_mode == "geometry_derived":
            source_mode = "geometry_derived"
            readiness["readiness_label"] = (
                "Geometry-derived structural screening available; semantic room/door review required"
            )
        elif self.building.extraction_mode == "semantic_spaces_inferred_topology":
            source_mode = "semantic_spaces_inferred_topology"
            readiness["readiness_label"] = (
                "Semantic spaces with inferred route topology; door/exit assumptions require review"
            )
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
        
        # Step 4: Parse regulations (if provided)
        regulation_clauses = []
        if regulation_text:
            logger.info("Step 4: Parsing regulations")
            regulation_clauses = self.regulation_parser.parse(regulation_text)
            
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
            self.scenario_generator.set_regulations(regulation_clauses)
        
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
            source_mode=source_mode,
            source_file_name=source_file_name,
            source_file_sha256=source_file_sha256,
            ifc_schema=readiness["schema"],
            regulation_source=regulation_source,
            regulation_clause_count=len(regulation_clauses),
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
                'building_name': result.building.name if result.building else 'Unknown',
                'source_file_name': result.source_file_name,
                'source_file_sha256': result.source_file_sha256,
                'ifc_schema': result.ifc_schema,
                'source_mode': result.source_mode,
                'regulation_source': result.regulation_source,
                'regulation_clause_count': result.regulation_clause_count,
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
