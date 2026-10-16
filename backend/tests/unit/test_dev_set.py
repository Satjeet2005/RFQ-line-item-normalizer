"""
Regression tests for development set cases (eval/dev/cases.jsonl).
Verifies that all 12 dev cases pass with the locked matching configuration.
"""
import json
from pathlib import Path
import pytest

from domain.normalizer import normalize_line
from domain.matcher import ProposedMatcher

ROOT_DIR = Path(__file__).resolve().parent.parent.parent.parent

@pytest.fixture(scope="module")
def dev_environment():
    catalog_path = ROOT_DIR / "data" / "catalog.json"
    with open(catalog_path, "r", encoding="utf-8") as f:
        catalog = json.load(f)

    config_path = ROOT_DIR / "data" / "matching_config.json"
    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)

    dev_cases_path = ROOT_DIR / "eval" / "dev" / "cases.jsonl"
    with open(dev_cases_path, "r", encoding="utf-8") as f:
        dev_cases = [json.loads(line) for line in f if line.strip()]

    matcher = ProposedMatcher(catalog, config)
    return matcher, dev_cases

def test_all_12_dev_cases_pass(dev_environment):
    matcher, dev_cases = dev_environment
    outcome_map = {
        "proposed": "match",
        "ambiguous": "review",
        "unmatched": "unmatched"
    }

    assert len(dev_cases) == 12

    for c in dev_cases:
        norm = normalize_line(c["input"])
        res = matcher.match(norm)
        actual_outcome = outcome_map.get(res.system_outcome)
        top_cand = res.candidates[0] if res.candidates else None
        top_sku = top_cand.sku if top_cand else None

        expected_outcome = c["expected_outcome"]
        expected_sku = c.get("expected_sku")

        assert actual_outcome == expected_outcome, (
            f"Case {c['id']} outcome mismatch: expected {expected_outcome}, got {actual_outcome} "
            f"(system_outcome={res.system_outcome}, reasons={res.reason_codes})"
        )

        if expected_outcome == "match":
            assert top_sku == expected_sku, (
                f"Case {c['id']} SKU mismatch: expected {expected_sku}, got {top_sku}"
            )
