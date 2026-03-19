"""Pytest conftest — ensure project root is on sys.path so `router` is importable."""

import sys
from pathlib import Path

# backend/ is where pytest runs from; project root is one level up.
_project_root = str(Path(__file__).resolve().parent.parent)
_backend_root = str(Path(__file__).resolve().parent)

for p in (_project_root, _backend_root):
    if p not in sys.path:
        sys.path.insert(0, p)
