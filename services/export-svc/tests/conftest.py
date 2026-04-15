"""Pytest-Konfiguration: sys.path-Setup damit `src.*` und `shared.domain.*`
importierbar sind ohne installiertes Paket."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # services/export-svc/
sys.path.insert(0, str(ROOT / "packages" / "shared"))
