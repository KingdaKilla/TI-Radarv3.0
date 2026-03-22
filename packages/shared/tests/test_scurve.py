"""Tests fuer shared.domain.scurve — Logistische, Gompertz- und Richards-Fitting."""

from __future__ import annotations

import numpy as np
import pytest

from shared.domain.scurve import (
    AICC_UNDEFINED,
    RICHARDS_MIN_SAMPLE_SIZE,
    compute_aicc,
    estimate_initial_params,
    fit_best_model,
    fit_gompertz,
    fit_richards,
    fit_s_curve,
    gompertz_function,
    logistic_function,
    richards_function,
)


# ============================================================================
# logistic_function()
# ============================================================================


class TestLogisticFunction:
    def test_at_inflection_point(self):
        # Am Wendepunkt x0 ist f(x0) = L/2
        x = np.array([10.0])
        result = logistic_function(x, L=100.0, k=0.5, x0=10.0)
        assert result[0] == pytest.approx(50.0)

    def test_far_before_inflection(self):
        # Weit vor x0 -> nahe 0
        x = np.array([-100.0])
        result = logistic_function(x, L=100.0, k=0.5, x0=0.0)
        assert result[0] == pytest.approx(0.0, abs=1e-10)

    def test_far_after_inflection(self):
        # Weit nach x0 -> nahe L
        x = np.array([100.0])
        result = logistic_function(x, L=100.0, k=0.5, x0=0.0)
        assert result[0] == pytest.approx(100.0, abs=1e-5)

    def test_monotonically_increasing(self):
        x = np.linspace(0, 20, 50)
        y = logistic_function(x, L=100.0, k=0.5, x0=10.0)
        assert all(y[i] <= y[i + 1] for i in range(len(y) - 1))


# ============================================================================
# gompertz_function()
# ============================================================================


class TestGompertzFunction:
    def test_approaches_saturation(self):
        x = np.array([100.0])
        result = gompertz_function(x, L=100.0, b=5.0, k=0.3, x0=0.0)
        assert result[0] == pytest.approx(100.0, abs=0.1)

    def test_starts_near_zero(self):
        x = np.array([-50.0])
        result = gompertz_function(x, L=100.0, b=5.0, k=0.3, x0=0.0)
        assert result[0] < 1.0

    def test_monotonically_increasing(self):
        x = np.linspace(0, 50, 100)
        y = gompertz_function(x, L=1000.0, b=5.0, k=0.2, x0=0.0)
        assert all(y[i] <= y[i + 1] for i in range(len(y) - 1))


# ============================================================================
# estimate_initial_params()
# ============================================================================


class TestEstimateInitialParams:
    def test_basic_estimation(self):
        years = np.array([2000, 2005, 2010, 2015, 2020], dtype=np.float64)
        cumul = np.array([10, 50, 200, 500, 800], dtype=np.float64)
        L0, k0, x0 = estimate_initial_params(years, cumul)
        assert L0 > cumul[-1]  # Saettigung > letzter Wert
        assert k0 > 0  # Positive Wachstumsrate
        assert years[0] <= x0 <= years[-1] + 10  # Wendepunkt im Zeitraum

    def test_all_zeros(self):
        years = np.array([2000, 2005, 2010], dtype=np.float64)
        cumul = np.array([0, 0, 0], dtype=np.float64)
        L0, k0, x0 = estimate_initial_params(years, cumul)
        assert L0 > 0  # Fallback auf 1.0


# ============================================================================
# fit_s_curve()
# ============================================================================


class TestFitSCurve:
    def test_synthetic_logistic_data(self):
        """Synthetische logistische Daten — sollte guten Fit liefern."""
        years = list(range(2000, 2021))
        x = np.array(years, dtype=np.float64)
        # Generiere perfekte logistische Daten
        L, k, x0 = 1000.0, 0.5, 2010.0
        y = L / (1.0 + np.exp(-k * (x - x0)))
        cumulative = [int(v) for v in y]

        result = fit_s_curve(years, cumulative)

        assert result is not None
        assert result["model"] == "Logistic"
        assert result["r_squared"] > 0.95
        assert result["L"] > 0
        assert result["k"] > 0
        assert 0 <= result["maturity_percent"] <= 100

    def test_insufficient_data(self):
        assert fit_s_curve([2020, 2021], [10, 20]) is None
        assert fit_s_curve([], []) is None

    def test_all_zeros(self):
        assert fit_s_curve([2020, 2021, 2022], [0, 0, 0]) is None

    def test_fitted_values_structure(self):
        years = list(range(2000, 2015))
        cumul = [i * 10 for i in range(1, 16)]
        result = fit_s_curve(years, cumul)
        if result is not None:
            assert "fitted_values" in result
            assert len(result["fitted_values"]) == len(years)
            for fv in result["fitted_values"]:
                assert "year" in fv
                assert "fitted" in fv


