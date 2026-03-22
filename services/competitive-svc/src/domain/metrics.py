"""UC3-spezifische Metriken und Hilfsfunktionen.

Re-exportiert Kernfunktionen aus shared.domain.metrics.
UC3 hat keine eigenen Metriken — alle kommen aus shared.
"""

from shared.domain.metrics import (  # noqa: F401
    cr4,
    hhi_concentration_level,
    hhi_index,
)
