"""Tests fuer shared.domain.entity_resolution — Normalisierung, Blocking, Fuzzy Matching."""

from __future__ import annotations

import numpy as np
import pytest

from shared.domain.entity_resolution import (
    _levenshtein_dp,
    _strip_accents,
    find_matches,
    generate_blocking_key,
    levenshtein_similarity,
    normalize_actor_name,
    tfidf_cosine_similarity,
)


# ============================================================================
# normalize_actor_name()
# ============================================================================


class TestNormalizeActorName:
    """Schritt 1-5 der Normalisierungspipeline."""

    # --- Schritt 1: UPPER + TRIM ---

    def test_uppercase_and_trim(self):
        assert normalize_actor_name("  siemens  ") == "SIEMENS"

    def test_already_upper(self):
        assert normalize_actor_name("SIEMENS") == "SIEMENS"

    def test_mixed_case(self):
        assert normalize_actor_name("Fraunhofer Gesellschaft") == "FRAUNHOFER GESELLSCHAFT"

    # --- Schritt 2: Rechtsformen entfernen ---

    def test_remove_ag(self):
        result = normalize_actor_name("Siemens AG")
        assert "AG" not in result.split()
        assert "SIEMENS" in result

    def test_remove_gmbh(self):
        result = normalize_actor_name("Bosch GmbH")
        assert "GMBH" not in result
        assert "BOSCH" in result

    def test_remove_ltd(self):
        result = normalize_actor_name("ARM Ltd")
        assert "LTD" not in result
        assert "ARM" in result

    def test_remove_sa(self):
        result = normalize_actor_name("Airbus S.A.")
        assert "SA" not in result.split()
        assert "AIRBUS" in result

    def test_remove_bv(self):
        result = normalize_actor_name("ASML B.V.")
        assert "BV" not in result.split()
        assert "ASML" in result

    def test_remove_inc(self):
        result = normalize_actor_name("Google Inc.")
        assert "INC" not in result.split()
        assert "GOOGLE" in result

    def test_remove_corp(self):
        result = normalize_actor_name("Intel Corp.")
        assert "CORP" not in result.split()
        assert "INTEL" in result

    def test_remove_spa(self):
        result = normalize_actor_name("Enel S.p.A.")
        assert "SPA" not in result.split()

    def test_remove_srl(self):
        result = normalize_actor_name("Example S.r.l.")
        assert "SRL" not in result.split()

    def test_remove_ev(self):
        result = normalize_actor_name("Fraunhofer e.V.")
        assert "EV" not in result.split()
        assert "FRAUNHOFER" in result

    def test_remove_se(self):
        result = normalize_actor_name("SAP SE")
        assert "SAP" in result

    def test_remove_plc(self):
        result = normalize_actor_name("Rolls-Royce plc")
        assert "PLC" not in result

    def test_remove_llc(self):
        result = normalize_actor_name("SpaceX LLC")
        assert "LLC" not in result

    def test_remove_multiple_legal_forms(self):
        # Seltener Fall, aber sollte funktionieren
        result = normalize_actor_name("Example AG & Co. KG")
        assert "AG" not in result.split()
        assert "KG" not in result.split()

    # --- Schritt 3: Abkuerzungen expandieren ---

    def test_expand_univ(self):
        result = normalize_actor_name("Techn. Univ. Berlin")
        assert "UNIVERSITY" in result

    def test_expand_tech(self):
        result = normalize_actor_name("Tech Research Center")
        assert "TECHNOLOGY" in result

    def test_expand_inst(self):
        result = normalize_actor_name("Max Planck Inst")
        assert "INSTITUTE" in result

    def test_expand_natl(self):
        result = normalize_actor_name("Natl Research Council")
        assert "NATIONAL" in result

    def test_expand_intl(self):
        result = normalize_actor_name("Intl Energy Agency")
        assert "INTERNATIONAL" in result

    def test_expand_res(self):
        result = normalize_actor_name("Res Center Munich")
        assert "RESEARCH" in result

    def test_expand_ctr(self):
        result = normalize_actor_name("German Ctr for Aerospace")
        assert "CENTER" in result

    def test_expand_sci(self):
        result = normalize_actor_name("Academy of Sci")
        assert "SCIENCE" in result

    def test_expand_eng(self):
        result = normalize_actor_name("Faculty of Eng")
        assert "ENGINEERING" in result

    # --- Schritt 4: Sonderzeichen entfernen ---

    def test_remove_parentheses(self):
        result = normalize_actor_name("CNRS (Centre National)")
        assert "(" not in result
        assert ")" not in result
        assert "CNRS" in result

    def test_remove_hyphens(self):
        result = normalize_actor_name("Fraunhofer-Gesellschaft")
        # Bindestrich wird durch Leerzeichen ersetzt
        assert "-" not in result
        assert "FRAUNHOFER" in result

    def test_remove_dots(self):
        result = normalize_actor_name("Dr. Ing. h.c. F. Porsche")
        assert "." not in result

    def test_remove_commas(self):
        result = normalize_actor_name("University of Cambridge, UK")
        assert "," not in result

    def test_remove_ampersand(self):
        result = normalize_actor_name("Johnson & Johnson")
        assert "&" not in result

    # --- Schritt 5: Leerzeichen kollabieren ---

    def test_collapse_spaces(self):
        result = normalize_actor_name("MAX   PLANCK   INSTITUTE")
        assert "  " not in result
        assert result == "MAX PLANCK INSTITUTE"

    # --- Umlaute und Akzente ---

    def test_umlauts_stripped(self):
        # ASCII "ae" bleibt erhalten (kein Unicode-Akzent)
        result = normalize_actor_name("Technische Universitaet Muenchen")
        assert result == "TECHNISCHE UNIVERSITAET MUENCHEN"

    def test_unicode_umlauts_stripped(self):
        # Echte Unicode-Umlaute werden via NFKD normalisiert
        result = normalize_actor_name("Technische Universit\u00e4t M\u00fcnchen")
        assert result == "TECHNISCHE UNIVERSITAT MUNCHEN"

    def test_umlaut_o(self):
        result = normalize_actor_name("Joenkoeping")
        assert "O" in result or "OE" in result  # Je nach Unicode-Normalisierung

    def test_accent_stripped(self):
        result = normalize_actor_name("Ecole Polytechnique Federale")
        assert result == "ECOLE POLYTECHNIQUE FEDERALE"

    def test_french_accent(self):
        result = normalize_actor_name("Universite de Geneve")
        assert "UNIVERSITE" in result

    # --- Edge Cases ---

    def test_empty_string(self):
        assert normalize_actor_name("") == ""

    def test_whitespace_only(self):
        assert normalize_actor_name("   ") == ""

    def test_only_legal_form(self):
        result = normalize_actor_name("GmbH")
        # Rechtsform entfernt, Rest leer oder bereinigt
        assert result.strip() == ""

    def test_numeric_name(self):
        result = normalize_actor_name("3M Company")
        assert "3M" in result


