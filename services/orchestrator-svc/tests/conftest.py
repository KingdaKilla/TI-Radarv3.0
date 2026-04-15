"""Conftest fuer orchestrator-svc Tests.

Fuegt ``packages/`` und den Service-Root auf sys.path, damit
``shared.domain.*`` und ``src.*`` importierbar sind.
"""

from __future__ import annotations

import sys
from pathlib import Path

_SERVICE_ROOT = Path(__file__).resolve().parent.parent
_PROJECT_ROOT = _SERVICE_ROOT.parent.parent
_PACKAGES_ROOT = _PROJECT_ROOT / "packages"

for p in (_PACKAGES_ROOT, _SERVICE_ROOT):
    ps = str(p)
    if ps not in sys.path:
        sys.path.insert(0, ps)
