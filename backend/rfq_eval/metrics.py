"""
Evaluation metric computations conforming to PRD Section K.
Metrics M1 through M9.
"""
from typing import List, Dict, Any, Optional

def round_4dp(val: Optional[float]) -> Optional[float]:
    if val is None:
        return None
    return round(float(val), 4)

def compute_metrics(
    results: List[Dict[str, Any]],
    system_name: str,
    catalog_map: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    n_total = len(results)
    n_expected_match = sum(1 for r in results if r["expected_outcome"] == "match")
    n_expected_review = sum(1 for r in results if r["expected_outcome"] == "review")
    n_expected_unmatched = sum(1 for r in results if r["expected_outcome"] == "unmatched")
    n_expected_escalated = n_expected_review + n_expected_unmatched

    n_proposed = sum(1 for r in results if r["actual_outcome"] == "proposed")
    n_ambiguous = sum(1 for r in results if r["actual_outcome"] == "ambiguous")
    n_unmatched = sum(1 for r in results if r["actual_outcome"] == "unmatched")

    # Correct proposed: P == proposed AND E == match AND proposed_sku == expected_sku
    correct_proposed_cases = [
        r for r in results
        if r["actual_outcome"] == "proposed"
        and r["expected_outcome"] == "match"
        and r.get("actual_sku") == r.get("expected_sku")
    ]
    n_correct_proposed = len(correct_proposed_cases)

    # M1: Top-candidate correct rate = correct_proposed / N(E=match)
    m1_rate = (n_correct_proposed / n_expected_match) if n_expected_match > 0 else None

    # M2: Proposed precision = correct_proposed / N(P=proposed)
    m2_rate = (n_correct_proposed / n_proposed) if n_proposed > 0 else None

    # M3: Incorrect confident suggestions = P==proposed and not correct_proposed
    m3_cases = [
        {
            "id": r["id"],
            "input": r["input"],
            "expected_outcome": r["expected_outcome"],
            "expected_sku": r.get("expected_sku"),
            "actual_outcome": r["actual_outcome"],
            "actual_sku": r.get("actual_sku")
        }
        for r in results
        if r["actual_outcome"] == "proposed"
        and not (r["expected_outcome"] == "match" and r.get("actual_sku") == r.get("expected_sku"))
    ]
    m3_rate = (len(m3_cases) / n_proposed) if n_proposed > 0 else None

    # M4: Missed escalations = P==proposed and E in {review, unmatched}
    m4_cases = [
        {
            "id": r["id"],
            "input": r["input"],
            "expected_outcome": r["expected_outcome"],
            "expected_sku": r.get("expected_sku"),
            "actual_outcome": r["actual_outcome"],
            "actual_sku": r.get("actual_sku")
        }
        for r in results
        if r["actual_outcome"] == "proposed"
        and r["expected_outcome"] in ("review", "unmatched")
    ]
    m4_rate = (len(m4_cases) / n_expected_escalated) if n_expected_escalated > 0 else None

    # M5: Over-abstention rate = N(E=match and P!=proposed) / N(E=match)
    n_over_abstention = sum(1 for r in results if r["expected_outcome"] == "match" and r["actual_outcome"] != "proposed")
    m5_rate = (n_over_abstention / n_expected_match) if n_expected_match > 0 else None

    # M6: Appropriate abstention = N(E=review and P!=proposed) / N(E=review)
    n_appropriate_abstention = sum(1 for r in results if r["expected_outcome"] == "review" and r["actual_outcome"] != "proposed")
    m6_rate = (n_appropriate_abstention / n_expected_review) if n_expected_review > 0 else None

    # M7: Unmatched detection = N(E=unmatched and P=unmatched) / N(E=unmatched)
    n_unmatched_detected = sum(1 for r in results if r["expected_outcome"] == "unmatched" and r["actual_outcome"] == "unmatched")
    m7_rate = (n_unmatched_detected / n_expected_unmatched) if n_expected_unmatched > 0 else None
    n_unmatched_proposed = sum(1 for r in results if r["expected_outcome"] == "unmatched" and r["actual_outcome"] == "proposed")


    # M8: Normalization accuracy (proposed system only)
    m8_data = None
    if system_name == "proposed":
        total_fields_checked = 0
        total_fields_matched = 0
        per_field = {
            "quantity": {"matched": 0, "total": 0},
            "unit": {"matched": 0, "total": 0},
            "spec": {"matched": 0, "total": 0},
            "issue_codes": {"matched": 0, "total": 0}
        }
        for r in results:
            exp_norm = r.get("expected_normalized")
            act_norm = r.get("actual_normalized")
            if not exp_norm or not act_norm:
                continue

            if exp_norm.get("quantity") is not None:
                per_field["quantity"]["total"] += 1
                total_fields_checked += 1
                act_qty = act_norm.get("quantity")
                act_qty_str = str(act_qty) if act_qty is not None else None
                if str(exp_norm["quantity"]) == act_qty_str:
                    per_field["quantity"]["matched"] += 1
                    total_fields_matched += 1

            if exp_norm.get("unit") is not None:
                per_field["unit"]["total"] += 1
                total_fields_checked += 1
                if exp_norm["unit"] == act_norm.get("unit"):
                    per_field["unit"]["matched"] += 1
                    total_fields_matched += 1

            exp_spec = exp_norm.get("spec", {})
            act_spec = act_norm.get("spec", {})
            for sk, sv in exp_spec.items():
                per_field["spec"]["total"] += 1
                total_fields_checked += 1
                if act_spec.get(sk) == sv:
                    per_field["spec"]["matched"] += 1
                    total_fields_matched += 1

            if "issue_codes" in exp_norm:
                per_field["issue_codes"]["total"] += 1
                total_fields_checked += 1
                if set(exp_norm.get("issue_codes", [])) == set(act_norm.get("issue_codes", [])):
                    per_field["issue_codes"]["matched"] += 1
                    total_fields_matched += 1

        overall_m8 = (total_fields_matched / total_fields_checked) if total_fields_checked > 0 else None
        m8_data = {
            "rate": round_4dp(overall_m8),
            "numerator": total_fields_matched,
            "denominator": total_fields_checked,
            "per_field": per_field
        }

    # M9: Validation rule violations (proposed system only)
    m9_data = None
    if system_name == "proposed":
        from domain.units import check_unit_compatibility
        violations = 0
        violation_details = []
        checked_cases = 0
        for r in results:
            if r["actual_outcome"] == "proposed":
                checked_cases += 1
                exp_norm = r.get("expected_normalized")
                cand_sku = r.get("actual_sku")
                if exp_norm and cand_sku and catalog_map:
                    cand_item = catalog_map.get(cand_sku, {})
                    cand_attrs = cand_item.get("attributes", {})
                    cand_uom = cand_item.get("uom", "")

                    for k, v in exp_norm.get("spec", {}).items():
                        c_val = cand_attrs.get(k)
                        if c_val is not None and c_val != v:
                            violations += 1
                            violation_details.append({
                                "case_id": r["id"],
                                "type": f"SPEC_VIOLATION:{k}",
                                "expected": v,
                                "candidate_value": c_val
                            })

                    exp_unit = exp_norm.get("unit")
                    if exp_unit and cand_uom:
                        compat, _ = check_unit_compatibility(exp_unit, cand_uom)
                        if not compat:
                            violations += 1
                            violation_details.append({
                                "case_id": r["id"],
                                "type": "UNIT_VIOLATION",
                                "expected_unit": exp_unit,
                                "candidate_uom": cand_uom
                            })

        m9_rate = (violations / n_proposed) if n_proposed > 0 else 0.0
        m9_data = {
            "count": violations,
            "rate": round_4dp(m9_rate),
            "denominator": n_proposed,
            "checked_cases": checked_cases,
            "violations": violation_details
        }

    return {
        "system": system_name,
        "sample_size": n_total,
        "counts": {
            "expected_match": n_expected_match,
            "expected_review": n_expected_review,
            "expected_unmatched": n_expected_unmatched,
            "system_proposed": n_proposed,
            "system_ambiguous": n_ambiguous,
            "system_unmatched": n_unmatched,
            "correct_proposed": n_correct_proposed
        },
        "m1_top_candidate_correct_rate": {
            "rate": round_4dp(m1_rate),
            "numerator": n_correct_proposed,
            "denominator": n_expected_match
        },
        "m2_proposed_precision": {
            "rate": round_4dp(m2_rate),
            "numerator": n_correct_proposed,
            "denominator": n_proposed
        },
        "m3_incorrect_confident_suggestions": {
            "count": len(m3_cases),
            "rate": round_4dp(m3_rate),
            "denominator": n_proposed,
            "cases": m3_cases
        },
        "m4_missed_escalations": {
            "count": len(m4_cases),
            "rate": round_4dp(m4_rate),
            "denominator": n_expected_escalated,
            "cases": m4_cases
        },
        "m5_over_abstention_rate": {
            "rate": round_4dp(m5_rate),
            "numerator": n_over_abstention,
            "denominator": n_expected_match
        },
        "m6_appropriate_abstention_rate": {
            "rate": round_4dp(m6_rate),
            "numerator": n_appropriate_abstention,
            "denominator": n_expected_review
        },
        "m7_unmatched_detection_rate": {
            "rate": round_4dp(m7_rate),
            "numerator": n_unmatched_detected,
            "denominator": n_expected_unmatched,
            "proposed_count": n_unmatched_proposed
        },
        "m8_normalization_accuracy": m8_data,
        "m9_validation_rule_violations": m9_data
    }
