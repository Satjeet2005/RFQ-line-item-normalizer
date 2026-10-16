"""
Generator for evaluation datasets:
- eval/dataset/v1/cases.jsonl (40 cases)
- eval/dev/cases.jsonl (12 dev cases)
"""
import json
from pathlib import Path

FROZEN_CASES = [
    # 1. Exact/clean match (5 cases -> match)
    {
        "id": "E-001",
        "category": "exact_clean_match",
        "input": "GI Pipe 25mm Class B 10 mtr",
        "expected_outcome": "match",
        "expected_sku": "PIPE-004",
        "expected_normalized": {
            "quantity": "10",
            "unit": "mtr",
            "spec": {"size_mm": "25", "class": "B", "material": "GI"},
            "issue_codes": []
        },
        "rationale": "Exact match to PIPE-004 (GI Pipe 25mm Class B). Clean input with quantity 10 and canonical unit mtr.",
        "label_pass": {
            "labelled_by": "initial_reviewer",
            "created_at": "2026-10-16T15:10:00Z",
            "second_pass_done": False
        }
    },
    {
        "id": "E-002",
        "category": "exact_clean_match",
        "input": "MS Hex Bolt M12x50 Grade 4.6 100 nos",
        "expected_outcome": "match",
        "expected_sku": "BOLT-007",
        "expected_normalized": {
            "quantity": "100",
            "unit": "nos",
            "spec": {"thread": "M12", "length_mm": "50", "grade": "4.6", "material": "MS"},
            "issue_codes": []
        },
        "rationale": "Exact match to BOLT-007 (MS Hex Bolt M12x50 Grade 4.6). Fully specified fastener dimensions and grade.",
        "label_pass": {
            "labelled_by": "initial_reviewer",
            "created_at": "2026-10-16T15:10:00Z",
            "second_pass_done": False
        }
    },
    {
        "id": "E-003",
        "category": "exact_clean_match",
        "input": "PVC Pipe 32mm Class A 50 mtr",
        "expected_outcome": "match",
        "expected_sku": "PIPE-021",
        "expected_normalized": {
            "quantity": "50",
            "unit": "mtr",
            "spec": {"size_mm": "32", "class": "A", "material": "PVC"},
            "issue_codes": []
        },
        "rationale": "Exact match to PIPE-021 (PVC Pipe 32mm Class A).",
        "label_pass": {
            "labelled_by": "initial_reviewer",
            "created_at": "2026-10-16T15:10:00Z",
            "second_pass_done": False
        }
    },
    {
        "id": "E-004",
        "category": "exact_clean_match",
        "input": "Brass Ball Valve Screwed 25mm 5 nos",
        "expected_outcome": "match",
        "expected_sku": "VALV-003",
        "expected_normalized": {
            "quantity": "5",
            "unit": "nos",
            "spec": {"size_mm": "25", "material": "BRASS"},
            "issue_codes": []
        },
        "rationale": "Exact match to VALV-003 (Brass Ball Valve Screwed 25mm).",
        "label_pass": {
            "labelled_by": "initial_reviewer",
            "created_at": "2026-10-16T15:10:00Z",
            "second_pass_done": False
        }
    },
    {
        "id": "E-005",
        "category": "exact_clean_match",
        "input": "GI 90 Degree Elbow 20mm Class B 20 nos",
        "expected_outcome": "match",
        "expected_sku": "FITT-002",
        "expected_normalized": {
            "quantity": "20",
            "unit": "nos",
            "spec": {"size_mm": "20", "class": "B", "material": "GI"},
            "issue_codes": []
        },
        "rationale": "Exact match to FITT-002 (GI 90 Degree Elbow 20mm Class B).",
        "label_pass": {
            "labelled_by": "initial_reviewer",
            "created_at": "2026-10-16T15:10:00Z",
            "second_pass_done": False
        }
    },

    # 2. Harmless variation (case, punctuation, abbreviations) (5 cases -> match)
    {
        "id": "E-006",
        "category": "harmless_variation",
        "input": "gi pipe, 15 mm, class-a, 12 mtr",
        "expected_outcome": "match",
        "expected_sku": "PIPE-001",
        "expected_normalized": {
            "quantity": "12",
            "unit": "mtr",
            "spec": {"size_mm": "15", "class": "A", "material": "GI"},
            "issue_codes": []
        },
        "rationale": "Punctuation and case variation of PIPE-001 (GI Pipe 15mm Class A).",
        "label_pass": {
            "labelled_by": "initial_reviewer",
            "created_at": "2026-10-16T15:10:00Z",
            "second_pass_done": False
        }
    },
    {
        "id": "E-007",
        "category": "harmless_variation",
        "input": "MILD STEEL HEX BOLT M16 X 60 MM GR 8.8 50 PCS",
        "expected_outcome": "match",
        "expected_sku": "BOLT-018",
        "expected_normalized": {
            "quantity": "50",
            "unit": "nos",
            "spec": {"thread": "M16", "length_mm": "60", "grade": "8.8", "material": "MS"},
            "issue_codes": []
        },
        "rationale": "Uppercase, 'MILD STEEL' expanded form of MS, 'GR' for Grade, 'PCS' for nos. Matches BOLT-018.",
        "label_pass": {
            "labelled_by": "initial_reviewer",
            "created_at": "2026-10-16T15:10:00Z",
            "second_pass_done": False
        }
    },
    {
        "id": "E-008",
        "category": "harmless_variation",
        "input": "SS 304 Bolt M10*40 25 nos",
        "expected_outcome": "match",
        "expected_sku": "BOLT-023",
        "expected_normalized": {
            "quantity": "25",
            "unit": "nos",
            "spec": {"thread": "M10", "length_mm": "40", "material": "SS304"},
            "issue_codes": []
        },
        "rationale": "Space in 'SS 304' and asterisk delimiter 'M10*40' resolves cleanly to BOLT-023.",
        "label_pass": {
            "labelled_by": "initial_reviewer",
            "created_at": "2026-10-16T15:10:00Z",
            "second_pass_done": False
        }
    },
    {
        "id": "E-009",
        "category": "harmless_variation",
        "input": "GI Equal Tee 50 mm Class B 15 no",
        "expected_outcome": "match",
        "expected_sku": "FITT-009",
        "expected_normalized": {
            "quantity": "15",
            "unit": "nos",
            "spec": {"size_mm": "50", "class": "B", "material": "GI"},
            "issue_codes": []
        },
        "rationale": "Space in '50 mm' and singular unit alias 'no' matches FITT-009.",
        "label_pass": {
            "labelled_by": "initial_reviewer",
            "created_at": "2026-10-16T15:10:00Z",
            "second_pass_done": False
        }
    },
    {
        "id": "E-010",
        "category": "harmless_variation",
        "input": "P.T.F.E. Thread Seal Tape 12mm 10 roll",
        "expected_outcome": "match",
        "expected_sku": "CONS-003",
        "expected_normalized": {
            "quantity": "10",
            "unit": "roll",
            "spec": {"size_mm": "12"},
            "issue_codes": []
        },
        "rationale": "Acronym punctuation 'P.T.F.E.' resolves to PTFE tape 12mm (CONS-003).",
        "label_pass": {
            "labelled_by": "initial_reviewer",
            "created_at": "2026-10-16T15:10:00Z",
            "second_pass_done": False
        }
    },

    # 3. Supported unit alias or convertible unit (4 cases -> match)
    {
        "id": "E-011",
        "category": "supported_unit_alias_or_convertible",
        "input": "GI Pipe 50mm Class B 100 ft",
        "expected_outcome": "match",
        "expected_sku": "PIPE-012",
        "expected_normalized": {
            "quantity": "100",
            "unit": "ft",
            "spec": {"size_mm": "50", "class": "B", "material": "GI"},
            "issue_codes": []
        },
        "rationale": "Unit 'ft' is dimensionally compatible with catalog UOM 'mtr' (length). 100 ft = 30.48 mtr. Matches PIPE-012.",
        "label_pass": {
            "labelled_by": "initial_reviewer",
            "created_at": "2026-10-16T15:10:00Z",
            "second_pass_done": False
        }
    },
    {
        "id": "E-012",
        "category": "supported_unit_alias_or_convertible",
        "input": "MS Hex Nut M16 200 piece",
        "expected_outcome": "match",
        "expected_sku": "BOLT-031",
        "expected_normalized": {
            "quantity": "200",
            "unit": "nos",
            "spec": {"thread": "M16", "material": "MS"},
            "issue_codes": []
        },
        "rationale": "Unit alias 'piece' maps to canonical count unit 'nos'. Matches BOLT-031.",
        "label_pass": {
            "labelled_by": "initial_reviewer",
            "created_at": "2026-10-16T15:10:00Z",
            "second_pass_done": False
        }
    },
    {
        "id": "E-013",
        "category": "supported_unit_alias_or_convertible",
        "input": "Welding Electrodes MS E6013 3.15mm 25000 g",
        "expected_outcome": "match",
        "expected_sku": "CONS-001",
        "expected_normalized": {
            "quantity": "25000",
            "unit": "g",
            "spec": {"size_mm": "3.15", "material": "MS"},
            "issue_codes": []
        },
        "rationale": "Unit 'g' is convertible to catalog UOM 'kg' (mass). 25000 g = 25 kg. Matches CONS-001.",
        "label_pass": {
            "labelled_by": "initial_reviewer",
            "created_at": "2026-10-16T15:10:00Z",
            "second_pass_done": False
        }
    },
    {
        "id": "E-014",
        "category": "supported_unit_alias_or_convertible",
        "input": "Red Oxide Metal Primer Paint 20 l",
        "expected_outcome": "match",
        "expected_sku": "CONS-004",
        "expected_normalized": {
            "quantity": "20",
            "unit": "ltr",
            "spec": {},
            "issue_codes": []
        },
        "rationale": "Single-letter volume alias 'l' maps to canonical unit 'ltr'. Matches CONS-004.",
        "label_pass": {
            "labelled_by": "initial_reviewer",
            "created_at": "2026-10-16T15:10:00Z",
            "second_pass_done": False
        }
    },

    # 4. Unit incompatible (3 cases -> review)
    {
        "id": "E-015",
        "category": "unit_incompatible",
        "input": "GI Pipe 25mm Class B 50 nos",
        "expected_outcome": "review",
        "expected_sku": None,
        "expected_normalized": {
            "quantity": "50",
            "unit": "nos",
            "spec": {"size_mm": "25", "class": "B", "material": "GI"},
            "issue_codes": []
        },
        "rationale": "Catalog item PIPE-004 is measured in length (mtr), while request asks for count (nos). Incompatible unit dimension requires human review.",
        "label_pass": {
            "labelled_by": "initial_reviewer",
            "created_at": "2026-10-16T15:10:00Z",
            "second_pass_done": False
        }
    },
    {
        "id": "E-016",
        "category": "unit_incompatible",
        "input": "MS Hex Bolt M10x40 Grade 4.6 15 kg",
        "expected_outcome": "review",
        "expected_sku": None,
        "expected_normalized": {
            "quantity": "15",
            "unit": "kg",
            "spec": {"thread": "M10", "length_mm": "40", "grade": "4.6", "material": "MS"},
            "issue_codes": []
        },
        "rationale": "Catalog fasteners (BOLT-005) have UOM nos (count). Request asks for mass (kg). Weight-to-piece conversion requires human input.",
        "label_pass": {
            "labelled_by": "initial_reviewer",
            "created_at": "2026-10-16T15:10:00Z",
            "second_pass_done": False
        }
    },
    {
        "id": "E-017",
        "category": "unit_incompatible",
        "input": "PTFE Thread Seal Tape 12mm 5 mtr",
        "expected_outcome": "review",
        "expected_sku": None,
        "expected_normalized": {
            "quantity": "5",
            "unit": "mtr",
            "spec": {"size_mm": "12"},
            "issue_codes": []
        },
        "rationale": "CONS-003 has UOM roll (count unit). Request specifies mtr (length). Cannot interchange roll with meter.",
        "label_pass": {
            "labelled_by": "initial_reviewer",
            "created_at": "2026-10-16T15:10:00Z",
            "second_pass_done": False
        }
    },

    # 5. Missing quantity (2 cases -> review)
    {
        "id": "E-018",
        "category": "missing_quantity",
        "input": "GI Pipe 40mm Class A mtr",
        "expected_outcome": "review",
        "expected_sku": None,
        "expected_normalized": {
            "quantity": None,
            "unit": None,
            "spec": {"size_mm": "40", "class": "A", "material": "GI"},
            "issue_codes": ["MISSING_QUANTITY"]
        },
        "rationale": "Unit 'mtr' appears at end without a preceding number. Free-text trailing quantity rule triggers MISSING_QUANTITY.",
        "label_pass": {
            "labelled_by": "initial_reviewer",
            "created_at": "2026-10-16T15:10:00Z",
            "second_pass_done": False
        }
    },
    {
        "id": "E-019",
        "category": "missing_quantity",
        "input": "Brass Ball Valve Screwed 20mm nos",
        "expected_outcome": "review",
        "expected_sku": None,
        "expected_normalized": {
            "quantity": None,
            "unit": None,
            "spec": {"size_mm": "20", "material": "BRASS"},
            "issue_codes": ["MISSING_QUANTITY"]
        },
        "rationale": "Unit 'nos' is present at end without a quantity number. System must flag MISSING_QUANTITY and abstain.",
        "label_pass": {
            "labelled_by": "initial_reviewer",
            "created_at": "2026-10-16T15:10:00Z",
            "second_pass_done": False
        }
    },

    # 6. Missing or unknown unit (3 cases -> review)
    {
        "id": "E-020",
        "category": "missing_or_unknown_unit",
        "input": "GI Pipe 32mm Class B 50",
        "expected_outcome": "review",
        "expected_sku": None,
        "expected_normalized": {
            "quantity": "50",
            "unit": None,
            "spec": {"size_mm": "32", "class": "B", "material": "GI"},
            "issue_codes": ["MISSING_UNIT"]
        },
        "rationale": "Trailing number '50' parsed as quantity, but unit is missing. Soft issue MISSING_UNIT forces review.",
        "label_pass": {
            "labelled_by": "initial_reviewer",
            "created_at": "2026-10-16T15:10:00Z",
            "second_pass_done": False
        }
    },
    {
        "id": "E-021",
        "category": "missing_or_unknown_unit",
        "input": "MS Hex Bolt M12x75 Grade 8.8 100",
        "expected_outcome": "review",
        "expected_sku": None,
        "expected_normalized": {
            "quantity": "100",
            "unit": None,
            "spec": {"thread": "M12", "length_mm": "75", "grade": "8.8", "material": "MS"},
            "issue_codes": ["MISSING_UNIT"]
        },
        "rationale": "Trailing number '100' lacks unit. Unsafe to guess unit (nos vs box vs kg). Forces review.",
        "label_pass": {
            "labelled_by": "initial_reviewer",
            "created_at": "2026-10-16T15:10:00Z",
            "second_pass_done": False
        }
    },
    {
        "id": "E-022",
        "category": "missing_or_unknown_unit",
        "input": "PVC Pipe 50mm Class A 30 bundles",
        "expected_outcome": "review",
        "expected_sku": None,
        "expected_normalized": {
            "quantity": None,
            "unit": None,
            "spec": {"size_mm": "50", "class": "A", "material": "PVC"},
            "issue_codes": ["MISSING_QUANTITY"]
        },
        "rationale": "'bundles' is not in the unit dictionary; per trailing rule 5, trailing number+word is not parsed as quantity. Forces review.",
        "label_pass": {
            "labelled_by": "initial_reviewer",
            "created_at": "2026-10-16T15:10:00Z",
            "second_pass_done": False
        }
    },

    # 7. Conflicting spec: request internally conflicting (1 case -> review)
    {
        "id": "E-023",
        "category": "conflicting_spec_internal",
        "input": "GI Pipe 25mm Class A Class B 10 mtr",
        "expected_outcome": "review",
        "expected_sku": None,
        "expected_normalized": {
            "quantity": "10",
            "unit": "mtr",
            "spec": {"size_mm": "25", "material": "GI"},
            "issue_codes": ["SPEC_CONFLICT_IN_REQUEST"]
        },
        "rationale": "Request contains mutually conflicting single-valued attribute 'class' (Class A and Class B). SPEC_CONFLICT_IN_REQUEST forces review.",
        "label_pass": {
            "labelled_by": "initial_reviewer",
            "created_at": "2026-10-16T15:10:00Z",
            "second_pass_done": False
        }
    },

    # 8. Conflicting spec: catalog has no compatible size/material (near-miss) (2 cases -> unmatched)
    {
        "id": "E-024",
        "category": "conflicting_spec_catalog_near_miss",
        "input": "GI Pipe 70mm Class B 10 mtr",
        "expected_outcome": "unmatched",
        "expected_sku": None,
        "expected_normalized": {
            "quantity": "10",
            "unit": "mtr",
            "spec": {"size_mm": "70", "class": "B", "material": "GI"},
            "issue_codes": []
        },
        "rationale": "70mm is not a manufactured nominal size in the catalog (available: 15, 20, 25, 32, 40, 50, 80, 100mm). All candidate matches conflict on size_mm.",
        "label_pass": {
            "labelled_by": "initial_reviewer",
            "created_at": "2026-10-16T15:10:00Z",
            "second_pass_done": False
        }
    },
    {
        "id": "E-025",
        "category": "conflicting_spec_catalog_near_miss",
        "input": "Brass Hex Bolt M12x50 50 nos",
        "expected_outcome": "unmatched",
        "expected_sku": None,
        "expected_normalized": {
            "quantity": "50",
            "unit": "nos",
            "spec": {"thread": "M12", "length_mm": "50", "material": "BRASS"},
            "issue_codes": []
        },
        "rationale": "Catalog only stocks Hex Bolts in MS and SS304. Brass hex bolts do not exist. All retrieved bolt candidates conflict on material (BRASS vs MS/SS304).",
        "label_pass": {
            "labelled_by": "initial_reviewer",
            "created_at": "2026-10-16T15:10:00Z",
            "second_pass_done": False
        }
    },

    # 9. Near-duplicate products with missing discriminator (3 cases -> review)
    {
        "id": "E-026",
        "category": "near_duplicate_missing_discriminator",
        "input": "GI Pipe 25mm 20 mtr",
        "expected_outcome": "review",
        "expected_sku": None,
        "expected_normalized": {
            "quantity": "20",
            "unit": "mtr",
            "spec": {"size_mm": "25", "material": "GI"},
            "issue_codes": []
        },
        "rationale": "Catalog has PIPE-003 (Class A) and PIPE-004 (Class B). Request lacks class specification. Missing discriminator prevents safe automatic proposal.",
        "label_pass": {
            "labelled_by": "initial_reviewer",
            "created_at": "2026-10-16T15:10:00Z",
            "second_pass_done": False
        }
    },
    {
        "id": "E-027",
        "category": "near_duplicate_missing_discriminator",
        "input": "MS Hex Bolt M10x40 100 nos",
        "expected_outcome": "review",
        "expected_sku": None,
        "expected_normalized": {
            "quantity": "100",
            "unit": "nos",
            "spec": {"thread": "M10", "length_mm": "40", "material": "MS"},
            "issue_codes": []
        },
        "rationale": "Catalog has BOLT-005 (Grade 4.6) and BOLT-014 (Grade 8.8). Request does not specify grade. Guessing structural bolt grade is unsafe.",
        "label_pass": {
            "labelled_by": "initial_reviewer",
            "created_at": "2026-10-16T15:10:00Z",
            "second_pass_done": False
        }
    },
    {
        "id": "E-028",
        "category": "near_duplicate_missing_discriminator",
        "input": "PVC Pipe 25mm 60 mtr",
        "expected_outcome": "review",
        "expected_sku": None,
        "expected_normalized": {
            "quantity": "60",
            "unit": "mtr",
            "spec": {"size_mm": "25", "material": "PVC"},
            "issue_codes": []
        },
        "rationale": "Catalog contains PIPE-019 (Class A) and PIPE-020 (Class B). Class discriminator missing.",
        "label_pass": {
            "labelled_by": "initial_reviewer",
            "created_at": "2026-10-16T15:10:00Z",
            "second_pass_done": False
        }
    },

    # 10. Multiple plausible candidates (2 cases -> review)
    {
        "id": "E-029",
        "category": "multiple_plausible_candidates",
        "input": "Brass Valve 25mm 5 nos",
        "expected_outcome": "review",
        "expected_sku": None,
        "expected_normalized": {
            "quantity": "5",
            "unit": "nos",
            "spec": {"size_mm": "25", "material": "BRASS"},
            "issue_codes": []
        },
        "rationale": "Both VALV-003 (Brass Ball Valve 25mm) and VALV-007 (Brass Gate Valve 25mm) are plausible candidates with near-tied scores. Review required.",
        "label_pass": {
            "labelled_by": "initial_reviewer",
            "created_at": "2026-10-16T15:10:00Z",
            "second_pass_done": False
        }
    },
    {
        "id": "E-030",
        "category": "multiple_plausible_candidates",
        "input": "GI Fitting 25mm 10 nos",
        "expected_outcome": "review",
        "expected_sku": None,
        "expected_normalized": {
            "quantity": "10",
            "unit": "nos",
            "spec": {"size_mm": "25", "material": "GI"},
            "issue_codes": []
        },
        "rationale": "FITT-003 (Elbow), FITT-008 (Tee), and FITT-012 (Socket) all match 'GI Fitting 25mm'. Top candidates tie, forcing abstention.",
        "label_pass": {
            "labelled_by": "initial_reviewer",
            "created_at": "2026-10-16T15:10:00Z",
            "second_pass_done": False
        }
    },

    # 11. Unknown catalog item (3 cases -> unmatched)
    {
        "id": "E-031",
        "category": "unknown_catalog_item",
        "input": "Cast Iron Submersible Sump Pump 2 HP 1 nos",
        "expected_outcome": "unmatched",
        "expected_sku": None,
        "expected_normalized": {
            "quantity": "1",
            "unit": "nos",
            "spec": {},
            "issue_codes": []
        },
        "rationale": "Submersible sump pumps are completely absent from the synthetic catalog. Must return unmatched.",
        "label_pass": {
            "labelled_by": "initial_reviewer",
            "created_at": "2026-10-16T15:10:00Z",
            "second_pass_done": False
        }
    },
    {
        "id": "E-032",
        "category": "unknown_catalog_item",
        "input": "Safety Helmet with Ratchet Suspension 10 nos",
        "expected_outcome": "unmatched",
        "expected_sku": None,
        "expected_normalized": {
            "quantity": "10",
            "unit": "nos",
            "spec": {},
            "issue_codes": []
        },
        "rationale": "Safety helmets / PPE do not exist in the piping and hardware catalog.",
        "label_pass": {
            "labelled_by": "initial_reviewer",
            "created_at": "2026-10-16T15:10:00Z",
            "second_pass_done": False
        }
    },
    {
        "id": "E-033",
        "category": "unknown_catalog_item",
        "input": "Copper Refrigeration Tubing 1/2 inch 15 mtr",
        "expected_outcome": "unmatched",
        "expected_sku": None,
        "expected_normalized": {
            "quantity": "15",
            "unit": "mtr",
            "spec": {"size_mm": "12.7", "material": "CU"},
            "issue_codes": []
        },
        "rationale": "Catalog only has GI and PVC pipes; copper refrigeration tubing is not stocked.",
        "label_pass": {
            "labelled_by": "initial_reviewer",
            "created_at": "2026-10-16T15:10:00Z",
            "second_pass_done": False
        }
    },

    # 12. Mixed Hindi–English / transliterated (4 cases: 3 match, 1 review)
    {
        "id": "E-034",
        "category": "mixed_hindi_english_transliterated",
        "input": "GI paip 20mm Class A 30 mtr",
        "expected_outcome": "match",
        "expected_sku": "PIPE-002",
        "expected_normalized": {
            "quantity": "30",
            "unit": "mtr",
            "spec": {"size_mm": "20", "class": "A", "material": "GI"},
            "issue_codes": []
        },
        "rationale": "Transliterated term 'paip' normalizes to 'pipe'. Clean match to PIPE-002 (GI Pipe 20mm Class A).",
        "label_pass": {
            "labelled_by": "initial_reviewer",
            "created_at": "2026-10-16T15:10:00Z",
            "second_pass_done": False
        }
    },
    {
        "id": "E-035",
        "category": "mixed_hindi_english_transliterated",
        "input": "pital ball valv 15mm 10 nag",
        "expected_outcome": "match",
        "expected_sku": "VALV-001",
        "expected_normalized": {
            "quantity": "10",
            "unit": "nos",
            "spec": {"size_mm": "15", "material": "BRASS"},
            "issue_codes": []
        },
        "rationale": "'pital' -> brass, 'valv' -> valve, 'nag' -> nos. Fully specifies VALV-001 (Brass Ball Valve Screwed 15mm).",
        "label_pass": {
            "labelled_by": "initial_reviewer",
            "created_at": "2026-10-16T15:10:00Z",
            "second_pass_done": False
        }
    },
    {
        "id": "E-036",
        "category": "mixed_hindi_english_transliterated",
        "input": "MS nat M12 50 नग",
        "expected_outcome": "match",
        "expected_sku": "BOLT-030",
        "expected_normalized": {
            "quantity": "50",
            "unit": "nos",
            "spec": {"thread": "M12", "material": "MS"},
            "issue_codes": []
        },
        "rationale": "'nat' -> nut, Devanagari unit 'नग' -> nos. Fully specifies BOLT-030 (MS Hex Nut M12).",
        "label_pass": {
            "labelled_by": "initial_reviewer",
            "created_at": "2026-10-16T15:10:00Z",
            "second_pass_done": False
        }
    },
    {
        "id": "E-037",
        "category": "mixed_hindi_english_transliterated",
        "input": "kohni 25mm 10 nos",
        "expected_outcome": "review",
        "expected_sku": None,
        "expected_normalized": {
            "quantity": "10",
            "unit": "nos",
            "spec": {"size_mm": "25"},
            "issue_codes": []
        },
        "rationale": "'kohni' maps to elbow. However, material (GI vs PVC) and class are absent. Matches both FITT-003 and FITT-015; review required.",
        "label_pass": {
            "labelled_by": "initial_reviewer",
            "created_at": "2026-10-16T15:10:00Z",
            "second_pass_done": False
        }
    },

    # 13. Malformed/incomplete but ingestible (dimension tail `x 50`, leading quantity, fractional count) (3 cases -> review)
    {
        "id": "E-038",
        "category": "malformed_incomplete_ingestible",
        "input": "MS Hex Bolt M12 x 50",
        "expected_outcome": "review",
        "expected_sku": None,
        "expected_normalized": {
            "quantity": None,
            "unit": None,
            "spec": {"thread": "M12", "length_mm": "50", "material": "MS"},
            "issue_codes": ["MISSING_QUANTITY"]
        },
        "rationale": "Trailing number preceded by 'x' is a dimension, not a quantity (rule 3). Resulting line lacks quantity and unit; review required.",
        "label_pass": {
            "labelled_by": "initial_reviewer",
            "created_at": "2026-10-16T15:10:00Z",
            "second_pass_done": False
        }
    },
    {
        "id": "E-039",
        "category": "malformed_incomplete_ingestible",
        "input": "50 mtr GI Pipe 25mm Class B",
        "expected_outcome": "review",
        "expected_sku": None,
        "expected_normalized": {
            "quantity": None,
            "unit": None,
            "spec": {"size_mm": "25", "class": "B", "material": "GI"},
            "issue_codes": ["MISSING_QUANTITY"]
        },
        "rationale": "Leading quantity '50 mtr' is not extracted in free-text mode (rule D9: trailing quantity only). Line flags MISSING_QUANTITY and routes to review.",
        "label_pass": {
            "labelled_by": "initial_reviewer",
            "created_at": "2026-10-16T15:10:00Z",
            "second_pass_done": False
        }
    },
    {
        "id": "E-040",
        "category": "malformed_incomplete_ingestible",
        "input": "MS Hex Bolt M12x50 Grade 4.6 12.5 nos",
        "expected_outcome": "review",
        "expected_sku": None,
        "expected_normalized": {
            "quantity": "12.5",
            "unit": "nos",
            "spec": {"thread": "M12", "length_mm": "50", "grade": "4.6", "material": "MS"},
            "issue_codes": ["FRACTIONAL_COUNT"]
        },
        "rationale": "Fractional quantity (12.5) for count unit 'nos' triggers blocking issue FRACTIONAL_COUNT (rule D14). Review required.",
        "label_pass": {
            "labelled_by": "initial_reviewer",
            "created_at": "2026-10-16T15:10:00Z",
            "second_pass_done": False
        }
    }
]