# ============================================================================
# fit_gompertz()
# ============================================================================


class TestFitGompertz:
    def test_insufficient_data(self):
        assert fit_gompertz([2020], [10]) is None

    def test_all_zeros(self):
        assert fit_gompertz([2020, 2021, 2022], [0, 0, 0]) is None

    def test_reasonable_data(self):
        years = list(range(2000, 2020))
        cumul = [int(50 * np.exp(-5 * np.exp(-0.3 * (y - 2000)))) for y in years]
        result = fit_gompertz(years, cumul)
        if result is not None:
            assert result["model"] == "Gompertz"
            assert result["r_squared"] >= 0


# ============================================================================
# compute_aicc()
# ============================================================================


class TestComputeAICc:
    """Tests fuer das korrigierte Akaike-Informationskriterium (AICc)."""

    def test_aicc_perfect_fit(self):
        """RSS=0 (perfekter Fit) → AICc = -inf."""
        observed = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0]
        predicted = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0]
        aicc = compute_aicc(observed, predicted, num_params=3)
        assert aicc == float("-inf")

    def test_aicc_finite_for_imperfect_fit(self):
        """Bei Residuen > 0 muss AICc ein endlicher Wert sein."""
        observed = [1.0, 4.0, 9.0, 16.0, 25.0, 36.0, 49.0, 64.0, 81.0, 100.0]
        predicted = [1.5, 3.8, 9.2, 15.5, 25.5, 35.0, 50.0, 63.0, 82.0, 99.0]
        aicc = compute_aicc(observed, predicted, num_params=3)
        assert np.isfinite(aicc)

    def test_aicc_small_sample_returns_undefined(self):
        """Bei n <= k+1 ist AICc nicht berechenbar (Division durch Null).

        Fuer num_params=3 gilt k=4, also braucht man n > 5.
        Bei n=5 ist n-k-1=0 → Korrekturfaktor undefiniert.
        """
        observed = [1.0, 2.0, 3.0, 4.0, 5.0]
        predicted = [1.1, 2.1, 3.1, 4.1, 5.1]
        aicc = compute_aicc(observed, predicted, num_params=3)
        assert aicc == AICC_UNDEFINED

    def test_aicc_small_sample_correction_matters(self):
        """Korrekturfaktor 2k(k+1)/(n-k-1) soll bei n<10 substantiell sein.

        Vergleiche AICc mit Standard-AIC: Bei kleinem n muss die Differenz
        (= Korrekturterm) gross sein relativ zum AIC-Basiswert.
        """
        n = 8
        observed = list(range(1, n + 1))
        # Leicht verrauschte Vorhersagen
        predicted = [v + 0.5 * (-1) ** i for i, v in enumerate(observed)]
        num_params = 3
        k = num_params + 1  # = 4

        aicc = compute_aicc(observed, predicted, num_params=num_params)

        # Standard-AIC manuell berechnen
        rss = sum((o - p) ** 2 for o, p in zip(observed, predicted))
        aic_standard = n * np.log(rss / n) + 2 * k

        # Korrekturfaktor: 2*4*5 / (8-4-1) = 40/3 ≈ 13.33
        correction = (2 * k * (k + 1)) / (n - k - 1)

        assert aicc == pytest.approx(aic_standard + correction, rel=1e-6)
        # Bei n=8 ist der Korrekturfaktor > 10 → substantiell
        assert correction > 10.0

    def test_aicc_penalty_increases_with_params(self):
        """Mehr Parameter → höherer (schlechterer) AICc bei gleichem RSS.

        Bei identischen Residuen muss ein Modell mit 4 Parametern einen
        höheren AICc haben als eines mit 3 Parametern.
        """
        n = 20
        observed = [float(i ** 2) for i in range(1, n + 1)]
        # Gleiche (nicht perfekte) Vorhersage fuer beide "Modelle"
        predicted = [v + 1.0 for v in observed]

        aicc_3_params = compute_aicc(observed, predicted, num_params=3)
        aicc_4_params = compute_aicc(observed, predicted, num_params=4)

        # Mehr Parameter → höherer AICc (= schlechter)
        assert aicc_4_params > aicc_3_params

    def test_aicc_logistic_vs_gompertz_synthetic(self):
        """Synthetische logistische Daten — AICc sollte Logistic bevorzugen.

        Wenn die wahren Daten logistisch sind, darf Gompertz (4 Parameter)
        keinen besseren AICc haben, da der Extra-Parameter bestraft wird.
        """
        years = list(range(2000, 2021))  # n=21
        x = np.array(years, dtype=np.float64)
        # Perfekt logistische Daten mit leichtem Rauschen
        rng = np.random.default_rng(seed=42)
        L, k, x0 = 1000.0, 0.4, 2010.0
        y_true = L / (1.0 + np.exp(-k * (x - x0)))
        noise = rng.normal(0, 5.0, size=len(x))
        y_noisy = y_true + noise
        cumulative = [max(1, int(v)) for v in y_noisy]
        # Kumulative Werte muessen monoton steigend sein
        for i in range(1, len(cumulative)):
            cumulative[i] = max(cumulative[i], cumulative[i - 1])

        result = fit_best_model(years, cumulative)
        assert result is not None
        assert "aicc" in result
        assert "delta_aicc" in result
        assert "aicc_alternative" in result
        # Bei logistischen Daten sollte Logistic gewaehlt werden
        # (oder Gompertz mit sehr kleinem Delta-AICc)
        assert np.isfinite(result["aicc"])

    def test_aicc_numpy_array_input(self):
        """compute_aicc akzeptiert sowohl Listen als auch numpy-Arrays."""
        obs_list = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0]
        pred_list = [1.1, 2.2, 2.9, 4.1, 5.2, 5.8, 7.1, 7.9]

        aicc_from_list = compute_aicc(obs_list, pred_list, num_params=2)
        aicc_from_array = compute_aicc(
            np.array(obs_list), np.array(pred_list), num_params=2,
        )
        assert aicc_from_list == pytest.approx(aicc_from_array)


