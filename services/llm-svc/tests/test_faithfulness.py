"""Tests fuer LLM Faithfulness-Guards (Asai et al. 2023, Yan et al. 2024).

Prueft:
- LLMFaithfulnessChecker.check_sufficiency: Context-Sufficiency-Check (CRAG)
- LLMFaithfulnessChecker.check_faithfulness: Faithfulness-Self-Check (Self-RAG)
- _parse_claims: Regex-Parser fuer CLAIM/VERDICT-Zeilen
- AnalyzePanelWithContext Integration: Dynamische Konfidenz statt hardcoded 0.85
- Settings: Neue faithfulness-Konfigurationsfelder

Alle Tests verwenden gemockte LLM-Provider (kein externer API-Aufruf).
"""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock

from src.config import Settings
from src.domain.ports import FaithfulnessPort, LLMProviderPort
from src.infrastructure.faithfulness import (
    LLMFaithfulnessChecker,
    _parse_claims,
)
from src.use_case import AnalyzePanelWithContext


# ---------------------------------------------------------------------------
# Mock LLM Provider
# ---------------------------------------------------------------------------


class MockLLMProvider(LLMProviderPort):
    """Test-Double fuer LLMProviderPort mit konfigurierbarer Antwort."""

    def __init__(
        self,
        generate_text: str = "",
        generate_model: str = "test-model",
    ) -> None:
        self.generate_text = generate_text
        self.generate_model = generate_model
        self.generate_calls: list[tuple[str, str]] = []

    async def generate(
        self, system_prompt: str, user_prompt: str
    ) -> tuple[str, str]:
        self.generate_calls.append((system_prompt, user_prompt))
        return self.generate_text, self.generate_model

    async def chat(
        self, system_prompt: str, messages: list[dict[str, str]]
    ) -> tuple[str, str]:
        return "", ""


class FailingLLMProvider(LLMProviderPort):
    """LLM-Provider der immer eine Exception wirft."""

    async def generate(
        self, system_prompt: str, user_prompt: str
    ) -> tuple[str, str]:
        raise RuntimeError("LLM API down")

    async def chat(
        self, system_prompt: str, messages: list[dict[str, str]]
    ) -> tuple[str, str]:
        raise RuntimeError("LLM API down")


# ---------------------------------------------------------------------------
# Tests: Settings — neue Faithfulness-Felder
# ---------------------------------------------------------------------------


class TestFaithfulnessSettings:
    """Prueft ob Settings die neuen Faithfulness-Felder hat."""

    def test_default_values(self) -> None:
        """Standardwerte der Faithfulness-Konfiguration."""
        s = Settings(_env_file=None)
        assert s.faithfulness_enabled is False
        assert s.sufficiency_threshold == "PARTIAL"
        assert s.faithfulness_model == "claude-haiku"

    def test_enabled_override(self) -> None:
        """faithfulness_enabled kann auf True gesetzt werden."""
        s = Settings(_env_file=None, faithfulness_enabled=True)
        assert s.faithfulness_enabled is True

    def test_threshold_override(self) -> None:
        """sufficiency_threshold kann ueberschrieben werden."""
        s = Settings(_env_file=None, sufficiency_threshold="SUFFICIENT")
        assert s.sufficiency_threshold == "SUFFICIENT"


# ---------------------------------------------------------------------------
# Tests: check_sufficiency (CRAG, Yan et al. 2024)
# ---------------------------------------------------------------------------


