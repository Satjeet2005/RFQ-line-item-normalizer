"""
Unit and invariant tests for the proposed deterministic matching engine.
Conforms to PRD Section E Workflows 4 & 5 and PRD_ACCEPTANCE_CHECKLIST.md Section 3 (P0 M1 - M6).
"""
import copy
import random
import pytest

from domain.normalizer import normalize_line
from domain.matcher import ProposedMatcher, dice_similarity

CATALOG_FIXTURE = [
    {
        "sku": "PIPE-001",
        "name": "GI Pipe 15mm Class A",
        "category": "pipe",
        "uom": "mtr",
        "attributes": {"material": "GI", "size_mm": "15", "class": "A"},
        "aliases": ["Galvanized Iron Pipe 15mm Light"]
    },
    {
        "sku": "PIPE-002",
        "name": "GI Pipe 15mm Class B",
        "category": "pipe",
        "uom": "mtr",
        "attributes": {"material": "GI", "size_mm": "15", "class": "B"},
        "aliases": ["Galvanized Iron Pipe 15mm Medium"]
    },
    {
        "sku": "BOLT-001",
        "name": "MS Hex Bolt M12x50 Grade 4.6",
        "category": "fastener",
        "uom": "nos",
        "attributes": {"material": "MS", "thread": "M12", "length_mm": "50", "grade": "4.6"},
        "aliases": []
    },
    {
        "sku": "BOLT-002",
        "name": "MS Hex Bolt M12x50 Grade 8.8",
        "category": "fastener",
        "uom": "nos",
        "attributes": {"material": "MS", "thread": "M12", "length_mm": "50", "grade": "8.8"},
        "aliases": []
    },
    {
        "sku": "VALV-001",
        "name": "Brass Ball Valve Screwed 25mm",
        "category": "valve",
        "uom": "nos",
        "attributes": {"material": "BRASS", "size_mm": "25"},
        "aliases": []
    }
]

CONFIG_FIXTURE = {
    "K": 5,
    "T_MIN_CANDIDATE": 0.30,
    "T_PROPOSE": 0.60,
    "T_MARGIN": 0.10
}

# 1. P0 M1: DETERMINISM AND REPEATED RUNS
def test_matcher_determinism():
    matcher = ProposedMatcher(CATALOG_FIXTURE, CONFIG_FIXTURE)
    line = normalize_line("GI Pipe 15mm Class A 10 mtr")
    res1 = matcher.match(line)
    res2 = matcher.match(line)

    assert res1.system_outcome == res2.system_outcome
    assert len(res1.candidates) == len(res2.candidates)
    assert [c.sku for c in res1.candidates] == [c.sku for c in res2.candidates]
    assert [c.similarity for c in res1.candidates] == [c.similarity for c in res2.candidates]
    assert res1.reason_codes == res2.reason_codes

# 2. P0 M4: INDEPENDENCE FROM CATALOG ORDER AND TIE-BREAKING BY SKU
def test_matcher_catalog_order_independence():
    shuffled_catalog = copy.deepcopy(CATALOG_FIXTURE)
    random.Random(42).shuffle(shuffled_catalog)

    matcher1 = ProposedMatcher(CATALOG_FIXTURE, CONFIG_FIXTURE)
    matcher2 = ProposedMatcher(shuffled_catalog, CONFIG_FIXTURE)

    line = normalize_line("GI Pipe 15mm 10 mtr")
    res1 = matcher1.match(line)
    res2 = matcher2.match(line)

    assert [c.sku for c in res1.candidates] == [c.sku for c in res2.candidates]
    assert [c.similarity for c in res1.candidates] == [c.similarity for c in res2.candidates]
    assert res1.system_outcome == res2.system_outcome

# 3. P0 M2: EACH ABSTENTION REASON CODE FORCES AMBIGUOUS
def test_abstention_reason_spec_missing_discriminator():
    # Input has material=MS, thread=M12, length=50, but missing grade!
    # BOLT-001 (4.6) and BOLT-002 (8.8) are near-tied
    matcher = ProposedMatcher(CATALOG_FIXTURE, CONFIG_FIXTURE)
    line = normalize_line("MS Hex Bolt M12x50 100 nos")
    res = matcher.match(line)
    assert res.system_outcome == "ambiguous"
    assert "SPEC_MISSING_DISCRIMINATOR" in res.reason_codes

