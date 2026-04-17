"""Unit-Tests fuer Multi-Label-aware Share-Normalisierung (Bundle E).

Hintergrund:
    Zuvor wurde `share` als `COUNT(DISTINCT project_id) / total_projects`
    berechnet. Bei Multi-Label-Zuordnung (ein Projekt in 3 Disziplinen)
    summierte das auf Σshare > 1 — Live beobachtet bei AI (1.38) und
    Blockchain (2.27). Fachlich korrekt ist `share = count / Σ(counts auf
    derselben Hierarchie-Ebene)`, d. h. pro Level (FIELD/SUBFIELD/TOPIC)
    Σ=1.0.

Da das Repository `asyncpg` benoetigt, werden die Queries hier nicht
"echt" gegen eine DB gefahren. Stattdessen wird ein Fake-Pool die
Python-Semantik der SQL-Normalisierung reproduzieren; der Test
verifiziert, dass die Service-Schicht / das Repository-Mapping diese
Shares durchreicht und die Summen-Invariante haelt.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from src.service import EuroSciVocServicer


# ---------------------------------------------------------------------------
# Fake-Repository, das die neue Normalisierung (count / Σ per Level) abbildet.
# ---------------------------------------------------------------------------


def _normalize_share_per_level(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Pythonisches Pendant zu `counts + level_totals + LEFT JOIN` in SQL.

    Fuer jede Hierarchie-Ebene: share_i = count_i / Σ(counts in Level).
    """
    level_totals: dict[str, float] = {}
    for row in rows:
        lvl = str(row.get("level", ""))
        level_totals[lvl] = level_totals.get(lvl, 0.0) + float(row["project_count"])

    out: list[dict[str, Any]] = []
    for row in rows:
        lvl = str(row.get("level", ""))
        total = level_totals.get(lvl, 0.0)
        share = (float(row["project_count"]) / total) if total > 0 else 0.0
        out.append({**row, "share": share})
    return out


class _FakeRepo:
    def __init__(
        self,
        *,
        disciplines: list[dict[str, Any]],
        total_mapped: int = 0,
        total_projects: int = 0,
    ) -> None:
        self._disciplines = disciplines
        self._total_mapped = total_mapped
        self._total_projects = total_projects

    async def discipline_distribution(self, technology: str, **_: Any) -> list[dict[str, Any]]:
        return self._disciplines

    async def discipline_trend(self, technology: str, **_: Any) -> list[dict[str, Any]]:
        return []

    async def cross_disciplinary_links(self, technology: str, **_: Any) -> list[dict[str, Any]]:
        return []

    async def total_mapped_projects(self, technology: str, **_: Any) -> int:
        return self._total_mapped

    async def total_projects(self, technology: str, **_: Any) -> int:
        return self._total_projects


def _make_servicer(repo: _FakeRepo) -> EuroSciVocServicer:
    servicer = EuroSciVocServicer.__new__(EuroSciVocServicer)  # type: ignore[call-arg]
    servicer._pool = None  # type: ignore[attr-defined]
    servicer._settings = SimpleNamespace()  # type: ignore[attr-defined]
    servicer._repo = repo  # type: ignore[attr-defined]
    return servicer


def _build_request(technology: str) -> SimpleNamespace:
    return SimpleNamespace(
        technology=technology,
        request_id="test-share-sum",
        time_range=SimpleNamespace(start_year=2020, end_year=2024),
    )


# ---------------------------------------------------------------------------
# 1) Normalisierungs-Logik: sollte pro Level Σshare == 1.0 ergeben.
# ---------------------------------------------------------------------------


class TestNormalizeSharePerLevel:
    def test_five_disciplines_sum_to_one(self) -> None:
        """Counts [10, 20, 30, 40, 0] in einem Level -> shares summieren zu 1.0."""
        rows = [
            {"id": f"d{i}", "label": f"L{i}", "level": "FIELD", "parent_code": "", "project_count": c}
            for i, c in enumerate([10, 20, 30, 40, 0])
        ]
        normalized = _normalize_share_per_level(rows)
        shares = [row["share"] for row in normalized]
        assert shares == pytest.approx([0.1, 0.2, 0.3, 0.4, 0.0])
        assert sum(shares) == pytest.approx(1.0)

    def test_multi_level_independently_sum_to_one(self) -> None:
        """FIELD- und SUBFIELD-Shares werden unabhaengig normiert (je Σ=1.0)."""
        rows = [
            {"id": "f1", "label": "F1", "level": "FIELD",    "parent_code": "",   "project_count": 3},
            {"id": "f2", "label": "F2", "level": "FIELD",    "parent_code": "",   "project_count": 7},
            {"id": "s1", "label": "S1", "level": "SUBFIELD", "parent_code": "f1", "project_count": 2},
            {"id": "s2", "label": "S2", "level": "SUBFIELD", "parent_code": "f1", "project_count": 8},
        ]
        normalized = _normalize_share_per_level(rows)
        field_sum = sum(r["share"] for r in normalized if r["level"] == "FIELD")
        sub_sum = sum(r["share"] for r in normalized if r["level"] == "SUBFIELD")
        assert field_sum == pytest.approx(1.0)
        assert sub_sum == pytest.approx(1.0)

    def test_all_zero_counts_no_division_error(self) -> None:
        rows = [
            {"id": "d1", "label": "D1", "level": "FIELD", "parent_code": "", "project_count": 0},
            {"id": "d2", "label": "D2", "level": "FIELD", "parent_code": "", "project_count": 0},
        ]
        normalized = _normalize_share_per_level(rows)
        assert all(r["share"] == 0.0 for r in normalized)


