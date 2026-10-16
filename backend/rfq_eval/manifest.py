"""
Dataset integrity verification tool.
Enforces Section J freeze protocol: tampering causes immediate exit 2 with DATASET_MODIFIED.
"""
import hashlib
import sys
from pathlib import Path

def compute_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()

def verify_manifest(dataset_dir: Path) -> str:
    manifest_path = dataset_dir / "MANIFEST.sha256"
    if not manifest_path.exists():
        sys.stderr.write("DATASET_MODIFIED: Missing MANIFEST.sha256\n")
        sys.exit(2)

    with open(manifest_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    if not lines:
        sys.stderr.write("DATASET_MODIFIED: Empty MANIFEST.sha256\n")
        sys.exit(2)

    for line in lines:
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        if len(parts) != 2:
            sys.stderr.write(f"DATASET_MODIFIED: Malformed manifest line: {line}\n")
            sys.exit(2)
        expected_hash, rel_path = parts
        target_path = dataset_dir / rel_path
        if not target_path.exists():
            sys.stderr.write(f"DATASET_MODIFIED: File not found: {rel_path}\n")
            sys.exit(2)
        actual_hash = compute_sha256(target_path)
        if actual_hash != expected_hash:
            sys.stderr.write(f"DATASET_MODIFIED: SHA-256 mismatch for {rel_path}\n")
            sys.exit(2)

    return compute_sha256(manifest_path)