def test_abstention_reason_low_similarity():
    # Query with similarity between T_MIN_CANDIDATE (0.30) and T_PROPOSE (0.60)
    # "Brass Valve 10 nos" shares material:BRASS and valve with VALV-001 (score = 0.50)
    matcher = ProposedMatcher(CATALOG_FIXTURE, CONFIG_FIXTURE)
    line = normalize_line("Brass Valve 10 nos")
    res = matcher.match(line)
    assert res.system_outcome == "ambiguous"
    assert "LOW_SIMILARITY" in res.reason_codes

def test_abstention_reason_unit_incompatible():
    # Valve uom is nos, input asks for kg
    matcher = ProposedMatcher(CATALOG_FIXTURE, CONFIG_FIXTURE)
    line = normalize_line("Brass Ball Valve Screwed 25mm 10 kg")
    res = matcher.match(line)
    assert res.system_outcome == "ambiguous"
    assert "UNIT_INCOMPATIBLE" in res.reason_codes

@pytest.mark.parametrize("input_text,expected_reason", [
    ("GI Pipe 15mm Class A mtr", "MISSING_QUANTITY"),
    ("GI Pipe 15mm Class A 10", "MISSING_UNIT"),
    ("GI Pipe 15mm Class A 12.5 nos", "FRACTIONAL_COUNT"),
    ("GI Pipe 15mm MS Class A 10 mtr", "SPEC_CONFLICT_IN_REQUEST"),
])
def test_abstention_reasons_blocking_issues(input_text, expected_reason):
    matcher = ProposedMatcher(CATALOG_FIXTURE, CONFIG_FIXTURE)
    line = normalize_line(input_text)
    res = matcher.match(line)
    assert res.system_outcome == "ambiguous"
    assert expected_reason in res.reason_codes

# 4. P0 M3 & M6: SPEC CONFLICT PREVENTS PROPOSED EVEN WITH HIGH SIMILARITY
def test_spec_conflict_never_proposed():
    matcher = ProposedMatcher(CATALOG_FIXTURE, CONFIG_FIXTURE)
    # Query matches BOLT-001 on almost all words, but asks for Grade 10.9 (not in catalog)
    line = normalize_line("MS Hex Bolt M12x50 Grade 10.9 100 nos")
    res = matcher.match(line)
    # All bolt candidates have grade 4.6 or 8.8 -> all disqualified -> unmatched
    assert res.system_outcome == "unmatched"
    assert "NO_COMPATIBLE_CANDIDATE" in res.reason_codes

def test_unknown_catalog_item():
    matcher = ProposedMatcher(CATALOG_FIXTURE, CONFIG_FIXTURE)
    line = normalize_line("Industrial Safety Helmet Yellow 5 nos")
    res = matcher.match(line)
    assert res.system_outcome == "unmatched"
    assert "NO_CANDIDATE" in res.reason_codes
    assert len(res.candidates) == 0

# 5. EXACT UNAMBIGUOUS MATCHES BECOME PROPOSED
def test_exact_clean_match():
    matcher = ProposedMatcher(CATALOG_FIXTURE, CONFIG_FIXTURE)
    line = normalize_line("GI Pipe 15mm Class A 10 mtr")
    res = matcher.match(line)
    assert res.system_outcome == "proposed"
    assert len(res.candidates) > 0
    assert res.candidates[0].sku == "PIPE-001"
    assert res.candidates[0].similarity == 1.0
    assert len(res.reason_codes) == 0

def test_unit_convertible_match_proposed():
    matcher = ProposedMatcher(CATALOG_FIXTURE, CONFIG_FIXTURE)
    # Pipe uom is mtr, input is ft (length dimension)
    line = normalize_line("GI Pipe 15mm Class A 30 ft")
    res = matcher.match(line)
    assert res.system_outcome == "proposed"
    assert res.candidates[0].sku == "PIPE-001"