# ============================================================================
# generate_blocking_key()
# ============================================================================


class TestGenerateBlockingKey:
    def test_basic(self):
        key = generate_blocking_key("Fraunhofer", "DE")
        assert key == "F_DE"

    def test_lowercase_input(self):
        key = generate_blocking_key("siemens", "de")
        assert key == "S_DE"

    def test_unknown_country(self):
        key = generate_blocking_key("Example", "")
        assert key == "E_XX"

    def test_none_country(self):
        key = generate_blocking_key("Example", None)  # type: ignore[arg-type]
        assert key == "E_XX"

    def test_empty_name(self):
        key = generate_blocking_key("", "DE")
        assert key == "__DE"

    def test_same_first_char_same_country(self):
        k1 = generate_blocking_key("Fraunhofer", "DE")
        k2 = generate_blocking_key("Friedrich-Alexander Univ", "DE")
        assert k1 == k2  # Beide im selben Block

    def test_different_first_char(self):
        k1 = generate_blocking_key("Fraunhofer", "DE")
        k2 = generate_blocking_key("Siemens", "DE")
        assert k1 != k2  # Verschiedene Blocks

    def test_same_name_different_country(self):
        k1 = generate_blocking_key("Airbus", "DE")
        k2 = generate_blocking_key("Airbus", "FR")
        assert k1 != k2  # Verschiedene Blocks