# ---------------------------------------------------------------------------
# 2) Service-Integration: fields_of_science.share summiert auf 1.0.
# ---------------------------------------------------------------------------


class TestServicePassThroughSumToOne:
    """Stellt sicher, dass der Service normalisierte Shares unveraendert
    durchreicht — d. h. `fields_of_science[].share` summiert auf 1.0.
    """

    @pytest.mark.asyncio
    async def test_disciplines_share_sum_to_one(self) -> None:
        raw = [
            {"id": f"f{i}", "label": f"F{i}", "level": "FIELD", "parent_code": "", "project_count": c}
            for i, c in enumerate([10, 20, 30, 40])
        ]
        disciplines = _normalize_share_per_level(raw)
        # Service erwartet Key "parent_id" statt "parent_code".
        for d in disciplines:
            d["parent_id"] = d.pop("parent_code", "") or ""

        repo = _FakeRepo(disciplines=disciplines, total_mapped=100, total_projects=100)
        servicer = _make_servicer(repo)

        response = await servicer.AnalyzeEuroSciVoc(_build_request("ai"), context=None)
        total_share = sum(float(d["share"]) for d in response["disciplines"])
        assert total_share == pytest.approx(1.0), (
            f"Σ disciplines.share muss 1.0 sein, ist aber {total_share:.4f}"
        )

    @pytest.mark.asyncio
    async def test_fields_of_science_share_sum_to_one(self) -> None:
        """Fields (level=FIELD) muessen isoliert auf Σ=1.0 normalisiert sein."""
        raw = [
            {"id": "f1", "label": "natural sciences", "level": "FIELD",    "parent_code": "",   "project_count": 40},
            {"id": "f2", "label": "engineering",      "level": "FIELD",    "parent_code": "",   "project_count": 60},
            # Subfields duerfen FIELD-Summen nicht beeinflussen.
            {"id": "s1", "label": "chemistry",        "level": "SUBFIELD", "parent_code": "f1", "project_count": 15},
            {"id": "s2", "label": "physics",          "level": "SUBFIELD", "parent_code": "f1", "project_count": 85},
        ]
        disciplines = _normalize_share_per_level(raw)
        for d in disciplines:
            d["parent_id"] = d.pop("parent_code", "") or ""

        repo = _FakeRepo(disciplines=disciplines, total_mapped=100, total_projects=100)
        servicer = _make_servicer(repo)

        response = await servicer.AnalyzeEuroSciVoc(_build_request("ai"), context=None)
        fields_of_science = response["fields_of_science"]
        assert len(fields_of_science) == 2
        total_field_share = sum(float(f["share"]) for f in fields_of_science)
        assert total_field_share == pytest.approx(1.0), (
            "Σ fields_of_science.share muss 1.0 sein, "
            f"ist aber {total_field_share:.4f}"
        )

    @pytest.mark.asyncio
    async def test_multi_label_does_not_break_invariant(self) -> None:
        """Regression fuer den urspruenglichen Bug: AI/Blockchain Σshare > 1.

        Simulation: 100 Projekte, aber jedes Projekt ist in 3 FIELDs getagged.
        Counts sind daher kumuliert 300 — aber share muss trotzdem Σ=1.0 ergeben,
        weil wir gegen Σ(counts) normieren und nicht gegen total_projects (100).
        """
        raw = [
            {"id": "f1", "label": "AI",          "level": "FIELD", "parent_code": "", "project_count": 138},
            {"id": "f2", "label": "Blockchain",  "level": "FIELD", "parent_code": "", "project_count": 227},
            {"id": "f3", "label": "Robotics",    "level": "FIELD", "parent_code": "", "project_count":  35},
        ]
        disciplines = _normalize_share_per_level(raw)
        for d in disciplines:
            d["parent_id"] = d.pop("parent_code", "") or ""

        # total_projects = 100 (distinct), aber SUM(project_count) = 400 (Multi-Label).
        repo = _FakeRepo(disciplines=disciplines, total_mapped=100, total_projects=100)
        servicer = _make_servicer(repo)

        response = await servicer.AnalyzeEuroSciVoc(_build_request("ai"), context=None)
        total_share = sum(float(d["share"]) for d in response["disciplines"])
        assert total_share == pytest.approx(1.0)

        # Sanity: Kein einzelner Share-Wert darf > 1 sein.
        for d in response["disciplines"]:
            assert 0.0 <= float(d["share"]) <= 1.0 + 1e-9
