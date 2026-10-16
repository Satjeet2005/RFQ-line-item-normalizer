"""
Naive baseline matching algorithm.
Defined in PRD Section E Workflow 4 and PRD_DECISIONS.md D4.

Rules:
- Raw lowercase alphanumeric tokens of description_raw
- No aliases, no spec extraction, no unit logic, no stop words
- Score = count of shared tokens with the catalog product name
- Pick max score; tie-break by lowest SKU (lexicographic ascending)
- Outcome: 'proposed' if score >= 1, else 'unmatched'
- Never returns 'ambiguous'
"""
import re
from typing import List, Dict, Any, Optional
from domain.types import MatchResult, Candidate

TOKEN_RE = re.compile(r"[a-z0-9]+")

def extract_tokens(text: str) -> set:
    if not text:
        return set()
    return set(TOKEN_RE.findall(text.lower()))

class NaiveBaselineMatcher:
    def __init__(self, catalog: List[Dict[str, Any]]):
        self.catalog = catalog
        # Pre-tokenize catalog product names
        self.catalog_tokens = []
        for item in sorted(catalog, key=lambda x: x["sku"]):
            tokens = extract_tokens(item["name"])
            self.catalog_tokens.append((item["sku"], item["name"], tokens))

    def match(self, description_raw: str) -> MatchResult:
        query_tokens = extract_tokens(description_raw)
        if not query_tokens:
            return MatchResult(system_outcome="unmatched", candidates=[], reason_codes=["NO_CANDIDATE"])

        scored = []
        for sku, name, c_tokens in self.catalog_tokens:
            overlap = len(query_tokens & c_tokens)
            if overlap >= 1:
                scored.append((overlap, sku, name))

        if not scored:
            return MatchResult(system_outcome="unmatched", candidates=[], reason_codes=["NO_CANDIDATE"])

        # Sort: score descending, then sku ascending
        scored.sort(key=lambda x: (-x[0], x[1]))

        top_overlap, top_sku, top_name = scored[0]

        top_candidate = Candidate(
            sku=top_sku,
            name=top_name,
            similarity=float(top_overlap),
            disqualified=False,
            flags=[]
        )

        # Baseline never returns ambiguous: proposed if score >= 1 else unmatched
        return MatchResult(
            system_outcome="proposed",
            candidates=[top_candidate],
            reason_codes=[]
        )
