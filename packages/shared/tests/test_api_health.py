"""Tests fuer shared.domain.api_health — JWT-Token-Pruefung und Runtime-Failure-Erkennung."""

from __future__ import annotations

import base64
import json
import time

import pytest

from shared.domain.api_health import check_jwt_expiry, detect_runtime_failures
from shared.domain.models import ApiAlert


def _make_jwt(payload: dict) -> str:
    """Hilfs-JWT ohne Signatur (nur Header + Payload)."""
    header = base64.urlsafe_b64encode(json.dumps({"alg": "HS256"}).encode()).rstrip(b"=")
    body = base64.urlsafe_b64encode(json.dumps(payload).encode()).rstrip(b"=")
    return f"{header.decode()}.{body.decode()}.signature"


# ============================================================================
# check_jwt_expiry()
# ============================================================================


class TestCheckJwtExpiry:
    def test_valid_token(self):
        token = _make_jwt({"exp": time.time() + 7 * 86400})  # 7 Tage gueltig (> 3-Tage-Schwelle)
        result = check_jwt_expiry(token, "TestAPI", now=time.time())
        assert result is None

    def test_expired_token(self):
        token = _make_jwt({"exp": time.time() - 3600})  # 1 Stunde abgelaufen
        result = check_jwt_expiry(token, "TestAPI", now=time.time())
        assert result is not None
        assert result.level == "error"
        assert "abgelaufen" in result.message

    def test_expiring_soon(self):
        token = _make_jwt({"exp": time.time() + 3600})  # 1 Stunde verbleibend
        result = check_jwt_expiry(token, "TestAPI", now=time.time())
        assert result is not None
        assert result.level == "warning"
        assert "laeuft" in result.message

    def test_expired_with_refresh_token(self):
        token = _make_jwt({"exp": time.time() - 3600})
        result = check_jwt_expiry(token, "TestAPI", has_refresh_token=True, now=time.time())
        assert result is None  # Auto-Refresh -> kein Alert

    def test_no_exp_field(self):
        token = _make_jwt({"sub": "test"})
        result = check_jwt_expiry(token, "TestAPI")
        assert result is None

    def test_empty_token(self):
        assert check_jwt_expiry("", "TestAPI") is None

    def test_not_a_jwt(self):
        assert check_jwt_expiry("not-a-jwt", "TestAPI") is None

    def test_source_name_in_message(self):
        token = _make_jwt({"exp": time.time() - 3600})
        result = check_jwt_expiry(token, "OpenAIRE", now=time.time())
        assert "OpenAIRE" in result.message


# ============================================================================
# detect_runtime_failures()
# ============================================================================


class TestDetectRuntimeFailures:
    def test_semantic_scholar_failure(self):
        warnings = ["Semantic Scholar Abfrage fehlgeschlagen: timeout"]
        result = detect_runtime_failures(warnings)
        assert len(result) == 1
        assert result[0].source == "Semantic Scholar"
        assert result[0].level == "error"

    def test_gleif_failure(self):
        warnings = ["GLEIF Entity Resolution fehlgeschlagen"]
        result = detect_runtime_failures(warnings)
        assert len(result) == 1
        assert result[0].source == "GLEIF"

    def test_openaire_failure(self):
        warnings = ["publication_years konnte nicht abgerufen werden"]
        result = detect_runtime_failures(warnings)
        assert len(result) == 1
        assert result[0].source == "OpenAIRE"

    def test_no_failures(self):
        warnings = ["Alles OK", "Keine Fehler"]
        result = detect_runtime_failures(warnings)
        assert result == []

    def test_empty(self):
        assert detect_runtime_failures([]) == []

    def test_deduplication(self):
        warnings = [
            "Semantic Scholar Abfrage fehlgeschlagen: A",
            "Semantic Scholar Abfrage fehlgeschlagen: B",
        ]
        result = detect_runtime_failures(warnings)
        assert len(result) == 1  # Nur ein Alert pro Quelle
