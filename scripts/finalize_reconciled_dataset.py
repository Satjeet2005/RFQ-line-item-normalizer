"""
Script to apply finalized reconciled labels to eval/dataset/v1/cases.jsonl.
Updates E-001, E-034, E-015, E-026, sets second_pass_done=True, and adds review metadata.
"""
import json
from pathlib import Path

ROOT = Path("/home/satjeet/Desktop/isocode")
DATASET_PATH = ROOT / "eval" / "dataset" / "v1" / "cases.jsonl"

def finalize_dataset():
    cases = []
    with open(DATASET_PATH, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                cases.append(json.loads(line))

    for c in cases:
        cid = c["id"]

        # Case E-001 correction
        if cid == "E-001":
            c["expected_sku"] = "PIPE-006"
            c["expected_normalized"]["spec"]["size_mm"] = "25"
            c["expected_normalized"]["spec"]["class"] = "B"
            c["rationale"] = "Exact match to PIPE-006 (GI Pipe 25mm Class B). Clean input with quantity 10 and canonical unit mtr (reconciled from draft typo PIPE-004)."

        # Case E-034 correction
        elif cid == "E-034":
            c["expected_sku"] = "PIPE-003"
            c["expected_normalized"]["spec"]["size_mm"] = "20"
            c["expected_normalized"]["spec"]["class"] = "A"
            c["rationale"] = "Transliterated term 'paip' normalizes to 'pipe'. Clean match to PIPE-003 (GI Pipe 20mm Class A) (reconciled from draft typo PIPE-002)."

        # Case E-015 rationale update
        elif cid == "E-015":
            c["rationale"] = "Catalog item PIPE-006 is measured in length (mtr), while request asks for count (nos). Incompatible unit dimension requires human review (reconciled SKU reference to PIPE-006)."

        # Case E-026 rationale update
        elif cid == "E-026":
            c["rationale"] = "Catalog has PIPE-005 (Class A) and PIPE-006 (Class B). Request lacks class specification. Missing discriminator prevents safe automatic proposal (reconciled SKU references to PIPE-005 and PIPE-006)."

        # Case E-039 rationale note
        elif cid == "E-039":
            c["rationale"] = "Leading quantity '50 mtr' is not extracted in free-text mode (rule D9: trailing quantity only). Line flags MISSING_QUANTITY and routes to review (Pass 2 proposed match; reconciled to review per PRD D9 specification)."

        # Update review metadata on all cases
        c["label_pass"] = {
            "labelled_by": "reconciled_pass1_pass2",
            "created_at": "2026-10-16T09:51:57Z",
            "second_pass_at": "2026-10-16T12:39:58Z",
            "second_pass_done": True,
            "waiver_applied": "project_owner_waiver_d33"
        }

    with open(DATASET_PATH, "w", encoding="utf-8") as f:
        for c in cases:
            f.write(json.dumps(c, ensure_ascii=False) + "\n")

    print(f"Successfully finalized {len(cases)} cases in {DATASET_PATH}")

if __name__ == "__main__":
    finalize_dataset()
