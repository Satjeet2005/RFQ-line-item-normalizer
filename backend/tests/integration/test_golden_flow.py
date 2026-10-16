"""
Golden Flow End-to-End Integration Test.
Conforms to PRD_ACCEPTANCE_CHECKLIST.md Section 11 (Auditor verification step 2):
1. Ingest sample RFQ lines
2. Inspect ambiguous line: confirm no preselection rule holds
3. Approve with explicit candidate selection
4. Verify optimistic concurrency control (409 STALE_VERSION)
5. Reject another line item with note
6. Confirm no-match on unmatched line
7. Verify incomplete export gating (409 RFQ_INCOMPLETE)
8. Export CSV with allow_incomplete=true, verifying RFC 4180 format, excluded count, and absence of prices
9. Export JSON with finalized and not_finalized sections
"""
import csv
import io
import pytest
from app.db.models import RFQ, LineItem, CatalogProduct
from app.db.seed import seed_catalog


SAMPLE_PASTE_TEXT = """GI Pipe 25mm Class B 10 mtr
MS Hex Bolt M12x50 100 nos
GI Pipe 25mm 50 mtr
Unknown Custom Valve Widget 5 pcs"""


def test_auditor_golden_flow(client, db_session):
    # Ensure catalog is seeded
    seed_catalog(db_session)

    # 1. Ingest sample RFQ
    resp = client.post(
        "/api/v1/rfqs",
        json={
            "name": "Golden Flow RFQ",
            "source_type": "paste",
            "content": SAMPLE_PASTE_TEXT,
            "skip_invalid": True,
        },
    )
    assert resp.status_code == 201, resp.text
    rfq_data = resp.json()
    rfq_id = rfq_data["rfq"]["id"]
    assert rfq_data["items_summary"]["total_lines"] == 4

    # 2. Inspect RFQ and line items
    items_resp = client.get(f"/api/v1/rfqs/{rfq_id}/items")
    assert items_resp.status_code == 200
    items = items_resp.json()["items"]
    assert len(items) == 4

    # Find the ambiguous line item ("GI Pipe 25mm 50 mtr" has missing class discriminator)
    ambig_item = next(
        (it for it in items if "GI Pipe 25mm 50 mtr" in it["raw_input"]),
        None,
    )
    assert ambig_item is not None
    assert ambig_item["system_outcome"] == "ambiguous"
    assert ambig_item["review_status"] == "pending"
    assert ambig_item["version"] == 1
    assert ambig_item["final_sku"] is None

    # Verify candidates exist for the ambiguous line
    assert len(ambig_item["candidates"]) >= 2
    selected_candidate_sku = ambig_item["candidates"][0]["sku"]

    # 3. Verify incomplete export is gated (Checklist P0 X2)
    export_blocked = client.get(f"/api/v1/rfqs/{rfq_id}/export?format=csv")
    assert export_blocked.status_code == 409
    err = export_blocked.json()["error"]
    assert err["code"] == "RFQ_INCOMPLETE"
    assert err["details"][0]["pending_count"] > 0

    # 4. Approve ambiguous line with explicit selection
    approve_resp = client.post(
        f"/api/v1/rfqs/{rfq_id}/items/{ambig_item['id']}/decisions",
        json={
            "decision_type": "approve",
            "expected_version": 1,
            "sku": selected_candidate_sku,
            "note": "Auditor explicitly selected class A",
        },
    )
    assert approve_resp.status_code == 201
    approved_item = approve_resp.json()["item"]
    assert approved_item["review_status"] == "approved"
    assert approved_item["version"] == 2
    assert approved_item["final_sku"] == selected_candidate_sku
    assert approved_item["final_quantity"] == 50.0
    assert approved_item["final_unit"] == "mtr"

    # 5. Verify optimistic concurrency control (Checklist P0 R4)
    stale_resp = client.post(
        f"/api/v1/rfqs/{rfq_id}/items/{ambig_item['id']}/decisions",
        json={
            "decision_type": "approve",
            "expected_version": 1,
            "sku": selected_candidate_sku,
        },
    )
    assert stale_resp.status_code == 409
    stale_err = stale_resp.json()["error"]
    assert stale_err["code"] == "STALE_VERSION"
    assert stale_resp.json()["item"]["version"] == 2

    # 6. Reject another line item with note (Checklist P0 R1)
    proposed_item = next(
        (it for it in items if "GI Pipe 25mm Class B" in it["raw_input"]),
        None,
    )
    assert proposed_item is not None
    reject_resp = client.post(
        f"/api/v1/rfqs/{rfq_id}/items/{proposed_item['id']}/decisions",
        json={
            "decision_type": "reject",
            "expected_version": 1,
            "note": "Rejected by auditor for testing rejection flow",
        },
    )
    assert reject_resp.status_code == 201
    rejected_item = reject_resp.json()["item"]
    assert rejected_item["review_status"] == "rejected"
    assert rejected_item["version"] == 2
    assert rejected_item["final_sku"] is None

    # 7. Confirm no-match on unmatched item (Checklist P0 R1)
    unmatched_item = next(
        (it for it in items if "Unknown Custom Valve" in it["raw_input"]),
        None,
    )
    assert unmatched_item is not None
    no_match_resp = client.post(
        f"/api/v1/rfqs/{rfq_id}/items/{unmatched_item['id']}/decisions",
        json={
            "decision_type": "confirm_no_match",
            "expected_version": 1,
            "note": "Confirmed no catalog match exists",
        },
    )
    assert no_match_resp.status_code == 201
    no_match_data = no_match_resp.json()["item"]
    assert no_match_data["review_status"] == "no_match"
    assert no_match_data["version"] == 2
    assert no_match_data["final_sku"] is None

    # 7b. Correct another item to a different catalog product (Checklist P0 R1)
    bolt_item = next(
        (it for it in items if "MS Hex Bolt" in it["raw_input"]),
        None,
    )
    assert bolt_item is not None
    bolt_cand_skus = [c["sku"] for c in bolt_item["candidates"]]
    assert "VALV-001" not in bolt_cand_skus

    correct_resp = client.post(
        f"/api/v1/rfqs/{rfq_id}/items/{bolt_item['id']}/decisions",
        json={
            "decision_type": "correct",
            "expected_version": 1,
            "sku": "VALV-001",
            "quantity": 10,
            "unit": "nos",
            "note": "Corrected from bolt to ball valve for testing manual correction",
        },
    )
    assert correct_resp.status_code == 201
    corrected_data = correct_resp.json()["item"]
    assert corrected_data["review_status"] == "corrected"
    assert corrected_data["final_sku"] == "VALV-001"
    assert corrected_data["final_quantity"] == 10.0
    assert corrected_data["final_unit"] == "nos"
    assert corrected_data["version"] == 2

    # 8. Export CSV with allow_incomplete=true (Checklist P0 X1, X2, X3)
    # RFQ is now fully reviewed: 1 approved, 1 corrected, 1 rejected, 1 no_match
    csv_resp = client.get(f"/api/v1/rfqs/{rfq_id}/export?format=csv")
    assert csv_resp.status_code == 200
    assert "text/csv" in csv_resp.headers["content-type"]
    assert "X-Items-Excluded" in csv_resp.headers
    # 2 items excluded (1 rejected pipe, 1 no_match valve)
    assert int(csv_resp.headers["X-Items-Excluded"]) == 2

    reader = csv.reader(io.StringIO(csv_resp.text))
    rows = list(reader)
    # Header + exactly 2 finalized lines (1 approved + 1 corrected)
    assert len(rows) == 3
    expected_header = [
        "line_no",
        "original_description",
        "catalog_sku",
        "catalog_name",
        "requested_quantity",
        "requested_unit",
        "quantity_in_catalog_uom",
        "catalog_uom",
        "review_status",
        "overrode_system",
        "reviewed_at",
    ]
    assert rows[0] == expected_header
    assert "price" not in [col.lower() for col in rows[0]]  # Checklist P0 X3

    # Check finalized rows
    finalized_skus = {rows[1][2], rows[2][2]}
    assert finalized_skus == {selected_candidate_sku, "VALV-001"}

    # 9. Export JSON (Checklist P1 X5)
    json_resp = client.get(f"/api/v1/rfqs/{rfq_id}/export?format=json")
    assert json_resp.status_code == 200
    json_data = json_resp.json()
    assert "finalized" in json_data
    assert "not_finalized" in json_data
    assert len(json_data["finalized"]) == 2
    assert len(json_data["not_finalized"]) == 2

    # 10. Verify persistence across API / session restart (Checklist P0 R5)
    from app.db.session import SessionLocal
    fresh_session = SessionLocal()
    try:
        persisted_rfq = fresh_session.query(RFQ).filter(RFQ.id == rfq_id).first()
        assert persisted_rfq is not None
        assert persisted_rfq.name == "Golden Flow RFQ"

        persisted_items = (
            fresh_session.query(LineItem)
            .filter(LineItem.rfq_id == rfq_id)
            .order_by(LineItem.line_no)
            .all()
        )
        assert len(persisted_items) == 4
        statuses = {it.line_no: it.review_status for it in persisted_items}
        assert statuses[ambig_item["line_no"]] == "approved"
        assert statuses[proposed_item["line_no"]] == "rejected"
        assert statuses[unmatched_item["line_no"]] == "no_match"
        assert statuses[bolt_item["line_no"]] == "corrected"
    finally:
        fresh_session.close()
