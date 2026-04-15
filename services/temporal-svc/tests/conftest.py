"""Conftest fuer temporal-svc Tests.

Fuegt ``packages/shared`` und den Service-Root zum sys.path hinzu, damit
sowohl ``shared.domain.*`` als auch ``src.*`` direkt importierbar sind.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Service-Root: services/temporal-svc/
_SERVICE_ROOT = Path(__file__).resolve().parent.parent
# Projekt-Root: mvp_v3.0_new/
_PROJECT_ROOT = _SERVICE_ROOT.parent.parent
# Packages-Root: mvp_v3.0_new/packages/ — enthaelt ``shared`` als Paket.
_SHARED_ROOT = _PROJECT_ROOT / "packages"

for p in (_SHARED_ROOT, _SERVICE_ROOT):
    ps = str(p)
    if ps not in sys.path:
        sys.path.insert(0, ps)
