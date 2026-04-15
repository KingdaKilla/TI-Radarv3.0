"""pytest conftest fuer euroscivoc-svc.

Fuegt den `src/`-Pfad des Service zum sys.path hinzu, damit
`from src.domain.metrics import ...` auch ohne `pip install -e .`
lauffaehig ist.
"""

from __future__ import annotations

import sys
from pathlib import Path

_SERVICE_ROOT = Path(__file__).resolve().parents[1]
_SRC_PARENT = str(_SERVICE_ROOT)

if _SRC_PARENT not in sys.path:
    sys.path.insert(0, _SRC_PARENT)
