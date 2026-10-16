"""
Tests for unit normalization, dimensions, and conversions.
Conforms to PRD Section E Workflow 3 and PRD_DECISIONS.md D11.
"""
from decimal import Decimal
import pytest

from domain.units import (
    normalize_unit,
    get_dimension,
    is_count_unit,
    convert_quantity,
    check_unit_compatibility,
    UNIT_DIMENSIONS,
    COUNT_UNITS,
)

def test_all_canonical_units_have_dimensions():
    expected_units = {
        "nos", "set", "pair", "box", "roll", "bag",
        "mtr", "ft", "kg", "g", "ltr", "ml"
    }
    assert set(UNIT_DIMENSIONS.keys()) == expected_units
    for u in expected_units:
        assert get_dimension(u) in ("count", "length", "mass", "volume")

@pytest.mark.parametrize("raw,expected", [
    # nos
    ("nos", "nos"), ("no", "nos"), ("pc", "nos"), ("pcs", "nos"),
    ("piece", "nos"), ("pieces", "nos"), ("unit", "nos"), ("nag", "nos"), ("नग", "nos"),
    # set
    ("set", "set"), ("sets", "set"),
    # pair
    ("pair", "pair"), ("pairs", "pair"),
    # box
    ("box", "box"), ("boxes", "box"),
    # roll
    ("roll", "roll"), ("rolls", "roll"),
    # bag
    ("bag", "bag"), ("bags", "bag"),
    # mtr
    ("m", "mtr"), ("mtr", "mtr"), ("mtrs", "mtr"), ("meter", "mtr"),
    ("meters", "mtr"), ("metre", "mtr"), ("metres", "mtr"), ("मीटर", "mtr"),
    # ft
    ("ft", "ft"), ("feet", "ft"), ("foot", "ft"), ("fut", "ft"), ("फुट", "ft"),
    # kg
    ("kg", "kg"), ("kgs", "kg"), ("kilo", "kg"), ("kilogram", "kg"), ("किलो", "kg"),
    # g
    ("g", "g"), ("gm", "g"), ("gms", "g"), ("gram", "g"), ("grams", "g"),
    # ltr
    ("l", "ltr"), ("lt", "ltr"), ("ltr", "ltr"), ("ltrs", "ltr"),
    ("liter", "ltr"), ("litre", "ltr"), ("लीटर", "ltr"),
    # ml
    ("ml", "ml"), ("mls", "ml"), ("millilitre", "ml"), ("milliliter", "ml"),
    # trailing dot
    ("nos.", "nos"), ("pcs.", "nos"), ("mtr.", "mtr"), ("kg.", "kg"),
    # case and whitespace
    ("  PCS  ", "nos"), ("MTR", "mtr"), ("Kg", "kg"),
])
def test_unit_alias_normalization(raw, expected):
    assert normalize_unit(raw) == expected

def test_unknown_unit_returns_none():
    assert normalize_unit("bundles") is None
    assert normalize_unit("carton") is None
    assert normalize_unit("unknown_xyz") is None
    assert normalize_unit(None) is None
    assert normalize_unit("") is None

def test_exact_conversions_same_dimension():
    # 1 ft = 0.3048 mtr
    res = convert_quantity(Decimal("100"), "ft", "mtr")
    assert res == Decimal("30.480000")

    # 1 g = 0.001 kg
    res = convert_quantity(Decimal("500"), "g", "kg")
    assert res == Decimal("0.500000")

    # 1 ml = 0.001 ltr
    res = convert_quantity(Decimal("250"), "ml", "ltr")
    assert res == Decimal("0.250000")

    # Identity conversion
    res = convert_quantity(Decimal("42.5"), "mtr", "mtr")
    assert res == Decimal("42.5")

def test_count_units_never_convert():
    for u1 in COUNT_UNITS:
        for u2 in COUNT_UNITS:
            if u1 != u2:
                assert convert_quantity(Decimal("10"), u1, u2) is None

def test_incompatible_dimensions_never_convert():
    assert convert_quantity(Decimal("10"), "kg", "mtr") is None
    assert convert_quantity(Decimal("10"), "ltr", "nos") is None
    assert convert_quantity(Decimal("10"), "ft", "kg") is None

def test_check_unit_compatibility():
    # Identical
    compat, flag = check_unit_compatibility("mtr", "mtr")
    assert compat is True and flag is None

    # Convertible same dimension
    compat, flag = check_unit_compatibility("ft", "mtr")
    assert compat is True and flag == "UNIT_CONVERTIBLE"

    compat, flag = check_unit_compatibility("g", "kg")
    assert compat is True and flag == "UNIT_CONVERTIBLE"

    # Incompatible dimension
    compat, flag = check_unit_compatibility("kg", "mtr")
    assert compat is False and flag == "UNIT_INCOMPATIBLE"

    # Distinct count units
    compat, flag = check_unit_compatibility("box", "nos")
    assert compat is False and flag == "UNIT_INCOMPATIBLE"

    # Missing unit
    compat, flag = check_unit_compatibility(None, "nos")
    assert compat is False and flag == "MISSING_UNIT"
