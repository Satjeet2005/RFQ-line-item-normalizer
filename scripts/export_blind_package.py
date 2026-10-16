"""
Export blind second-pass review package.
Strips all Pass 1 outcomes, SKUs, normalized fields, rationales, and category hints.
"""
import json
import shutil
from pathlib import Path

ROOT = Path("/home/satjeet/Desktop/isocode")
DATASET_PATH = ROOT / "eval" / "dataset" / "v1" / "cases.jsonl"
CATALOG_PATH = ROOT / "data" / "catalog.json"
SECOND_PASS_DIR = ROOT / "eval" / "second_pass"
SUBMISSIONS_DIR = SECOND_PASS_DIR / "submissions"

def export_blind_package():
    SECOND_PASS_DIR.mkdir(parents=True, exist_ok=True)
    SUBMISSIONS_DIR.mkdir(parents=True, exist_ok=True)

    # 1. Export blind_cases.jsonl
    blind_cases = []
    template_cases = []
    with open(DATASET_PATH, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            case = json.loads(line)
            blind_cases.append({
                "id": case["id"],
                "input": case["input"]
            })
            template_cases.append({
                "id": case["id"],
                "input": case["input"],
                "expected_outcome": None,
                "expected_sku": None,
                "rationale": ""
            })

    blind_cases_path = SECOND_PASS_DIR / "blind_cases.jsonl"
    with open(blind_cases_path, "w", encoding="utf-8") as f:
        for c in blind_cases:
            f.write(json.dumps(c, ensure_ascii=False) + "\n")

    template_path = SUBMISSIONS_DIR / "template_submission.jsonl"
    with open(template_path, "w", encoding="utf-8") as f:
        for c in template_cases:
            f.write(json.dumps(c, ensure_ascii=False) + "\n")

    # 2. Copy catalog.json for reviewer reference
    shutil.copy2(CATALOG_PATH, SECOND_PASS_DIR / "catalog.json")

    print(f"Exported blind review package to {SECOND_PASS_DIR}:")
    print(f"  - {blind_cases_path} ({len(blind_cases)} cases)")
    print(f"  - {template_path} (blank template)")
    print(f"  - {SECOND_PASS_DIR / 'catalog.json'} (reference catalog)")

if __name__ == "__main__":
    export_blind_package()
