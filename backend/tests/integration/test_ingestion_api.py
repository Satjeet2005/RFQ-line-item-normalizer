from app.db.models import RFQ, LineItem


def test_paste_ingestion_clean(client):
    content = """# RFQ for plumbing works
GI pipe 25mm class B 100 mtr
# another comment
Brass ball valve 1 inch | 10 | nos
MS hex bolt M12 x 50
"""
    res = client.post(
        "/api/v1/rfqs",
        json={"name": "Plumbing Order 1", "source_type": "paste", "content": content},
    )
    assert res.status_code == 201
    data = res.json()
    assert "rfq" in data
    assert data["rfq"]["name"] == "Plumbing Order 1"
    assert data["items_summary"]["total_lines"] == 3
    assert len(data["skipped"]) == 0

    rfq_id = data["rfq"]["id"]
    items_res = client.get(f"/api/v1/rfqs/{rfq_id}/items")
    assert items_res.status_code == 200
    items = items_res.json()["items"]
    assert len(items) == 3
    assert items[0]["raw_input"] == "GI pipe 25mm class B 100 mtr"
    assert items[1]["raw_input"] == "Brass ball valve 1 inch | 10 | nos"
    assert items[2]["raw_input"] == "MS hex bolt M12 x 50"

def test_paste_raw_input_byte_for_byte_preservation(client):
    raw_str = "GI pipe 25mm class B 100 mtr   "
    res = client.post(
        "/api/v1/rfqs",
        json={"name": "Preserve Test", "source_type": "paste", "content": raw_str},
    )
    assert res.status_code == 201
    rfq_id = res.json()["rfq"]["id"]
    items_res = client.get(f"/api/v1/rfqs/{rfq_id}/items")
    assert items_res.json()["items"][0]["raw_input"] == raw_str

def test_paste_hard_row_error_atomic(client, db_session):
    content = """GI pipe 25mm class B 10 mtr
Brass ball valve 1 inch | -5 | nos
MS hex bolt M12 50 nos
"""
    res = client.post(
        "/api/v1/rfqs",
        json={"name": "Atomic Fail", "source_type": "paste", "content": content, "skip_invalid": False},
    )
    assert res.status_code == 422
    err = res.json()
    assert err["error"]["code"] == "ROW_ERRORS"
    assert len(err["error"]["details"]) == 1
    assert err["error"]["details"][0]["code"] == "INVALID_QUANTITY"

    # Confirm nothing was saved in DB
    assert db_session.query(RFQ).filter(RFQ.name == "Atomic Fail").count() == 0

def test_paste_skip_invalid_partial_success(client):
    content = """GI pipe 25mm class B 10 mtr
Brass ball valve 1 inch | -5 | nos
MS hex bolt M12 50 nos
"""
    res = client.post(
        "/api/v1/rfqs",
        json={"name": "Skip Invalid Test", "source_type": "paste", "content": content, "skip_invalid": True},
    )
    assert res.status_code == 201
    data = res.json()
    assert data["items_summary"]["total_lines"] == 2
    assert len(data["skipped"]) == 1
    assert data["skipped"][0]["code"] == "INVALID_QUANTITY"

def test_csv_file_errors(client):
    # EMPTY_FILE
    res = client.post("/api/v1/rfqs", json={"name": "T1", "source_type": "csv", "content": ""})
    assert res.status_code == 422
    assert res.json()["error"]["code"] == "EMPTY_FILE"

    # MISSING_REQUIRED_COLUMN (quantity)
    csv_missing_qty = "description,unit\nGI pipe 25mm,mtr\n"
    res = client.post("/api/v1/rfqs", json={"name": "T2", "source_type": "csv", "content": csv_missing_qty})
    assert res.status_code == 422
    assert res.json()["error"]["code"] == "MISSING_REQUIRED_COLUMN"
    assert "quantity" in res.json()["error"]["message"]

    # DUPLICATE_COLUMN
    csv_dup = "description,quantity,Description\nGI pipe,10,GI pipe 2\n"
    res = client.post("/api/v1/rfqs", json={"name": "T3", "source_type": "csv", "content": csv_dup})
    assert res.status_code == 422
    assert res.json()["error"]["code"] == "DUPLICATE_COLUMN"

    # NO_ROWS (header only)
    csv_no_rows = "description,quantity,unit\n"
    res = client.post("/api/v1/rfqs", json={"name": "T4", "source_type": "csv", "content": csv_no_rows})
    assert res.status_code == 422
    assert res.json()["error"]["code"] == "NO_ROWS"

    # UNSUPPORTED_ENCODING (U+FFFD)
    csv_bad_enc = "description,quantity\nGI pipe \ufffd,10\n"
    res = client.post("/api/v1/rfqs", json={"name": "T5", "source_type": "csv", "content": csv_bad_enc})
    assert res.status_code == 422
    assert res.json()["error"]["code"] == "UNSUPPORTED_ENCODING"

