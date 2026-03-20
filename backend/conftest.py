"""Pytest conftest -- ensure backend root is on sys.path."""

import sys
from pathlib import Path

_backend_root = str(Path(__file__).resolve().parent)
if _backend_root not in sys.path:
    sys.path.insert(0, _backend_root)
