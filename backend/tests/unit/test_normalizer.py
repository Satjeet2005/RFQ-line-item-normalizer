"""
Tests for deterministic normalizer and spec extraction.
Conforms to PRD Section E Workflows 1 & 3 and PRD_ACCEPTANCE_CHECKLIST.md N1-N5.
"""
from decimal import Decimal
import pytest

from domain.normalizer import (
    normalize_line,
    parse_quantity,
    clean_text_nfkc,
    extract_specifications,
)

# 1. QUANTITY PARSING TESTS
@pytest.mark.parametrize("qty_str,canonical_unit,expected_val", [
    ("123", "nos", Decimal("123")),
    ("12.5", "mtr", Decimal("12.5")),
    ("12.345", "kg", Decimal("12.345")),
    ("1,000", "nos", Decimal("1000")),
    ("1,00,000", "nos", Decimal("100000")),
    ("10,00,000", "nos", Decimal("1000000")),
    ("१२५", "nos", Decimal("125")),
    ("२.५", "mtr", Decimal("2.5")),
])
def test_accepted_quantity_formats(qty_str, canonical_unit, expected_val):
    val, issues = parse_quantity(qty_str, canonical_unit)
    assert val == expected_val
    assert len(issues) == 0

@pytest.mark.parametrize("qty_str", [
    "1,5",       # comma decimal rejected
    "1e3",       # scientific notation rejected
    "1E3",
    "0",         # zero rejected
    "0.0",
    "-5",        # negative rejected
    "-10.5",
    "1000001",   # > 1,000,000 rejected
    "12.3456",   # > 3 decimal places rejected
    "abc",       # unparseable text
    "1,0000",    # invalid grouping
])
def test_rejected_quantity_formats(qty_str):
    val, issues = parse_quantity(qty_str, "nos")
    assert val is None
    assert any(i.code == "INVALID_QUANTITY" for i in issues)

def test_fractional_count_unit():
    val, issues = parse_quantity("12.5", "nos")
    assert val == Decimal("12.5")
    assert any(i.code == "FRACTIONAL_COUNT" for i in issues)

    val, issues = parse_quantity("0.5", "box")
    assert val == Decimal("0.5")
    assert any(i.code == "FRACTIONAL_COUNT" for i in issues)

    # Decimal for continuous units is valid without issue
    val, issues = parse_quantity("12.5", "mtr")
    assert val == Decimal("12.5")
    assert len(issues) == 0

# 2. FREE-TEXT TRAILING QUANTITY RULES (1-5)
def test_trailing_rule_1_number_and_unit():
    # Rule 1: <number> <unit-alias> at end
    res = normalize_line("GI Pipe 25mm Class B 10 mtr")
    assert res.quantity == Decimal("10")
    assert res.unit == "mtr"
    assert "MISSING_QUANTITY" not in res.issue_codes
    assert "MISSING_UNIT" not in res.issue_codes

def test_trailing_rule_2_number_only_missing_unit():
    # Rule 2: <number> at end not preceded by x
    res = normalize_line("GI Socket Coupling 20mm Class B 50")
    assert res.quantity == Decimal("50")
    assert res.unit is None
    assert "MISSING_UNIT" in res.issue_codes

def test_trailing_rule_3_dimension_at_end_missing_quantity():
    # Rule 3: <number> preceded by x is a dimension, not quantity
    res = normalize_line("MS Hex Bolt M12 x 50")
    assert res.quantity is None
    assert "MISSING_QUANTITY" in res.issue_codes

def test_trailing_rule_4_missing_quantity():
    # Rule 4: non-number at end
    res = normalize_line("MS Hex Nut M10 nos")
    assert res.quantity is None
    assert "MISSING_QUANTITY" in res.issue_codes

def test_trailing_rule_5_unrecognized_trailing_word():
    # Rule 5: <number> <unknown-word> is not parsed as quantity
    res = normalize_line("PVC Pipe 50mm Class A 30 bundles")
    assert res.quantity is None
    assert "MISSING_QUANTITY" in res.issue_codes

def test_delimited_input_unknown_unit():
    # Delimited input with explicit unrecognized unit column
    res = normalize_line("PVC Pipe 50mm Class A|30|bundles")
    assert res.quantity == Decimal("30")
    assert res.unit is None
    assert "UNKNOWN_UNIT" in res.issue_codes

# 3. SPEC EXTRACTION TESTS
def test_spec_extraction_metric_mm():
    spec, _, issues = extract_specifications("GI Pipe 25mm Class B")
    assert spec.get("size_mm") == "25"
    assert spec.get("class") == "B"
    assert spec.get("material") == "GI"
    assert len(issues) == 0

def test_spec_extraction_metric_cm():
    spec, _, _ = extract_specifications("GI Pipe 2.5 cm Class B")
    assert spec.get("size_mm") == "25"