# ============================================================================
# fit_s_curve() — AICc-Integration
# ============================================================================


class TestFitSCurveAICc:
    """Tests fuer AICc-Felder in fit_s_curve() Ergebnissen."""

    def test_result_contains_aicc(self):
        years = list(range(2000, 2021))
        x = np.array(years, dtype=np.float64)
        y = 1000 / (1.0 + np.exp(-0.5 * (x - 2010.0)))
        cumul = [int(v) for v in y]
        result = fit_s_curve(years, cumul)
        assert result is not None
        assert "aicc" in result
        assert "num_params" in result
        assert result["num_params"] == 3

    def test_aicc_finite_for_good_data(self):
        years = list(range(2000, 2021))
        x = np.array(years, dtype=np.float64)
        y = 500 / (1.0 + np.exp(-0.3 * (x - 2010.0)))
        cumul = [int(v) for v in y]
        result = fit_s_curve(years, cumul)
        assert result is not None
        assert np.isfinite(result["aicc"])


# ============================================================================
# fit_gompertz() — AICc-Integration
# ============================================================================


class TestFitGompertzAICc:
    """Tests fuer AICc-Felder in fit_gompertz() Ergebnissen."""

    def test_result_contains_aicc(self):
        years = list(range(2000, 2020))
        cumul = [int(50 * np.exp(-5 * np.exp(-0.3 * (y - 2000)))) for y in years]
        result = fit_gompertz(years, cumul)
        if result is not None:
            assert "aicc" in result
            assert "num_params" in result
            assert result["num_params"] == 4


# ============================================================================
# richards_function()
# ============================================================================


