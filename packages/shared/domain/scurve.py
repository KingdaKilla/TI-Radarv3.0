"""S-Curve Fitting via logistische, Gompertz- und Richards-Funktion.

Implementiert drei Wachstumskurven zur Reifegrad-Analyse:
- Logistisch: f(x) = L / (1 + exp(-k*(x - x0))) — symmetrisch
- Gompertz: f(x) = L * exp(-b * exp(-k*(x - x0))) — asymmetrisch
- Richards: f(x) = L / (1 + exp(-k*(x - x0)))^(1/m) — verallgemeinert

Richards (1959) generalisiert Logistic (m=1) und nähert Gompertz (m→0) an.
Der Formparameter m steuert die Asymmetrie der Kurve.

Phasenklassifikation nach Gao et al. (2013). Modellselektion nach Franses (1994).
Ensemble-Selektion via AICc (korrigiertes Akaike-Informationskriterium).
AICc bevorzugt parsimoniöse Modelle und ist robuster als R² bei kleinen Stichproben
(n < 30, typisch für Patent-Zeitreihen). Burnham & Anderson (2002).
"""

from __future__ import annotations

import logging
from typing import Any

import numpy as np
from numpy.typing import NDArray
from scipy.optimize import curve_fit

logger = logging.getLogger(__name__)

# Sentinel-Wert fuer nicht-berechenbare AICc (z.B. perfekter Fit oder n <= k+1)
AICC_UNDEFINED = float("inf")


def compute_aicc(
    observed: list[float] | NDArray[np.float64],
    predicted: list[float] | NDArray[np.float64],
    num_params: int,
) -> float:
    """Berechne korrigiertes Akaike-Informationskriterium (AICc).

    AICc = n * ln(RSS/n) + 2k + 2k(k+1)/(n-k-1)

    Dabei ist k = num_params + 1 (Modellparameter + Fehlervarianz-Schaetzung).
    Niedrigere Werte bedeuten bessere Modelle. Die Korrektur (dritter Term)
    ist besonders bei kleinen Stichproben (n < 30) relevant und bestraft
    Überanpassung stärker als das Standard-AIC.

    Referenz: Burnham & Anderson (2002), Model Selection and Multimodel Inference.

    Args:
        observed: Beobachtete Werte (y)
        predicted: Vorhergesagte Werte aus dem Modell (y_hat)
        num_params: Anzahl Modell-Parameter (Logistic=3, Gompertz=4)

    Returns:
        AICc-Wert (niedriger = besser). AICC_UNDEFINED (inf) bei
        nicht-berechenbaren Fällen (RSS=0, n <= k+1).
    """
    obs = np.asarray(observed, dtype=np.float64)
    pred = np.asarray(predicted, dtype=np.float64)

    n = len(obs)
    k = num_params + 1  # +1 fuer Fehlervarianz-Parameter

    # Mindestens k+2 Datenpunkte noetig, damit der Korrekturfaktor definiert ist
    if n <= k + 1:
        logger.debug(
            "AICc nicht berechenbar: n=%d <= k+1=%d (zu wenige Datenpunkte)",
            n, k + 1,
        )
        return AICC_UNDEFINED

    # Residual Sum of Squares (RSS)
    rss = float(np.sum((obs - pred) ** 2))

    # Perfekter Fit (RSS=0) → ln(0) undefiniert
    if rss <= 0.0:
        logger.debug("AICc: RSS=0 (perfekter Fit), gebe -inf zurueck")
        return float("-inf")

    # AICc-Berechnung
    aic = n * np.log(rss / n) + 2.0 * k
    correction = (2.0 * k * (k + 1.0)) / (n - k - 1.0)

    return float(aic + correction)


def logistic_function(
    x: NDArray[np.float64], L: float, k: float, x0: float  # noqa: N803
) -> NDArray[np.float64]:
    """
    Logistische Funktion: f(x) = L / (1 + exp(-k * (x - x0))).

    Args:
        x: Zeitpunkte (Jahre)
        L: Saettigungsniveau (Obergrenze)
        k: Wachstumsrate (Steilheit)
        x0: Wendepunkt (Jahr mit staerkstem Wachstum)
    """
    result: NDArray[np.float64] = L / (1.0 + np.exp(-k * (x - x0)))
    return result