def test_csv_row_errors_and_skip(client):
    csv_data = """description,quantity,unit
GI pipe 25mm class B,50,mtr
,10,nos
Brass ball valve 1",invalid_qty,nos
PVC pipe 50mm,20,mtr
"""
    # skip_invalid = false -> 422 ROW_ERRORS
    res = client.post(
        "/api/v1/rfqs",
        json={"name": "CSV Row Err", "source_type": "csv", "content": csv_data, "skip_invalid": False},
    )
    assert res.status_code == 422
    err = res.json()["error"]
    assert err["code"] == "ROW_ERRORS"
    assert len(err["details"]) == 2  # EMPTY_DESCRIPTION on row 2, INVALID_QUANTITY on row 3

    # skip_invalid = true -> 201 with 2 valid lines, 2 skipped
    res2 = client.post(
        "/api/v1/rfqs",
        json={"name": "CSV Row Err Skip", "source_type": "csv", "content": csv_data, "skip_invalid": True},
    )
    assert res2.status_code == 201
    data = res2.json()
    assert data["items_summary"]["total_lines"] == 2
    assert len(data["skipped"]) == 2

def test_csv_unknown_columns_warning(client):
    csv_data = """description,quantity,unit,extra_notes,vendor_code
GI pipe 25mm class B,50,mtr,urgent,V-102
"""
    res = client.post(
        "/api/v1/rfqs",
        json={"name": "CSV Warning", "source_type": "csv", "content": csv_data},
    )
    assert res.status_code == 201
    warnings = res.json()["items_summary"]["warnings"]
    assert len(warnings) == 1
    assert "extra_notes" in warnings[0] and "vendor_code" in warnings[0]

def test_duplicate_row_detection(client):
    content = """GI pipe 25mm class B 50 mtr
GI pipe 25mm class B 50 mtr
"""
    res = client.post(
        "/api/v1/rfqs",
        json={"name": "Dup RFQ", "source_type": "paste", "content": content},
    )
    assert res.status_code == 201
    rfq_id = res.json()["rfq"]["id"]
    items_res = client.get(f"/api/v1/rfqs/{rfq_id}/items")
    items = items_res.json()["items"]
    assert len(items) == 2
    # Second item must have DUPLICATE_OF_LINE issue
    issue_codes = [iss["code"] for iss in items[1]["issues"]]
    assert "DUPLICATE_OF_LINE" in issue_codes

def test_rfq_creation_atomicity_on_failure(client, db_session, monkeypatch):
    from unittest.mock import patch
    import app.services.ingest as ingest_module

    initial_rfqs = db_session.query(RFQ).count()
    initial_items = db_session.query(LineItem).count()

    # Simulate a mid-processing failure during line item insertion
    def fail_normalize(*args, **kwargs):
        raise RuntimeError("Simulated mid-ingestion processing explosion")

    monkeypatch.setattr(ingest_module, "normalize_line", fail_normalize)

    content = "GI pipe 25mm class B 50 mtr\n"
    res = client.post(
        "/api/v1/rfqs",
        json={"name": "Atomic Fail RFQ", "source_type": "paste", "content": content},
    )
    assert res.status_code == 500

    # Ensure transaction was rolled back and 0 partial records remain
    assert db_session.query(RFQ).count() == initial_rfqs
    assert db_session.query(LineItem).count() == initial_items
