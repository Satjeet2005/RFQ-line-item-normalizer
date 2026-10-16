"""
Automated dataset and catalog consistency validation tool.
Enforces internal consistency, non-overlap, schema compliance, and manifest integrity.
"""
import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path("/home/satjeet/Desktop/isocode")
sys.path.insert(0, str(ROOT))
FROZEN_DIR = ROOT / "eval" / "dataset" / "v1"
DEV_DIR = ROOT / "eval" / "dev"
DATA_DIR = ROOT / "data"

EXPECTED_CATEGORIES = {
    "exact_clean_match": (5, {"match": 5}),
    "harmless_variation": (5, {"match": 5}),
    "supported_unit_alias_or_convertible": (4, {"match": 4}),
    "unit_incompatible": (3, {"review": 3}),
    "missing_quantity": (2, {"review": 2}),
    "missing_or_unknown_unit": (3, {"review": 3}),
    "conflicting_spec_internal": (1, {"review": 1}),
    "conflicting_spec_catalog_near_miss": (2, {"unmatched": 2}),
    "near_duplicate_missing_discriminator": (3, {"review": 3}),
    "multiple_plausible_candidates": (2, {"review": 2}),
    "unknown_catalog_item": (3, {"unmatched": 3}),
    "mixed_hindi_english_transliterated": (4, {"match": 3, "review": 1}),
    "malformed_incomplete_ingestible": (3, {"review": 3}),
}

def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()

