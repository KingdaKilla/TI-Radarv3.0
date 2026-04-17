"""UC2 MaturityServicer — gRPC-Implementierung der Reifegrad-Analyse.

Empfaengt AnalysisRequest, fuehrt S-Curve-Fit auf kumulative
Patent-Familien-Zeitreihen durch und klassifiziert die Technologie-Phase.

Migration von MVP v1.0:
- SQLite FTS5 MATCH -> PostgreSQL tsvector @@ plainto_tsquery
- aiosqlite -> asyncpg Connection Pool
- FastAPI Response -> gRPC Protobuf Messages
- S-Curve-Fit via shared.domain.scurve (Logistic + Gompertz)
"""

from __future__ import annotations

import itertools
import math
import time
from datetime import datetime, timezone
from typing import Any

import numpy as np

import asyncpg
import structlog

# --- gRPC-Imports (try/except, da Stubs noch nicht generiert) ---
try:
    import grpc
    from grpc import aio as grpc_aio
except ImportError:
    grpc = None  # type: ignore[assignment]
    grpc_aio = None  # type: ignore[assignment]

try:
    from shared.generated.python import common_pb2
    from shared.generated.python import uc2_maturity_pb2
    from shared.generated.python import uc2_maturity_pb2_grpc
except ImportError:
    common_pb2 = None  # type: ignore[assignment]
    uc2_maturity_pb2 = None  # type: ignore[assignment]
    uc2_maturity_pb2_grpc = None  # type: ignore[assignment]

# --- Shared Domain Metriken ---
from shared.domain.metrics import (
    R2_RELIABILITY_THRESHOLD,
    cagr,
    classify_maturity_phase,
    detect_decline,
    is_potentially_overfit,
    s_curve_confidence,
)
from shared.domain.scurve import fit_best_model, logistic_function, gompertz_function, richards_function
from shared.domain.year_completeness import last_complete_year

from src.config import Settings
from src.infrastructure.repository import MaturityRepository

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Helper: Basis-Klasse ermitteln (gRPC Servicer oder object)
# ---------------------------------------------------------------------------
def _get_base_class() -> type:
    """Gibt die gRPC-Servicer-Basisklasse zurueck, oder object als Fallback."""
    if uc2_maturity_pb2_grpc is not None:
        return uc2_maturity_pb2_grpc.MaturityServiceServicer  # type: ignore[return-value]
    return object


