"""
Test architectural isolation of evaluation harness and domain modules.
Covers Checklist P0 V11 and P0 S5.
"""
import subprocess
import sys


def test_evaluator_imports_no_web_or_db():
    # Run in a clean subprocess to ensure independence from test runner imports
    code = """
import sys
import domain.baseline
import domain.split
import domain.types
import domain.units
import domain.normalizer
import domain.matcher
import rfq_eval.run
import rfq_eval.metrics
import rfq_eval.manifest
import rfq_eval.report

forbidden_modules = [
    "fastapi",
    "sqlalchemy",
    "psycopg2",
    "asyncpg",
    "alembic",
    "starlette",
    "pydantic_settings"
]

loaded_modules = set(sys.modules.keys())
for mod in forbidden_modules:
    assert mod not in loaded_modules, f"Forbidden module '{mod}' was imported into evaluation context!"
"""
    result = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        env={"PYTHONPATH": "backend"},
    )
    assert result.returncode == 0, f"Isolation check failed:\n{result.stderr}"