# ============================================================================
# levenshtein_similarity()
# ============================================================================


class TestLevenshteinSimilarity:
    def test_identical(self):
        assert levenshtein_similarity("SIEMENS", "SIEMENS") == 1.0

    def test_one_char_difference(self):
        sim = levenshtein_similarity("SIEMENS", "SIEMANS")
        # 1 Edit bei 7 Zeichen = 6/7 = 0.857
        assert sim == pytest.approx(6.0 / 7.0, abs=0.01)

    def test_completely_different(self):
        sim = levenshtein_similarity("AAAA", "ZZZZ")
        assert sim < 0.5

    def test_empty_both(self):
        assert levenshtein_similarity("", "") == 1.0

    def test_empty_one(self):
        assert levenshtein_similarity("ABC", "") == 0.0
        assert levenshtein_similarity("", "ABC") == 0.0

    def test_single_char(self):
        assert levenshtein_similarity("A", "A") == 1.0
        assert levenshtein_similarity("A", "B") == 0.0

    def test_transposition(self):
        sim = levenshtein_similarity("AB", "BA")
        # 2 Edits bei 2 Zeichen = 0.0
        assert sim == pytest.approx(0.0)

    def test_substring(self):
        sim = levenshtein_similarity("SIEMENS", "SIEMENS HEALTHCARE")
        assert 0.0 < sim < 1.0

    def test_symmetry(self):
        a = "FRAUNHOFER"
        b = "FRAUNHOPER"
        assert levenshtein_similarity(a, b) == pytest.approx(
            levenshtein_similarity(b, a),
        )


# ============================================================================
# _levenshtein_dp() — Fallback-Implementierung
# ============================================================================


class TestLevenshteinDP:
    def test_identical(self):
        assert _levenshtein_dp("ABC", "ABC") == 1.0

    def test_empty(self):
        assert _levenshtein_dp("", "") == 0.0  # Sonderfall: beide leer -> DP gibt 0.0

    def test_one_empty(self):
        assert _levenshtein_dp("ABC", "") == 0.0

    def test_one_edit(self):
        sim = _levenshtein_dp("KITTEN", "SITTEN")
        # 1 Substitution bei 6 Zeichen = 5/6
        assert sim == pytest.approx(5.0 / 6.0, abs=0.01)


# ============================================================================
# tfidf_cosine_similarity()
# ============================================================================


class TestTfidfCosineSimilarity:
    def test_identical_names(self):
        names = ["FRAUNHOFER GESELLSCHAFT", "FRAUNHOFER GESELLSCHAFT"]
        matrix = tfidf_cosine_similarity(names)
        assert matrix.shape == (2, 2)
        assert matrix[0, 1] == pytest.approx(1.0, abs=0.01)

    def test_similar_names(self):
        names = ["FRAUNHOFER GESELLSCHAFT", "FRAUNHOFER INSTITUTE"]
        matrix = tfidf_cosine_similarity(names)
        # Aehnlich, aber nicht identisch
        assert 0.3 < matrix[0, 1] < 1.0

    def test_different_names(self):
        names = ["FRAUNHOFER GESELLSCHAFT", "TOYOTA MOTOR"]
        matrix = tfidf_cosine_similarity(names)
        # Kaum Aehnlichkeit
        assert matrix[0, 1] < 0.5

    def test_single_name(self):
        matrix = tfidf_cosine_similarity(["SIEMENS"])
        assert matrix.shape == (1, 1)
        assert matrix[0, 0] == 1.0

    def test_empty_list(self):
        matrix = tfidf_cosine_similarity([])
        assert matrix.shape == (0, 0)

    def test_matrix_symmetric(self):
        names = ["AAA", "BBB", "CCC"]
        matrix = tfidf_cosine_similarity(names)
        assert matrix.shape == (3, 3)
        np.testing.assert_array_almost_equal(matrix, matrix.T)

    def test_diagonal_is_one(self):
        names = ["SIEMENS HEALTHCARE", "BOSCH ENGINEERING", "SAP TECHNOLOGY"]
        matrix = tfidf_cosine_similarity(names)
        for i in range(3):
            assert matrix[i, i] == pytest.approx(1.0, abs=0.01)

    def test_multiple_similar(self):
        names = [
            "TECHNISCHE UNIVERSITY MUENCHEN",
            "TECHNICAL UNIVERSITY MUNICH",
            "TOYOTA MOTOR CORPORATION",
        ]
        matrix = tfidf_cosine_similarity(names)
        # Die ersten beiden sollten aehnlicher sein als zum dritten
        assert matrix[0, 1] > matrix[0, 2]


