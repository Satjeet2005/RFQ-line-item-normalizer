"""
Report generator for rfq_eval.
Generates deterministic report.json and report.md per PRD Section K.
"""
import json
from typing import Dict, Any

def generate_report_markdown(report_data: Dict[str, Any]) -> str:
    meta = report_data["metadata"]
    b = report_data["baseline"]
    p = report_data["proposed"]

    lines = [
        "# RFQ Matcher Evaluation Benchmark Report",
        "",
        "> [!IMPORTANT]",
        "> Results are on 40 synthetic cases authored by the project owner; they are not real-world accuracy and do not show business impact.",
        "",
        "> [!NOTE]",
        "> The baseline is a deliberately naive highest-token-overlap heuristic with zero unit logic, spec extraction, or abstention capability. Its failure rates on this synthetic benchmark highlight the risks of unguided lexical matching on near-duplicate products; they do not represent real-world procurement failure rates or third-party performance.",
        "",
        "## 1. Traceability and Metadata",
        "",
        f"- **Dataset Version:** `{meta['dataset_version']}`",
        f"- **Dataset Manifest SHA-256:** `{meta['dataset_manifest_sha256']}`",
        f"- **Config SHA-256:** `{meta['config_sha256']}`",
        f"- **Code Revision:** `{meta['code_revision']}`",
        f"- **Command:** `{meta['command']}`",
        f"- **Raw Results:** `{meta['results_path']}`",
        "",
        "## 2. Critical Safety Failures (Reported First)",
        "",
        "### A. Incorrect Confident Suggestions (M3)",
        ""
    ]

    m3_cases = b["m3_incorrect_confident_suggestions"]["cases"]
    if m3_cases:
        lines.append(f"**Baseline observed {len(m3_cases)} incorrect confident suggestion(s):**")
        lines.append("")
        lines.append("| Case ID | Input | Expected Outcome | Expected SKU | Baseline Outcome | Baseline SKU |")
        lines.append("|---|---|---|---|---|---|")
        for c in m3_cases:
            lines.append(f"| `{c['id']}` | `{c['input']}` | `{c['expected_outcome']}` | `{c.get('expected_sku') or 'null'}` | `{c['actual_outcome']}` | `{c.get('actual_sku') or 'null'}` |")
        lines.append("")
    else:
        lines.append("Baseline: none observed on this dataset.")
        lines.append("")

    if p and p.get("status") != "unavailable":
        p_m3 = p["m3_incorrect_confident_suggestions"]["cases"]
        if p_m3:
            lines.append(f"**Proposed Matcher observed {len(p_m3)} incorrect confident suggestion(s):**")
            lines.append("")
            lines.append("| Case ID | Input | Expected Outcome | Expected SKU | Proposed Outcome | Proposed SKU |")
            lines.append("|---|---|---|---|---|---|")
            for c in p_m3:
                lines.append(f"| `{c['id']}` | `{c['input']}` | `{c['expected_outcome']}` | `{c.get('expected_sku') or 'null'}` | `{c['actual_outcome']}` | `{c.get('actual_sku') or 'null'}` |")
            lines.append("")
        else:
            lines.append("**Proposed Matcher observed 0 incorrect confident suggestions on this dataset.**")
            lines.append("")

    lines.append("### B. Missed Escalations (M4)")
    lines.append("")
    m4_cases = b["m4_missed_escalations"]["cases"]
    if m4_cases:
        lines.append(f"**Baseline observed {len(m4_cases)} missed escalation(s) (proposing when review or unmatched was required):**")
        lines.append("")
        lines.append("| Case ID | Input | Expected Outcome | Baseline Outcome | Baseline SKU |")
        lines.append("|---|---|---|---|---|")
        for c in m4_cases:
            lines.append(f"| `{c['id']}` | `{c['input']}` | `{c['expected_outcome']}` | `{c['actual_outcome']}` | `{c.get('actual_sku') or 'null'}` |")
        lines.append("")
    else:
        lines.append("Baseline: none observed on this dataset.")
        lines.append("")

    if p and p.get("status") != "unavailable":
        p_m4 = p["m4_missed_escalations"]["cases"]
        if p_m4:
            lines.append(f"**Proposed Matcher observed {len(p_m4)} missed escalation(s):**")
            lines.append("")
            lines.append("| Case ID | Input | Expected Outcome | Proposed Outcome | Proposed SKU |")
            lines.append("|---|---|---|---|---|")
            for c in p_m4:
                lines.append(f"| `{c['id']}` | `{c['input']}` | `{c['expected_outcome']}` | `{c['actual_outcome']}` | `{c.get('actual_sku') or 'null'}` |")
            lines.append("")
        else:
            lines.append("**Proposed Matcher observed 0 missed escalations on this dataset.**")
            lines.append("")

    lines.append("## 3. Benchmark Metrics Summary")
    lines.append("")
    lines.append("| Metric ID | Metric Description | Naive Baseline | Proposed Matcher |")
    lines.append("|---|---|---|---|")

    def fmt_rate(obj):
        if not obj or obj.get("rate") is None:
            return "n/a"
        num = obj.get("numerator")
        den = obj.get("denominator")
        pct = obj["rate"] * 100
        if num is not None and den is not None:
            return f"{pct:.2f}% ({num}/{den})"
        return f"{pct:.2f}%"

    p_available = p and p.get("status") != "unavailable"

    p_m1 = fmt_rate(p.get("m1_top_candidate_correct_rate")) if p_available else "*pending Phase 2*"
    p_m2 = fmt_rate(p.get("m2_proposed_precision")) if p_available else "*pending Phase 2*"
    p_m3 = fmt_rate(p.get("m3_incorrect_confident_suggestions")) if p_available else "*pending Phase 2*"
    p_m4 = fmt_rate(p.get("m4_missed_escalations")) if p_available else "*pending Phase 2*"
    p_m5 = fmt_rate(p.get("m5_over_abstention_rate")) if p_available else "*pending Phase 2*"
    p_m6 = fmt_rate(p.get("m6_appropriate_abstention_rate")) if p_available else "*pending Phase 2*"
    p_m7 = fmt_rate(p.get("m7_unmatched_detection_rate")) if p_available else "*pending Phase 2*"
    p_m8 = fmt_rate(p.get("m8_normalization_accuracy")) if p_available else "*pending Phase 2*"
    p_m9 = fmt_rate(p.get("m9_validation_rule_violations")) if p_available else "*pending Phase 2*"

    lines.append(f"| **M1** | Top-candidate correct rate | {fmt_rate(b['m1_top_candidate_correct_rate'])} | {p_m1} |")
    lines.append(f"| **M2** | Proposed precision | {fmt_rate(b['m2_proposed_precision'])} | {p_m2} |")
    lines.append(f"| **M3** | Incorrect confident suggestions rate | {fmt_rate(b['m3_incorrect_confident_suggestions'])} | {p_m3} |")
    lines.append(f"| **M4** | Missed escalations rate | {fmt_rate(b['m4_missed_escalations'])} | {p_m4} |")
    lines.append(f"| **M5** | Over-abstention rate | {fmt_rate(b['m5_over_abstention_rate'])} | {p_m5} |")
    lines.append(f"| **M6** | Appropriate abstention rate | {fmt_rate(b['m6_appropriate_abstention_rate'])} | {p_m6} |")
    lines.append(f"| **M7** | Unmatched detection rate | {fmt_rate(b['m7_unmatched_detection_rate'])} | {p_m7} |")
    lines.append(f"| **M8** | Normalization accuracy | n/a (no normalizer in baseline) | {p_m8} |")
    lines.append(f"| **M9** | Validation rule violations | n/a | {p_m9} |")
    lines.append("")

    lines.append("## 4. Proposed Matcher Status")
    lines.append("")
    if p_available:
        lines.append("> [!NOTE]")
        lines.append("> Proposed matcher (`domain/matcher.py`) and deterministic normalizer (`domain/normalizer.py`) evaluated under locked configuration `data/matching_config.json`.")
    else:
        lines.append("> [!NOTE]")
        lines.append(f"> {p.get('note', 'Phase 1 placeholder')}")
    lines.append("")

    return "\n".join(lines) + "\n"
