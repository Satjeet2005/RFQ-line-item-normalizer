"""
Unit tests for metric computation functions on hand-computed fixture dataset.
Covers Checklist P1 V12.
"""
from rfq_eval.metrics import compute_metrics

def test_metrics_hand_computed_fixture():
    # 5 test cases with known hand-computed expected metrics:
    # 1. E=match, P=proposed, actual_sku matches expected_sku -> correct proposed
    # 2. E=match, P=proposed, actual_sku differs -> incorrect confident suggestion (M3)
    # 3. E=review, P=proposed -> missed escalation (M4) + M3
    # 4. E=review, P=ambiguous -> appropriate abstention (M6)
    # 5. E=unmatched, P=unmatched -> unmatched detection (M7)
    tiny_results = [
        {
            "id": "T-1",
            "input": "item 1",
            "expected_outcome": "match",
            "expected_sku": "SKU-1",
            "actual_outcome": "proposed",
            "actual_sku": "SKU-1"
        },
        {
            "id": "T-2",
            "input": "item 2",
            "expected_outcome": "match",
            "expected_sku": "SKU-2",
            "actual_outcome": "proposed",
            "actual_sku": "SKU-9"
        },
        {
            "id": "T-3",
            "input": "item 3",
            "expected_outcome": "review",
            "expected_sku": None,
            "actual_outcome": "proposed",
            "actual_sku": "SKU-3"
        },
        {
            "id": "T-4",
            "input": "item 4",
            "expected_outcome": "review",
            "expected_sku": None,
            "actual_outcome": "ambiguous",
            "actual_sku": None
        },
        {
            "id": "T-5",
            "input": "item 5",
            "expected_outcome": "unmatched",
            "expected_sku": None,
            "actual_outcome": "unmatched",
            "actual_sku": None
        }
    ]

    metrics = compute_metrics(tiny_results, "tiny_system")

    # Hand calculations:
    # N total = 5
    # E=match: 2 (T-1, T-2)
    # E=review: 2 (T-3, T-4)
    # E=unmatched: 1 (T-5)
    # E in {review, unmatched}: 3
    # P=proposed: 3 (T-1, T-2, T-3)
    # Correct proposed: 1 (T-1)
    # M1 (Top-candidate correct rate): 1 / 2 = 0.5000
    assert metrics["m1_top_candidate_correct_rate"]["rate"] == 0.5000
    assert metrics["m1_top_candidate_correct_rate"]["numerator"] == 1
    assert metrics["m1_top_candidate_correct_rate"]["denominator"] == 2

    # M2 (Proposed precision): 1 / 3 = 0.3333
    assert metrics["m2_proposed_precision"]["rate"] == 0.3333
    assert metrics["m2_proposed_precision"]["numerator"] == 1
    assert metrics["m2_proposed_precision"]["denominator"] == 3

    # M3 (Incorrect confident suggestions): 2 (T-2, T-3), rate = 2/3 = 0.6667
    assert metrics["m3_incorrect_confident_suggestions"]["count"] == 2
    assert metrics["m3_incorrect_confident_suggestions"]["rate"] == 0.6667
    assert [c["id"] for c in metrics["m3_incorrect_confident_suggestions"]["cases"]] == ["T-2", "T-3"]

    # M4 (Missed escalations): 1 (T-3), rate = 1 / 3 = 0.3333
    assert metrics["m4_missed_escalations"]["count"] == 1
    assert metrics["m4_missed_escalations"]["rate"] == 0.3333
    assert [c["id"] for c in metrics["m4_missed_escalations"]["cases"]] == ["T-3"]

    # M5 (Over-abstention rate): 0 / 2 = 0.0
    assert metrics["m5_over_abstention_rate"]["rate"] == 0.0

    # M6 (Appropriate abstention): 1 / 2 = 0.5000 (T-4 was review and ambiguous)
    assert metrics["m6_appropriate_abstention_rate"]["rate"] == 0.5000

    # M7 (Unmatched detection): 1 / 1 = 1.0000 (T-5)
    assert metrics["m7_unmatched_detection_rate"]["rate"] == 1.0000

def test_metrics_edge_cases_zero_division():
    # Case with 0 proposed cases and 0 expected matches
    empty_results = [
        {
            "id": "T-E1",
            "input": "unknown item",
            "expected_outcome": "unmatched",
            "expected_sku": None,
            "actual_outcome": "unmatched",
            "actual_sku": None
        }
    ]
    metrics = compute_metrics(empty_results, "edge_system")
    # M1 has 0 expected matches -> None
    assert metrics["m1_top_candidate_correct_rate"]["rate"] is None
    # M2 has 0 proposed -> None
    assert metrics["m2_proposed_precision"]["rate"] is None
    # M3 rate has 0 proposed -> None
    assert metrics["m3_incorrect_confident_suggestions"]["rate"] is None
    assert metrics["m3_incorrect_confident_suggestions"]["count"] == 0
    # M4 has 1 expected unmatched, 0 proposed -> count 0, rate 0.0
    assert metrics["m4_missed_escalations"]["count"] == 0
    assert metrics["m4_missed_escalations"]["rate"] == 0.0
    # M7 has 1 unmatched -> rate 1.0
    assert metrics["m7_unmatched_detection_rate"]["rate"] == 1.0
