"""
Reconciliation tool for comparing Pass 1 and Pass 2 evaluation labels.
Validates submission schema, computes inter-annotator agreement, and reports discrepancies.
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path("/home/satjeet/Desktop/isocode")
PASS1_PATH = ROOT / "eval" / "dataset" / "v1" / "cases.jsonl"
CATALOG_PATH = ROOT / "data" / "catalog.json"

def reconcile(pass2_path: Path):
    if not pass2_path.exists():
        print(f"Error: Submission file {pass2_path} does not exist.")
        sys.exit(1)

    with open(CATALOG_PATH, "r", encoding="utf-8") as f:
        catalog = {p["sku"]: p for p in json.load(f)}

    pass1_cases = {}
    with open(PASS1_PATH, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                c = json.loads(line)
                pass1_cases[c["id"]] = c

    pass2_cases = {}
    validation_errors = []
    with open(pass2_path, "r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, 1):
            if not line.strip():
                continue
            try:
                c = json.loads(line)
            except Exception as e:
                validation_errors.append(f"Line {line_no}: invalid JSON ({e})")
                continue

            cid = c.get("id")
            if not cid:
                validation_errors.append(f"Line {line_no}: missing 'id'")
                continue
            if cid not in pass1_cases:
                validation_errors.append(f"Line {line_no}: unknown case ID '{cid}'")
                continue
            if cid in pass2_cases:
                validation_errors.append(f"Line {line_no}: duplicate case ID '{cid}'")
                continue

            outcome = c.get("expected_outcome")
            if outcome not in ("match", "review", "unmatched"):
                validation_errors.append(f"Case {cid}: invalid expected_outcome '{outcome}'")

            sku = c.get("expected_sku")
            if outcome == "match":
                if not sku:
                    validation_errors.append(f"Case {cid}: expected_outcome is match but expected_sku is null")
                elif sku not in catalog:
                    validation_errors.append(f"Case {cid}: expected_sku '{sku}' not in catalog")
            else:
                if sku is not None:
                    validation_errors.append(f"Case {cid}: expected_sku must be null for outcome '{outcome}'")

            rat = c.get("rationale")
            if not rat or not isinstance(rat, str) or len(rat.strip()) < 5:
                validation_errors.append(f"Case {cid}: rationale is missing or too brief")

            pass2_cases[cid] = c

    if len(pass2_cases) != len(pass1_cases):
        validation_errors.append(f"Expected {len(pass1_cases)} cases, got {len(pass2_cases)}")

    if validation_errors:
        print(f"Validation FAILED with {len(validation_errors)} error(s):")
        for err in validation_errors:
            print(f"  - {err}")
        sys.exit(1)

    print("Submission schema validation PASSED.\n")

    # Compare Pass 1 and Pass 2
    outcome_matches = 0
    sku_matches = 0
    total = len(pass1_cases)
    discrepancies = []

    for cid in sorted(pass1_cases.keys()):
        p1 = pass1_cases[cid]
        p2 = pass2_cases[cid]

        outcome_agree = (p1["expected_outcome"] == p2["expected_outcome"])
        sku_agree = (p1.get("expected_sku") == p2.get("expected_sku"))

        if outcome_agree:
            outcome_matches += 1
        if sku_agree:
            sku_matches += 1

        if not (outcome_agree and sku_agree):
            discrepancies.append({
                "id": cid,
                "input": p1["input"],
                "pass1_outcome": p1["expected_outcome"],
                "pass1_sku": p1.get("expected_sku"),
                "pass1_rationale": p1.get("rationale"),
                "pass2_outcome": p2["expected_outcome"],
                "pass2_sku": p2.get("expected_sku"),
                "pass2_rationale": p2.get("rationale"),
            })

    outcome_agreement_rate = (outcome_matches / total) * 100
    sku_agreement_rate = (sku_matches / total) * 100

    print("=" * 70)
    print("INTER-ANNOTATOR RECONCILIATION SUMMARY")
    print("=" * 70)
    print(f"Total Cases Evaluated:       {total}")
    print(f"Outcome Agreement Rate:      {outcome_agreement_rate:.2f}% ({outcome_matches}/{total})")
    print(f"Full Agreement (Outcome+SKU): {sku_agreement_rate:.2f}% ({sku_matches}/{total})")
    print(f"Discrepancies Identified:   {len(discrepancies)}")
    print("=" * 70)

    if discrepancies:
        print("\nDISCREPANCIES IDENTIFIED (Requires Reviewer Reconciliation):")
        print("-" * 70)
        for d in discrepancies:
            print(f"Case ID: {d['id']} | Input: \"{d['input']}\"")
            print(f"  Pass 1: outcome={d['pass1_outcome']}, sku={d['pass1_sku']}")
            print(f"  Pass 2: outcome={d['pass2_outcome']}, sku={d['pass2_sku']}")
            print(f"  Pass 1 Rationale: {d['pass1_rationale']}")
            print(f"  Pass 2 Rationale: {d['pass2_rationale']}")
            print("-" * 70)
    else:
        print("\nAll cases have identical outcomes and SKUs across both passes!")

def main():
    parser = argparse.ArgumentParser(description="Reconcile Pass 1 and Pass 2 Evaluation Labels")
    parser.add_argument("--submission", required=True, type=Path, help="Path to second-pass labels JSONL file")
    args = parser.parse_args()
    reconcile(args.submission)

if __name__ == "__main__":
    main()
