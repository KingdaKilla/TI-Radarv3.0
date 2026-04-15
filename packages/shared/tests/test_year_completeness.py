"""Tests fuer shared.domain.year_completeness — Jahres-Vollstaendigkeits-Helfer.

Hintergrund: Bug MAJ-7/MAJ-8 — Zeitreihen enthielten das laufende (unvollstaendige)
Kalenderjahr, was CAGR/S-Curve-Fit verfaelscht hat. Diese Helper stellen sicher,
dass Services nur ueber vollstaendig abgeschlossene Jahre rechnen.
"""

from __future__ import annotations

from datetime import date

import pytest

from shared.domain.year_completeness import (
    clip_to_complete_years,
    is_year_complete,
    last_complete_year,
)


# ============================================================================
# last_complete_year()
# ============================================================================


class TestLastCompleteYear:
    def test_mid_year_2026(self):
        """Mitten im Jahr 2026 → letztes abgeschlossenes Jahr ist 2025."""
        assert last_complete_year(date(2026, 4, 14)) == 2025

    def test_january_first_2026(self):
        """01.01.2026 → 2025 ist gerade abgeschlossen."""
        assert last_complete_year(date(2026, 1, 1)) == 2025

    def test_december_last_2026(self):
        """31.12.2026 → 2026 ist noch nicht komplett, also 2025."""
        assert last_complete_year(date(2026, 12, 31)) == 2025

    def test_january_first_2027(self):
        """01.01.2027 → 2026 ist gerade abgeschlossen."""
        assert last_complete_year(date(2027, 1, 1)) == 2026

    def test_uses_today_by_default(self):
        """Ohne Argument nutzt die Funktion das heutige Datum."""
        result = last_complete_year()
        # Muss ein plausibles Jahr zurueckliefern (>= 2024)
        assert isinstance(result, int)
        assert result >= 2024


# ============================================================================
# is_year_complete()
# ============================================================================


class TestIsYearComplete:
    def test_last_year_is_complete(self):
        """Das Vorjahr ist am 14.04.2026 abgeschlossen."""
        assert is_year_complete(2025, date(2026, 4, 14)) is True

    def test_current_year_not_complete(self):
        """Das laufende Jahr ist nie abgeschlossen."""
        assert is_year_complete(2026, date(2026, 4, 14)) is False

    def test_future_year_not_complete(self):
        """Zukuenftige Jahre sind nicht abgeschlossen."""
        assert is_year_complete(2030, date(2026, 4, 14)) is False

    def test_old_year_complete(self):
        """Weit zurueckliegende Jahre sind abgeschlossen."""
        assert is_year_complete(2000, date(2026, 4, 14)) is True

    def test_boundary_january_first(self):
        """Am 01.01.Y+1 gilt Y als gerade abgeschlossen."""
        assert is_year_complete(2025, date(2026, 1, 1)) is True

    def test_boundary_december_last(self):
        """Am 31.12.Y ist Y noch nicht abgeschlossen."""
        assert is_year_complete(2026, date(2026, 12, 31)) is False


# ============================================================================
# clip_to_complete_years()
# ============================================================================


class TestClipToCompleteYears:
    def test_removes_current_year(self):
        """Laufendes 2026 wird aus der Liste entfernt."""
        result = clip_to_complete_years([2023, 2024, 2025, 2026], date(2026, 4, 14))
        assert result == [2023, 2024, 2025]

    def test_removes_future_years(self):
        """Zukunftsjahre werden entfernt."""
        result = clip_to_complete_years([2024, 2025, 2026, 2027], date(2026, 4, 14))
        assert result == [2024, 2025]

    def test_keeps_all_when_all_complete(self):
        """Alle Jahre vollstaendig abgeschlossen → Liste bleibt erhalten."""
        result = clip_to_complete_years([2020, 2021, 2022], date(2026, 4, 14))
        assert result == [2020, 2021, 2022]

    def test_empty_list(self):
        """Leere Liste bleibt leer."""
        assert clip_to_complete_years([], date(2026, 4, 14)) == []

    def test_preserves_order(self):
        """Reihenfolge der Eingabe wird beibehalten."""
        result = clip_to_complete_years([2025, 2023, 2024], date(2026, 4, 14))
        assert result == [2025, 2023, 2024]

    def test_removes_only_incomplete(self):
        """Nur unvollstaendige Jahre werden entfernt, nicht sortiert."""
        result = clip_to_complete_years([2023, 2026, 2024], date(2026, 4, 14))
        assert result == [2023, 2024]

    def test_uses_today_by_default(self):
        """Ohne `today` wird das Systemdatum verwendet."""
        result = clip_to_complete_years([1990, 2000])
        assert result == [1990, 2000]
