import csv
import io


def test_export_incomplete_gating_409(client):
    content = "GI pipe 25mm class B 50 mtr\nBrass ball valve 1 inch 10 nos\n"
    res = client.post(
        "/api/v1/rfqs",
        json={"name": "Export Test 1", "source_type": "paste", "content": content},
    )
    rfq_id = res.json()["rfq"]["id"]

    # Without allow_incomplete -> 409 RFQ_INCOMPLETE
    exp_res = client.get(f"/api/v1/rfqs/{rfq_id}/export?format=csv")
    assert exp_res.status_code == 409
    assert exp_res.json()["error"]["code"] == "RFQ_INCOMPLETE"

    # With allow_incomplete=true -> 200, 0 lines finalized, 2 excluded
    exp_res_allow = client.get(f"/api/v1/rfqs/{rfq_id}/export?format=csv&allow_incomplete=true")
    assert exp_res_allow.status_code == 200
    assert exp_res_allow.headers["X-Items-Excluded"] == "2"

def test_export_csv_finalized_only_and_formula_neutralization(client):
    # Description starting with =SUM(1,2) to test formula injection protection
    content = """=SUM(1,2) GI pipe 25mm class B 50 mtr
+10 Brass ball valve 1 inch 10 nos
MS hex bolt M12 50 nos
"""
    res = client.post(
        "/api/v1/rfqs",
        json={"name": "Export Formula Test", "source_type": "paste", "content": content},
    )
    rfq_id = res.json()["rfq"]["id"]
    items = client.get(f"/api/v1/rfqs/{rfq_id}/items").json()["items"]

    # 1. Approve line 0
    client.post(
        f"/api/v1/rfqs/{rfq_id}/items/{items[0]['id']}/decisions",
        json={"decision_type": "approve", "expected_version": 1, "sku": items[0]["candidates"][0]["sku"]},
    )
    # 2. Reject line 1
    client.post(
        f"/api/v1/rfqs/{rfq_id}/items/{items[1]['id']}/decisions",
        json={"decision_type": "reject", "expected_version": 1, "note": "Rejected line item"},
    )
    # 3. Confirm no match for line 2
    client.post(
        f"/api/v1/rfqs/{rfq_id}/items/{items[2]['id']}/decisions",
        json={"decision_type": "confirm_no_match", "expected_version": 1},
    )

    # Now RFQ is complete (0 pending)
    exp_res = client.get(f"/api/v1/rfqs/{rfq_id}/export?format=csv")
    assert exp_res.status_code == 200
    assert exp_res.headers["X-Items-Excluded"] == "2"  # rejected + no_match

    csv_text = exp_res.content.decode("utf-8")
    reader = csv.reader(io.StringIO(csv_text))
    rows = list(reader)

    header = rows[0]
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
    assert header == expected_header
    assert "price" not in [h.lower() for h in header]

    # Only 1 finalized row in CSV!
    assert len(rows) == 2
    data_row = rows[1]
    assert data_row[0] == "1"
    # Check formula neutralization: '=SUM(1,2)...' must start with "'"
    assert data_row[1].startswith("'=")
    assert data_row[8] == "approved"

def test_export_json_format(client):
    content = "GI pipe 25mm class B 50 mtr\nBrass ball valve 1 inch 10 nos\n"
    res = client.post(
        "/api/v1/rfqs",
        json={"name": "JSON Export RFQ", "source_type": "paste", "content": content},
    )
    rfq_id = res.json()["rfq"]["id"]
    items = client.get(f"/api/v1/rfqs/{rfq_id}/items").json()["items"]

    # Approve first line
    client.post(
        f"/api/v1/rfqs/{rfq_id}/items/{items[0]['id']}/decisions",
        json={"decision_type": "approve", "expected_version": 1, "sku": items[0]["candidates"][0]["sku"]},
    )

    # Export JSON with allow_incomplete=true
    exp_res = client.get(f"/api/v1/rfqs/{rfq_id}/export?format=json&allow_incomplete=true")
    assert exp_res.status_code == 200
    data = exp_res.json()
    assert "rfq" in data
    assert "complete" in data
    assert data["complete"] is False
    assert len(data["finalized"]) == 1
    assert len(data["not_finalized"]) == 1
    # Check suggestion labelled as unapproved
    not_fin = data["not_finalized"][0]
    assert not_fin["suggestion"] is not None
    assert "unapproved" in not_fin["suggestion"]["disclaimer"].lower()
