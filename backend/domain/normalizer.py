"""
Deterministic normalizer and structured extraction engine.
Conforms to PRD Section E Workflow 3 and PRD_DECISIONS.md.
"""
import re
import unicodedata
from decimal import Decimal, InvalidOperation
from typing import Dict, List, Optional, Set, Tuple, Any

from domain.types import NormalizedLine, Issue, IngestedLine
from domain.units import (
    normalize_unit,
    get_dimension,
    is_count_unit,
    COUNT_UNITS,
    UNIT_ALIASES,
)
from domain.split import split_raw_line

# Devanagari to ASCII translation
DEV_DIGITS = str.maketrans("०१२३४५६७८९", "0123456789")

# Accepted quantity patterns:
# 123, 12.5, 1,000, 1,00,000, 10,00,000
# Reject: comma decimals (1,5), scientific notation (1e3), more than 3 decimals
PLAIN_NUMBER_RE = re.compile(r"^\d+(?:\.\d{1,3})?$")
INTL_GROUPED_RE = re.compile(r"^\d{1,3}(?:,\d{3})+(?:\.\d{1,3})?$")
INDIAN_GROUPED_RE = re.compile(r"^\d{1,2}(?:,\d{2})*,\d{3}(?:\.\d{1,3})?$")

# Stop words per PRD Section E line 150
STOP_WORDS: Set[str] = {
    "of", "the", "and", "with", "for", "type", "make", "quality", "item", "supply"
}

# Product-term transliterations per data/aliases.json
PRODUCT_TERM_ALIASES: Dict[str, str] = {
    "paip": "pipe", "पाइप": "pipe",
    "bolt": "bolt", "बोल्ट": "bolt",
    "nat": "nut", "नट": "nut",
    "valv": "valve", "वाल्व": "valve",
    "kohni": "elbow", "कोहनी": "elbow",
    "pital": "brass", "पीतल": "brass",
    "tamba": "copper", "तांबा": "copper",
    "dasta": "gi", "जस्ता": "gi",
}

UNICODE_FRACTIONS = {
    "½": Decimal("0.5"),
    "¼": Decimal("0.25"),
    "¾": Decimal("0.75"),
}

def clean_text_nfkc(text: str) -> str:
    """Normalize unicode NFKC, translate devanagari digits, and collapse whitespace."""
    if not text:
        return ""
    normalized = unicodedata.normalize("NFKC", text)
    translated = normalized.translate(DEV_DIGITS)
    return " ".join(translated.split())

def parse_quantity(
    qty_str: Optional[str], canonical_unit: Optional[str]
) -> Tuple[Optional[Decimal], List[Issue]]:
    """
    Parse and validate quantity string per PRD Section E Workflow 3.
    Returns (Decimal quantity or None, list of issues).
    """
    issues: List[Issue] = []
    if not qty_str:
        issues.append(Issue(
            code="MISSING_QUANTITY",
            severity="blocking",
            detail="Quantity is missing or could not be parsed."
        ))
        return None, issues

    raw_clean = qty_str.strip().translate(DEV_DIGITS)

    # Check accepted grouping patterns
    is_valid_format = (
        bool(PLAIN_NUMBER_RE.match(raw_clean))
        or bool(INTL_GROUPED_RE.match(raw_clean))
        or bool(INDIAN_GROUPED_RE.match(raw_clean))
    )

    if not is_valid_format:
        issues.append(Issue(
            code="INVALID_QUANTITY",
            severity="blocking",
            detail=f"Quantity format invalid: '{qty_str}'"
        ))
        return None, issues

    # Strip commas for Decimal construction
    plain_num_str = raw_clean.replace(",", "")
    try:
        val = Decimal(plain_num_str)
    except InvalidOperation:
        issues.append(Issue(
            code="INVALID_QUANTITY",
            severity="blocking",
            detail=f"Quantity unparseable: '{qty_str}'"
        ))
        return None, issues

    # Range checks
    if val <= Decimal("0"):
        issues.append(Issue(
            code="INVALID_QUANTITY",
            severity="blocking",
            detail=f"Quantity must be positive: {val}"
        ))
        return None, issues

    if val > Decimal("1000000"):
        issues.append(Issue(
            code="INVALID_QUANTITY",
            severity="blocking",
            detail=f"Quantity exceeds maximum allowable limit of 1,000,000: {val}"
        ))
        return None, issues

    # Max 3 decimal places
    exp = val.as_tuple().exponent
    if isinstance(exp, int) and exp < -3:
        issues.append(Issue(
            code="INVALID_QUANTITY",
            severity="blocking",
            detail=f"Quantity precision exceeds 3 decimal places: {val}"
        ))
        return None, issues

    # Check discrete count units: nos, set, pair, box, roll, bag require integers
    if canonical_unit and is_count_unit(canonical_unit):
        if val % Decimal("1") != Decimal("0"):
            issues.append(Issue(
                code="FRACTIONAL_COUNT",
                severity="blocking",
                detail=f"Count unit '{canonical_unit}' requires integer quantity; received {val}"
            ))

    return val, issues

