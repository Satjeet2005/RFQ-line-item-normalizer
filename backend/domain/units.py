"""
Unit normalization, dimension lookup, and exact same-dimension conversions.
Conforms to PRD Section E Workflow 3 and PRD_DECISIONS.md D11.
"""
import unicodedata
from decimal import Decimal, ROUND_HALF_EVEN
from typing import Optional, Tuple, Dict, Set

# Dimensions and canonical units
UNIT_DIMENSIONS: Dict[str, str] = {
    # count
    "nos": "count",
    "set": "count",
    "pair": "count",
    "box": "count",
    "roll": "count",
    "bag": "count",
    # length
    "mtr": "length",
    "ft": "length",
    # mass
    "kg": "mass",
    "g": "mass",
    # volume
    "ltr": "volume",
    "ml": "volume",
}

COUNT_UNITS: Set[str] = {"nos", "set", "pair", "box", "roll", "bag"}

# Default alias mapping (mirrors data/aliases.json)
UNIT_ALIASES: Dict[str, str] = {
    # nos
    "nos": "nos", "no": "nos", "nr": "nos", "pc": "nos", "pcs": "nos",
    "piece": "nos", "pieces": "nos", "unit": "nos", "units": "nos",
    "nag": "nos", "नग": "nos",
    # set
    "set": "set", "sets": "set",
    # pair
    "pair": "pair", "pairs": "pair",
    # box
    "box": "box", "boxes": "box",
    # roll
    "roll": "roll", "rolls": "roll",
    # bag
    "bag": "bag", "bags": "bag",
    # mtr
    "m": "mtr", "mtr": "mtr", "mtrs": "mtr", "meter": "mtr",
    "meters": "mtr", "metre": "mtr", "metres": "mtr",
    "meetar": "mtr", "मीटर": "mtr",
    # ft
    "ft": "ft", "feet": "ft", "foot": "ft", "fut": "ft", "फुट": "ft",
    # kg
    "kg": "kg", "kgs": "kg", "kilo": "kg", "kilos": "kg",
    "kilogram": "kg", "kilograms": "kg", "किलो": "kg",
    # g
    "g": "g", "gm": "g", "gms": "g", "gram": "g", "grams": "g",
    # ltr
    "l": "ltr", "lt": "ltr", "ltr": "ltr", "ltrs": "ltr",
    "liter": "ltr", "liters": "ltr", "litre": "ltr", "litres": "ltr", "लीटर": "ltr",
    # ml
    "ml": "ml", "mls": "ml", "millilitre": "ml", "milliliter": "ml",
}

CONVERSION_FACTORS = {
    ("ft", "mtr"): Decimal("0.3048"),
    ("g", "kg"): Decimal("0.001"),
    ("ml", "ltr"): Decimal("0.001"),
}

def normalize_unit(raw_unit: Optional[str]) -> Optional[str]:
    """Normalize raw unit token using unicode NFKC, stripping punctuation and checking aliases."""
    if not raw_unit:
        return None
    cleaned = unicodedata.normalize("NFKC", str(raw_unit)).strip().lower().rstrip(".")
    return UNIT_ALIASES.get(cleaned)

def get_dimension(unit: Optional[str]) -> Optional[str]:
    """Return physical dimension of canonical unit code."""
    if not unit:
        return None
    return UNIT_DIMENSIONS.get(unit)

def is_count_unit(unit: Optional[str]) -> bool:
    """Return True if unit is a discrete count unit."""
    return unit in COUNT_UNITS

def convert_quantity(qty: Decimal, from_unit: str, to_unit: str) -> Optional[Decimal]:
    """
    Perform exact same-dimension conversion between compatible units.
    Quantized to 6 decimal places with ROUND_HALF_EVEN.
    Count units never convert to each other.
    """
    if from_unit == to_unit:
        return qty

    dim_from = get_dimension(from_unit)
    dim_to = get_dimension(to_unit)
    if not dim_from or not dim_to or dim_from != dim_to:
        return None

    # Count units never convert to each other
    if dim_from == "count":
        return None

    factor = CONVERSION_FACTORS.get((from_unit, to_unit))
    if factor is not None:
        converted = qty * factor
        return converted.quantize(Decimal("0.000001"), rounding=ROUND_HALF_EVEN)

    # Reverse direction
    reverse_factor = CONVERSION_FACTORS.get((to_unit, from_unit))
    if reverse_factor is not None:
        converted = qty / reverse_factor
        return converted.quantize(Decimal("0.000001"), rounding=ROUND_HALF_EVEN)

    return None

def check_unit_compatibility(req_unit: Optional[str], cat_uom: str) -> Tuple[bool, Optional[str]]:
    """
    Check compatibility between requested canonical unit and candidate catalog UOM.
    Returns: (is_compatible, flag)
    - req_unit is None -> (False, "MISSING_UNIT")
    - Identical canonical units -> (True, None)
    - Convertible same-dimension units -> (True, "UNIT_CONVERTIBLE")
    - Incompatible dimension or distinct count units -> (False, "UNIT_INCOMPATIBLE")
    """
    if not req_unit:
        return False, "MISSING_UNIT"

    if req_unit == cat_uom:
        return True, None

    dim_req = get_dimension(req_unit)
    dim_cat = get_dimension(cat_uom)

    if not dim_req or not dim_cat or dim_req != dim_cat:
        return False, "UNIT_INCOMPATIBLE"

    if dim_req == "count":
        # Distinct count units are never interchangeable
        return False, "UNIT_INCOMPATIBLE"

    # Same dimension (length, mass, volume)
    return True, "UNIT_CONVERTIBLE"