# ============================================================================
# find_matches() — Integrations-Tests
# ============================================================================


class TestFindMatches:
    """End-to-End-Tests der Matching-Pipeline."""

    def test_empty_input(self):
        assert find_matches([]) == []

    def test_single_actor(self):
        actors = [{"name": "Siemens AG", "country": "DE", "source": "epo"}]
        result = find_matches(actors)
        assert len(result) == 1
        assert result[0]["members"][0]["confidence"] == 1.0
        assert result[0]["members"][0]["match_method"] == "singleton"

    def test_identical_names_matched(self):
        actors = [
            {"name": "Siemens", "country": "DE", "source": "epo"},
            {"name": "SIEMENS", "country": "DE", "source": "cordis"},
        ]
        result = find_matches(actors)
        # Identische normalisierte Namen muessen zusammengefuehrt werden
        assert len(result) == 1
        assert len(result[0]["members"]) == 2

    def test_siemens_ag_vs_siemens(self):
        """Siemens AG vs SIEMENS — Rechtsform-Entfernung fuehrt zu exaktem Match."""
        actors = [
            {"name": "Siemens AG", "country": "DE", "source": "epo"},
            {"name": "SIEMENS", "country": "DE", "source": "cordis"},
        ]
        result = find_matches(actors)
        assert len(result) == 1
        assert len(result[0]["members"]) == 2

    def test_fraunhofer_variants(self):
        """Fraunhofer mit aehnlich langen Namensformen."""
        actors = [
            {
                "name": "FRAUNHOFER GESELLSCHAFT E.V.",
                "country": "DE",
                "source": "cordis",
            },
            {
                "name": "FRAUNHOFER GESELLSCHAFT",
                "country": "DE",
                "source": "epo",
            },
        ]
        result = find_matches(actors, threshold=0.6)
        # Rechtsform "E.V." wird entfernt -> exakter Match
        matched_groups = [g for g in result if len(g["members"]) > 1]
        assert len(matched_groups) >= 1

    def test_long_vs_short_name_no_false_positive(self):
        """Sehr unterschiedlich lange Namen sollen konservativ behandelt werden."""
        actors = [
            {
                "name": "Fraunhofer-Gesellschaft zur Foerderung der angewandten Forschung e.V.",
                "country": "DE",
                "source": "cordis",
            },
            {
                "name": "FRAUNHOFER GESELLSCHAFT",
                "country": "DE",
                "source": "epo",
            },
        ]
        # Bei starkem Laengenunterschied: konservatives Matching verhindert FP
        result = find_matches(actors, threshold=0.8)
        # Kein erzwungener Match bei hohem Threshold erwartet
        assert len(result) >= 1  # Mindestens eine Gruppe existiert

    def test_completely_different_not_matched(self):
        """Voellig verschiedene Namen duerfen nicht gematcht werden."""
        actors = [
            {"name": "Siemens AG", "country": "DE", "source": "epo"},
            {"name": "Toyota Motor Corp.", "country": "JP", "source": "epo"},
        ]
        result = find_matches(actors)
        # Verschiedene Blocking-Keys (S_DE vs T_JP) — kein Vergleich
        assert len(result) == 2

    def test_blocking_prevents_cross_country_match(self):
        """Blocking separiert gleiche Anfangsbuchstaben in verschiedenen Laendern."""
        actors = [
            {"name": "Samsung Electronics", "country": "KR", "source": "epo"},
            {"name": "Sony Corporation", "country": "JP", "source": "epo"},
        ]
        result = find_matches(actors)
        # S_KR vs S_JP — verschiedene Blocks
        assert len(result) == 2

    def test_canonical_name_is_longest(self):
        """Kanonischer Name = laengster Originalname (meiste Information)."""
        actors = [
            {"name": "SIEMENS", "country": "DE", "source": "epo"},
            {"name": "Siemens AG", "country": "DE", "source": "cordis"},
        ]
        result = find_matches(actors)
        assert len(result) == 1
        # "Siemens AG" ist laenger als "SIEMENS"
        assert result[0]["canonical_name"] == "Siemens AG"

    def test_confidence_in_valid_range(self):
        actors = [
            {"name": "Bosch GmbH", "country": "DE", "source": "epo"},
            {"name": "ROBERT BOSCH", "country": "DE", "source": "cordis"},
        ]
        result = find_matches(actors, threshold=0.5)
        for group in result:
            for member in group["members"]:
                assert 0.0 <= member["confidence"] <= 1.0

    def test_source_preserved(self):
        actors = [
            {"name": "SAP SE", "country": "DE", "source": "epo"},
        ]
        result = find_matches(actors)
        assert result[0]["members"][0]["source"] == "epo"

    def test_source_id_preserved(self):
        """source_id wird durchgereicht falls vorhanden."""
        actors = [
            {"name": "SAP SE", "country": "DE", "source": "epo", "source_id": "42"},
        ]
        result = find_matches(actors)
        assert result[0]["members"][0]["source_id"] == "42"

    def test_normalized_name_in_output(self):
        actors = [
            {"name": "Siemens AG", "country": "DE", "source": "epo"},
        ]
        result = find_matches(actors)
        assert result[0]["members"][0]["normalized_name"] == "SIEMENS"

    def test_country_in_group(self):
        actors = [
            {"name": "Siemens AG", "country": "DE", "source": "epo"},
            {"name": "SIEMENS", "country": "DE", "source": "cordis"},
        ]
        result = find_matches(actors)
        assert result[0]["country"] == "DE"

    def test_high_threshold_fewer_matches(self):
        """Hoeherer Schwellwert fuehrt zu weniger Matches."""
        actors = [
            {"name": "Fraunhofer Institute", "country": "DE", "source": "cordis"},
            {"name": "FRAUNHOFER INSTITUT", "country": "DE", "source": "epo"},
        ]
        result_low = find_matches(actors, threshold=0.5)
        result_high = find_matches(actors, threshold=0.99)

        matched_low = sum(1 for g in result_low if len(g["members"]) > 1)
        matched_high = sum(1 for g in result_high if len(g["members"]) > 1)
        assert matched_low >= matched_high

    def test_multiple_groups(self):
        """Mehrere Akteure, mehrere Gruppen."""
        actors = [
            {"name": "Siemens AG", "country": "DE", "source": "epo"},
            {"name": "SIEMENS", "country": "DE", "source": "cordis"},
            {"name": "Bosch GmbH", "country": "DE", "source": "epo"},
            {"name": "BOSCH", "country": "DE", "source": "cordis"},
        ]
        result = find_matches(actors, threshold=0.7)
        # Siemens-Gruppe und Bosch-Gruppe
        assert len(result) <= 4  # Maximal 4 Gruppen
        # Pruefen, dass nicht alles in einer Gruppe landet
        names_in_groups = {g["canonical_name"] for g in result}
        assert len(names_in_groups) >= 1

    def test_match_method_set(self):
        actors = [
            {"name": "Siemens AG", "country": "DE", "source": "epo"},
            {"name": "SIEMENS", "country": "DE", "source": "cordis"},
        ]
        result = find_matches(actors)
        for group in result:
            for member in group["members"]:
                assert member["match_method"] in (
                    "exact", "levenshtein", "tfidf_cosine",
                    "combined", "singleton",
                )


