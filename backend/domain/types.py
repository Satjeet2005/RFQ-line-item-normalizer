"""
Core domain types and dataclasses.
Pure Python, zero dependencies on FastAPI or SQLAlchemy.
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any

@dataclass
class Product:
    sku: str
    name: str
    category: str
    uom: str
    attributes: Dict[str, str] = field(default_factory=dict)
    aliases: List[str] = field(default_factory=list)

@dataclass
class IngestedLine:
    raw_input: str
    description_raw: str
    quantity_raw: Optional[str] = None
    unit_raw: Optional[str] = None

@dataclass
class Candidate:
    sku: str
    name: str
    similarity: float
    disqualified: bool = False
    flags: List[str] = field(default_factory=list)

@dataclass
class MatchResult:
    system_outcome: str  # proposed, ambiguous, unmatched
    candidates: List[Candidate] = field(default_factory=list)
    reason_codes: List[str] = field(default_factory=list)
