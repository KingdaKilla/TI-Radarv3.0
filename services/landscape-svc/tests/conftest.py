"""Conftest fuer landscape-svc Tests.

Fuegt Projekt-Root und Service-Root zum sys.path hinzu,
damit sowohl `shared.*` als auch `src.*` importierbar sind.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Service-Root: services/landscape-svc/
_SERVICE_ROOT = Path(__file__).resolve().parent.parent
# Projekt-Root: mvp_v3.0/
_PROJECT_ROOT = _SERVICE_ROOT.parent.parent

for p in (_PROJECT_ROOT, _SERVICE_ROOT):
    ps = str(p)
    if ps not in sys.path:
        sys.path.insert(0, ps)
