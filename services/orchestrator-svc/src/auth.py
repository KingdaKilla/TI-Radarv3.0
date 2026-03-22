"""API-Key-basierte Authentifizierung fuer den Orchestrator.

Einfache API-Key-Validierung via X-API-Key Header. Fuer MVP ausreichend —
JWT/OAuth2 waere Overkill fuer ein internes System ohne Benutzerkonten.

Verhalten:
- TI_RADAR_API_KEY nicht gesetzt → offener Zugang (MVP-Modus)
- TI_RADAR_API_KEY gesetzt → Key wird gegen Header geprueft

Verwendung in Routern (nicht global, damit Health-Checks offen bleiben):

    from src.auth import verify_api_key
    from fastapi import Depends

    @router.post("/api/v1/radar", dependencies=[Depends(verify_api_key)])
    async def analyze(...): ...
"""

from __future__ import annotations

import hmac
import os

import structlog
from fastapi import HTTPException, Security
from fastapi.security import APIKeyHeader

logger = structlog.get_logger(__name__)

# Header-Name fuer den API-Key (De-facto-Standard fuer interne APIs)
API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)


async def verify_api_key(
    api_key: str | None = Security(API_KEY_HEADER),
) -> None:
    """Validiert den API-Key aus dem X-API-Key Header.

    Wenn die Umgebungsvariable TI_RADAR_API_KEY nicht gesetzt ist,
    wird die Authentifizierung uebersprungen (offener Zugang im MVP-Modus).
    Das ermoeglicht einfaches Testen ohne Konfiguration.

    Args:
        api_key: Wert aus dem X-API-Key Header (None wenn nicht gesendet).

    Raises:
        HTTPException 401: API-Key fehlt oder ist ungueltig.
    """
    expected = os.getenv("TI_RADAR_API_KEY", "")

    if not expected:
        # Kein Key konfiguriert → offener Zugang (MVP-Modus)
        return

    if not api_key:
        logger.warning("auth_fehlgeschlagen", grund="Kein API-Key im Header")
        raise HTTPException(
            status_code=401,
            detail="API-Key erforderlich (X-API-Key Header fehlt)",
        )

    if not hmac.compare_digest(api_key, expected):
        logger.warning("auth_fehlgeschlagen", grund="Ungueltiger API-Key")
        raise HTTPException(
            status_code=401,
            detail="Ungueltiger API-Key",
        )
