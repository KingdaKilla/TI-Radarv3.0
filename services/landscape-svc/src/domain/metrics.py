"""UC1-spezifische Metriken und Hilfsfunktionen.

Re-exportiert Kernfunktionen aus shared.domain.metrics.
UC1 hat keine eigenen Metriken — alle kommen aus shared.
"""

from shared.domain.metrics import (  # noqa: F401
    cagr,
    merge_country_data,
    merge_time_series,
    yoy_growth,
)