def format_decimal_str(d: Decimal) -> str:
    """Format decimal without trailing unnecessary zeros (e.g. 25.0 -> 25, 25.40 -> 25.4)."""
    s = f"{d:f}"
    if "." in s:
        s = s.rstrip("0").rstrip(".")
    return s

def extract_specifications(text: str) -> Tuple[Dict[str, str], List[Tuple[int, int]], List[Issue]]:
    """
    Extract technical specifications from text:
    size_mm, length_mm, thread, material, class, grade.
    Returns:
    - spec: Dict[str, str]
    - matched_spans: List of (start, end) character spans to remove from description text
    - issues: List[Issue] (e.g. SPEC_CONFLICT_IN_REQUEST)
    """
    spec: Dict[str, str] = {}
    matched_spans: List[Tuple[int, int]] = []
    issues: List[Issue] = []

    lower = text.lower()
    is_washer_context = bool(re.search(r"\b(?:washer|वारशल|flat\s+washer)\b", lower))

    # 1. MATERIAL
    # Candidates: GI, MS, SS304, SS316, PVC, BRASS, CU
    mat_matches = []
    # SS316
    for m in re.finditer(r"\b(?:ss\s*316|stainless\s+steel\s+316)\b", lower):
        mat_matches.append(("SS316", m.span()))
    # SS304
    for m in re.finditer(r"\b(?:ss\s*304|stainless\s+steel\s+304|stainless\s+steel)\b", lower):
        mat_matches.append(("SS304", m.span()))
    # GI
    for m in re.finditer(r"\b(?:gi|galvanized|galvanised|dasta|जस्ता)\b", lower):
        mat_matches.append(("GI", m.span()))
    # MS
    for m in re.finditer(r"\b(?:ms|mild\s+steel|loha|लोहा|iron)\b", lower):
        mat_matches.append(("MS", m.span()))
    # PVC
    for m in re.finditer(r"\b(?:pvc)\b", lower):
        mat_matches.append(("PVC", m.span()))
    # BRASS
    for m in re.finditer(r"\b(?:brass|pital|पीतल)\b", lower):
        mat_matches.append(("BRASS", m.span()))
    # CU
    for m in re.finditer(r"\b(?:cu|copper|tamba|तांबा)\b", lower):
        mat_matches.append(("CU", m.span()))

    # Deduplicate overlapping spans
    distinct_materials = set(val for val, _ in mat_matches)
    if len(distinct_materials) == 1:
        spec["material"] = mat_matches[0][0]
        matched_spans.extend(span for _, span in mat_matches)
    elif len(distinct_materials) > 1:
        issues.append(Issue(
            code="SPEC_CONFLICT_IN_REQUEST",
            severity="blocking",
            detail=f"Conflicting material specifications: {sorted(list(distinct_materials))}"
        ))

    # 2. CLASS: A, B, C
    class_matches = []
    for m in re.finditer(r"\bclass[-\s]*([abc])\b", lower):
        class_matches.append((m.group(1).upper(), m.span()))

    distinct_classes = set(val for val, _ in class_matches)
    if len(distinct_classes) == 1:
        spec["class"] = class_matches[0][0]
        matched_spans.extend(span for _, span in class_matches)
    elif len(distinct_classes) > 1:
        issues.append(Issue(
            code="SPEC_CONFLICT_IN_REQUEST",
            severity="blocking",
            detail=f"Conflicting class specifications: {sorted(list(distinct_classes))}"
        ))

    # 3. GRADE: 4.6, 8.8, 10.9
    grade_matches = []
    for m in re.finditer(r"\b(?:grade|gr)[-\s]*(4\.6|8\.8|10\.9)\b", lower):
        grade_matches.append((m.group(1), m.span()))
    if not grade_matches:
        # Standalone grade digits in fastener context
        for m in re.finditer(r"\b(4\.6|8\.8|10\.9)\b", lower):
            grade_matches.append((m.group(1), m.span()))

    distinct_grades = set(val for val, _ in grade_matches)
    if len(distinct_grades) == 1:
        spec["grade"] = grade_matches[0][0]
        matched_spans.extend(span for _, span in grade_matches)
    elif len(distinct_grades) > 1:
        issues.append(Issue(
            code="SPEC_CONFLICT_IN_REQUEST",
            severity="blocking",
            detail=f"Conflicting grade specifications: {sorted(list(distinct_grades))}"
        ))

    # 4. FASTENER THREAD & LENGTH
    # e.g. M12x50, M12 x 50, M16*60, M12
    # If washer context, M12 is size_mm: "12"
    length_matches = []
    thread_matches = []

    # Combined thread and length: M12x50, M12 x 50 mm
    for m in re.finditer(r"\b[m](\d{1,2})\s*[x×*]\s*(\d+(?:\.\d+)?)(?:\s*mm)?\b", lower):
        t_val = f"M{m.group(1)}"
        l_val = format_decimal_str(Decimal(m.group(2)))
        thread_matches.append((t_val, m.span()))
        length_matches.append((l_val, m.span()))

    # Standalone M<d>
    if not thread_matches:
        for m in re.finditer(r"\b[m](\d{1,2})\b", lower):
            d_val = m.group(1)
            if is_washer_context:
                spec["size_mm"] = d_val
                matched_spans.append(m.span())
            else:
                thread_matches.append((f"M{d_val}", m.span()))

    distinct_threads = set(val for val, _ in thread_matches)
    if len(distinct_threads) == 1:
        spec["thread"] = thread_matches[0][0]
        matched_spans.extend(span for _, span in thread_matches)
    elif len(distinct_threads) > 1:
        issues.append(Issue(
            code="SPEC_CONFLICT_IN_REQUEST",
            severity="blocking",
            detail=f"Conflicting thread specifications: {sorted(list(distinct_threads))}"
        ))

    distinct_lengths = set(val for val, _ in length_matches)
    if len(distinct_lengths) == 1:
        spec["length_mm"] = length_matches[0][0]
        matched_spans.extend(span for _, span in length_matches)
    elif len(distinct_lengths) > 1:
        issues.append(Issue(
            code="SPEC_CONFLICT_IN_REQUEST",
            severity="blocking",
            detail=f"Conflicting length specifications: {sorted(list(distinct_lengths))}"
        ))

    # 5. SIZE MM (pipes, fittings, valves, consumables)
    # Skip if washer already extracted size_mm
    size_matches = []
    if "size_mm" not in spec:
        # Inch mixed fraction: 1 1/2", 1 1/2 inch
        for m in re.finditer(r"\b(\d+)\s+([1-9]\d*)\s*/\s*([1-9]\d*)\s*(?:(?:inch|inches|in)\b|\")?", lower):
            w = Decimal(m.group(1))
            a = Decimal(m.group(2))
            b = Decimal(m.group(3))
            mm_val = (w + (a / b)) * Decimal("25.4")
            size_matches.append((format_decimal_str(mm_val), m.span()))

        # Inch simple fraction: 1/2", 1/2 inch, 3/4 in
        for m in re.finditer(r"\b([1-9]\d*)\s*/\s*([1-9]\d*)\s*(?:(?:inch|inches|in)\b|\")?", lower):
            # Check not already part of a mixed fraction
            if not any(s[0] <= m.start() and m.end() <= s[1] for _, s in size_matches):
                a = Decimal(m.group(1))
                b = Decimal(m.group(2))
                mm_val = (a / b) * Decimal("25.4")
                size_matches.append((format_decimal_str(mm_val), m.span()))

        # Unicode fractions: 1½", ½", ¼", ¾"
        for m in re.finditer(r"(?:(\d+)\s*)?([½¼¾])\s*(?:inch|inches|in|\")?", text):
            w = Decimal(m.group(1)) if m.group(1) else Decimal("0")
            frac = UNICODE_FRACTIONS[m.group(2)]
            mm_val = (w + frac) * Decimal("25.4")
            size_matches.append((format_decimal_str(mm_val), m.span()))

        # Integer / decimal inch: 1 inch, 2", 1.5 in
        for m in re.finditer(r"\b(\d+(?:\.\d+)?)\s*(?:(?:inch|inches|in)\b|\")", lower):
            if not any(s[0] <= m.start() and m.end() <= s[1] for _, s in size_matches):
                val = Decimal(m.group(1)) * Decimal("25.4")
                size_matches.append((format_decimal_str(val), m.span()))

        # Metric cm: 2.5 cm -> 25 mm
        for m in re.finditer(r"\b(\d+(?:\.\d+)?)\s*cm\b", lower):
            val = Decimal(m.group(1)) * Decimal("10")
            size_matches.append((format_decimal_str(val), m.span()))

        # Metric mm: 25mm, 25 mm, 3.15 mm
        for m in re.finditer(r"\b(\d+(?:\.\d+)?)\s*mm\b", lower):
            # Check not part of length_mm (e.g. M12x50mm)
            if not any(s[0] <= m.start() and m.end() <= s[1] for s in matched_spans):
                val = Decimal(m.group(1))
                size_matches.append((format_decimal_str(val), m.span()))

        distinct_sizes = set(val for val, _ in size_matches)
        if len(distinct_sizes) == 1:
            spec["size_mm"] = size_matches[0][0]
            matched_spans.extend(span for _, span in size_matches)
        elif len(distinct_sizes) > 1:
            issues.append(Issue(
                code="SPEC_CONFLICT_IN_REQUEST",
                severity="blocking",
                detail=f"Conflicting size specifications: {sorted(list(distinct_sizes))}"
            ))

    return spec, matched_spans, issues