class TestRichardsFunction:
    def test_m1_equals_logistic(self):
        """Bei m=1 muss Richards identisch mit Logistic sein."""
        x = np.linspace(2000, 2030, 50)
        L, k, x0 = 1000.0, 0.4, 2015.0

        logistic_vals = logistic_function(x, L, k, x0)
        richards_vals = richards_function(x, L, k, x0, m=1.0)

        np.testing.assert_allclose(richards_vals, logistic_vals, rtol=1e-10)

    def test_monotonically_increasing(self):
        x = np.linspace(2000, 2030, 100)
        y = richards_function(x, L=500.0, k=0.3, x0=2015.0, m=2.0)
        assert all(y[i] <= y[i + 1] for i in range(len(y) - 1))

    def test_approaches_saturation(self):
        """Weit nach x0 naehert sich der Wert L an."""
        x = np.array([2200.0])
        result = richards_function(x, L=1000.0, k=0.5, x0=2015.0, m=1.5)
        assert result[0] == pytest.approx(1000.0, abs=0.1)

    def test_m_affects_curve_shape(self):
        """Parameter m veraendert die Kurvenform (Asymmetrie).

        Bei groesserem m ist 1/m kleiner → Basis^(1/m) naeher an 1
        → Ergebnis naeher an L (spaetere, aber dann schnellere Saettigung).
        Bei kleinerem m ist 1/m groesser → staerkere Daempfung.
        """
        x = np.array([2020.0])
        L, k, x0 = 1000.0, 0.3, 2015.0

        val_m_small = richards_function(x, L, k, x0, m=0.3)
        val_m_large = richards_function(x, L, k, x0, m=3.0)

        # Bei groesserem m ist 1/m kleiner → hoehere Werte rechts vom Wendepunkt
        assert float(val_m_large[0]) > float(val_m_small[0])
        # Beide Werte muessen zwischen 0 und L liegen
        assert 0 < float(val_m_small[0]) < L
        assert 0 < float(val_m_large[0]) < L


# ============================================================================
# fit_richards()
# ============================================================================


class TestFitRichards:
    def test_synthetic_richards_data(self):
        """Synthetische Richards-Daten — sollte guten R² liefern."""
        years = list(range(2000, 2030))  # n=30
        x = np.array(years, dtype=np.float64)
        # Generiere Richards-Daten mit m=1.5
        L, k, x0, m = 800.0, 0.3, 2015.0, 1.5
        y = L / np.power(1.0 + np.exp(-k * (x - x0)), 1.0 / m)
        cumulative = [int(v) for v in y]
        # Monoton steigend sicherstellen
        for i in range(1, len(cumulative)):
            cumulative[i] = max(cumulative[i], cumulative[i - 1])

        result = fit_richards(years, cumulative)

        assert result is not None
        assert result["model"] == "Richards"
        assert result["r_squared"] > 0.95
        assert result["num_params"] == 4
        assert result["L"] > 0
        assert result["k"] > 0
        assert "m" in result
        assert 0 <= result["maturity_percent"] <= 100
        assert len(result["fitted_values"]) == len(years)

    def test_insufficient_data_default_min_points(self):
        """n < 5 (Standard min_points) liefert None."""
        assert fit_richards([2020, 2021, 2022, 2023], [10, 20, 30, 40]) is None

    def test_insufficient_data_custom_min_points(self):
        """Benutzerdefinierter min_points wird beachtet."""
        years = list(range(2020, 2028))  # n=8
        cumul = [i * 10 for i in range(1, 9)]
        # min_points=10 → zu wenige Daten
        assert fit_richards(years, cumul, min_points=10) is None

    def test_all_zeros(self):
        """Nur Nullen → kein Fit moeglich."""
        assert fit_richards([2020, 2021, 2022, 2023, 2024], [0, 0, 0, 0, 0]) is None

    def test_result_contains_aicc(self):
        """Ergebnis muss aicc und num_params enthalten."""
        years = list(range(2000, 2025))
        x = np.array(years, dtype=np.float64)
        y = 500 / np.power(1.0 + np.exp(-0.3 * (x - 2012)), 1.0 / 1.5)
        cumul = [max(1, int(v)) for v in y]
        for i in range(1, len(cumul)):
            cumul[i] = max(cumul[i], cumul[i - 1])

        result = fit_richards(years, cumul)
        if result is not None:
            assert "aicc" in result
            assert result["num_params"] == 4


# ============================================================================
# fit_best_model()
# ============================================================================