class MaturityServicer(_get_base_class()):  # type: ignore[misc]
    """gRPC-Servicer fuer UC2 Technology Maturity Assessment.

    Analysiert den Reifegrad einer Technologie:
    1. Patent-Familien-Zeitreihe (PostgreSQL, tsvector-Suche)
    2. Kumulative Summe berechnen
    3. S-Curve-Fit (Levenberg-Marquardt, Logistic + Gompertz)
    4. Phasenklassifikation nach Gao et al. (2013)
    5. CAGR-Wachstumsrate
    """

    def __init__(self, pool: asyncpg.Pool, settings: Settings | None = None) -> None:
        self._pool = pool
        self._settings = settings or Settings()
        self._repo = MaturityRepository(pool)

    async def AnalyzeMaturity(
        self,
        request: Any,
        context: Any,
    ) -> Any:
        """UC2: Technologie-Reifegrad analysieren.

        Empfaengt einen AnalysisRequest mit technology, time_range.
        Fuehrt S-Curve-Fit auf kumulative Patent-Familien-Zeitreihe durch.

        Args:
            request: tip.common.AnalysisRequest Protobuf-Message
            context: gRPC ServicerContext (fuer Fehlerbehandlung)

        Returns:
            tip.uc2.MaturityResponse Protobuf-Message
        """
        t0 = time.monotonic()

        # --- Request-Parameter extrahieren ---
        technology = request.technology
        request_id = request.request_id or ""

        # Zeitraum: Default 2010-2024 wenn nicht angegeben
        start_year = 2010
        end_year = 2024
        if request.time_range and request.time_range.start_year:
            start_year = request.time_range.start_year
        if request.time_range and request.time_range.end_year:
            end_year = request.time_range.end_year

        logger.info(
            "maturity_analyse_gestartet",
            technology=technology,
            start_year=start_year,
            end_year=end_year,
            request_id=request_id,
        )

        # --- Validierung ---
        if not technology or not technology.strip():
            if context is not None and grpc is not None:
                await context.abort(
                    grpc.StatusCode.INVALID_ARGUMENT,
                    "Feld 'technology' darf nicht leer sein",
                )
            return self._build_empty_response(request_id, t0)

        # --- Patent-Familien-Zeitreihe abfragen ---
        warnings: list[dict[str, str]] = []
        data_sources: list[dict[str, Any]] = []

        patent_years: dict[int, int] = {}
        try:
            # Primaer: unique families (OECD 2009 — Dopplungen vermeiden)
            rows = await self._repo.count_families_by_year(
                technology, start_year=start_year, end_year=end_year,
            )
            patent_years = {r.year: r.count for r in rows}

            # Fallback auf count_by_year falls keine family_id vorhanden
            if not patent_years:
                rows = await self._repo.count_patents_by_year(
                    technology, start_year=start_year, end_year=end_year,
                )
                patent_years = {r.year: r.count for r in rows}
        except Exception as e:
            logger.warning("patent_abfrage_fehlgeschlagen", fehler=str(e))
            warnings.append({
                "message": f"Patent-Abfrage fehlgeschlagen: {e}",
                "severity": "HIGH",
                "code": "QUERY_FAILED_PATENTS",
            })

        if patent_years:
            total_patents = sum(patent_years.values())
            data_sources.append({
                "name": "EPO DOCDB (PostgreSQL)",
                "type": "PATENT",
                "record_count": total_patents,
            })
        else:
            total_patents = 0

        # --- Daten-Vollstaendigkeits-Cutoff ---
        # MAJ-7/MAJ-8: ``last_complete_year()`` aus shared-Helper liefert das
        # letzte voll abgeschlossene Kalenderjahr (heute 2026-04-14 → 2025).
        # S-Curve-Fit und Phasen-Klassifikation duerfen NIE Teiljahre
        # einbeziehen, sonst wird R² fuer 2026 kuenstlich hoch und CAGR zu
        # niedrig.  Vorher hardcoded 2024 → ab 2026 stale.
        data_complete_year = last_complete_year()

        if end_year > data_complete_year:
            warnings.append({
                "message": (
                    f"Patentdaten ab {data_complete_year + 1} möglicherweise unvollständig "
                    f"(letztes vollständig abgeschlossenes Kalenderjahr: {data_complete_year})"
                ),
                "severity": "MEDIUM",
                "code": "DATA_INCOMPLETE_RECENT_YEARS",
            })

        # --- Kumulative Zeitreihe berechnen ---
        all_years = sorted(set(range(start_year, end_year + 1)))
        combined: list[int] = [patent_years.get(year, 0) for year in all_years]
        cumulative = list(itertools.accumulate(combined))

        # --- CAGR berechnen ---
        # Bug C-004: maturity.cagr muss methodisch identisch zu
        # landscape.patent_cagr sein, sonst flippt z.B. bei mRNA das
        # Vorzeichen (maturity -18.4 % vs landscape +3.1 %).
        # Gleiches Vorgehen wie ``landscape-svc/_safe_cagr``:
        #   1. Filter auf Jahre <= data_complete_year (kein Teiljahr).
        #   2. Erster/letzter Jahrgang mit Zaehlwert >= 0 aus dem gefilterten
        #      Bereich (Endpunkt-basiert, konsistent mit OECD-Praxis).
        #   3. Gleicher ``shared.domain.metrics.cagr``-Aufruf.
        # Dies liefert den "empirischen" CAGR, der spaeter als Alias fuer
        # das deprecated ``cagr``-Feld (Proto-5) und als neues ``empirical_cagr``
        # (Proto-18) ausgeliefert wird.
        growth_rate = _compute_empirical_cagr(
            all_years=all_years,
            combined=combined,
            data_complete_year=data_complete_year,
        )

        # --- S-Curve-Fit (nur auf vollstaendige Jahre) ---
        min_patents = self._settings.min_patents_for_fit
        s_curve_result: dict[str, Any] | None = None

        # Fit nur auf Jahre mit vollstaendigen Daten
        fit_end_idx = len(all_years)
        for i, y in enumerate(all_years):
            if y > data_complete_year:
                fit_end_idx = i
                break
        fit_years = all_years[:fit_end_idx]
        fit_cumulative = cumulative[:fit_end_idx]

        if fit_cumulative and fit_cumulative[-1] >= min_patents:
            s_curve_result = fit_best_model(fit_years, fit_cumulative)
        elif cumulative and cumulative[-1] > 0:
            warnings.append({
                "message": (
                    f"Zu wenige Patente ({cumulative[-1]}) fuer S-Curve-Fit "
                    f"(Minimum: {min_patents}) — Fallback auf Heuristik"
                ),
                "severity": "MEDIUM",
                "code": "INSUFFICIENT_DATA_FOR_FIT",
            })

        # --- Phasenklassifikation ---
        maturity_pct = 0.0
        sat_level = 0.0
        inflection = 0.0
        growth_rate_k = 0.0
        r_sq = 0.0
        fitted_on = "patents"
        s_curve_fitted: list[dict[str, Any]] = []
        conf = 0.0
        confidence_lower = 0.0
        confidence_upper = 0.0
        confidence_level = 0.0
        years_to_next_phase = 0
        aicc_selected = 0.0
        aicc_alternative = 0.0
        delta_aicc = 0.0
        # Bug MAJ-9: Reliability-Flag, das die UI deterministisch bewerten kann.
        # True nur, wenn ein Sigmoid-Fit zustande kam UND R² >= R2_RELIABILITY_THRESHOLD.
        fit_reliability_flag = False
        # Overfitting-Warnung: R² > 0.98 bei n < 30 Datenpunkten ist ein
        # klassisches Overfitting-Signal (3-Parameter Sigmoid mit wenig Daten).
        # Ergaenzt fit_reliability_flag um den umgekehrten Fall "Fit zu gut".
        overfit_warning = False

        if s_curve_result is not None:
            maturity_pct = s_curve_result["maturity_percent"]
            sat_level = s_curve_result["L"]
            inflection = s_curve_result["x0"]
            growth_rate_k = s_curve_result["k"]
            r_sq = s_curve_result["r_squared"]
            s_curve_fitted = s_curve_result["fitted_values"]
            fitted_on = s_curve_result.get("model", "Logistic").lower()

            # Extrapolate fitted values for years beyond data_complete_year
            fitted_year_set = {fv["year"] for fv in s_curve_fitted}
            extra_years = [y for y in all_years if y not in fitted_year_set]
            if extra_years:
                x_extra = np.array(extra_years, dtype=np.float64)
                model_name = s_curve_result.get("model", "Logistic")
                if model_name == "Gompertz":
                    b_param = s_curve_result.get("b", 5.0)
                    extrapolated = gompertz_function(x_extra, sat_level, b_param, growth_rate_k, inflection)
                elif model_name == "Richards":
                    m_param = s_curve_result.get("m", 1.0)
                    extrapolated = richards_function(x_extra, sat_level, growth_rate_k, inflection, m_param)
                else:
                    extrapolated = logistic_function(x_extra, sat_level, growth_rate_k, inflection)
                for i, yr in enumerate(extra_years):
                    s_curve_fitted.append({"year": yr, "fitted": round(float(extrapolated[i]), 1)})

            # AICc-Werte (Modellselektion nach Burnham & Anderson 2002)
            raw_aicc = s_curve_result.get("aicc", 0.0)
            aicc_selected = raw_aicc if isinstance(raw_aicc, (int, float)) and math.isfinite(raw_aicc) else 0.0
            raw_alt = s_curve_result.get("aicc_alternative", 0.0)
            aicc_alternative = raw_alt if isinstance(raw_alt, (int, float)) and math.isfinite(raw_alt) else 0.0
            delta_aicc = s_curve_result.get("delta_aicc", 0.0)

            # Gewichtete Konfidenz (s_curve_confidence gibt bei R² < 0.5 hart 0 zurueck)
            conf = s_curve_confidence(r_sq, len(all_years), cumulative[-1] if cumulative else 0)
            confidence_level = conf

            # Bug MAJ-9: Bei unzuverlaessigem Fit (R² < Threshold) keine Phase-Sicherheit.
            # Strukturelle Kopplung: confidence ist bereits 0 (s_curve_confidence-Gate),
            # zusaetzlich wird das Phase-Label auf "Unknown" gesetzt und der Reliability-
            # Flag bleibt False, damit das Frontend den Badge ausgrauen kann.
            if r_sq < R2_RELIABILITY_THRESHOLD:
                phase_en = "Unknown"
                confidence_level = 0.0
                conf = 0.0
                confidence_lower = 0.0
                confidence_upper = 0.0
                years_to_next_phase = 0
                warnings.append({
                    "message": (
                        f"S-Curve-Fit unzuverlaessig (R²={r_sq:.3f} < "
                        f"{R2_RELIABILITY_THRESHOLD}) — Phase-Label nicht aussagekraeftig"
                    ),
                    "severity": "MEDIUM",
                    "code": "FIT_UNRELIABLE_LOW_R2",
                })
            else:
                fit_reliability_flag = True
                # Overfitting-Pruefung: nur sinnvoll bei zuverlaessigem Fit.
                # Basis ist die Anzahl der Jahre, die tatsaechlich in den Fit
                # eingingen (fit_years — schliesst Teiljahre via data_complete_year aus).
                overfit_warning = is_potentially_overfit(r_sq, len(fit_years))
                if overfit_warning:
                    warnings.append({
                        "message": (
                            f"Hoher R²-Wert ({r_sq:.3f}) bei nur {len(fit_years)} "
                            "Datenpunkten — Fit moeglicherweise ueberangepasst"
                        ),
                        "severity": "MEDIUM",
                        "code": "FIT_POTENTIALLY_OVERFIT",
                    })
                # Phase via maturity_percent (Gao et al. 2013)
                phase_en, _phase_de, _ = classify_maturity_phase(
                    combined, maturity_percent=maturity_pct, r_squared=r_sq,
                )

                # Konfidenzintervall (einfache Schaetzung via R²)
                spread = (1.0 - r_sq) * 20.0  # Breite abhaengig von Fit-Guete
                confidence_lower = max(0.0, maturity_pct - spread)
                confidence_upper = min(100.0, maturity_pct + spread)

                # Jahre bis zur naechsten Phase (grobe Schaetzung)
                years_to_next_phase = _estimate_years_to_next_phase(
                    maturity_pct, growth_rate_k, sat_level, cumulative[-1] if cumulative else 0,
                )
        else:
            # Fallback: Kein Sigmoid-Fit moeglich. Heuristik darf KEINE Konfidenz
            # transportieren (Bug MAJ-9), da kein R² zur Verankerung vorliegt.
            # Konfidenz zwingend 0 ueber s_curve_confidence(0, ...) — strukturell.
            phase_en = "Unknown"
            conf = s_curve_confidence(0.0, len(all_years), cumulative[-1] if cumulative else 0)
            confidence_level = conf  # immer 0.0 (R²-Kopplung in s_curve_confidence)
            fit_reliability_flag = False
            if cumulative and cumulative[-1] > 0 and cumulative[-1] >= min_patents:
                warnings.append({
                    "message": "S-Curve-Fit fehlgeschlagen — kein zuverlaessiges Phase-Label",
                    "severity": "MEDIUM",
                    "code": "FIT_FAILED_FALLBACK",
                })

        # --- Decline-Erkennung (ergaenzt S-Kurve) ---
        # Bug A-002 / B-9: Vor dem Fix wurde is_declining nur gesetzt, wenn
        # maturity_pct >= 90 UND detect_decline(combined) gleichzeitig zutrafen.
        # Bei mRNA (cagr -18.4 %, maturity 39 %) und CRISPR (cagr -22 %, maturity
        # 41 %) blieb is_declining=False, obwohl der Trend klar negativ ist.
        # Neue Regel (siehe ``determine_is_declining``):
        #   (a) empirical_cagr < 0                              -> Decline
        #   (b) maturity_pct >= 90 UND detect_decline(combined) -> Plateau-Decline
        # Zusaetzlich: Phase-Konsistenz — is_declining <=> phase == DECLINING.
        is_declining = determine_is_declining(
            empirical_cagr_percent=growth_rate,
            maturity_pct=maturity_pct,
            combined=combined,
        )
        if is_declining:
            phase_en = "Decline"
            logger.info(
                "decline_phase_erkannt",
                technology=technology,
                maturity_pct=round(maturity_pct, 1),
                empirical_cagr=round(growth_rate, 2),
            )
        elif phase_en == "Decline":
            # Gegenrichtung: Ist das Phase-Label bereits Decline (z.B. via
            # classify_maturity_phase), muss is_declining=True folgen.
            is_declining = True

        # --- Fitted growth rate (Gompertz/Logistic/Richards) ---
        # Dies ist die momentane Wachstumsrate aus dem gefitteten Modell am
        # letzten Datenpunkt, NICHT der historische Durchschnitt. Vorher
        # wurde dieser Wert teilweise als "cagr" verkauft, was zu C-004 fuehrte.
        fitted_growth_rate = _compute_fitted_growth_rate(
            s_curve_result=s_curve_result,
            fit_years=fit_years,
        )

        # --- Verarbeitungszeit ---
        processing_time_ms = int((time.monotonic() - t0) * 1000)

        logger.info(
            "maturity_analyse_abgeschlossen",
            technology=technology,
            phase=phase_en,
            maturity_pct=round(maturity_pct, 1),
            r_squared=round(r_sq, 4),
            total_patents=total_patents,
            dauer_ms=processing_time_ms,
        )

        # --- Response bauen ---
        return self._build_response(
            all_years=all_years,
            cumulative=cumulative,
            combined=combined,
            s_curve_fitted=s_curve_fitted,
            phase_en=phase_en,
            maturity_pct=maturity_pct,
            r_sq=r_sq,
            growth_rate=growth_rate,
            sat_level=sat_level,
            growth_rate_k=growth_rate_k,
            inflection=inflection,
            confidence_lower=confidence_lower,
            confidence_upper=confidence_upper,
            confidence_level=confidence_level,
            years_to_next_phase=years_to_next_phase,
            fitted_on=fitted_on,
            is_declining=is_declining,
            data_sources=data_sources,
            warnings=warnings,
            request_id=request_id,
            processing_time_ms=processing_time_ms,
            data_complete_year=data_complete_year,
            aicc_selected=aicc_selected,
            aicc_alternative=aicc_alternative,
            delta_aicc=delta_aicc,
            fit_reliability_flag=fit_reliability_flag,
            overfit_warning=overfit_warning,
            fitted_growth_rate=fitted_growth_rate,
        )

    # -----------------------------------------------------------------------
    # Response Builder
    # -----------------------------------------------------------------------

    def _build_response(
        self,
        *,
        all_years: list[int],
        cumulative: list[int],
        combined: list[int],
        s_curve_fitted: list[dict[str, Any]],
        phase_en: str,
        maturity_pct: float,
        r_sq: float,
        growth_rate: float,
        sat_level: float,
        growth_rate_k: float,
        inflection: float,
        confidence_lower: float,
        confidence_upper: float,
        confidence_level: float,
        years_to_next_phase: int,
        fitted_on: str,
        is_declining: bool = False,
        data_sources: list[dict[str, Any]],
        warnings: list[dict[str, str]],
        request_id: str,
        processing_time_ms: int,
        data_complete_year: int | None = None,
        aicc_selected: float = 0.0,
        aicc_alternative: float = 0.0,
        delta_aicc: float = 0.0,
        fit_reliability_flag: bool = False,
        overfit_warning: bool = False,
        fitted_growth_rate: float = 0.0,
    ) -> Any:
        """MaturityResponse aus berechneten Daten zusammenbauen.

        Wenn gRPC-Stubs nicht verfuegbar sind, wird ein dict zurueckgegeben
        (fuer Tests und Entwicklung ohne generierten Code).
        """
        # MAJ-7/MAJ-8: Default-Vollstaendigkeitsjahr aus dem shared-Helper.
        if data_complete_year is None:
            data_complete_year = last_complete_year()
        if uc2_maturity_pb2 is None or common_pb2 is None:
            return self._build_dict_response(
                all_years=all_years,
                cumulative=cumulative,
                combined=combined,
                s_curve_fitted=s_curve_fitted,
                phase_en=phase_en,
                maturity_pct=maturity_pct,
                r_sq=r_sq,
                growth_rate=growth_rate,
                sat_level=sat_level,
                growth_rate_k=growth_rate_k,
                inflection=inflection,
                confidence_lower=confidence_lower,
                confidence_upper=confidence_upper,
                confidence_level=confidence_level,
                years_to_next_phase=years_to_next_phase,
                fitted_on=fitted_on,
                is_declining=is_declining,
                data_sources=data_sources,
                warnings=warnings,
                request_id=request_id,
                processing_time_ms=processing_time_ms,
                data_complete_year=data_complete_year,
                aicc_selected=aicc_selected,
                aicc_alternative=aicc_alternative,
                delta_aicc=delta_aicc,
                fit_reliability_flag=fit_reliability_flag,
                overfit_warning=overfit_warning,
                fitted_growth_rate=fitted_growth_rate,
            )

        # --- Protobuf-Messages bauen ---
        # S-Curve Datenpunkte
        fitted_map = {fv["year"]: fv["fitted"] for fv in s_curve_fitted}
        s_curve_data = []
        for i, year in enumerate(all_years):
            s_curve_data.append(uc2_maturity_pb2.SCurveDataPoint(
                year=year,
                cumulative=float(cumulative[i]),
                fitted=fitted_map.get(year, 0.0),
                annual_count=float(combined[i]),
            ))

        # Phase-Enum mappen
        phase_map = {
            "Emerging": uc2_maturity_pb2.EMERGING,
            "Growing": uc2_maturity_pb2.GROWING,
            "Mature": uc2_maturity_pb2.MATURE,
            "Saturation": uc2_maturity_pb2.SATURATION,
            "Decline": uc2_maturity_pb2.DECLINE,
        }
        phase_enum = phase_map.get(phase_en, uc2_maturity_pb2.TECHNOLOGY_PHASE_UNSPECIFIED)

        # Logistic Parameters
        model_params = uc2_maturity_pb2.LogisticParameters(
            carrying_capacity=sat_level,
            growth_rate=growth_rate_k,
            inflection_year=inflection,
        )

        # Confidence
        confidence = uc2_maturity_pb2.MaturityConfidence(
            lower_bound=confidence_lower,
            upper_bound=confidence_upper,
            confidence_level=confidence_level,
        )

        # Metadata
        _severity_map = {
            "LOW": common_pb2.LOW,
            "MEDIUM": common_pb2.MEDIUM,
            "HIGH": common_pb2.HIGH,
        }
        _source_type_map = {
            "PATENT": common_pb2.PATENT,
            "PUBLICATION": common_pb2.PUBLICATION,
            "PROJECT": common_pb2.PROJECT,
            "FUNDING": common_pb2.FUNDING,
        }

        pb_warnings = [
            common_pb2.Warning(
                message=w["message"],
                severity=_severity_map.get(w.get("severity", "LOW"), common_pb2.LOW),
                code=w.get("code", ""),
            )
            for w in warnings
        ]

        pb_sources = [
            common_pb2.DataSource(
                name=ds["name"],
                type=_source_type_map.get(ds.get("type", ""), common_pb2.DATA_SOURCE_TYPE_UNSPECIFIED),
                record_count=ds.get("record_count", 0),
            )
            for ds in data_sources
        ]

        metadata = common_pb2.ResponseMetadata(
            processing_time_ms=processing_time_ms,
            data_sources=pb_sources,
            warnings=pb_warnings,
            request_id=request_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

        # ``overfit_warning`` ist Proto-Feld 17 — erst ab regeneriertem Stub
        # verfuegbar. Defensive Konstruktion: Feld nur setzen, wenn der
        # Message-Type es unterstuetzt (vermeidet Crash bei veralteten Stubs).
        # C-004: ``cagr`` bleibt aus Abwaertskompatibilitaet als Alias
        # fuer den empirischen CAGR stehen. Neue Clients lesen stattdessen
        # ``empirical_cagr`` (Feld 18) oder ``fitted_growth_rate`` (Feld 19).
        empirical_cagr_fraction = growth_rate / 100.0
        response_kwargs: dict[str, Any] = dict(
            s_curve_data=s_curve_data,
            phase=phase_enum,
            maturity_percent=maturity_pct,
            r_squared=r_sq,
            cagr=empirical_cagr_fraction,  # Protobuf: Fraction, nicht Prozent
            model_parameters=model_params,
            confidence=confidence,
            years_to_next_phase=years_to_next_phase,
            fitted_on=fitted_on,
            metadata=metadata,
            data_complete_year=data_complete_year,
            aicc_selected=aicc_selected,
            aicc_alternative=aicc_alternative,
            delta_aicc=delta_aicc,
            is_declining=is_declining,
            fit_reliability_flag=fit_reliability_flag,
        )
        _fields = uc2_maturity_pb2.MaturityResponse.DESCRIPTOR.fields_by_name
        if "overfit_warning" in _fields:
            response_kwargs["overfit_warning"] = overfit_warning
        # Neue Felder aus Bundle H (C-004): nur setzen, wenn der generierte
        # Stub bereits den erweiterten Proto-Stand kennt. Sonst defensiv
        # weglassen, damit veraltete Stubs nicht crashen.
        if "empirical_cagr" in _fields:
            response_kwargs["empirical_cagr"] = empirical_cagr_fraction
        if "fitted_growth_rate" in _fields:
            response_kwargs["fitted_growth_rate"] = fitted_growth_rate
        return uc2_maturity_pb2.MaturityResponse(**response_kwargs)

    def _build_dict_response(
        self,
        *,
        all_years: list[int],
        cumulative: list[int],
        combined: list[int],
        s_curve_fitted: list[dict[str, Any]],
        phase_en: str,
        maturity_pct: float,
        r_sq: float,
        growth_rate: float,
        sat_level: float,
        growth_rate_k: float,
        inflection: float,
        confidence_lower: float,
        confidence_upper: float,
        confidence_level: float,
        years_to_next_phase: int,
        fitted_on: str,
        is_declining: bool = False,
        data_sources: list[dict[str, Any]],
        warnings: list[dict[str, str]],
        request_id: str,
        processing_time_ms: int,
        data_complete_year: int | None = None,
        aicc_selected: float = 0.0,
        aicc_alternative: float = 0.0,
        delta_aicc: float = 0.0,
        fit_reliability_flag: bool = False,
        overfit_warning: bool = False,
        fitted_growth_rate: float = 0.0,
    ) -> dict[str, Any]:
        """Fallback-Response als dict (wenn gRPC-Stubs nicht generiert)."""
        # MAJ-7/MAJ-8: Default kommt aus dem shared-Helper, kein Hardcoding.
        if data_complete_year is None:
            data_complete_year = last_complete_year()
        fitted_map = {fv["year"]: fv["fitted"] for fv in s_curve_fitted}
        # C-004: ``cagr`` bleibt als Alias fuer den empirischen CAGR erhalten.
        empirical_cagr_fraction = growth_rate / 100.0
        return {
            "s_curve_data": [
                {
                    "year": year,
                    "cumulative": float(cumulative[i]),
                    "fitted": fitted_map.get(year, 0.0),
                    "annual_count": float(combined[i]),
                }
                for i, year in enumerate(all_years)
            ],
            "phase": phase_en,
            "maturity_percent": maturity_pct,
            "r_squared": r_sq,
            "cagr": empirical_cagr_fraction,
            "empirical_cagr": empirical_cagr_fraction,
            "fitted_growth_rate": fitted_growth_rate,
            "model_parameters": {
                "carrying_capacity": sat_level,
                "growth_rate": growth_rate_k,
                "inflection_year": inflection,
            },
            "confidence": {
                "lower_bound": confidence_lower,
                "upper_bound": confidence_upper,
                "confidence_level": confidence_level,
            },
            "years_to_next_phase": years_to_next_phase,
            "fitted_on": fitted_on,
            "is_declining": is_declining,
            "data_complete_year": data_complete_year,
            "aicc_selected": aicc_selected,
            "aicc_alternative": aicc_alternative,
            "delta_aicc": delta_aicc,
            "fit_reliability_flag": fit_reliability_flag,
            "overfit_warning": overfit_warning,
            "metadata": {
                "processing_time_ms": processing_time_ms,
                "data_sources": data_sources,
                "warnings": warnings,
                "request_id": request_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        }

    def _build_empty_response(self, request_id: str, t0: float) -> Any:
        """Leere Response bei ungueltigem Request."""
        processing_time_ms = int((time.monotonic() - t0) * 1000)
        return self._build_response(
            all_years=[],
            cumulative=[],
            combined=[],
            s_curve_fitted=[],
            phase_en="Unknown",
            maturity_pct=0.0,
            r_sq=0.0,
            growth_rate=0.0,
            sat_level=0.0,
            growth_rate_k=0.0,
            inflection=0.0,
            confidence_lower=0.0,
            confidence_upper=0.0,
            confidence_level=0.95,
            years_to_next_phase=0,
            fitted_on="",
            data_sources=[],
            warnings=[],
            request_id=request_id,
            processing_time_ms=processing_time_ms,
        )


# ---------------------------------------------------------------------------
# Hilfsfunktionen
# ---------------------------------------------------------------------------

def _compute_empirical_cagr(
    *,
    all_years: list[int],
    combined: list[int],
    data_complete_year: int,
) -> float:
    """Naiver (Endpunkt-)CAGR ueber die jaehrlichen Raten.

    Gleiche Methode wie ``landscape-svc._safe_cagr`` (Bug C-004 Fix):
    - Filter auf Jahre ``<= data_complete_year`` (keine Teiljahre).
    - Erster/letzter Jahrgang mit Zaehlwert > 0 aus dem gefilterten Fenster.
    - ``shared.domain.metrics.cagr`` liefert Prozent (z.B. 12.5 fuer 12.5 %).

    Gibt 0.0 zurueck, wenn keine zwei positiven Jahrgaenge gefunden werden
    oder der Zeitraum null ist.
    """
    if not all_years or not combined:
        return 0.0

    # Indices nur fuer vollstaendige Jahre behalten und davon die mit Count > 0.
    valid_indices = [
        i
        for i, y in enumerate(all_years)
        if y <= data_complete_year and combined[i] > 0
    ]
    if len(valid_indices) < 2:
        return 0.0

    first_idx = valid_indices[0]
    last_idx = valid_indices[-1]
    year_span = all_years[last_idx] - all_years[first_idx]
    if year_span <= 0:
        return 0.0

    return cagr(
        float(combined[first_idx]),
        float(combined[last_idx]),
        year_span,
    )


def _compute_fitted_growth_rate(
    *,
    s_curve_result: dict[str, Any] | None,
    fit_years: list[int],
) -> float:
    """Momentane Wachstumsrate aus dem gewaehlten Modell (Bug C-004).

    Gibt die relative Steigung der Fit-Kurve am letzten Fit-Jahr zurueck
    (``(y[n] / y[n-1]) - 1``). Fraction (0.123 = 12.3 %), kein Prozent.

    Warum ueber die fitted_values und nicht die Parameter selbst:
    Gompertz- und Logistic-Parameter sind unterschiedlich skaliert, was zu
    C-004 gefuehrt hat. Die empirische Steigung der gefitteten Kurve ist
    modell-unabhaengig vergleichbar.
    """
    if s_curve_result is None or not fit_years or len(fit_years) < 2:
        return 0.0

    fitted_points = s_curve_result.get("fitted_values") or []
    if len(fitted_points) < 2:
        return 0.0

    # letzte zwei gefittete Werte im Fit-Fenster
    year_to_fit = {fv["year"]: float(fv["fitted"]) for fv in fitted_points}
    y_last = year_to_fit.get(fit_years[-1])
    y_prev = year_to_fit.get(fit_years[-2])
    if y_last is None or y_prev is None or y_prev <= 0:
        return 0.0

    return (y_last / y_prev) - 1.0


def determine_is_declining(
    *,
    empirical_cagr_percent: float,
    maturity_pct: float,
    combined: list[int],
) -> bool:
    """Decline-Regel fuer Bundle H (Bug A-002 / B-9).

    Zwei unabhaengige Kriterien — ODER-Verknuepfung:
      (a) ``empirical_cagr_percent < 0`` — klarer historischer Rueckgang,
          auch ohne 90 %-Plateau (mRNA cagr=-18.4 %, CRISPR cagr=-22 %).
      (b) ``maturity_pct >= 90`` UND ``detect_decline(combined)`` — klassischer
          Post-Peak-Decline auf dem Plateau.

    Vorher war nur (b) aktiv, weshalb mRNA und CRISPR trotz stark negativem
    CAGR mit is_declining=False ausgeliefert wurden.
    """
    if empirical_cagr_percent < 0.0:
        return True
    if maturity_pct >= 90.0 and detect_decline(combined):
        return True
    return False


def _estimate_years_to_next_phase(
    maturity_pct: float,
    growth_rate_k: float,
    carrying_capacity: float,
    current_cumulative: int,
) -> int:
    """Grobe Schaetzung: Jahre bis zur naechsten Phasengrenze.

    Phasengrenzen (Gao et al. 2013):
    - Emerging -> Growing: 10%
    - Growing -> Mature: 50%
    - Mature -> Saturation: 90%

    Gibt 0 zurueck wenn bereits in Saturation oder Berechnung nicht moeglich.
    """
    if growth_rate_k <= 0 or carrying_capacity <= 0:
        return 0

    # Naechste Grenze bestimmen
    if maturity_pct < 10.0:
        target_pct = 10.0
    elif maturity_pct < 50.0:
        target_pct = 50.0
    elif maturity_pct < 90.0:
        target_pct = 90.0
    else:
        return 0  # Bereits in Saturation

    # Einfache lineare Schaetzung basierend auf aktuellem Wachstum
    target_value = carrying_capacity * target_pct / 100.0
    remaining = target_value - current_cumulative

    if remaining <= 0:
        return 0

    # Durchschnittliche jaehrliche Zunahme aus k und aktuellem Stand
    # Naeherung: bei k=0.3 und Mitte der S-Kurve waechst es ca. L*k/4 pro Jahr
    annual_growth = carrying_capacity * growth_rate_k / 4.0
    if annual_growth <= 0:
        return 0

    return max(1, int(remaining / annual_growth))
