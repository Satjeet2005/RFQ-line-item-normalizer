"""
Ingestion line splitting logic for free-text and delimited inputs.
Implements Section E Workflows 1 & 3 trailing quantity rules.
"""
import re
from typing import Set, Tuple, Optional
from domain.types import IngestedLine

# Pattern for valid quantity numbers:
# 123, 12.5, 1,000, 1,00,000, Devanagari digits ०-९
DEV_DIGITS = str.maketrans("०१२३४५६७८९", "0123456789")
NUMBER_RE = re.compile(r"^\d+(?:,\d{2,3})*(?:\.\d+)?$")

def is_valid_qty_token(token: str) -> bool:
    # translate devanagari digits if present
    t = token.translate(DEV_DIGITS)
    return bool(NUMBER_RE.match(t))

def split_raw_line(line: str, known_unit_aliases: Set[str]) -> IngestedLine:
    raw_input = line.strip()
    if not raw_input:
        return IngestedLine(raw_input="", description_raw="")

    # Delimited check: '|' or '\t'
    if "|" in raw_input or "\t" in raw_input:
        delim = "|" if "|" in raw_input else "\t"
        parts = [p.strip() for p in raw_input.split(delim)]
        desc = parts[0]
        qty = parts[1] if len(parts) > 1 and parts[1] else None
        unit = parts[2] if len(parts) > 2 and parts[2] else None
        return IngestedLine(
            raw_input=raw_input,
            description_raw=desc,
            quantity_raw=qty,
            unit_raw=unit
        )

    # Free-text line trailing rules
    tokens = raw_input.split()
    if not tokens:
        return IngestedLine(raw_input=raw_input, description_raw=raw_input)

    # Check rule 1 & rule 5: <number> <unit-alias>
    if len(tokens) >= 2:
        last_tok = tokens[-1].lower().rstrip(".")
        penult_tok = tokens[-2]

        if is_valid_qty_token(penult_tok) and last_tok in known_unit_aliases:
            # Rule 1 match
            desc = " ".join(tokens[:-2])
            return IngestedLine(
                raw_input=raw_input,
                description_raw=desc,
                quantity_raw=penult_tok,
                unit_raw=tokens[-1]
            )

    # Check rule 3 & rule 2: <number> at end
    last_tok = tokens[-1]
    if is_valid_qty_token(last_tok):
        if len(tokens) >= 2 and tokens[-2].lower() in ("x", "×"):
            # Rule 3: dimension, not a quantity
            return IngestedLine(
                raw_input=raw_input,
                description_raw=raw_input,
                quantity_raw=None,
                unit_raw=None
            )
        # Rule 2: quantity at end, no unit
        desc = " ".join(tokens[:-1])
        return IngestedLine(
            raw_input=raw_input,
            description_raw=desc,
            quantity_raw=last_tok,
            unit_raw=None
        )

    # Rule 4 / Rule 5 fallback: entire line is description
    return IngestedLine(
        raw_input=raw_input,
        description_raw=raw_input,
        quantity_raw=None,
        unit_raw=None
    )