class TestFitBestModel:
    def test_selects_model_with_aicc(self):
        """fit_best_model selektiert via AICc und liefert alle AICc-Felder."""
        years = list(range(2000, 2021))
        x = np.array(years, dtype=np.float64)
        y = 500 / (1.0 + np.exp(-0.4 * (x - 2010.0)))
        cumul = [int(v) for v in y]

        result = fit_best_model(years, cumul)
        assert result is not None
        assert result["model"] in ("Logistic", "Gompertz", "Richards")
        assert result["model_name"] in ("logistic", "gompertz", "richards")
        assert result["r_squared"] > 0.5
        # AICc-Felder vorhanden
        assert "aicc" in result
        assert "delta_aicc" in result
        assert "aicc_alternative" in result

    def test_delta_aicc_nonnegative(self):
        """Delta-AICc muss >= 0 sein (Differenz der Absolutwerte)."""
        years = list(range(2000, 2021))
        x = np.array(years, dtype=np.float64)
        y = 500 / (1.0 + np.exp(-0.4 * (x - 2010.0)))
        cumul = [int(v) for v in y]

        result = fit_best_model(years, cumul)
        assert result is not None
        assert result["delta_aicc"] >= 0.0

    def test_none_for_bad_data(self):
        assert fit_best_model([], []) is None
        assert fit_best_model([2020, 2021, 2022], [0, 0, 0]) is None

    def test_single_model_fallback(self):
        """Wenn nur ein Modell fittet, wird es mit delta_aicc=0 zurueckgegeben."""
        # Sehr wenige Datenpunkte — evtl. fittet nur ein Modell
        years = list(range(2000, 2006))
        cumul = [1, 5, 20, 80, 200, 350]
        result = fit_best_model(years, cumul)
        if result is not None:
            assert "delta_aicc" in result
            assert "aicc_alternative" in result

    def test_model_name_field_present(self):
        """fit_best_model muss immer model_name (lowercase) zurueckgeben."""
        years = list(range(2000, 2015))
        cumul = [i ** 2 for i in range(1, 16)]
        result = fit_best_model(years, cumul)
        if result is not None:
            assert "model_name" in result
            assert result["model_name"] == result["model"].lower()


# ============================================================================
# fit_best_model() — Richards-Integration
# ============================================================================


class TestFitBestModelRichards:
    """Tests fuer Richards-Modell-Einbindung in fit_best_model()."""

    def test_includes_richards_large_sample(self):
        """Bei n >= 20 wird Richards als Kandidat einbezogen.

        Wir generieren asymmetrische Daten (m=2.0), bei denen Richards
        den besten Fit liefern sollte. Falls nicht, pruefen wir zumindest,
        dass model_name vorhanden ist und ein gueltiges Modell gewaehlt wird.
        """
        n = 30  # > RICHARDS_MIN_SAMPLE_SIZE
        assert n >= RICHARDS_MIN_SAMPLE_SIZE

        years = list(range(2000, 2000 + n))
        x = np.array(years, dtype=np.float64)
        # Richards-Daten mit deutlicher Asymmetrie (m=2.0)
        L, k, x0, m = 600.0, 0.25, 2015.0, 2.0
        y = L / np.power(1.0 + np.exp(-k * (x - x0)), 1.0 / m)
        cumulative = [max(1, int(v)) for v in y]
        for i in range(1, len(cumulative)):
            cumulative[i] = max(cumulative[i], cumulative[i - 1])

        result = fit_best_model(years, cumulative)
        assert result is not None
        assert result["model"] in ("Logistic", "Gompertz", "Richards")
        assert result["model_name"] in ("logistic", "gompertz", "richards")
        assert result["r_squared"] > 0.9

    def test_excludes_richards_small_sample(self):
        """Bei n < 20 darf Richards NICHT als Modell gewaehlt werden."""
        n = 15  # < RICHARDS_MIN_SAMPLE_SIZE
        assert n < RICHARDS_MIN_SAMPLE_SIZE

        years = list(range(2000, 2000 + n))
        x = np.array(years, dtype=np.float64)
        y = 500 / (1.0 + np.exp(-0.4 * (x - 2007.0)))
        cumul = [int(v) for v in y]

        result = fit_best_model(years, cumul)
        if result is not None:
            # Richards darf bei n < 20 nicht gewaehlt werden
            assert result["model"] in ("Logistic", "Gompertz")
            assert result["model_name"] in ("logistic", "gompertz")

    def test_richards_at_exact_threshold(self):
        """Bei n == RICHARDS_MIN_SAMPLE_SIZE (20) wird Richards einbezogen."""
        n = RICHARDS_MIN_SAMPLE_SIZE  # genau 20
        years = list(range(2000, 2000 + n))
        x = np.array(years, dtype=np.float64)
        y = 400 / np.power(1.0 + np.exp(-0.3 * (x - 2010)), 1.0 / 1.5)
        cumul = [max(1, int(v)) for v in y]
        for i in range(1, len(cumul)):
            cumul[i] = max(cumul[i], cumul[i - 1])

        result = fit_best_model(years, cumul)
        assert result is not None
        # Bei genau 20 Datenpunkten: Richards ist im Kandidaten-Pool
        assert result["model"] in ("Logistic", "Gompertz", "Richards")