def validate_all():
    errors = []

    # 1. Validate catalog
    from scripts.validate_catalog import validate_catalog
    catalog_path = DATA_DIR / "catalog.json"
    cat_errs = validate_catalog(catalog_path)
    if cat_errs:
        errors.extend([f"Catalog: {e}" for e in cat_errs])

    with open(catalog_path, "r", encoding="utf-8") as f:
        catalog = json.load(f)
    catalog_skus = {item["sku"]: item for item in catalog}

    # 2. Validate frozen cases
    frozen_cases_path = FROZEN_DIR / "cases.jsonl"
    if not frozen_cases_path.exists():
        errors.append(f"Missing {frozen_cases_path}")
        return errors

    frozen_cases = []
    frozen_ids = set()
    frozen_inputs = set()
    category_counts = {}

    with open(frozen_cases_path, "r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                case = json.loads(line)
            except Exception as e:
                errors.append(f"Frozen cases line {line_no}: invalid JSON: {e}")
                continue

            cid = case.get("id")
            if not cid or not isinstance(cid, str):
                errors.append(f"Frozen line {line_no}: missing or invalid id")
            elif cid in frozen_ids:
                errors.append(f"Duplicate case id in frozen set: {cid}")
            else:
                frozen_ids.add(cid)

            c_input = case.get("input")
            if not c_input or not isinstance(c_input, str):
                errors.append(f"Case {cid}: invalid input")
            else:
                frozen_inputs.add(c_input)

            cat = case.get("category")
            if cat not in EXPECTED_CATEGORIES:
                errors.append(f"Case {cid}: unexpected category '{cat}'")
            else:
                category_counts.setdefault(cat, []).append(case)

            outcome = case.get("expected_outcome")
            if outcome not in ("match", "review", "unmatched"):
                errors.append(f"Case {cid}: invalid expected_outcome '{outcome}'")

            sku = case.get("expected_sku")
            if outcome == "match":
                if not sku:
                    errors.append(f"Case {cid}: expected_outcome is match but expected_sku is null")
                elif sku not in catalog_skus:
                    errors.append(f"Case {cid}: expected_sku '{sku}' not in catalog")
            else:
                if sku is not None:
                    errors.append(f"Case {cid}: expected_sku must be null when outcome is {outcome}")

            rationale = case.get("rationale")
            if not rationale or not isinstance(rationale, str) or len(rationale.strip()) < 10:
                errors.append(f"Case {cid}: rationale is missing or too brief")

            lp = case.get("label_pass")
            if not isinstance(lp, dict):
                errors.append(f"Case {cid}: label_pass object missing")
            else:
                if "labelled_by" not in lp or "created_at" not in lp or "second_pass_done" not in lp:
                    errors.append(f"Case {cid}: label_pass missing required keys")

            frozen_cases.append(case)

    if len(frozen_cases) != 40:
        errors.append(f"Frozen cases count is {len(frozen_cases)}, expected 40")

    # Validate category breakdown
    for cat, (exp_count, exp_outcomes) in EXPECTED_CATEGORIES.items():
        actual_cases = category_counts.get(cat, [])
        if len(actual_cases) != exp_count:
            errors.append(f"Category '{cat}' has {len(actual_cases)} cases, expected {exp_count}")
        actual_outcomes = {}
        for c in actual_cases:
            o = c.get("expected_outcome")
            actual_outcomes[o] = actual_outcomes.get(o, 0) + 1
        if actual_outcomes != exp_outcomes:
            errors.append(f"Category '{cat}' outcomes {actual_outcomes} != expected {exp_outcomes}")

    # 3. Validate dev cases
    dev_cases_path = DEV_DIR / "cases.jsonl"
    if not dev_cases_path.exists():
        errors.append(f"Missing {dev_cases_path}")
        return errors

    dev_cases = []
    dev_ids = set()

    with open(dev_cases_path, "r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                case = json.loads(line)
            except Exception as e:
                errors.append(f"Dev cases line {line_no}: invalid JSON: {e}")
                continue

            cid = case.get("id")
            if not cid or not isinstance(cid, str):
                errors.append(f"Dev line {line_no}: missing or invalid id")
            elif cid in dev_ids:
                errors.append(f"Duplicate case id in dev set: {cid}")
            else:
                dev_ids.add(cid)

            if cid in frozen_ids:
                errors.append(f"Dev case id '{cid}' overlaps with frozen cases")

            d_input = case.get("input")
            if d_input in frozen_inputs:
                errors.append(f"Dev case input overlaps with frozen case: '{d_input}'")

            outcome = case.get("expected_outcome")
            sku = case.get("expected_sku")
            if outcome == "match":
                if not sku or sku not in catalog_skus:
                    errors.append(f"Dev case {cid}: invalid expected_sku '{sku}'")
            else:
                if sku is not None:
                    errors.append(f"Dev case {cid}: expected_sku must be null when outcome is {outcome}")

            dev_cases.append(case)

    if len(dev_cases) != 12:
        errors.append(f"Dev cases count is {len(dev_cases)}, expected 12")

    # 4. Validate copies consistency
    for name in ("catalog.json", "aliases.json", "vocab.json"):
        p_primary = DATA_DIR / name
        p_frozen = FROZEN_DIR / name
        if not p_frozen.exists():
            errors.append(f"Missing frozen copy {p_frozen}")
        elif sha256_file(p_primary) != sha256_file(p_frozen):
            errors.append(f"Frozen copy {p_frozen} does not match primary {p_primary}")

    # 5. Validate manifest
    manifest_path = FROZEN_DIR / "MANIFEST.sha256"
    if not manifest_path.exists():
        errors.append(f"Missing {manifest_path}")
    else:
        with open(manifest_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                parts = line.split()
                if len(parts) != 2:
                    errors.append(f"Malformed manifest line: '{line}'")
                    continue
                expected_hash, rel_file = parts
                target_file = FROZEN_DIR / rel_file
                if not target_file.exists():
                    errors.append(f"Manifest targets non-existent file: {rel_file}")
                else:
                    actual_hash = sha256_file(target_file)
                    if actual_hash != expected_hash:
                        errors.append(f"Manifest hash mismatch for {rel_file}: expected {expected_hash}, got {actual_hash}")

    return errors

if __name__ == "__main__":
    errs = validate_all()
    if errs:
        print(f"Dataset validation FAILED ({len(errs)} errors):")
        for e in errs:
            print(f"  - {e}")
        sys.exit(1)
    else:
        print("Dataset validation PASSED: all 40 frozen cases, 12 dev cases, catalog, and manifest are valid and consistent.")
