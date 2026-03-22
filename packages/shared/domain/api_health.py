"""API-Key/Token Health Checks — reine Funktionen (kein I/O)."""

from __future__ import annotations

import base64
import json
import logging
import time

from shared.domain.models import ApiAlert

logger = logging.getLogger(__name__)

_EXPIRY_WARNING_SECONDS = 3 * 24 * 3600  # 3 Tage


def check_jwt_expiry(
    token: str,
    source_name: str,
    *,
    now: float | None = None,
    has_refresh_token: bool = False,
) -> ApiAlert | None:
    """JWT-Token auf Ablauf pruefen (lokaler base64-Decode, kein Netzwerk).

    Args:
        token: JWT-Access-Token
        source_name: Anzeigename der API (z.B. "OpenAIRE")
        now: Override fuer aktuelle Zeit (fuer Tests)
        has_refresh_token: Wenn True, wird bei abgelaufenem Token kein
            Fehler gemeldet, da Auto-Refresh greift.

    Returns:
        ApiAlert mit level="error" wenn abgelaufen (ohne Refresh-Token),
        level="warning" wenn < 3 Tage verbleiben,
        None wenn gueltig, Auto-Refresh verfuegbar, oder kein JWT.
    """
    if not token or "." not in token:
        return None
    try:
        parts = token.split(".")
        if len(parts) < 2:
            return None
        payload_b64 = parts[1]
        # base64url Padding korrigieren
        payload_b64 += "=" * (4 - len(payload_b64) % 4)
        payload = json.loads(base64.urlsafe_b64decode(payload_b64))
        exp = payload.get("exp")
        if exp is None:
            return None

        current_time = now if now is not None else time.time()
        remaining = exp - current_time

        if remaining <= 0:
            if has_refresh_token:
                # Auto-Refresh verfuegbar — kein Alert noetig
                return None
            hours_ago = abs(remaining) / 3600
            return ApiAlert(
                source=source_name,
                level="error",
                message=f"{source_name}-Token abgelaufen (seit {hours_ago:.0f}h)",
            )

        if remaining < _EXPIRY_WARNING_SECONDS:
            if has_refresh_token:
                # Auto-Refresh verfuegbar — kein Alert noetig
                return None
            hours_left = remaining / 3600
            if hours_left >= 24:
                time_str = f"{hours_left / 24:.1f} Tagen"
            else:
                time_str = f"{hours_left:.0f} Stunden"
            return ApiAlert(
                source=source_name,
                level="warning",
                message=f"{source_name}-Token laeuft in {time_str} ab",
            )
    except Exception:
        logger.debug("JWT decode failed fuer %s", source_name)

    return None


_FAILURE_PATTERNS: list[tuple[str, str]] = [
    ("Semantic Scholar Abfrage fehlgeschlagen", "Semantic Scholar"),
    ("GLEIF Entity Resolution fehlgeschlagen", "GLEIF"),
    ("publication_years", "OpenAIRE"),
]


def detect_runtime_failures(warnings: list[str]) -> list[ApiAlert]:
    """UC-Warnungen nach API-Fehlern durchsuchen und als ApiAlerts zurueckgeben."""
    alerts: list[ApiAlert] = []
    seen_sources: set[str] = set()
    for warning in warnings:
        for pattern, source in _FAILURE_PATTERNS:
            if pattern in warning and source not in seen_sources:
                alerts.append(ApiAlert(
                    source=source,
                    level="error",
                    message=f"{source}: Daten nicht verfuegbar",
                ))
                seen_sources.add(source)
    return alerts
