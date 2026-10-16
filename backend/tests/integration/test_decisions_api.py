import pytest
from app.db.models import LineItem


def _create_sample_rfq(client):
    content = """GI pipe 25mm class B 50 mtr
Brass ball valve 1 inch 10 nos
Unknown special gizmo 5 nos
"""
    res = client.post(
        "/api/v1/rfqs",
        json={"name": "Decision Test RFQ", "source_type": "paste", "content": content},
    )
    assert res.status_code == 201
    rfq_id = res.json()["rfq"]["id"]
    items = client.get(f"/api/v1/rfqs/{rfq_id}/items").json()["items"]
    return rfq_id, items

def test_approve_decision(client):
    rfq_id, items = _create_sample_rfq(client)
    item = items[0]
    cand = item["candidates"][0]

    res = client.post(
        f"/api/v1/rfqs/{rfq_id}/items/{item['id']}/decisions",
        json={
            "decision_type": "approve",
            "expected_version": item["version"],
            "sku": cand["sku"],
        },
    )
    assert res.status_code == 201
    data = res.json()
    assert data["item"]["review_status"] == "approved"
    assert data["item"]["final_sku"] == cand["sku"]
    assert data["item"]["final_quantity"] == 50.0
    assert data["item"]["final_unit"] == "mtr"
    assert data["item"]["version"] == item["version"] + 1

    # Check decision record
    assert data["decision"]["decision_type"] == "approve"
    assert data["decision"]["sku"] == cand["sku"]
    assert data["decision"]["status_before"] == "pending"
    assert data["decision"]["status_after"] == "approved"
    assert data["decision"]["version_before"] == item["version"]

def test_approve_validation_sku_not_a_candidate(client):
    rfq_id, items = _create_sample_rfq(client)
    item = items[0]

    # Use a valid catalog SKU that is not in candidates
    res = client.post(
        f"/api/v1/rfqs/{rfq_id}/items/{item['id']}/decisions",
        json={
            "decision_type": "approve",
            "expected_version": item["version"],
            "sku": "VALV-001",  # Ball valve, not pipe candidate
        },
    )
    assert res.status_code == 422
    assert res.json()["error"]["code"] == "SKU_NOT_A_CANDIDATE"

def test_correct_decision(client):
    rfq_id, items = _create_sample_rfq(client)
    item = items[0]  # GI pipe line
    cand_skus = [c["sku"] for c in item["candidates"]]
    assert "VALV-001" not in cand_skus

    # Correct to BBV-025, but BBV-025 requires count unit (nos), so supply unit override
    res = client.post(
        f"/api/v1/rfqs/{rfq_id}/items/{item['id']}/decisions",
        json={
            "decision_type": "correct",
            "expected_version": item["version"],
            "sku": "VALV-001",
            "quantity": 10,
            "unit": "nos",
        },
    )
    assert res.status_code == 201
    data = res.json()
    assert data["item"]["review_status"] == "corrected"
    assert data["item"]["final_sku"] == "VALV-001"
    assert data["item"]["final_quantity"] == 10.0
    assert data["item"]["final_unit"] == "nos"
    assert data["decision"]["overrode_system"] is True

def test_correct_validation_sku_is_a_candidate(client):
    rfq_id, items = _create_sample_rfq(client)
    item = items[0]
    cand_sku = item["candidates"][0]["sku"]

    res = client.post(
        f"/api/v1/rfqs/{rfq_id}/items/{item['id']}/decisions",
        json={
            "decision_type": "correct",
            "expected_version": item["version"],
            "sku": cand_sku,
        },
    )
    assert res.status_code == 422
    assert res.json()["error"]["code"] == "SKU_IS_A_CANDIDATE"

def test_reject_decision(client):
    rfq_id, items = _create_sample_rfq(client)
    item = items[0]

    # Note too short
    res_short = client.post(
        f"/api/v1/rfqs/{rfq_id}/items/{item['id']}/decisions",
        json={
            "decision_type": "reject",
            "expected_version": item["version"],
            "note": "no",
        },
    )
    assert res_short.status_code == 422
    assert res_short.json()["error"]["code"] == "NOTE_REQUIRED"

    # Valid reject
    res = client.post(
        f"/api/v1/rfqs/{rfq_id}/items/{item['id']}/decisions",
        json={
            "decision_type": "reject",
            "expected_version": item["version"],
            "note": "Specifications do not match project requirements",
        },
    )
    assert res.status_code == 201
    data = res.json()
    assert data["item"]["review_status"] == "rejected"
    assert data["item"]["final_sku"] is None
    assert data["item"]["final_quantity"] is None
    assert data["item"]["final_unit"] is None

