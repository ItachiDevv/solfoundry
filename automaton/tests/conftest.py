"""Pytest configuration for automaton tests."""

import sys
from pathlib import Path

# Ensure the repo root is on sys.path so `from automaton...` imports work.
_repo_root = str(Path(__file__).resolve().parents[2])
if _repo_root not in sys.path:
    sys.path.insert(0, _repo_root)
