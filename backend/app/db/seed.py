import hashlib
import json

from app.core.config import DATA_DIR
from app.core.logging import logger
from app.db.models import CatalogProduct
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session


def get_catalog_version() -> str:
    catalog_path = DATA_DIR / "catalog.json"
    content = catalog_path.read_bytes()
    return hashlib.sha256(content).hexdigest()[:12]

def get_matching_config_hash() -> str:
    config_path = DATA_DIR / "matching_config.json"
    content = config_path.read_bytes()
    return hashlib.sha256(content).hexdigest()

def seed_catalog(db: Session) -> int:
    catalog_path = DATA_DIR / "catalog.json"
    with open(catalog_path, "r", encoding="utf-8") as f:
        products = json.load(f)

    for item in products:
        stmt = insert(CatalogProduct).values(
            sku=item["sku"],
            name=item["name"],
            category=item["category"],
            uom=item["uom"],
            attributes=item.get("attributes", {}),
            aliases=item.get("aliases", []),
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=["sku"],
            set_={
                "name": stmt.excluded.name,
                "category": stmt.excluded.category,
                "uom": stmt.excluded.uom,
                "attributes": stmt.excluded.attributes,
                "aliases": stmt.excluded.aliases,
            },
        )
        db.execute(stmt)

    db.commit()
    count = db.query(CatalogProduct).count()
    logger.info("Catalog seeded idempotently", extra={"extra_data": {"count": count}})
    return count