class TestCheckSufficiency:
    """Context-Sufficiency-Check (CRAG, Yan et al. 2024)."""

    async def test_sufficient_context(self) -> None:
        """LLM antwortet SUFFICIENT -> returns 'SUFFICIENT'."""
        mock = MockLLMProvider(generate_text="SUFFICIENT")
        checker = LLMFaithfulnessChecker(mock)

        result = await checker.check_sufficiency(
            context="Quantum computing uses qubits...",
            question="What is quantum computing?",
        )

        assert result == "SUFFICIENT"
        assert len(mock.generate_calls) == 1

    async def test_insufficient_context(self) -> None:
        """LLM antwortet INSUFFICIENT -> returns 'INSUFFICIENT'."""
        mock = MockLLMProvider(generate_text="INSUFFICIENT")
        checker = LLMFaithfulnessChecker(mock)

        result = await checker.check_sufficiency(
            context="The weather is nice today.",
            question="What is quantum computing?",
        )

        assert result == "INSUFFICIENT"

    async def test_partial_context(self) -> None:
        """LLM antwortet PARTIAL -> returns 'PARTIAL'."""
        mock = MockLLMProvider(generate_text="PARTIAL")
        checker = LLMFaithfulnessChecker(mock)

        result = await checker.check_sufficiency(
            context="Quantum computing is emerging...",
            question="What are the top 10 quantum algorithms?",
        )

        assert result == "PARTIAL"

    async def test_sufficient_with_extra_text(self) -> None:
        """LLM antwortet mit extra Text, aber SUFFICIENT drin -> 'SUFFICIENT'."""
        mock = MockLLMProvider(
            generate_text="The context is SUFFICIENT to answer the question."
        )
        checker = LLMFaithfulnessChecker(mock)

        result = await checker.check_sufficiency(context="...", question="...")
        assert result == "SUFFICIENT"

    async def test_malformed_response_defaults_to_partial(self) -> None:
        """Unerwartete LLM-Antwort -> defaults to 'PARTIAL'."""
        mock = MockLLMProvider(generate_text="I'm not sure what you mean.")
        checker = LLMFaithfulnessChecker(mock)

        result = await checker.check_sufficiency(context="...", question="...")
        assert result == "PARTIAL"

    async def test_llm_error_defaults_to_partial(self) -> None:
        """LLM-Fehler -> defaults to 'PARTIAL' (fail-open)."""
        checker = LLMFaithfulnessChecker(FailingLLMProvider())

        result = await checker.check_sufficiency(context="...", question="...")
        assert result == "PARTIAL"

    async def test_empty_response_defaults_to_partial(self) -> None:
        """Leere LLM-Antwort -> defaults to 'PARTIAL'."""
        mock = MockLLMProvider(generate_text="")
        checker = LLMFaithfulnessChecker(mock)

        result = await checker.check_sufficiency(context="...", question="...")
        assert result == "PARTIAL"

    async def test_lowercase_response_recognized(self) -> None:
        """Kleinschreibung wird korrekt erkannt (case-insensitive)."""
        mock = MockLLMProvider(generate_text="sufficient")
        checker = LLMFaithfulnessChecker(mock)

        result = await checker.check_sufficiency(context="...", question="...")
        assert result == "SUFFICIENT"


# ---------------------------------------------------------------------------
# Tests: check_faithfulness (Self-RAG, Asai et al. 2023)
# ---------------------------------------------------------------------------


