"""
Evaluation execution engine.
Implements Section E Workflow 8 evaluation execution and reporting.
"""
import argparse
import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path

# Ensure backend root is on sys.path
BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from domain.baseline import NaiveBaselineMatcher
from domain.matcher import ProposedMatcher
from domain.normalizer import normalize_line
from domain.split import split_raw_line
from rfq_eval.manifest import verify_manifest, compute_sha256
from rfq_eval.metrics import compute_metrics
from rfq_eval.report import generate_report_markdown

def get_code_revision() -> str:
    git_sha = os.environ.get("GIT_SHA")
    if git_sha:
        return git_sha
    try:
        tag_res = subprocess.run(
            ["git", "describe", "--tags", "--exact-match"],
            capture_output=True,
            text=True,
            check=False
        )
        if tag_res.returncode == 0 and tag_res.stdout.strip():
            rev = tag_res.stdout.strip()
        else:
            res = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                capture_output=True,
                text=True,
                check=False
            )
            rev = res.stdout.strip() if res.returncode == 0 else "unknown"

        # check dirty
        status_res = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True,
            text=True,
            check=False
        )
        if status_res.returncode == 0 and status_res.stdout.strip():
            rev += "+dirty"
        return rev
    except Exception:
        pass
    return "unknown"

def run_evaluation(dataset_dir: Path, system: str, out_dir: Path, command_str: str):
    start_time = time.perf_counter()

    # 1. Verify manifest (exits 2 on mismatch)
    manifest_hash = verify_manifest(dataset_dir)

    # 2. Load catalog
    catalog_path = dataset_dir / "catalog.json"
    if not catalog_path.exists():
        sys.stderr.write("Catalog file missing from dataset\n")
        sys.exit(1)
    with open(catalog_path, "r", encoding="utf-8") as f:
        catalog = json.load(f)

    # 3. Load aliases for splitting
    aliases_path = dataset_dir / "aliases.json"
    if not aliases_path.exists():
        sys.stderr.write("Aliases file missing from dataset\n")
        sys.exit(1)
    with open(aliases_path, "r", encoding="utf-8") as f:
        aliases_data = json.load(f)

    known_unit_aliases = set()
    for u, alias_list in aliases_data.get("units", {}).items():
        known_unit_aliases.add(u.lower())
        for a in alias_list:
            known_unit_aliases.add(a.lower())

    # 4. Load config hash
    config_path = dataset_dir.parent.parent.parent / "data" / "matching_config.json"
    if not config_path.exists():
        # fallback to data/
        config_path = Path("data/matching_config.json")
    config_hash = compute_sha256(config_path) if config_path.exists() else "unknown"

    # 5. Load cases
    cases_path = dataset_dir / "cases.jsonl"
    cases = []
    with open(cases_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                cases.append(json.loads(line))
    # Deterministic order by id
    cases.sort(key=lambda x: x["id"])

    # 6. Run Baseline Matcher
    baseline_matcher = NaiveBaselineMatcher(catalog)
    baseline_results = []
    raw_results_records = []

    for c in cases:
        ingested = split_raw_line(c["input"], known_unit_aliases)
        match_res = baseline_matcher.match(ingested.description_raw)

        top_cand = match_res.candidates[0] if match_res.candidates else None
        rec = {
            "id": c["id"],
            "category": c["category"],
            "input": c["input"],
            "expected_outcome": c["expected_outcome"],
            "expected_sku": c.get("expected_sku"),
            "expected_normalized": c.get("expected_normalized"),
            "actual_outcome": match_res.system_outcome,
            "actual_sku": top_cand.sku if top_cand else None,
            "similarity": top_cand.similarity if top_cand else None,
            "reason_codes": match_res.reason_codes
        }
        baseline_results.append(rec)

        # Raw results file entry
        raw_results_records.append({
            "case_id": c["id"],
            "system": "baseline",
            "input": c["input"],
            "description_raw": ingested.description_raw,
            "expected_outcome": c["expected_outcome"],
            "expected_sku": c.get("expected_sku"),
            "system_outcome": match_res.system_outcome,
            "top_sku": top_cand.sku if top_cand else None,
            "similarity": top_cand.similarity if top_cand else None
        })

    baseline_metrics = compute_metrics(baseline_results, "baseline")

    catalog_map = {item["sku"]: item for item in catalog}

    # 7. Proposed system evaluation
    proposed_metrics = {
        "status": "unavailable",
        "note": "Proposed matcher not executed for this run."
    }
    if system in ("proposed", "both"):
        with open(config_path, "r", encoding="utf-8") as f:
            matching_cfg = json.load(f)
        proposed_matcher = ProposedMatcher(catalog, matching_cfg)
        proposed_results = []
        for c in cases:
            norm_line = normalize_line(c["input"])
            match_res = proposed_matcher.match(norm_line)
            top_cand = match_res.candidates[0] if match_res.candidates else None

            act_normalized = {
                "quantity": str(norm_line.quantity) if norm_line.quantity is not None else None,
                "unit": norm_line.unit,
                "spec": norm_line.spec,
                "issue_codes": norm_line.issue_codes
            }

            rec = {
                "id": c["id"],
                "category": c["category"],
                "input": c["input"],
                "expected_outcome": c["expected_outcome"],
                "expected_sku": c.get("expected_sku"),
                "expected_normalized": c.get("expected_normalized"),
                "actual_normalized": act_normalized,
                "actual_outcome": match_res.system_outcome,
                "actual_sku": top_cand.sku if top_cand else None,
                "similarity": top_cand.similarity if top_cand else None,
                "reason_codes": match_res.reason_codes
            }
            proposed_results.append(rec)

            raw_results_records.append({
                "case_id": c["id"],
                "system": "proposed",
                "input": c["input"],
                "description_raw": norm_line.description_raw,
                "expected_outcome": c["expected_outcome"],
                "expected_sku": c.get("expected_sku"),
                "system_outcome": match_res.system_outcome,
                "top_sku": top_cand.sku if top_cand else None,
                "similarity": top_cand.similarity if top_cand else None,
                "reason_codes": match_res.reason_codes
            })

        proposed_metrics = compute_metrics(proposed_results, "proposed", catalog_map)

    all_second_pass = len(cases) > 0 and all(
        c.get("label_pass", {}).get("second_pass_done") is True for c in cases
    )
    dataset_version = "v1-frozen" if all_second_pass else "v1-draft"

    # 8. Assemble report data
    report_data = {
        "metadata": {
            "dataset_version": dataset_version,
            "dataset_manifest_sha256": manifest_hash,
            "config_sha256": config_hash,
            "code_revision": get_code_revision(),
            "command": command_str,
            "results_path": "results.jsonl"
        },
        "baseline": baseline_metrics,
        "proposed": proposed_metrics
    }

    report_md = generate_report_markdown(report_data)

    # 9. Write outputs
    out_dir.mkdir(parents=True, exist_ok=True)
    results_path = out_dir / "results.jsonl"
    with open(results_path, "w", encoding="utf-8") as f:
        for r in raw_results_records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    report_json_path = out_dir / "report.json"
    with open(report_json_path, "w", encoding="utf-8") as f:
        json.dump(report_data, f, indent=2, sort_keys=True, ensure_ascii=False)
        f.write("\n")

    report_md_path = out_dir / "report.md"
    with open(report_md_path, "w", encoding="utf-8") as f:
        f.write(report_md)

    end_time = time.perf_counter()
    duration = end_time - start_time

    # Timing file (excluded from byte-identical determinism guarantee)
    timing_path = out_dir / "timing.json"
    with open(timing_path, "w", encoding="utf-8") as f:
        json.dump({"wall_clock_seconds": round(duration, 4)}, f, indent=2)
        f.write("\n")

    print(f"Evaluation complete in {duration:.4f}s.")
    print(f"Outputs written to {out_dir}:")
    print(f"  - {results_path}")
    print(f"  - {report_json_path}")
    print(f"  - {report_md_path}")
    print(f"  - {timing_path}")

def main():
    parser = argparse.ArgumentParser(description="RFQ Matcher Evaluation Runner")
    parser.add_argument("--dataset", required=True, type=Path, help="Path to dataset directory")
    parser.add_argument("--system", default="both", choices=["baseline", "proposed", "both"], help="System to evaluate")
    parser.add_argument("--out", required=True, type=Path, help="Output directory for reports")

    args = parser.parse_args()
    cmd_str = f"python -m rfq_eval run --dataset {args.dataset} --system {args.system} --out {args.out}"
    run_evaluation(args.dataset, args.system, args.out, cmd_str)

if __name__ == "__main__":
    main()
