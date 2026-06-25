"""
Regulation text parser using spaCy.
"""
import re
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field

try:
    import spacy
    SPACY_AVAILABLE = True
except ImportError:
    SPACY_AVAILABLE = False

from ..utils.logger import get_logger
from ..utils.config_loader import get_config

logger = get_logger("regulation_parser")


@dataclass
class RegulationClause:
    """Extracted regulation clause."""
    clause_id: str
    text: str
    section: str = ""
    applies_to: str = ""
    constraint_type: str = ""  # min_width, max_distance, etc.
    value: Optional[float] = None
    unit: str = ""


class RegulationParser:
    """Parse building regulations using NLP."""
    
    # Patterns for extracting measurements
    MEASUREMENT_PATTERNS = [
        (r'(\d+(?:\.\d+)?)\s*(mm|millimetres?)', 0.001),  # Convert to meters
        (r'(\d+(?:\.\d+)?)\s*(cm|centimetres?)', 0.01),
        (r'(\d+(?:\.\d+)?)\s*(m|metres?)', 1.0),
        (r'(\d+(?:\.\d+)?)\s*(m²|sqm|square\s*m)', 1.0),
    ]
    
    def __init__(self):
        """Initialize regulation parser."""
        self.config = get_config()
        self.nlp = None
        self.clauses: List[RegulationClause] = []
        
        if SPACY_AVAILABLE:
            try:
                model_name = self.config.get('nlp.model', 'en_core_web_sm')
                self.nlp = spacy.load(model_name)
                logger.info(f"Loaded spaCy model: {model_name}")
            except OSError:
                logger.warning(f"spaCy model not found. Using pattern matching.")
        else:
            logger.warning("spaCy not available. Using pattern matching only.")
    
    def parse(self, text: str) -> List[RegulationClause]:
        """
        Parse regulation text.
        
        Args:
            text: Regulation text
            
        Returns:
            List of extracted clauses
        """
        logger.info("Parsing regulation text")
        
        self.clauses = []
        
        # Split into sections/clauses
        sections = self._split_into_sections(text)
        
        for section_id, section_text in sections:
            clause = self._extract_clause(section_id, section_text)
            if clause:
                self.clauses.append(clause)
        
        logger.info(f"Extracted {len(self.clauses)} clauses")
        return self.clauses
    
    def _split_into_sections(self, text: str) -> List[tuple]:
        """Split text into sections."""
        sections = []
        
        # Split by numbered sections (e.g., "2.1", "3.4")
        pattern = r'(?:\n|\r|^)(\d+\.\d+)\s+'
        parts = re.split(pattern, text)
        
        if len(parts) > 1:
            for i in range(1, len(parts), 2):
                section_id = parts[i]
                section_text = parts[i + 1] if i + 1 < len(parts) else ""
                sections.append((section_id, section_text.strip()))
        
        # If no numbered sections, split by paragraphs
        if not sections:
            paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
            for i, para in enumerate(paragraphs):
                sections.append((f"PARA_{i+1}", para))
        
        return sections
    
    def _extract_clause(self, clause_id: str, text: str) -> Optional[RegulationClause]:
        """Extract clause information."""
        clause = RegulationClause(clause_id=clause_id, text=text[:500])  # Limit text length
        
        # Determine what it applies to
        clause.applies_to = self._determine_applies_to(text)
        
        # Determine constraint type
        clause.constraint_type = self._determine_constraint_type(text)
        
        # Extract value
        value, unit = self._extract_measurement(text)
        if value is not None:
            clause.value = value
            clause.unit = unit
        
        return clause
    
    def _determine_applies_to(self, text: str) -> str:
        """Determine what building element the clause applies to."""
        text_lower = text.lower()
        
        if 'door' in text_lower or 'exit' in text_lower:
            return 'door'
        elif 'stair' in text_lower:
            return 'stair'
        elif 'corridor' in text_lower or 'passage' in text_lower:
            return 'corridor'
        elif 'space' in text_lower or 'room' in text_lower:
            return 'space'
        elif 'travel' in text_lower or 'distance' in text_lower:
            return 'route'
        
        return 'general'
    
    def _determine_constraint_type(self, text: str) -> str:
        """Determine the type of constraint."""
        text_lower = text.lower()
        
        # Check for minimum/maximum
        has_minimum = any(word in text_lower for word in ['minimum', 'min', 'at least', 'not less than'])
        has_maximum = any(word in text_lower for word in [
            'maximum',
            'max',
            'not more than',
            'no more than',
            'not exceed',
            'must not exceed',
            'shall not exceed',
            'should not exceed',
            'exceeding',
        ])
        
        # Check what is being constrained
        if 'width' in text_lower:
            if has_minimum:
                return 'min_width'
            elif has_maximum:
                return 'max_width'
        
        if 'distance' in text_lower or 'travel' in text_lower:
            if has_maximum:
                return 'max_distance'
        
        if 'height' in text_lower:
            if has_minimum:
                return 'min_height'
            elif has_maximum:
                return 'max_height'
        
        if 'occupancy' in text_lower:
            if has_maximum:
                return 'max_occupancy'
        
        if 'area' in text_lower:
            if has_maximum:
                return 'max_area'
        
        return 'general'
    
    def _extract_measurement(self, text: str) -> tuple:
        """Extract measurement value and unit from text."""
        for pattern, multiplier in self.MEASUREMENT_PATTERNS:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                value = float(match.group(1))
                unit = match.group(2)
                return value * multiplier, unit
        
        return None, ""
    
    def get_constraints_dict(self) -> Dict[str, Any]:
        """Get extracted constraints as dictionary."""
        constraints = {}
        
        for clause in self.clauses:
            if clause.value is not None:
                key = f"{clause.applies_to}_{clause.constraint_type}"
                constraints[key] = {
                    'value': clause.value,
                    'unit': clause.unit,
                    'clause_id': clause.clause_id,
                    'text': clause.text[:200]
                }
        
        return constraints
    
    def search_clauses(self, query: str) -> List[RegulationClause]:
        """Search clauses by keyword."""
        query_lower = query.lower()
        results = []
        
        for clause in self.clauses:
            if query_lower in clause.text.lower():
                results.append(clause)
        
        return results
