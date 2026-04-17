"""Conftest fuer geographic-svc Tests.

Fuegt Projekt-Root, Service-Root und ``packages/`` zum sys.path hinzu,
damit sowohl ``shared.*`` als auch ``src.*`` importierbar sind.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Service-Root: services/geographic-svc/
_SERVICE_ROOT = Path(__file__).resolve().parent.parent
# Projekt-Root: mvp_v3.0_new/
_PROJECT_ROOT = _SERVICE_ROOT.parent.parent
# Packages-Root: ``packages/`` — stellt ``shared.domain.*`` bereit.
_PACKAGES_ROOT = _PROJECT_ROOT / "packages"

for p in (_PROJECT_ROOT, _PACKAGES_ROOT, _SERVICE_ROOT):
    ps = str(p)
    if ps not in sys.path:
        sys.path.insert(0, ps)