class TestCheckFaithfulness:
    """Faithfulness-Self-Check (Self-RAG, Asai et al. 2023)."""

    async def test_all_supported(self) -> None:
        """Alle Claims SUPPORTED -> score 1.0, empty unsupported list."""
        mock = MockLLMProvider(
            generate_text=(
                "CLAIM: Quantum computing uses qubits | VERDICT: SUPPORTED\n"
                "CLAIM: QC has exponential speedup | VERDICT: SUPPORTED\n"
                "CLAIM: IBM leads in QC | VERDICT: SUPPORTED"
            )
        )
        checker = LLMFaithfulnessChecker(mock)

        score, unsupported = await checker.check_faithfulness(
            context="Quantum computing...", answer="Analysis text..."
        )

        assert score == 1.0
        assert unsupported == []

    async def test_mixed_support(self) -> None:
        """2/4 SUPPORTED, 2/4 UNSUPPORTED -> score 0.5, 2 unsupported claims."""
        mock = MockLLMProvider(
            generate_text=(
                "CLAIM: Quantum computing uses qubits | VERDICT: SUPPORTED\n"
                "CLAIM: QC will replace classical computing by 2025 | VERDICT: UNSUPPORTED\n"
                "CLAIM: IBM has 1000-qubit processor | VERDICT: SUPPORTED\n"
                "CLAIM: Google achieved AGI with QC | VERDICT: UNSUPPORTED"
            )
        )
        checker = LLMFaithfulnessChecker(mock)

        score, unsupported = await checker.check_faithfulness(
            context="Quantum computing...", answer="Analysis text..."
        )

        assert score == 0.5
        assert len(unsupported) == 2
        assert "QC will replace classical computing by 2025" in unsupported
        assert "Google achieved AGI with QC" in unsupported

    async def test_all_unsupported(self) -> None:
        """Alle Claims UNSUPPORTED -> score 0.0."""
        mock = MockLLMProvider(
            generate_text=(
                "CLAIM: Totally made up fact | VERDICT: UNSUPPORTED\n"
                "CLAIM: Another fabrication | VERDICT: UNSUPPORTED"
            )
        )
        checker = LLMFaithfulnessChecker(mock)

        score, unsupported = await checker.check_faithfulness(
            context="Quantum computing...", answer="Analysis text..."
        )

        assert score == 0.0
        assert len(unsupported) == 2

    async def test_no_claims_found(self) -> None:
        """Keine Claims extrahierbar -> score 0.0."""
        mock = MockLLMProvider(
            generate_text="I could not identify any specific claims."
        )
        checker = LLMFaithfulnessChecker(mock)

        score, unsupported = await checker.check_faithfulness(
            context="...", answer="..."
        )

        assert score == 0.0
        assert unsupported == []

    async def test_llm_error_returns_zero(self) -> None:
        """LLM-Fehler -> score 0.0, empty list."""
        checker = LLMFaithfulnessChecker(FailingLLMProvider())

        score, unsupported = await checker.check_faithfulness(
            context="...", answer="..."
        )

        assert score == 0.0
        assert unsupported == []

    async def test_single_supported_claim(self) -> None:
        """Ein einzelner SUPPORTED Claim -> score 1.0."""
        mock = MockLLMProvider(
            generate_text="CLAIM: Valid fact | VERDICT: SUPPORTED"
        )
        checker = LLMFaithfulnessChecker(mock)

        score, unsupported = await checker.check_faithfulness(
            context="...", answer="..."
        )

        assert score == 1.0
        assert unsupported == []

    async def test_three_of_four_supported(self) -> None:
        """3/4 SUPPORTED -> score 0.75."""
        mock = MockLLMProvider(
            generate_text=(
                "CLAIM: Fact A | VERDICT: SUPPORTED\n"
                "CLAIM: Fact B | VERDICT: SUPPORTED\n"
                "CLAIM: Fact C | VERDICT: SUPPORTED\n"
                "CLAIM: Fact D | VERDICT: UNSUPPORTED"
            )
        )
        checker = LLMFaithfulnessChecker(mock)

        score, unsupported = await checker.check_faithfulness(
            context="...", answer="..."
        )

        assert score == 0.75
        assert len(unsupported) == 1
        assert "Fact D" in unsupported


# ---------------------------------------------------------------------------
# Tests: _parse_claims
# ---------------------------------------------------------------------------


class TestParseClaims:
    """Regex-Parser fuer CLAIM/VERDICT-Zeilen."""

    def test_standard_format(self) -> None:
        """Standard-Format wird korrekt geparst."""
        text = "CLAIM: Some fact | VERDICT: SUPPORTED"
        claims = _parse_claims(text)
        assert len(claims) == 1
        assert claims[0] == ("Some fact", "SUPPORTED")

    def test_multiple_claims(self) -> None:
        """Mehrere Claims werden alle geparst."""
        text = (
            "CLAIM: Fact A | VERDICT: SUPPORTED\n"
            "CLAIM: Fact B | VERDICT: UNSUPPORTED\n"
            "CLAIM: Fact C | VERDICT: SUPPORTED"
        )
        claims = _parse_claims(text)
        assert len(claims) == 3

    def test_case_insensitive(self) -> None:
        """Gross-/Kleinschreibung wird korrekt behandelt."""
        text = "Claim: Some fact | Verdict: Supported"
        claims = _parse_claims(text)
        assert len(claims) == 1
        assert claims[0][1] == "SUPPORTED"

    def test_extra_whitespace(self) -> None:
        """Extra Whitespace wird ignoriert."""
        text = "CLAIM:   Extra spaces here   |   VERDICT:   UNSUPPORTED  "
        claims = _parse_claims(text)
        assert len(claims) == 1
        assert claims[0] == ("Extra spaces here", "UNSUPPORTED")

    def test_no_claims(self) -> None:
        """Text ohne Claims ergibt leere Liste."""
        text = "I could not identify any claims in the text."
        claims = _parse_claims(text)
        assert claims == []

    def test_empty_text(self) -> None:
        """Leerer Text ergibt leere Liste."""
        assert _parse_claims("") == []

    def test_mixed_with_preamble(self) -> None:
        """Claims werden auch mit Praembel-Text korrekt geparst."""
        text = (
            "Here are the claims I found:\n\n"
            "CLAIM: First claim | VERDICT: SUPPORTED\n"
            "Some additional commentary\n"
            "CLAIM: Second claim | VERDICT: UNSUPPORTED\n"
        )
        claims = _parse_claims(text)
        assert len(claims) == 2


