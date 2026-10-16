"""
Evaluation metric computations conforming to PRD Section K.
Metrics M1 through M9.
"""
from typing import List, Dict, Any, Optional

def round_4dp(val: Optional[float]) -> Optional[float]:
    if val is None:
        return None
    return round(float(val), 4)

def compute_metrics(results: List[Dict[str, Any]], system_name: str) -> Dict[str, Any]:
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
        "m8_normalization_accuracy": None,
        "m9_validation_rule_violations": None
    }
