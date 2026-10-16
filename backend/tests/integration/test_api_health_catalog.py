from app.db.models import RFQ, CatalogProduct, LineItem
from app.db.seed import seed_catalog


def test_health_check_ok(client):
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data == {"status": "ok"}
    assert "X-Request-ID" in response.headers

def test_catalog_search(client):
    response = client.get("/api/v1/catalog?q=pipe&limit=10")
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data
    assert data["total"] > 0
    assert len(data["items"]) <= 10
    for item in data["items"]:
        assert "sku" in item
        assert "name" in item
        assert "price" not in item  # Checklist P0 X3: No price field

def test_catalog_search_alias(client):
    # Test searching by product alias, e.g. "Galvanized Iron" which is an alias for PIPE-001
    response = client.get("/api/v1/catalog?q=Galvanized")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] > 0
    assert any("PIPE-001" in item["sku"] for item in data["items"])

def test_catalog_products_route_alias(client):
    # Test that /api/v1/catalog/products works identically to /api/v1/catalog
    response = client.get("/api/v1/catalog/products?q=pipe&limit=10")
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data
    assert data["total"] > 0

def test_seed_idempotency(db_session):
    count1 = seed_catalog(db_session)
    count2 = seed_catalog(db_session)
    assert count1 == 100
    assert count2 == 100
    total_db = db_session.query(CatalogProduct).count()
    assert total_db == 100

def test_no_price_column_in_db_models():
    # Verify no price field in any DB model
    for model in [RFQ, LineItem, CatalogProduct]:
        cols = [c.name.lower() for c in model.__table__.columns]
        assert "price" not in cols, f"Price column found in {model.__name__}"
        assert not any("price" in col for col in cols)
