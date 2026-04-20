"""Tests fuer die extrahierten Use Cases in use_case.py.

Prueft:
- AnalyzePanel: Delegiert an LLMProviderPort, validiert Eingaben
- AnalyzePanelWithContext: Baut Kontext in Prompt ein
- ChatWithContext: Baut Messages korrekt, verarbeitet Quellen
- truncate_data: Kuerzt lange Daten, behaelt kurze Daten bei
- extract_key_findings: Extrahiert max 5 Saetze > 15 Zeichen
"""

from __future__ import annotations

import json

import pytest
from unittest.mock import AsyncMock, MagicMock

from src.domain.ports import AnalysisResult, ChatResult, LLMProviderPort
from src.use_case import (
    AnalyzePanel,
    AnalyzePanelWithContext,
    ChatWithContext,
    extract_key_findings,
    truncate_data,
)


# ---------------------------------------------------------------------------
# Mock LLM Provider
# ---------------------------------------------------------------------------


class MockLLMProvider(LLMProviderPort):
    """Test-Double fuer LLMProviderPort."""

    def __init__(
        self,
        generate_text: str = "Analyse-Ergebnis.",
        generate_model: str = "test-model",
        chat_text: str = "Chat-Antwort.",
        chat_model: str = "test-model",
    ) -> None:
        self.generate_text = generate_text
        self.generate_model = generate_model
        self.chat_text = chat_text
        self.chat_model = chat_model
        self.generate_calls: list[tuple[str, str]] = []
        self.chat_calls: list[tuple[str, list[dict[str, str]]]] = []

    async def generate(
        self, system_prompt: str, user_prompt: str
    ) -> tuple[str, str]:
        self.generate_calls.append((system_prompt, user_prompt))
        return self.generate_text, self.generate_model

    async def chat(
        self, system_prompt: str, messages: list[dict[str, str]]
    ) -> tuple[str, str]:
        self.chat_calls.append((system_prompt, messages))
        return self.chat_text, self.chat_model


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
# Tests: AnalyzePanel
# ---------------------------------------------------------------------------


class TestAnalyzePanel:
    """Panel-Analyse Use Case Tests."""

    async def test_delegates_to_llm(self) -> None:
        """generate() wird mit korrektem Prompt aufgerufen."""
        mock = MockLLMProvider(generate_text="Die Analyse zeigt steigende Patentzahlen.")
        uc = AnalyzePanel(mock, default_language="de")

        result = await uc.execute(
            technology="Quantum Computing",
            use_case_key="landscape",
            panel_data_json='{"total": 100}',
        )

        assert isinstance(result, AnalysisResult)
        assert result.analysis_text == "Die Analyse zeigt steigende Patentzahlen."
        assert result.model_used == "test-model"
        assert result.confidence == 0.85
        assert len(result.key_findings) >= 1
        assert result.processing_time_ms >= 0

        # generate() wurde genau einmal aufgerufen
        assert len(mock.generate_calls) == 1
        system_prompt, user_prompt = mock.generate_calls[0]
        assert "Quantum Computing" in user_prompt
        assert "100" in user_prompt

    async def test_invalid_technology_returns_empty(self) -> None:
        """Leere Technologie gibt sofort leeres Ergebnis zurueck."""
        mock = MockLLMProvider()
        uc = AnalyzePanel(mock)

        result = await uc.execute(
            technology="",
            use_case_key="landscape",
            panel_data_json="{}",
        )

        assert result.analysis_text == ""
        assert result.confidence == 0.0
        assert result.key_findings == []
        # generate() wurde NICHT aufgerufen
        assert len(mock.generate_calls) == 0

    async def test_whitespace_technology_returns_empty(self) -> None:
        """Nur-Whitespace-Technologie gibt sofort leeres Ergebnis zurueck."""
        mock = MockLLMProvider()
        uc = AnalyzePanel(mock)

        result = await uc.execute(
            technology="   ",
            use_case_key="landscape",
            panel_data_json="{}",
        )

        assert result.analysis_text == ""
        assert len(mock.generate_calls) == 0

    async def test_unknown_uc_key_returns_empty(self) -> None:
        """Unbekannter UC-Key gibt leeres Ergebnis zurueck ohne LLM-Aufruf."""
        mock = MockLLMProvider()
        uc = AnalyzePanel(mock)

        result = await uc.execute(
            technology="Quantum Computing",
            use_case_key="nonexistent_uc",
            panel_data_json="{}",
        )

        assert result.analysis_text == ""
        assert result.confidence == 0.0
        assert len(mock.generate_calls) == 0

    async def test_llm_error_returns_empty(self) -> None:
        """LLM-Fehler fuehrt zu leerer Analyse (Graceful Degradation)."""
        uc = AnalyzePanel(FailingLLMProvider())

        result = await uc.execute(
            technology="QC",
            use_case_key="landscape",
            panel_data_json="{}",
        )

        assert result.analysis_text == ""
        assert result.confidence == 0.0
        assert result.key_findings == []

    async def test_uses_custom_language(self) -> None:
        """Language-Parameter wird korrekt gesetzt."""
        mock = MockLLMProvider()
        uc = AnalyzePanel(mock, default_language="de")

        await uc.execute(
            technology="QC",
            use_case_key="landscape",
            panel_data_json="{}",
            language="en",
        )

        assert len(mock.generate_calls) == 1

    async def test_empty_llm_response_gives_zero_confidence(self) -> None:
        """Leere LLM-Antwort ergibt confidence 0.0."""
        mock = MockLLMProvider(generate_text="", generate_model="test-model")
        uc = AnalyzePanel(mock)

        result = await uc.execute(
            technology="QC",
            use_case_key="landscape",
            panel_data_json="{}",
        )

        assert result.analysis_text == ""
        assert result.confidence == 0.0
        assert result.key_findings == []