def estimate_initial_params(
    years: NDArray[np.float64],
    cumulative: NDArray[np.float64],
) -> tuple[float, float, float]:
    """
    Initiale Parameter fuer curve_fit schaetzen.

    Returns:
        (L0, k0, x0) — Startwerte fuer Saettigung, Wachstumsrate, Wendepunkt
    """
    y_max = float(cumulative[-1])
    sat = y_max * 1.5 if y_max > 0 else 1.0

    # x0: Jahr, in dem cumulative am naechsten an sat/2 liegt
    half_sat = sat / 2.0
    idx_mid = int(np.argmin(np.abs(cumulative - half_sat)))
    x0 = float(years[idx_mid])

    # k0: Aus 10%-90% Transitionsbreite schaetzen
    threshold_10 = sat * 0.1
    threshold_90 = sat * 0.9
    idx_10 = int(np.argmin(np.abs(cumulative - threshold_10)))
    idx_90 = int(np.argmin(np.abs(cumulative - threshold_90)))
    width = float(years[idx_90] - years[idx_10])
    k0 = 4.0 / width if width > 0 else 0.5

    return sat, k0, x0


def fit_s_curve(
    years: list[int],
    cumulative: list[int],
) -> dict[str, Any] | None:
    """
    S-Curve an kumulative Zeitreihe fitten.

    Args:
        years: Liste von Jahren
        cumulative: Kumulative Werte (monoton steigend)

    Returns:
        Dict mit L, k, x0, r_squared, fitted_values, maturity_percent
        oder None bei Fehler / unzureichenden Daten.
    """
    if len(years) < 3 or len(cumulative) < 3:
        return None

    x = np.array(years, dtype=np.float64)
    y = np.array(cumulative, dtype=np.float64)

    # Nur Nullen → kein Fit moeglich
    if y[-1] <= 0:
        return None

    try:
        sat0, k0, x0_init = estimate_initial_params(x, y)

        # Bounds: L > 0, k > 0, x0 innerhalb des Zeitraums
        lower = [y[-1] * 0.5, 0.001, float(x[0]) - 10.0]
        upper = [y[-1] * 10.0, 5.0, float(x[-1]) + 10.0]

        popt, _ = curve_fit(
            logistic_function,
            x,
            y,
            p0=[sat0, k0, x0_init],
            bounds=(lower, upper),
            method="trf",
            maxfev=5000,
        )

        sat_fit, k_fit, x0_fit = float(popt[0]), float(popt[1]), float(popt[2])

        # Gefittete Werte
        fitted = logistic_function(x, sat_fit, k_fit, x0_fit)

        # R² berechnen
        ss_res = float(np.sum((y - fitted) ** 2))
        ss_tot = float(np.sum((y - np.mean(y)) ** 2))
        r_squared = 1.0 - (ss_res / ss_tot) if ss_tot > 0 else 0.0

        # AICc berechnen (Logistic: 3 Parameter — L, k, x0)
        aicc = compute_aicc(y, fitted, num_params=3)

        # Maturity Percent: aktueller Wert / Saettigung
        maturity_percent = (float(y[-1]) / sat_fit) * 100.0 if sat_fit > 0 else 0.0

        return {
            "L": round(sat_fit, 2),
            "k": round(k_fit, 6),
            "x0": round(x0_fit, 2),
            "r_squared": round(r_squared, 4),
            "aicc": round(aicc, 4) if np.isfinite(aicc) else aicc,
            "num_params": 3,
            "maturity_percent": round(min(maturity_percent, 100.0), 2),
            "model": "Logistic",
            "fitted_values": [
                {"year": int(years[i]), "fitted": round(float(fitted[i]), 1)}
                for i in range(len(years))
            ],
        }

    except (RuntimeError, ValueError, TypeError) as e:
        logger.warning("S-Curve fit fehlgeschlagen: %s", e)
        return None


def gompertz_function(
    x: NDArray[np.float64], L: float, b: float, k: float, x0: float  # noqa: N803
) -> NDArray[np.float64]:
    """
    Gompertz-Funktion: f(x) = L * exp(-b * exp(-k * (x - x0))).

    Asymmetrische S-Kurve — Wachstum verlangsamt sich frueher als bei Logistic.

    Args:
        x: Zeitpunkte (Jahre)
        L: Saettigungsniveau (Obergrenze)
        b: Verschiebungsparameter (bestimmt den Start)
        k: Wachstumsrate
        x0: Referenz-Zeitpunkt
    """
    result: NDArray[np.float64] = L * np.exp(-b * np.exp(-k * (x - x0)))
    return result