def test_spec_extraction_inch_integer_and_decimal():
    spec, _, _ = extract_specifications("GI Pipe 1 inch Class B")
    assert spec.get("size_mm") == "25.4"

    spec, _, _ = extract_specifications("GI Pipe 2\" Class B")
    assert spec.get("size_mm") == "50.8"

def test_spec_extraction_inch_fraction():
    spec, _, _ = extract_specifications("Copper Tubing 1/2 inch")
    assert spec.get("size_mm") == "12.7"

    spec, _, _ = extract_specifications("Copper Tubing 1/4\"")
    assert spec.get("size_mm") == "6.35"

    spec, _, _ = extract_specifications("Copper Tubing 3/4 in")
    assert spec.get("size_mm") == "19.05"

def test_spec_extraction_inch_mixed_fraction():
    spec, _, _ = extract_specifications("GI Pipe 1 1/2 inch Class B")
    assert spec.get("size_mm") == "38.1"

def test_spec_extraction_unicode_fraction():
    spec, _, _ = extract_specifications("GI Pipe ½\" Class B")
    assert spec.get("size_mm") == "12.7"

    spec, _, _ = extract_specifications("GI Pipe 1½\" Class B")
    assert spec.get("size_mm") == "38.1"

def test_spec_extraction_washer_hole_size():
    spec, _, _ = extract_specifications("MS Plain Washer M12")
    assert spec.get("size_mm") == "12"
    assert "thread" not in spec

def test_spec_extraction_bolt_thread_length_grade():
    spec, _, _ = extract_specifications("MS Hex Bolt M12x50 Grade 4.6")
    assert spec.get("material") == "MS"
    assert spec.get("thread") == "M12"
    assert spec.get("length_mm") == "50"
    assert spec.get("grade") == "4.6"

def test_spec_extraction_materials():
    for text, expected in [
        ("GI Pipe 25mm", "GI"),
        ("galvanized pipe 25mm", "GI"),
        ("dasta paip 25mm", "GI"),
        ("MS Hex Bolt M10", "MS"),
        ("mild steel bolt", "MS"),
        ("loha bolt M12", "MS"),
        ("SS304 Hex Bolt M12", "SS304"),
        ("Stainless Steel Hex Bolt M12", "SS304"),
        ("SS316 Valve 25mm", "SS316"),
        ("PVC Pipe 25mm", "PVC"),
        ("Brass Ball Valve 25mm", "BRASS"),
        ("pital valve 25mm", "BRASS"),
        ("cu tube 1/2 inch", "CU"),
        ("copper tubing 1/2 inch", "CU"),
        ("tamba pipe 15mm", "CU"),
    ]:
        spec, _, _ = extract_specifications(text)
        assert spec.get("material") == expected, f"Failed for '{text}'"

def test_spec_conflict_detection():
    # Multiple materials in same line
    spec, _, issues = extract_specifications("GI Pipe 25mm MS")
    assert "material" not in spec
    assert any(i.code == "SPEC_CONFLICT_IN_REQUEST" for i in issues)

    # Multiple classes in same line
    spec, _, issues = extract_specifications("GI Pipe 25mm Class A Class B")
    assert "class" not in spec
    assert any(i.code == "SPEC_CONFLICT_IN_REQUEST" for i in issues)

    # Multiple sizes in same line
    spec, _, issues = extract_specifications("GI Pipe 25mm 50mm Class B")
    assert "size_mm" not in spec
    assert any(i.code == "SPEC_CONFLICT_IN_REQUEST" for i in issues)

# 4. STOP WORDS AND ALIASES
def test_stop_words_removed():
    res = normalize_line("supply of the item and make with quality GI Pipe 25mm Class B 10 mtr")
    # Stop words: of, the, and, with, for, type, make, quality, item, supply
    for sw in ["of", "the", "and", "with", "make", "quality", "item", "supply"]:
        assert sw not in res.tokens
    assert "pipe" in res.tokens

def test_transliterations_applied():
    res = normalize_line("pital valv 25mm 5 nos")
    assert "valve" in res.tokens
    assert "material:BRASS" in res.tokens

    res = normalize_line("kohni 25mm Class B 10 nos")
    assert "elbow" in res.tokens

# 5. PRESERVATION OF RAW INPUT (P0 N2)
def test_raw_input_preserved():
    raw = "  GI Pipe 25mm Class B  10 mtr  "
    res = normalize_line(raw)
    assert res.description_raw == raw.strip()

# 6. IDEMPOTENCY OF NORMALIZATION (P1 N5)
def test_normalization_idempotency():
    raw_lines = [
        "MS Hex Bolt M12x50 Grade 4.6 100 nos",
        "GI Pipe 25mm Class B 10 mtr",
        "pital valv 25mm 5 nos",
        "GI Socket Coupling 20mm Class B 50",
    ]
    for raw in raw_lines:
        res1 = normalize_line(raw)
        desc1 = res1.description_normalized
        # Re-normalizing an already normalized description is idempotent
        res2 = normalize_line(desc1)
        assert res2.description_normalized == desc1
