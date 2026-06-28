"""
Helper utilities.
"""
import uuid
from typing import Dict, List, Any
from dataclasses import dataclass, asdict
from enum import Enum


class RiskLevel(str, Enum):
    """Risk level enumeration."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ComplianceStatus(str, Enum):
    """Compliance status enumeration."""
    COMPLIANT = "compliant"
    NON_COMPLIANT = "non_compliant"
    PARTIAL = "partial"
    UNKNOWN = "unknown"
    REQUIRES_REVIEW = "requires_review"
    INSUFFICIENT_DATA = "insufficient_data"


def generate_id(prefix: str = "ID") -> str:
    """Generate unique identifier."""
    return f"{prefix}_{uuid.uuid4().hex[:8].upper()}"


def safe_divide(numerator: float, denominator: float, default: float = 0.0) -> float:
    """Safely divide two numbers."""
    if denominator == 0:
        return default
    return numerator / denominator


def format_distance(meters: float) -> str:
    """Format distance in human-readable form."""
    if meters < 1:
        return f"{meters * 100:.0f}cm"
    return f"{meters:.2f}m"