def fit_gompertz(
    years: list[int],
    cumulative: list[int],
) -> dict[str, Any] | None:
    """
    Gompertz-Curve an kumulative Zeitreihe fitten.

    Args:
        years: Liste von Jahren
        cumulative: Kumulative Werte (monoton steigend)

    Returns:
        Dict mit L, b, k, x0, r_squared, fitted_values, maturity_percent, model
        oder None bei Fehler / unzureichenden Daten.
    """
    if len(years) < 3 or len(cumulative) < 3:
        return None

    x = np.array(years, dtype=np.float64)
    y = np.array(cumulative, dtype=np.float64)

    if y[-1] <= 0:
        return None

    try:
        y_max = float(y[-1])
        sat0 = y_max * 1.5 if y_max > 0 else 1.0

        # Initiale Parameter: b so, dass Start bei ~5% von L liegt
        b0 = 5.0
        # k aus 10-90% Transitionsbreite
        idx_10 = int(np.argmin(np.abs(y - sat0 * 0.1)))
        idx_90 = int(np.argmin(np.abs(y - sat0 * 0.9)))
        width = float(x[idx_90] - x[idx_10])
        k0 = 4.0 / width if width > 0 else 0.3
        x0_init = float(x[0])

        lower = [y_max * 0.5, 0.1, 0.001, float(x[0]) - 10.0]
        upper = [y_max * 10.0, 50.0, 5.0, float(x[-1]) + 10.0]

        popt, _ = curve_fit(
            gompertz_function,
            x,
            y,
            p0=[sat0, b0, k0, x0_init],
            bounds=(lower, upper),
            method="trf",
            maxfev=5000,
        )

        sat_fit, b_fit, k_fit, x0_fit = (
            float(popt[0]), float(popt[1]), float(popt[2]), float(popt[3])
        )

        fitted = gompertz_function(x, sat_fit, b_fit, k_fit, x0_fit)

        ss_res = float(np.sum((y - fitted) ** 2))
        ss_tot = float(np.sum((y - np.mean(y)) ** 2))
        r_squared = 1.0 - (ss_res / ss_tot) if ss_tot > 0 else 0.0

        # AICc berechnen (Gompertz: 4 Parameter — L, b, k, x0)
        aicc = compute_aicc(y, fitted, num_params=4)

        maturity_percent = (float(y[-1]) / sat_fit) * 100.0 if sat_fit > 0 else 0.0

        return {
            "L": round(sat_fit, 2),
            "k": round(k_fit, 6),
            "x0": round(x0_fit, 2),
            "r_squared": round(r_squared, 4),
            "aicc": round(aicc, 4) if np.isfinite(aicc) else aicc,
            "num_params": 4,
            "maturity_percent": round(min(maturity_percent, 100.0), 2),
            "model": "Gompertz",
            "fitted_values": [
                {"year": int(years[i]), "fitted": round(float(fitted[i]), 1)}
                for i in range(len(years))
            ],
        }

    except (RuntimeError, ValueError, TypeError) as e:
        logger.warning("Gompertz fit fehlgeschlagen: %s", e)
        return None


def richards_function(
    x: NDArray[np.float64],
    L: float,  # noqa: N803
    k: float,
    x0: float,
    m: float,
) -> NDArray[np.float64]:
    """Richards-Wachstumskurve (Generalisierung von Logistic/Gompertz).

    f(x) = L / (1 + exp(-k * (x - x0)))^(1/m)

    Parameter m steuert die Asymmetrie:
    - m=1: identisch mit Logistic (symmetrisch)
    - m<1: fruehere Saettigung (Gompertz-aehnlich)
    - m>1: spaetere Saettigung

    Referenz: Richards, F.J. (1959). A Flexible Growth Function for Empirical Use.
    Journal of Experimental Botany, 10(2), 290-301.

    Args:
        x: Zeitpunkte (Jahre)
        L: Saettigungsniveau (Obergrenze)
        k: Wachstumsrate (Steilheit)
        x0: Wendepunkt (Jahr mit staerkstem Wachstum)
        m: Formparameter (Asymmetrie)
    """
    base = 1.0 + np.exp(-k * (x - x0))
    # Numerische Stabilitaet: base > 0 ist garantiert (exp > 0 → base > 1)
    result: NDArray[np.float64] = L / np.power(base, 1.0 / m)
    return result