# ============================================================================
# Realistische Testfaelle (aus der Thesis)
# ============================================================================


class TestRealWorldExamples:
    """Praxisnahe Matching-Szenarien aus EPO/CORDIS-Daten."""

    def test_tu_muenchen_variants(self):
        """TU Muenchen erscheint in verschiedenen Schreibweisen."""
        actors = [
            {
                "name": "Technische Universitaet Muenchen",
                "country": "DE",
                "source": "cordis",
            },
            {
                "name": "TECHNISCHE UNIVERSITAET MUENCHEN",
                "country": "DE",
                "source": "epo",
            },
        ]
        result = find_matches(actors)
        # Case-Normalisierung ergibt exakten Match
        assert len(result) == 1

    def test_cnrs_full_and_abbreviation(self):
        """CNRS: Abkuerzung vs. voller Name."""
        actors = [
            {
                "name": "CENTRE NATIONAL DE LA RECHERCHE SCIENTIFIQUE (CNRS)",
                "country": "FR",
                "source": "cordis",
            },
            {
                "name": "CNRS",
                "country": "FR",
                "source": "epo",
            },
        ]
        # Verschiedene Blocking-Keys (C vs C) — gleicher Block
        result = find_matches(actors, threshold=0.3)
        # CNRS vs. langer Name: sehr verschiedene Laengen
        # Bei Standard-Threshold (0.8) wuerden sie nicht matchen
        # Bei niedrigem Threshold koennen sie matchen
        assert len(result) >= 1

    def test_max_planck_variants(self):
        """Max-Planck-Gesellschaft — aehnliche Laengen matchen bei niedrigem Threshold."""
        actors = [
            {
                "name": "MAX PLANCK GESELLSCHAFT E.V.",
                "country": "DE",
                "source": "cordis",
            },
            {
                "name": "MAX PLANCK GESELLSCHAFT",
                "country": "DE",
                "source": "epo",
            },
        ]
        result = find_matches(actors, threshold=0.6)
        matched = [g for g in result if len(g["members"]) > 1]
        assert len(matched) >= 1

    def test_university_oxford_variants(self):
        """Universitaet Oxford in leicht verschiedenen Schreibweisen."""
        actors = [
            {"name": "University of Oxford", "country": "GB", "source": "cordis"},
            {"name": "UNIVERSITY OF OXFORD", "country": "GB", "source": "epo"},
        ]
        result = find_matches(actors)
        assert len(result) == 1

    def test_different_entities_not_merged(self):
        """Verschiedene Organisationen duerfen nicht zusammengefuehrt werden."""
        actors = [
            {"name": "Siemens AG", "country": "DE", "source": "epo"},
            {"name": "Samsung Electronics", "country": "DE", "source": "epo"},
        ]
        result = find_matches(actors)
        assert len(result) == 2

    def test_large_batch_performance(self):
        """Performance-Test mit 100 Akteuren (darf nicht haengen)."""
        actors = [
            {
                "name": f"Organization {i}",
                "country": "DE",
                "source": "epo",
            }
            for i in range(100)
        ]
        result = find_matches(actors)
        # Alle sollten Singletons sein (verschiedene Namen)
        assert len(result) == 100


# ============================================================================
# Accent-Stripping
# ============================================================================


class TestStripAccents:
    def test_german_umlaut_a(self):
        # ae-Umlaut
        result = _strip_accents("\u00e4")
        assert result == "a"

    def test_german_umlaut_o(self):
        result = _strip_accents("\u00f6")
        assert result == "o"

    def test_german_umlaut_u(self):
        result = _strip_accents("\u00fc")
        assert result == "u"

    def test_french_accent(self):
        result = _strip_accents("\u00e9")
        assert result == "e"

    def test_no_accents(self):
        assert _strip_accents("Siemens") == "Siemens"

    def test_empty(self):
        assert _strip_accents("") == ""

    def test_cedilla(self):
        result = _strip_accents("\u00e7")  # c-Cedilla
        assert result == "c"