def build_normalized_description_and_tokens(
    text: str,
    spec: Dict[str, str],
    spec_spans: List[Tuple[int, int]]
) -> Tuple[str, List[str]]:
    """
    Remove spec spans, apply aliases, strip punctuation & stop words.
    Return (description_normalized, sorted_unique_tokens).
    """
    # 1. Mask out matched spec spans with spaces
    chars = list(text)
    for start, end in spec_spans:
        for idx in range(max(0, start), min(len(chars), end)):
            chars[idx] = " "
    masked_text = "".join(chars).lower()

    # 2. Replace punctuation with space (keep alphanumerics and devanagari)
    cleaned = re.sub(r"[^\w\s]", " ", masked_text)

    # 3. Tokenize words
    raw_words = cleaned.split()

    # 4. Apply transliteration aliases and remove stop words
    filtered_words: List[str] = []
    for w in raw_words:
        # check transliteration alias
        aliased = PRODUCT_TERM_ALIASES.get(w, w)
        if aliased in STOP_WORDS:
            continue
        filtered_words.append(aliased)

    description_normalized = " ".join(filtered_words)

    # 5. Build token set: description words + spec tokens
    token_set: Set[str] = set(filtered_words)

    if "material" in spec:
        token_set.add(f"material:{spec['material']}")
    if "class" in spec:
        token_set.add(f"class:{spec['class']}")
    if "grade" in spec:
        token_set.add(f"grade:{spec['grade']}")
    if "thread" in spec:
        token_set.add(f"thread:{spec['thread']}")
    if "length_mm" in spec:
        token_set.add(f"length:{spec['length_mm']}")
    if "size_mm" in spec:
        token_set.add(f"size:{spec['size_mm']}")

    sorted_tokens = sorted(list(token_set))
    return description_normalized, sorted_tokens