def fit_richards(
    years: list[int],
    cumulative: list[int],
    min_points: int = 5,
) -> dict[str, Any] | None:
    """Richards-Modell an kumulative Zeitreihe fitten.

    Das Richards-Modell hat 4 Parameter (L, k, x0, m) und erfordert
    daher mehr Datenpunkte als Logistic (3 Parameter), um Overfitting
    zu vermeiden. Empfohlen: min. 20 Datenpunkte (n >= 20).

    Bei min_points < 5 wird der Fit nicht versucht (zu wenige Daten
    fuer 4 Parameter). Standardwert ist 5, aber fuer robuste Ergebnisse
    sollte n >= 20 gelten.

    Args:
        years: Liste von Jahren
        cumulative: Kumulative Werte (monoton steigend)
        min_points: Mindestanzahl Datenpunkte (Standard: 5, empfohlen: 20)

    Returns:
        Dict mit L, k, x0, m, r_squared, fitted_values, maturity_percent, model,
        aicc, num_params=4 oder None bei Fehler / unzureichenden Daten.
    """
    if len(years) < min_points or len(cumulative) < min_points:
        return None

    x = np.array(years, dtype=np.float64)
    y = np.array(cumulative, dtype=np.float64)

    if y[-1] <= 0:
        return None

    try:
        sat0, k0, x0_init = estimate_initial_params(x, y)
        m0 = 1.0  # Startwert: symmetrisch (Logistic)

        # Bounds: L > 0, k ∈ [0.001, 5], x0 im Zeitraum ±10, m ∈ [0.1, 10]
        lower = [y[-1] * 0.5, 0.001, float(x[0]) - 10.0, 0.1]
        upper = [y[-1] * 10.0, 5.0, float(x[-1]) + 10.0, 10.0]

        popt, _ = curve_fit(
            richards_function,
            x,
            y,
            p0=[sat0, k0, x0_init, m0],
            bounds=(lower, upper),
            method="trf",
            maxfev=5000,
        )

        sat_fit = float(popt[0])
        k_fit = float(popt[1])
        x0_fit = float(popt[2])
        m_fit = float(popt[3])

        # Gefittete Werte
        fitted = richards_function(x, sat_fit, k_fit, x0_fit, m_fit)

        # R² berechnen
        ss_res = float(np.sum((y - fitted) ** 2))
        ss_tot = float(np.sum((y - np.mean(y)) ** 2))
        r_squared = 1.0 - (ss_res / ss_tot) if ss_tot > 0 else 0.0

        # AICc berechnen (Richards: 4 Parameter — L, k, x0, m)
        aicc = compute_aicc(y, fitted, num_params=4)

        # Maturity Percent: aktueller Wert / Saettigung
        maturity_percent = (float(y[-1]) / sat_fit) * 100.0 if sat_fit > 0 else 0.0

        return {
            "L": round(sat_fit, 2),
            "k": round(k_fit, 6),
            "x0": round(x0_fit, 2),
            "m": round(m_fit, 4),
            "r_squared": round(r_squared, 4),
            "aicc": round(aicc, 4) if np.isfinite(aicc) else aicc,
            "num_params": 4,
            "maturity_percent": round(min(maturity_percent, 100.0), 2),
            "model": "Richards",
            "fitted_values": [
                {"year": int(years[i]), "fitted": round(float(fitted[i]), 1)}
                for i in range(len(years))
            ],
        }

    except (RuntimeError, ValueError, TypeError) as e:
        logger.warning("Richards fit fehlgeschlagen: %s", e)
        return None


# Schwellenwert: Ab dieser Stichprobengroesse wird Richards in die
# Modellselektion einbezogen (4 Parameter erhoehen Overfitting-Risiko).
RICHARDS_MIN_SAMPLE_SIZE = 20