# ---------------------------------------------------------------------------
# Tests: AnalyzePanelWithContext
# ---------------------------------------------------------------------------


class TestAnalyzePanelWithContext:
    """RAG-gestuetzte Panel-Analyse Use Case Tests."""

    async def test_context_in_prompt(self) -> None:
        """Kontext-Dokumente werden in den Prompt eingebaut."""
        mock = MockLLMProvider(generate_text="Analyse mit Kontext.")
        uc = AnalyzePanelWithContext(mock)

        docs = [
            MagicMock(source="patent", title="QC Method", text_snippet="Method for quantum..."),
            MagicMock(source="project", title="QuTech", text_snippet="Research on quantum..."),
        ]

        result = await uc.execute(
            technology="Quantum Computing",
            use_case_key="landscape",
            panel_data_json='{"total": 42}',
            context_documents=docs,
        )

        assert isinstance(result, AnalysisResult)
        assert result.analysis_text == "Analyse mit Kontext."
        assert result.confidence == 0.85

        # Prompt muss Kontext enthalten
        assert len(mock.generate_calls) == 1
        _, user_prompt = mock.generate_calls[0]
        assert "QC Method" in user_prompt
        assert "Method for quantum..." in user_prompt
        assert "QuTech" in user_prompt
        assert "42" in user_prompt

    async def test_empty_context(self) -> None:
        """Leere Dokumentliste fuehrt nicht zu Fehler."""
        mock = MockLLMProvider(generate_text="Analyse ohne Kontext.")
        uc = AnalyzePanelWithContext(mock)

        result = await uc.execute(
            technology="QC",
            use_case_key="landscape",
            panel_data_json="{}",
            context_documents=[],
        )

        assert result.analysis_text == "Analyse ohne Kontext."
        assert len(mock.generate_calls) == 1

    async def test_error_graceful_degradation(self) -> None:
        """Fehler beim LLM-Aufruf gibt leere Analyse zurueck."""
        uc = AnalyzePanelWithContext(FailingLLMProvider())

        result = await uc.execute(
            technology="QC",
            use_case_key="landscape",
            panel_data_json="{}",
            context_documents=[],
        )

        assert result.analysis_text == ""
        assert result.confidence == 0.0


# ---------------------------------------------------------------------------
# Tests: ChatWithContext
# ---------------------------------------------------------------------------


class TestChatWithContext:
    """Interaktiver Chat Use Case Tests."""

    async def test_messages_built_correctly(self) -> None:
        """Chat-Nachrichten werden korrekt aus Historie und User-Message gebaut."""
        mock = MockLLMProvider(chat_text="Antwort auf Ihre Frage.")
        uc = ChatWithContext(mock, default_language="de")

        prev_msg = MagicMock()
        prev_msg.role = "user"
        prev_msg.content = "Hallo"

        docs = [
            MagicMock(title="Patent A", text_snippet="...", source="patent"),
        ]

        result = await uc.execute(
            technology="Quantum Computing",
            user_message="Welche Patente gibt es?",
            context_documents=docs,
            history=[prev_msg],
            language="de",
        )

        assert isinstance(result, ChatResult)
        assert result.answer == "Antwort auf Ihre Frage."
        assert result.model_used == "test-model"
        assert len(result.sources) == 1
        assert "[1] Patent A" in result.sources[0]
        assert result.processing_time_ms >= 0

        # chat() wurde genau einmal aufgerufen
        assert len(mock.chat_calls) == 1
        system_prompt, messages = mock.chat_calls[0]

        # System-Prompt enthaelt Technologie
        assert "Quantum Computing" in system_prompt

        # History (1) + aktuelle Nachricht (1) = 2
        assert len(messages) == 2
        assert messages[0]["role"] == "user"
        assert messages[0]["content"] == "Hallo"
        assert messages[1]["role"] == "user"
        assert "Welche Patente gibt es?" in messages[1]["content"]

    async def test_chat_error_returns_fallback(self) -> None:
        """Fehler beim LLM-Aufruf gibt Fehlernachricht zurueck."""
        uc = ChatWithContext(FailingLLMProvider())

        result = await uc.execute(
            technology="QC",
            user_message="Test",
            context_documents=[],
            history=[],
        )

        assert "Fehler" in result.answer
        assert result.model_used == "none"

    async def test_no_provider_returns_fallback(self) -> None:
        """Null-Provider (leere Antwort) gibt Konfigurationsnachricht zurueck."""
        mock = MockLLMProvider(chat_text="", chat_model="")
        uc = ChatWithContext(mock)

        result = await uc.execute(
            technology="QC",
            user_message="Test",
            context_documents=[],
            history=[],
        )

        assert "Kein LLM-Provider konfiguriert" in result.answer
        assert result.model_used == "none"

    async def test_sources_built_from_documents(self) -> None:
        """Quellen-Labels werden aus Dokumenten generiert."""
        mock = MockLLMProvider(chat_text="Antwort")
        uc = ChatWithContext(mock)

        docs = [
            MagicMock(title="Doc A"),
            MagicMock(title="Doc B"),
            MagicMock(title="Doc C"),
        ]

        result = await uc.execute(
            technology="QC",
            user_message="Test",
            context_documents=docs,
            history=[],
        )

        assert len(result.sources) == 3
        assert "[1] Doc A" in result.sources[0]
        assert "[2] Doc B" in result.sources[1]
        assert "[3] Doc C" in result.sources[2]

    async def test_key_findings_extracted(self) -> None:
        """Key Findings werden aus der Chat-Antwort extrahiert."""
        mock = MockLLMProvider(
            chat_text="Erste wichtige Erkenntnis hier. Zweite Erkenntnis ist ebenfalls relevant."
        )
        uc = ChatWithContext(mock)

        result = await uc.execute(
            technology="QC",
            user_message="Test",
            context_documents=[],
            history=[],
        )

        assert len(result.key_findings) >= 1


