"""
Tests for catalog and dataset schema validation.
"""
from pathlib import Path
from scripts.validate_catalog import validate_catalog
from scripts.validate_dataset import validate_all

def test_catalog_is_valid():
    errs = validate_catalog(Path("data/catalog.json"))
    assert not errs, f"Catalog validation errors: {errs}"

def test_dataset_is_valid():
    errs = validate_all()
    assert not errs, f"Dataset validation errors: {errs}"
