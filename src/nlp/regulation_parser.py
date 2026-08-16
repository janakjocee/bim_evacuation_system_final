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


@dataclass
class RegulationRule:
    """Structured regulation rule extracted from uploaded text."""
    rule_id: str
    source_section: str
    source_text: str
    applies_to: str
    condition: str
    metric: str
    operator: str
    value: float
    unit: str
    confidence: float = 0.75
    extracted_by: str = "pattern_parser"


class RegulationParser:
    """Parse building regulations using NLP."""
    
    # Patterns for extracting measurements
    MEASUREMENT_PATTERNS = [
        (r'(\d+(?:\.\d+)?)\s*(m²|sqm|square\s*m)\b', 1.0, "m2"),
        (r'(\d+(?:\.\d+)?)\s*(mm|millimetres?)\b', 0.001, "m"),
        (r'(\d+(?:\.\d+)?)\s*(cm|centimetres?)\b', 0.01, "m"),
        (r'(\d+(?:\.\d+)?)\s*(m|metres?)\b', 1.0, "m"),
    ]
    
    def __init__(self):
        """Initialize regulation parser."""
        self.config = get_config()
        self.nlp = None
        self.clauses: List[RegulationClause] = []
        self.rules: List[RegulationRule] = []
        
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
        self.rules = []
        
        # Split into sections/clauses
        sections = self._split_into_sections(text)
        
        for section_id, section_text in sections:
            clause = self._extract_clause(section_id, section_text)
            if clause:
                self.clauses.append(clause)
                self.rules.extend(self._extract_rules(section_id, section_text, clause))
        
        logger.info(f"Extracted {len(self.clauses)} clauses and {len(self.rules)} structured rules")
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

    def _extract_rules(
        self,
        section_id: str,
        text: str,
        clause: RegulationClause,
    ) -> List[RegulationRule]:
        """Extract every actionable numeric rule from a clause."""
        rules: List[RegulationRule] = []
        measurements = self._extract_measurements(text)
        if not measurements:
            return rules

        sentences = self._split_sentences(text)
        if not sentences:
            sentences = [text]

        seen = set()
        for value, unit, start, end in measurements:
            sentence = next(
                (s for s in sentences if start >= s["start"] and end <= s["end"]),
                {"text": text, "start": 0, "end": len(text)},
            )
            source_text = sentence["text"].strip()[:500]
            applies_to = self._determine_applies_to(source_text)
            constraint_type = self._determine_constraint_type(source_text)
            metric = self._metric_from_constraint(source_text, applies_to, constraint_type)
            operator = self._operator_from_constraint(constraint_type)

            if metric == "general" or operator == "":
                continue
            if re.search(r'\bper\s+(?:person|occupant)\b', source_text, re.IGNORECASE):
                # Per-person width formulas need an occupant calculation and must
                # not be misapplied as a global fixed-width threshold.
                continue

            key = (metric, operator, value, source_text)
            if key in seen:
                continue
            seen.add(key)

            rule_number = len(rules) + 1
            rules.append(RegulationRule(
                rule_id=f"{section_id}-R{rule_number}",
                source_section=section_id,
                source_text=source_text,
                applies_to=applies_to or clause.applies_to,
                condition=self._condition_from_text(source_text),
                metric=metric,
                operator=operator,
                value=value,
                unit=unit,
                confidence=self._rule_confidence(source_text, metric),
            ))

        return rules
    
    def _determine_applies_to(self, text: str) -> str:
        """Determine what building element the clause applies to."""
        text_lower = text.lower()
        
        if 'travel' in text_lower or 'distance' in text_lower:
            return 'route'
        if 'door' in text_lower or 'exit' in text_lower:
            return 'door'
        elif 'stair' in text_lower:
            return 'stair'
        elif 'corridor' in text_lower or 'passage' in text_lower:
            return 'corridor'
        elif 'space' in text_lower or 'room' in text_lower:
            return 'space'

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

    def _metric_from_constraint(self, text: str, applies_to: str, constraint_type: str) -> str:
        """Normalize a parsed clause into a compliance metric key."""
        text_lower = text.lower()

        if constraint_type == "max_distance":
            if any(term in text_lower for term in ["hose", "fire main", "firefighting shaft"]):
                return "max_fire_hose_distance"
            if "travel" not in text_lower:
                return "max_other_distance"
            if "direct distance" in text_lower:
                return "max_direct_travel_distance"
            if "small premises" in text_lower or "small-premises" in text_lower:
                return "max_small_premises_travel_distance"
            if "alternative" in text_lower or "more than one direction" in text_lower:
                return "max_alternative_travel_distance"
            if "single direction" in text_lower or "one direction" in text_lower:
                return "max_single_direction_travel_distance"
            return "max_travel_distance"

        if constraint_type == "min_width":
            if "firefighting stair" in text_lower or "fire-fighting stair" in text_lower:
                return "min_firefighting_stair_width"
            if "final exit" in text_lower or ("exit" in text_lower and applies_to == "door"):
                return "min_exit_width"
            if "corridor" in text_lower or applies_to == "corridor":
                return "min_corridor_width"
            if "stair" in text_lower or applies_to == "stair":
                return "min_stair_width"
            if "door" in text_lower or "clear opening" in text_lower or applies_to == "door":
                return "min_door_width"

        if constraint_type == "max_height" and "riser" in text_lower:
            return "max_riser_height"
        if "tread" in text_lower and constraint_type in {"min_width", "min_height"}:
            return "min_tread_length"
        if constraint_type == "max_occupancy":
            return "max_occupancy"
        if constraint_type == "max_area":
            return "max_area"

        return "general"

    def _operator_from_constraint(self, constraint_type: str) -> str:
        """Map a constraint type to a comparison operator."""
        if constraint_type.startswith("max_"):
            return "<="
        if constraint_type.startswith("min_"):
            return ">="
        return ""

    def _condition_from_text(self, text: str) -> str:
        """Extract a short human-readable condition for the rule."""
        text_lower = text.lower()
        occupants_up_to = re.search(r'occupants?\s+(?:up to|not more than|maximum)\s*(\d+)', text_lower)
        if occupants_up_to:
            return f"occupants_at_most:{occupants_up_to.group(1)}"
        occupants_above = re.search(r'(?:more than|above)\s*(\d+)\s+occupants?', text_lower)
        if occupants_above:
            return f"occupants_above:{occupants_above.group(1)}"
        people_context = re.search(r'for\s+(\d+)\s+(?:people|persons?|occupants?)', text_lower)
        if people_context:
            return f"occupants_context:{people_context.group(1)}"
        if "direct distance" in text_lower:
            return "direct_distance_method"
        if "small premises" in text_lower or "small-premises" in text_lower:
            return "small_premises_scope"
        if "alternative" in text_lower or "more than one direction" in text_lower:
            return "alternative_escape"
        if "single direction" in text_lower or "one direction" in text_lower:
            return "single_direction_escape"
        if "final exit" in text_lower:
            return "final_exit"
        return "general"

    def _rule_confidence(self, text: str, metric: str) -> float:
        """Estimate extraction confidence from explicitness of wording."""
        text_lower = text.lower()
        confidence = 0.65
        if metric != "general":
            confidence += 0.15
        if any(term in text_lower for term in ["must", "shall", "minimum", "maximum", "not exceed", "not less than"]):
            confidence += 0.1
        if any(term in text_lower for term in ["door", "exit", "travel", "distance", "corridor", "stair"]):
            confidence += 0.1
        return min(confidence, 0.95)
    
    def _extract_measurement(self, text: str) -> tuple:
        """Extract measurement value and unit from text."""
        measurements = self._extract_measurements(text)
        if measurements:
            value, unit, _, _ = measurements[0]
            return value, unit
        return None, ""

    def _extract_measurements(self, text: str) -> List[tuple]:
        """Extract all measurement values and normalized units from text."""
        measurements = []
        for pattern, multiplier, normalized_unit in self.MEASUREMENT_PATTERNS:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                value = float(match.group(1))
                measurements.append((value * multiplier, normalized_unit, match.start(), match.end()))

        measurements.sort(key=lambda item: item[2])
        return measurements

    def _split_sentences(self, text: str) -> List[Dict[str, Any]]:
        """Split text into sentence-like spans while preserving offsets.

        Uses spaCy sentence boundary detection when available for more
        accurate splitting, with a regex fallback otherwise.
        """
        if self.nlp is not None:
            line_matches = list(re.finditer(r'[^\r\n]+', text))
            spans = []
            for line_match, doc in zip(
                line_matches,
                self.nlp.pipe([match.group(0) for match in line_matches]),
            ):
                for sent in doc.sents:
                    source_text = sent.text.strip()
                    if source_text:
                        start = line_match.start() + sent.start_char
                        spans.append({
                            "text": source_text,
                            "start": start,
                            "end": line_match.start() + sent.end_char,
                        })
            return spans

        # Regex fallback when spaCy is not available
        spans = []
        start = 0
        for match in re.finditer(r'(?<=[.!?])\s+|[\r\n]+', text):
            end = match.start()
            sentence = text[start:end].strip()
            if sentence:
                spans.append({"text": sentence, "start": start, "end": end})
            start = match.end()

        tail = text[start:].strip()
        if tail:
            spans.append({"text": tail, "start": start, "end": len(text)})

        return spans
    
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