DEV_CASES = [
    {
        "id": "D-001",
        "category": "exact_clean_match",
        "input": "GI Pipe 80mm Class A 24 mtr",
        "expected_outcome": "match",
        "expected_sku": "PIPE-013",
        "expected_normalized": {
            "quantity": "24",
            "unit": "mtr",
            "spec": {"size_mm": "80", "class": "A", "material": "GI"},
            "issue_codes": []
        },
        "rationale": "Exact match to PIPE-013 (GI Pipe 80mm Class A).",
        "label_pass": {
            "labelled_by": "initial_reviewer",
            "created_at": "2026-10-16T15:10:00Z",
            "second_pass_done": False
        }
    },
    {
        "id": "D-002",
        "category": "harmless_variation",
        "input": "ms hex bolt m8x30 grade 4.6 200 nos",
        "expected_outcome": "match",
        "expected_sku": "BOLT-003",
        "expected_normalized": {
            "quantity": "200",
            "unit": "nos",
            "spec": {"thread": "M8", "length_mm": "30", "grade": "4.6", "material": "MS"},
            "issue_codes": []
        },
        "rationale": "Lowercase variation of BOLT-003.",
        "label_pass": {
            "labelled_by": "initial_reviewer",
            "created_at": "2026-10-16T15:10:00Z",
            "second_pass_done": False
        }
    },
    {
        "id": "D-003",
        "category": "supported_unit_alias_or_convertible",
        "input": "GI Pipe 100mm Class B 300 ft",
        "expected_outcome": "match",
        "expected_sku": "PIPE-016",
        "expected_normalized": {
            "quantity": "300",
            "unit": "ft",
            "spec": {"size_mm": "100", "class": "B", "material": "GI"},
            "issue_codes": []
        },
        "rationale": "Length unit 'ft' converted to 'mtr'. Matches PIPE-016.",
        "label_pass": {
            "labelled_by": "initial_reviewer",
            "created_at": "2026-10-16T15:10:00Z",
            "second_pass_done": False
        }
    },
    {
        "id": "D-004",
        "category": "supported_unit_alias_or_convertible",
        "input": "MS Plain Washer M12 500 pcs",
        "expected_outcome": "match",
        "expected_sku": "BOLT-035",
        "expected_normalized": {
            "quantity": "500",
            "unit": "nos",
            "spec": {"material": "MS", "size_mm": "12"},
            "issue_codes": []
        },
        "rationale": "'pcs' alias for 'nos'. Matches BOLT-035.",
        "label_pass": {
            "labelled_by": "initial_reviewer",
            "created_at": "2026-10-16T15:10:00Z",
            "second_pass_done": False
        }
    },
    {
        "id": "D-005",
        "category": "unit_incompatible",
        "input": "PVC Pipe 20mm Class B 100 kg",
        "expected_outcome": "review",
        "expected_sku": None,
        "expected_normalized": {
            "quantity": "100",
            "unit": "kg",
            "spec": {"size_mm": "20", "class": "B", "material": "PVC"},
            "issue_codes": []
        },
        "rationale": "Pipe UOM is mtr (length), input requests kg (mass). Unit incompatible forces review.",
        "label_pass": {
            "labelled_by": "initial_reviewer",
            "created_at": "2026-10-16T15:10:00Z",
            "second_pass_done": False
        }
    },
    {
        "id": "D-006",
        "category": "missing_quantity",
        "input": "MS Hex Nut M10 nos",
        "expected_outcome": "review",
        "expected_sku": None,
        "expected_normalized": {
            "quantity": None,
            "unit": None,
            "spec": {"thread": "M10", "material": "MS"},
            "issue_codes": ["MISSING_QUANTITY"]
        },
        "rationale": "Missing numerical quantity before unit nos.",
        "label_pass": {
            "labelled_by": "initial_reviewer",
            "created_at": "2026-10-16T15:10:00Z",
            "second_pass_done": False
        }
    },
    {
        "id": "D-007",
        "category": "missing_or_unknown_unit",
        "input": "GI Socket Coupling 20mm Class B 50",
        "expected_outcome": "review",
        "expected_sku": None,
        "expected_normalized": {
            "quantity": "50",
            "unit": None,
            "spec": {"size_mm": "20", "class": "B", "material": "GI"},
            "issue_codes": ["MISSING_UNIT"]
        },
        "rationale": "Quantity 50 present but missing unit.",
        "label_pass": {
            "labelled_by": "initial_reviewer",
            "created_at": "2026-10-16T15:10:00Z",
            "second_pass_done": False
        }
    },
    {
        "id": "D-008",
        "category": "near_duplicate_missing_discriminator",
        "input": "MS Hex Bolt M16x60 50 nos",
        "expected_outcome": "review",
        "expected_sku": None,
        "expected_normalized": {
            "quantity": "50",
            "unit": "nos",
            "spec": {"thread": "M16", "length_mm": "60", "material": "MS"},
            "issue_codes": []
        },
        "rationale": "BOLT-009 (Grade 4.6) and BOLT-018 (Grade 8.8) differ by grade. Missing grade discriminator requires review.",
        "label_pass": {
            "labelled_by": "initial_reviewer",
            "created_at": "2026-10-16T15:10:00Z",
            "second_pass_done": False
        }
    },
    {
        "id": "D-009",
        "category": "conflicting_spec_internal",
        "input": "GI Pipe 25mm MS 10 mtr",
        "expected_outcome": "review",
        "expected_sku": None,
        "expected_normalized": {
            "quantity": "10",
            "unit": "mtr",
            "spec": {"size_mm": "25"},
            "issue_codes": ["SPEC_CONFLICT_IN_REQUEST"]
        },
        "rationale": "Request contains conflicting material specifications: GI and MS. SPEC_CONFLICT_IN_REQUEST forces review.",
        "label_pass": {
            "labelled_by": "initial_reviewer",
            "created_at": "2026-10-16T15:10:00Z",
            "second_pass_done": False
        }
    },
    {
        "id": "D-010",
        "category": "conflicting_spec_catalog_near_miss",
        "input": "Stainless Steel Hex Bolt M24x100 20 nos",
        "expected_outcome": "unmatched",
        "expected_sku": None,
        "expected_normalized": {
            "quantity": "20",
            "unit": "nos",
            "spec": {"thread": "M24", "length_mm": "100", "material": "SS304"},
            "issue_codes": []
        },
        "rationale": "Thread M24 is not stocked in the catalog (fasteners range up to M20). Unmatched.",
        "label_pass": {
            "labelled_by": "initial_reviewer",
            "created_at": "2026-10-16T15:10:00Z",
            "second_pass_done": False
        }
    },
    {
        "id": "D-011",
        "category": "unknown_catalog_item",
        "input": "Industrial Safety Goggles Clear 5 nos",
        "expected_outcome": "unmatched",
        "expected_sku": None,
        "expected_normalized": {
            "quantity": "5",
            "unit": "nos",
            "spec": {},
            "issue_codes": []
        },
        "rationale": "Safety goggles are not stocked in the catalog. Unmatched.",
        "label_pass": {
            "labelled_by": "initial_reviewer",
            "created_at": "2026-10-16T15:10:00Z",
            "second_pass_done": False
        }
    },
    {
        "id": "D-012",
        "category": "mixed_hindi_english_transliterated",
        "input": "loha bolt M12x75 Gr 4.6 40 nos",
        "expected_outcome": "match",
        "expected_sku": "BOLT-008",
        "expected_normalized": {
            "quantity": "40",
            "unit": "nos",
            "spec": {"thread": "M12", "length_mm": "75", "grade": "4.6", "material": "MS"},
            "issue_codes": []
        },
        "rationale": "'loha' maps to iron/MS. Fully specifies BOLT-008 (MS Hex Bolt M12x75 Grade 4.6).",
        "label_pass": {
            "labelled_by": "initial_reviewer",
            "created_at": "2026-10-16T15:10:00Z",
            "second_pass_done": False
        }
    }
]

def write_jsonl(cases, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for c in cases:
            f.write(json.dumps(c, ensure_ascii=False) + "\n")
    print(f"Wrote {len(cases)} cases to {path}")

if __name__ == "__main__":
    frozen_path = Path("/home/satjeet/Desktop/isocode/eval/dataset/v1/cases.jsonl")
    dev_path = Path("/home/satjeet/Desktop/isocode/eval/dev/cases.jsonl")
    write_jsonl(FROZEN_CASES, frozen_path)
    write_jsonl(DEV_CASES, dev_path)
