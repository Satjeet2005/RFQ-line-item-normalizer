"""
CLI entry point for rfq_eval.
Usage: python -m rfq_eval run --dataset eval/dataset/v1 --system both --out eval/reports/latest
"""
import sys
from pathlib import Path

# Ensure backend directory is in sys.path
backend_root = Path(__file__).resolve().parent.parent
if str(backend_root) not in sys.path:
    sys.path.insert(0, str(backend_root))

from rfq_eval.run import main

if __name__ == "__main__":
    # If first argument is 'run', strip it for argparse in run.py
    if len(sys.argv) > 1 and sys.argv[1] == "run":
        sys.argv.pop(1)
    main()
