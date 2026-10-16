"""
Tests for naive baseline matcher.
"""
import pytest
from domain.baseline import NaiveBaselineMatcher
from domain.types import MatchResult

SAMPLE_CATALOG = [
    {
        "sku": "PIPE-001",
        "name": "GI Pipe 15mm Class A",
        "category": "pipe",
        "uom": "mtr",
        "attributes": {"material": "GI", "size_mm": "15", "class": "A"},
        "aliases": []
    },
    {
        "sku": "PIPE-002",
        "name": "GI Pipe 15mm Class B",
        "category": "pipe",
        "uom": "mtr",
        "attributes": {"material": "GI", "size_mm": "15", "class": "B"},
        "aliases": []
    },
    {
        "sku": "BOLT-001",
        "name": "MS Hex Bolt M12x50 Grade 4.6",
        "category": "fastener",
        "uom": "nos",
        "attributes": {"material": "MS", "thread": "M12", "length_mm": "50"},
        "aliases": []
    }
]

def test_baseline_proposed_when_overlap_ge_1():
    matcher = NaiveBaselineMatcher(SAMPLE_CATALOG)
    res = matcher.match("gi pipe 15mm")
    assert res.system_outcome == "proposed"
    assert len(res.candidates) == 1
    # Both PIPE-001 and PIPE-002 share tokens 'gi', 'pipe', '15mm'. Tie-break is lowest SKU -> PIPE-001
    assert res.candidates[0].sku == "PIPE-001"
    assert res.candidates[0].similarity >= 1.0

def test_baseline_unmatched_when_zero_overlap():
    matcher = NaiveBaselineMatcher(SAMPLE_CATALOG)
    res = matcher.match("Submersible Water Pump")
    assert res.system_outcome == "unmatched"
    assert len(res.candidates) == 0

def test_baseline_tie_break_lowest_sku():
    matcher = NaiveBaselineMatcher(SAMPLE_CATALOG)
    # Query matching both PIPE-001 and PIPE-002 equally
    res = matcher.match("pipe")
    assert res.system_outcome == "proposed"
    assert res.candidates[0].sku == "PIPE-001"