def normalize_line(
    raw_input: str,
    quantity_input: Optional[str] = None,
    unit_input: Optional[str] = None
) -> NormalizedLine:
    """
    Complete deterministic line item normalization conforming to PRD Section E Workflow 3.
    Accepts raw_input string (free-text or delimited) or pre-split fields.
    """
    issues: List[Issue] = []

    # 1. Clean input
    trimmed_input = raw_input.strip()

    # 2. Ingestion split (if quantity/unit not explicitly passed)
    if quantity_input is None and unit_input is None:
        ingested = split_raw_line(trimmed_input, set(UNIT_ALIASES.keys()))
        desc_raw = ingested.description_raw
        raw_qty = ingested.quantity_raw
        raw_unit = ingested.unit_raw
    else:
        desc_raw = trimmed_input
        raw_qty = quantity_input
        raw_unit = unit_input

    # 3. Unit normalization
    canonical_unit = None
    unit_dim = None
    if raw_unit is not None:
        raw_unit_str = str(raw_unit).strip()
        if raw_unit_str:
            canonical_unit = normalize_unit(raw_unit_str)
            if canonical_unit is None:
                issues.append(Issue(
                    code="UNKNOWN_UNIT",
                    severity="blocking",
                    detail=f"Unrecognized unit token: '{raw_unit_str}'"
                ))
            else:
                unit_dim = get_dimension(canonical_unit)

    # 4. Quantity parsing
    quantity_val, qty_issues = parse_quantity(raw_qty, canonical_unit)
    issues.extend(qty_issues)

    # Check missing unit when quantity exists
    if quantity_val is not None and canonical_unit is None and not any(i.code == "UNKNOWN_UNIT" for i in issues):
        issues.append(Issue(
            code="MISSING_UNIT",
            severity="blocking",
            detail="Quantity specified without a valid unit."
        ))

    # 5. Extract specifications from description
    spec, spec_spans, spec_issues = extract_specifications(desc_raw)
    issues.extend(spec_issues)

    # 6. Build normalized description and tokens
    desc_norm, tokens = build_normalized_description_and_tokens(desc_raw, spec, spec_spans)

    return NormalizedLine(
        description_raw=trimmed_input,
        description_normalized=desc_norm,
        tokens=tokens,
        spec=spec,
        quantity=quantity_val,
        unit=canonical_unit,
        unit_dimension=unit_dim,
        issues=issues
    )