def fit_best_model(
    years: list[int],
    cumulative: list[int],
) -> dict[str, Any] | None:
    """Alle verfuegbaren Modelle fitten, via AICc selektieren.

    Modell-Pool:
    - Logistic (3 Parameter) — immer
    - Gompertz (4 Parameter) — immer
    - Richards (4 Parameter) — nur bei n >= RICHARDS_MIN_SAMPLE_SIZE (20)

    Richards wird bei kleinen Stichproben ausgeschlossen, da 4 frei
    variierbare Parameter (inkl. Formparameter m) zu Overfitting fuehren.

    AICc (korrigiertes Akaike-Informationskriterium) bestraft Modell-
    Komplexitaet und ist robuster als R² bei kleinen Stichproben.
    Niedrigerer AICc = besseres Modell.

    Delta-AICc Interpretation (Burnham & Anderson 2002):
    - < 2: Kaum Unterschied, beide Modelle plausibel
    - 2-7: Moderate Evidenz fuer das bessere Modell
    - > 7: Starke Evidenz fuer das bessere Modell

    Falls AICc nicht berechenbar (zu wenige Datenpunkte), Fallback auf R².

    Returns:
        Dict des besseren Modells mit 'model', 'model_name', 'aicc',
        'delta_aicc', 'aicc_alternative' Feldern, oder None.
    """
    # Kandidaten sammeln
    candidates: list[dict[str, Any]] = []

    logistic_result = fit_s_curve(years, cumulative)
    if logistic_result is not None:
        candidates.append(logistic_result)

    gompertz_result = fit_gompertz(years, cumulative)
    if gompertz_result is not None:
        candidates.append(gompertz_result)

    # Richards nur bei ausreichend Datenpunkten (Overfitting-Schutz)
    n = len(years)
    if n >= RICHARDS_MIN_SAMPLE_SIZE:
        richards_result = fit_richards(years, cumulative)
        if richards_result is not None:
            candidates.append(richards_result)

    if not candidates:
        return None

    # model_name Feld setzen (lowercase, konsistent mit Frontend)
    for c in candidates:
        c["model_name"] = c["model"].lower()

    if len(candidates) == 1:
        selected = candidates[0]
        selected["delta_aicc"] = 0.0
        selected["aicc_alternative"] = AICC_UNDEFINED
        return selected

    # AICc-basierte Selektion ueber alle Kandidaten
    valid_aicc = [(c, c["aicc"]) for c in candidates if np.isfinite(c["aicc"])]

    if len(valid_aicc) >= 2:
        # Sortiere nach AICc (niedrigster = bester)
        valid_aicc.sort(key=lambda t: t[1])
        selected = valid_aicc[0][0]
        runner_up = valid_aicc[1][0]

        # Delta-AICc: Differenz zwischen bestem und zweitbestem
        delta = abs(valid_aicc[1][1] - valid_aicc[0][1])
        selected["delta_aicc"] = round(delta, 4)
        selected["aicc_alternative"] = runner_up["aicc"]

        model_names = [c["model"] for c in candidates]
        aicc_values = {c["model"]: c["aicc"] for c in candidates}

        logger.info(
            "modellselektion_aicc",
            gewinner=selected["model"],
            kandidaten=model_names,
            aicc_werte=aicc_values,
            delta_aicc=round(delta, 4),
        )
        return selected

    if len(valid_aicc) == 1:
        # Nur ein Modell mit gueltigem AICc
        selected = valid_aicc[0][0]
        # Finde Alternative (beliebiger anderer Kandidat)
        alternatives = [c for c in candidates if c is not selected]
        alt_aicc = alternatives[0]["aicc"] if alternatives else AICC_UNDEFINED
        selected["delta_aicc"] = 0.0
        selected["aicc_alternative"] = alt_aicc
        return selected

    # Fallback: AICc nicht berechenbar (z.B. perfekter Fit oder n zu klein)
    # → R² als Ausweichkriterium
    logger.info(
        "modellselektion_fallback_r2",
        grund="AICc nicht berechenbar",
    )

    candidates.sort(key=lambda c: c["r_squared"], reverse=True)
    selected = candidates[0]
    runner_up = candidates[1]

    selected["delta_aicc"] = 0.0
    selected["aicc_alternative"] = runner_up["aicc"]
    return selected
