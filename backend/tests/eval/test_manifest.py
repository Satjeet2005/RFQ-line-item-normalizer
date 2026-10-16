"""
Tests for dataset manifest validation and tamper detection.
Covers Checklist P0 V4.
"""
import pytest
from pathlib import Path
from rfq_eval.manifest import verify_manifest

def test_manifest_verifies_clean_dataset():
    dataset_dir = Path("eval/dataset/v1")
    manifest_hash = verify_manifest(dataset_dir)
    assert len(manifest_hash) == 64

def test_manifest_fails_on_tampered_file(tmp_path):
    # Copy dataset to temporary path
    import shutil
    shutil.copytree("eval/dataset/v1", tmp_path / "v1")

    # Tamper with cases.jsonl
    with open(tmp_path / "v1" / "cases.jsonl", "a", encoding="utf-8") as f:
        f.write("\n// tampered\n")

    with pytest.raises(SystemExit) as exc_info:
        verify_manifest(tmp_path / "v1")
    assert exc_info.value.code == 2
