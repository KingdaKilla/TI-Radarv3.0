"""Conftest fuer patent-grant-svc Tests.

Fuegt Projekt-Root und Service-Root zum sys.path hinzu, damit sowohl
``shared.*`` als auch ``src.*`` importierbar sind.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Service-Root: services/patent-grant-svc/
_SERVICE_ROOT = Path(__file__).resolve().parent.parent
# Projekt-Root: mvp_v3.0/
_PROJECT_ROOT = _SERVICE_ROOT.parent.parent
# Packages-Root: damit ``import shared.*`` aufloest
_PACKAGES_ROOT = _PROJECT_ROOT / "packages"

for p in (_PROJECT_ROOT, _SERVICE_ROOT, _PACKAGES_ROOT):
    ps = str(p)
    if ps not in sys.path:
        sys.path.insert(0, ps)