def test_confirm_no_match_decision(client):
    rfq_id, items = _create_sample_rfq(client)
    item = items[2]  # Unknown gizmo

    res = client.post(
        f"/api/v1/rfqs/{rfq_id}/items/{item['id']}/decisions",
        json={
            "decision_type": "confirm_no_match",
            "expected_version": item["version"],
        },
    )
    assert res.status_code == 201
    data = res.json()
    assert data["item"]["review_status"] == "no_match"
    assert data["item"]["final_sku"] is None

def test_optimistic_concurrency_stale_version_409(client):
    rfq_id, items = _create_sample_rfq(client)
    item = items[0]
    cand = item["candidates"][0]

    # First decision succeeds
    res1 = client.post(
        f"/api/v1/rfqs/{rfq_id}/items/{item['id']}/decisions",
        json={
            "decision_type": "approve",
            "expected_version": item["version"],
            "sku": cand["sku"],
        },
    )
    assert res1.status_code == 201

    # Second decision using same old expected_version must fail with 409 STALE_VERSION
    res2 = client.post(
        f"/api/v1/rfqs/{rfq_id}/items/{item['id']}/decisions",
        json={
            "decision_type": "reject",
            "expected_version": item["version"],  # Stale!
            "note": "Changed mind, rejecting now",
        },
    )
    assert res2.status_code == 409
    err_body = res2.json()
    assert err_body["error"]["code"] == "STALE_VERSION"
    assert "item" in err_body
    assert err_body["item"]["version"] == item["version"] + 1
    assert err_body["item"]["review_status"] == "approved"

def test_redecision_append_only_audit_trail(client):
    rfq_id, items = _create_sample_rfq(client)
    item = items[0]
    cand = item["candidates"][0]

    # 1. Approve
    res1 = client.post(
        f"/api/v1/rfqs/{rfq_id}/items/{item['id']}/decisions",
        json={
            "decision_type": "approve",
            "expected_version": 1,
            "sku": cand["sku"],
        },
    )
    assert res1.status_code == 201

    # 2. Re-decide to reject
    res2 = client.post(
        f"/api/v1/rfqs/{rfq_id}/items/{item['id']}/decisions",
        json={
            "decision_type": "reject",
            "expected_version": 2,
            "note": "Client cancelled this pipe line item",
        },
    )
    assert res2.status_code == 201

    # Fetch detail and verify decision history
    detail = client.get(f"/api/v1/rfqs/{rfq_id}/items/{item['id']}").json()
    assert len(detail["decisions"]) == 2
    assert detail["decisions"][0]["decision_type"] == "approve"
    assert detail["decisions"][1]["decision_type"] == "reject"
    assert detail["review_status"] == "rejected"
    assert detail["version"] == 3

def test_db_check_constraint_final_fields(db_session):
    import uuid

    from app.db.models import RFQ
    from sqlalchemy.exc import IntegrityError

    rfq = RFQ(
        id=uuid.uuid4(),
        name="Constraint Test",
        source_type="paste",
        catalog_version="test",
        matching_config_hash="test",
    )
    db_session.add(rfq)
    db_session.flush()

    # 1. Approved status with NULL final_sku must fail DB check constraint
    invalid_approved = LineItem(
        id=uuid.uuid4(),
        rfq_id=rfq.id,
        line_no=1,
        source_row=1,
        raw_input="sample",
        description_raw="sample",
        description_normalized="sample",
        system_outcome="proposed",
        review_status="approved",
        final_sku=None,  # Invalid: must not be null when approved
        final_quantity=None,
        final_unit=None,
    )
    db_session.add(invalid_approved)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()

    # 2. Pending status with non-NULL final_sku must fail DB check constraint
    invalid_pending = LineItem(
        id=uuid.uuid4(),
        rfq_id=rfq.id,
        line_no=1,
        source_row=1,
        raw_input="sample",
        description_raw="sample",
        description_normalized="sample",
        system_outcome="proposed",
        review_status="pending",
        final_sku="VALV-001",  # Invalid: must be null when pending
        final_quantity=10,
        final_unit="nos",
    )
    db_session.add(invalid_pending)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()