# ---------------------------------------------------------------------------
# Tests: AnalyzePanelWithContext Integration mit Faithfulness
# ---------------------------------------------------------------------------


class TestAnalyzePanelWithContextFaithfulness:
    """Integration: AnalyzePanelWithContext mit Faithfulness-Guards."""

    async def test_without_faithfulness_backward_compatible(self) -> None:
        """Ohne Faithfulness bleibt Verhalten identisch (hardcoded 0.85)."""
        mock = MockLLMProvider(generate_text="Analyse-Ergebnis hier.")
        uc = AnalyzePanelWithContext(mock)

        result = await uc.execute(
            technology="Quantum Computing",
            use_case_key="landscape",
            panel_data_json='{"total": 100}',
            context_documents=[],
        )

        assert result.confidence == 0.85
        assert result.analysis_text == "Analyse-Ergebnis hier."

    async def test_with_faithfulness_dynamic_confidence(self) -> None:
        """Mit Faithfulness wird Score als dynamische Konfidenz verwendet."""
        # Main LLM liefert Analyse-Text
        main_llm = MockLLMProvider(generate_text="Analyse basierend auf Kontext.")

        # Faithfulness-Checker mock
        faith_mock = AsyncMock(spec=FaithfulnessPort)
        faith_mock.check_sufficiency = AsyncMock(return_value="SUFFICIENT")
        faith_mock.check_faithfulness = AsyncMock(return_value=(0.75, ["Unsupported claim"]))

        uc = AnalyzePanelWithContext(main_llm, faithfulness=faith_mock)

        result = await uc.execute(
            technology="Quantum Computing",
            use_case_key="landscape",
            panel_data_json='{"total": 100}',
            context_documents=[],
        )

        assert result.analysis_text == "Analyse basierend auf Kontext."
        assert result.confidence == 0.75
        faith_mock.check_sufficiency.assert_called_once()
        faith_mock.check_faithfulness.assert_called_once()

    async def test_insufficient_context_skips_generation(self) -> None:
        """INSUFFICIENT mit threshold PARTIAL -> kein LLM-Aufruf, confidence 0.0."""
        main_llm = MockLLMProvider(generate_text="Should not be called.")

        faith_mock = AsyncMock(spec=FaithfulnessPort)
        faith_mock.check_sufficiency = AsyncMock(return_value="INSUFFICIENT")

        uc = AnalyzePanelWithContext(
            main_llm, faithfulness=faith_mock, sufficiency_threshold="PARTIAL"
        )

        result = await uc.execute(
            technology="Quantum Computing",
            use_case_key="landscape",
            panel_data_json='{"total": 100}',
            context_documents=[],
        )

        assert result.analysis_text == ""
        assert result.confidence == 0.0
        assert result.key_findings == []
        # Main LLM should NOT have been called
        assert len(main_llm.generate_calls) == 0
        # Faithfulness check should NOT have been called (skipped generation)
        faith_mock.check_faithfulness.assert_not_called()

    async def test_partial_context_accepted_with_partial_threshold(self) -> None:
        """PARTIAL mit threshold PARTIAL -> Generierung wird ausgefuehrt."""
        main_llm = MockLLMProvider(generate_text="Partial analysis result.")

        faith_mock = AsyncMock(spec=FaithfulnessPort)
        faith_mock.check_sufficiency = AsyncMock(return_value="PARTIAL")
        faith_mock.check_faithfulness = AsyncMock(return_value=(0.9, []))

        uc = AnalyzePanelWithContext(
            main_llm, faithfulness=faith_mock, sufficiency_threshold="PARTIAL"
        )

        result = await uc.execute(
            technology="QC",
            use_case_key="landscape",
            panel_data_json="{}",
            context_documents=[],
        )

        assert result.analysis_text == "Partial analysis result."
        assert result.confidence == 0.9
        assert len(main_llm.generate_calls) == 1

    async def test_partial_rejected_with_sufficient_threshold(self) -> None:
        """PARTIAL mit threshold SUFFICIENT -> Generierung wird uebersprungen."""
        main_llm = MockLLMProvider(generate_text="Should not be called.")

        faith_mock = AsyncMock(spec=FaithfulnessPort)
        faith_mock.check_sufficiency = AsyncMock(return_value="PARTIAL")

        uc = AnalyzePanelWithContext(
            main_llm, faithfulness=faith_mock, sufficiency_threshold="SUFFICIENT"
        )

        result = await uc.execute(
            technology="QC",
            use_case_key="landscape",
            panel_data_json="{}",
            context_documents=[],
        )

        assert result.analysis_text == ""
        assert result.confidence == 0.0
        assert len(main_llm.generate_calls) == 0

    async def test_sufficient_accepted_with_sufficient_threshold(self) -> None:
        """SUFFICIENT mit threshold SUFFICIENT -> Generierung wird ausgefuehrt."""
        main_llm = MockLLMProvider(generate_text="High-quality analysis.")

        faith_mock = AsyncMock(spec=FaithfulnessPort)
        faith_mock.check_sufficiency = AsyncMock(return_value="SUFFICIENT")
        faith_mock.check_faithfulness = AsyncMock(return_value=(1.0, []))

        uc = AnalyzePanelWithContext(
            main_llm, faithfulness=faith_mock, sufficiency_threshold="SUFFICIENT"
        )

        result = await uc.execute(
            technology="QC",
            use_case_key="landscape",
            panel_data_json="{}",
            context_documents=[],
        )

        assert result.analysis_text == "High-quality analysis."
        assert result.confidence == 1.0

    async def test_faithfulness_error_uses_fallback_confidence(self) -> None:
        """Faithfulness-Fehler -> confidence 0.0 als fallback."""
        main_llm = MockLLMProvider(generate_text="Some analysis.")

        faith_mock = AsyncMock(spec=FaithfulnessPort)
        faith_mock.check_sufficiency = AsyncMock(return_value="SUFFICIENT")
        faith_mock.check_faithfulness = AsyncMock(return_value=(0.0, []))

        uc = AnalyzePanelWithContext(main_llm, faithfulness=faith_mock)

        result = await uc.execute(
            technology="QC",
            use_case_key="landscape",
            panel_data_json="{}",
            context_documents=[],
        )

        # Faithfulness returned 0.0 score -> confidence is 0.0
        assert result.analysis_text == "Some analysis."
        assert result.confidence == 0.0

    async def test_empty_llm_response_with_faithfulness(self) -> None:
        """Leere LLM-Antwort -> confidence 0.0, kein faithfulness check."""
        main_llm = MockLLMProvider(generate_text="")

        faith_mock = AsyncMock(spec=FaithfulnessPort)
        faith_mock.check_sufficiency = AsyncMock(return_value="SUFFICIENT")

        uc = AnalyzePanelWithContext(main_llm, faithfulness=faith_mock)

        result = await uc.execute(
            technology="QC",
            use_case_key="landscape",
            panel_data_json="{}",
            context_documents=[],
        )

        assert result.analysis_text == ""
        assert result.confidence == 0.0
        # Faithfulness check should NOT be called for empty response
        faith_mock.check_faithfulness.assert_not_called()

    async def test_llm_error_with_faithfulness_graceful(self) -> None:
        """LLM-Hauptfehler bei aktiviertem Faithfulness -> graceful degradation."""
        faith_mock = AsyncMock(spec=FaithfulnessPort)
        faith_mock.check_sufficiency = AsyncMock(return_value="SUFFICIENT")

        uc = AnalyzePanelWithContext(
            FailingLLMProvider(), faithfulness=faith_mock
        )

        result = await uc.execute(
            technology="QC",
            use_case_key="landscape",
            panel_data_json="{}",
            context_documents=[],
        )

        assert result.analysis_text == ""
        assert result.confidence == 0.0