# ---------------------------------------------------------------------------
# Tests: truncate_data
# ---------------------------------------------------------------------------


class TestTruncateData:
    """Modul-Level truncate_data Funktion Tests."""

    def test_short_text_unchanged(self) -> None:
        """Kurzer Text bleibt unveraendert."""
        short = '{"key": "value"}'
        assert truncate_data(short) == short

    def test_long_text_truncated(self) -> None:
        """Langer Text wird gekuerzt mit Hinweis."""
        long_text = "x" * 10000
        result = truncate_data(long_text, max_chars=100)
        assert len(result) <= 100 + len("\n... [gekürzt]")
        assert "gekürzt" in result

    def test_long_json_list_truncated(self) -> None:
        """Grosse JSON-Liste wird auf max_items gekuerzt."""
        # Erstelle eine Liste mit 50 langen Strings, die max_chars ueberschreitet
        data = {"items": [f"item_{i}_" + "x" * 100 for i in range(50)]}
        long_json = json.dumps(data)
        # max_chars muss kleiner sein als long_json, aber gross genug fuer 20 items
        result = truncate_data(long_json, max_chars=4000)
        parsed = json.loads(result)
        # Letztes Element ist der Truncation-Hinweis
        assert "weitere Einträge" in str(parsed["items"][-1])
        # Maximal 20 items + Hinweis
        assert len(parsed["items"]) <= 21

    def test_exact_limit_unchanged(self) -> None:
        """Text genau am Limit bleibt unveraendert."""
        text = "a" * 8000
        assert truncate_data(text) == text

    def test_invalid_json_fallback(self) -> None:
        """Ungültiges JSON wird einfach abgeschnitten."""
        invalid = "not json " * 2000
        result = truncate_data(invalid, max_chars=100)
        assert "gekürzt" in result


# ---------------------------------------------------------------------------
# Tests: extract_key_findings
# ---------------------------------------------------------------------------


class TestExtractKeyFindings:
    """Modul-Level extract_key_findings Funktion Tests."""

    def test_extracts_sentences(self) -> None:
        """Extrahiert Saetze als Key Findings."""
        text = "Erste Erkenntnis ist wichtig. Zweite Erkenntnis auch. Dritte ebenso relevant."
        findings = extract_key_findings(text)
        assert len(findings) == 3

    def test_max_five_findings(self) -> None:
        """Maximal 5 Findings werden extrahiert."""
        text = ". ".join([f"Satz Nummer {i} ist ein wichtiger Befund" for i in range(10)]) + "."
        findings = extract_key_findings(text)
        assert len(findings) == 5

    def test_filters_short_sentences(self) -> None:
        """Saetze <= 15 Zeichen werden herausgefiltert."""
        text = "Kurz. Dies ist ein langer genug Satz fuer Key Findings. Auch kurz."
        findings = extract_key_findings(text)
        # Nur der lange Satz sollte durchkommen
        assert len(findings) == 1
        assert "Dies ist ein langer genug" in findings[0]

    def test_empty_text(self) -> None:
        """Leerer Text ergibt leere Liste."""
        assert extract_key_findings("") == []

    def test_whitespace_text(self) -> None:
        """Nur-Whitespace-Text ergibt leere Liste."""
        assert extract_key_findings("   ") == []

    def test_single_sentence(self) -> None:
        """Einzelner langer Satz wird als Finding extrahiert."""
        text = "Dies ist der einzige Satz in der Analyse und er ist wichtig."
        findings = extract_key_findings(text)
        assert len(findings) == 1
