"""Tests fuer Chat + RAG-Erweiterung des LLM-Service.

Prueft:
- format_context_block: Kontext-Block-Formatierung
- AnalyzePanelWithContext: RAG-gestuetzte Panel-Analyse (via Servicer)
- Chat: Interaktiver Chat mit Retrieval-Kontext und Historie (via Servicer)

Die Tests erstellen den Servicer via __new__ und setzen manuell die
internen Use-Case-Instanzen mit gemockten LLM-Providern auf.

Hinweis: Responses koennen Protobuf-Objekte oder Dicts sein, je nachdem
ob gRPC-Stubs verfuegbar sind. Die Hilfsfunktion _get() abstrahiert den
Zugriff.
"""

from __future__ import annotations

import pytest
from typing import Any
from unittest.mock import AsyncMock, MagicMock

from src.domain.ports import LLMProviderPort
from src.service import _AnthropicProvider, _OpenAIProvider, _NullProvider
from src.use_case import AnalyzePanelWithContext, ChatWithContext


def _get(obj: Any, key: str) -> Any:
    """Attribut-/Subscript-Zugriff auf Response (Protobuf oder Dict)."""
    if isinstance(obj, dict):
        return obj[key]
    return getattr(obj, key)


def _make_servicer_with_anthropic_mock():
    """Servicer mit gemocktem Anthropic-Provider erstellen."""
    from src.service import LlmAnalysisServicer

    s = LlmAnalysisServicer.__new__(LlmAnalysisServicer)
    s._settings = MagicMock()
    s._settings.model_name = "claude-sonnet-4-20250514"
    s._settings.max_tokens = 1024
    s._settings.temperature = 0.3
    s._settings.default_language = "de"

    s._anthropic_client = AsyncMock()
    s._openai_client = None

    s._provider = _AnthropicProvider(s._anthropic_client, s._settings)

    from src.use_case import AnalyzePanel
    s._analyze_panel = AnalyzePanel(s._provider, s._settings.default_language)
    s._analyze_panel_with_context = AnalyzePanelWithContext(s._provider)
    s._chat_with_context = ChatWithContext(s._provider, s._settings.default_language)

    return s


def _make_servicer_with_openai_mock():
    """Servicer mit gemocktem OpenAI-Provider erstellen."""
    from src.service import LlmAnalysisServicer

    s = LlmAnalysisServicer.__new__(LlmAnalysisServicer)
    s._settings = MagicMock()
    s._settings.model_name = "gpt-4o"
    s._settings.max_tokens = 1024
    s._settings.temperature = 0.3
    s._settings.default_language = "de"

    s._anthropic_client = None
    s._openai_client = AsyncMock()

    s._provider = _OpenAIProvider(s._openai_client, s._settings)

    from src.use_case import AnalyzePanel
    s._analyze_panel = AnalyzePanel(s._provider, s._settings.default_language)
    s._analyze_panel_with_context = AnalyzePanelWithContext(s._provider)
    s._chat_with_context = ChatWithContext(s._provider, s._settings.default_language)

    return s


def _make_servicer_no_provider():
    """Servicer ohne LLM-Provider (Null-Provider)."""
    from src.service import LlmAnalysisServicer

    s = LlmAnalysisServicer.__new__(LlmAnalysisServicer)
    s._settings = MagicMock()
    s._settings.model_name = "none"
    s._settings.max_tokens = 1024
    s._settings.temperature = 0.3
    s._settings.default_language = "de"

    s._anthropic_client = None
    s._openai_client = None

    s._provider = _NullProvider()

    from src.use_case import AnalyzePanel
    s._analyze_panel = AnalyzePanel(s._provider, s._settings.default_language)
    s._analyze_panel_with_context = AnalyzePanelWithContext(s._provider)
    s._chat_with_context = ChatWithContext(s._provider, s._settings.default_language)

    return s


# ---------------------------------------------------------------------------
# Tests: format_context_block
# ---------------------------------------------------------------------------


class TestFormatContextBlock:
    """Kontext-Block-Formatierung fuer RAG-Prompts."""

    def test_formats_documents(self) -> None:
        from src.prompts import format_context_block

        docs = [
            MagicMock(source="patent", title="QC Method", text_snippet="A method for..."),
            MagicMock(source="project", title="QuTech", text_snippet="Research on..."),
        ]
        result = format_context_block(docs)
        assert "[1] (patent) QC Method: A method for..." in result
        assert "[2] (project) QuTech: Research on..." in result

    def test_empty_documents(self) -> None:
        from src.prompts import format_context_block

        result = format_context_block([])
        assert result == ""

    def test_single_document(self) -> None:
        from src.prompts import format_context_block

        docs = [MagicMock(source="paper", title="Paper A", text_snippet="Abstract...")]
        result = format_context_block(docs)
        assert "[1] (paper) Paper A: Abstract..." in result
        assert "\n" not in result  # nur eine Zeile

    def test_missing_attributes_fallback(self) -> None:
        from src.prompts import format_context_block

        # Objekt ohne spezifische Attribute -> Fallback auf defaults
        doc = MagicMock(spec=[])
        result = format_context_block([doc])
        assert "[1] (unknown)" in result


# ---------------------------------------------------------------------------
# Tests: AnalyzePanelWithContext
# ---------------------------------------------------------------------------


class TestAnalyzePanelWithContext:
    """RAG-gestuetzte Panel-Analyse mit Kontext-Dokumenten."""

    @pytest.fixture
    def servicer(self) -> MagicMock:
        """Servicer mit gemocktem Anthropic-Client."""
        return _make_servicer_with_anthropic_mock()

    async def test_includes_context_in_prompt(self, servicer: MagicMock) -> None:
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="Analyse basierend auf Kontext")]
        mock_response.model = "claude-sonnet-4-20250514"
        servicer._anthropic_client.messages.create = AsyncMock(return_value=mock_response)

        request = MagicMock()
        request.technology = "Quantum Computing"
        request.use_case_key = "landscape"
        request.panel_data_json = '{"total": 100}'
        request.language = "de"
        request.request_id = "test-1"
        request.context_documents = [
            MagicMock(source="paper", title="QC Paper", text_snippet="Quantum gates research"),
        ]

        ctx = MagicMock()
        result = await servicer.AnalyzePanelWithContext(request, ctx)

        # Prompt muss Kontext-Dokumente enthalten
        call_args = servicer._anthropic_client.messages.create.call_args
        user_msg = call_args.kwargs["messages"][0]["content"]
        assert "Quantum gates research" in user_msg
        assert "QC Paper" in user_msg

    async def test_includes_panel_data_in_prompt(self, servicer: MagicMock) -> None:
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="Analyse")]
        mock_response.model = "claude-sonnet-4-20250514"
        servicer._anthropic_client.messages.create = AsyncMock(return_value=mock_response)

        request = MagicMock()
        request.technology = "Quantum Computing"
        request.use_case_key = "landscape"
        request.panel_data_json = '{"total_patents": 500}'
        request.language = "de"
        request.request_id = "test-1b"
        request.context_documents = []

        ctx = MagicMock()
        await servicer.AnalyzePanelWithContext(request, ctx)

        call_args = servicer._anthropic_client.messages.create.call_args
        user_msg = call_args.kwargs["messages"][0]["content"]
        assert "total_patents" in user_msg

    async def test_returns_key_findings(self, servicer: MagicMock) -> None:
        mock_response = MagicMock()
        mock_response.content = [
            MagicMock(text="Erster wichtiger Befund hier. Zweiter Befund ist ebenfalls relevant.")
        ]
        mock_response.model = "claude-sonnet-4-20250514"
        servicer._anthropic_client.messages.create = AsyncMock(return_value=mock_response)

        request = MagicMock()
        request.technology = "QC"
        request.use_case_key = "landscape"
        request.panel_data_json = "{}"
        request.language = "de"
        request.request_id = "test-1c"
        request.context_documents = []

        ctx = MagicMock()
        result = await servicer.AnalyzePanelWithContext(request, ctx)

        # Response sollte key_findings enthalten
        assert len(_get(result, "key_findings")) >= 1

    async def test_graceful_degradation_on_error(self, servicer: MagicMock) -> None:
        servicer._anthropic_client.messages.create = AsyncMock(
            side_effect=Exception("API down")
        )

        request = MagicMock()
        request.technology = "QC"
        request.use_case_key = "landscape"
        request.panel_data_json = "{}"
        request.language = "de"
        request.request_id = "test-2"
        request.context_documents = []

        ctx = MagicMock()
        result = await servicer.AnalyzePanelWithContext(request, ctx)

        # Sollte nicht werfen — leere Analyse zurueckgeben
        assert _get(result, "analysis_text") == ""
        assert _get(result, "confidence") == 0.0

    async def test_no_provider_returns_empty(self) -> None:
        servicer = _make_servicer_no_provider()

        request = MagicMock()
        request.technology = "QC"
        request.use_case_key = "landscape"
        request.panel_data_json = "{}"
        request.language = "de"
        request.request_id = "test-2b"
        request.context_documents = []

        ctx = MagicMock()
        result = await servicer.AnalyzePanelWithContext(request, ctx)

        assert _get(result, "analysis_text") == ""


# ---------------------------------------------------------------------------
# Tests: Chat
# ---------------------------------------------------------------------------


class TestChat:
    """Interaktiver Chat mit RAG-Kontext und Historie."""

    @pytest.fixture
    def servicer(self) -> MagicMock:
        """Servicer mit gemocktem Anthropic-Client."""
        return _make_servicer_with_anthropic_mock()

    async def test_chat_calls_llm_with_history(self, servicer: MagicMock) -> None:
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="Basierend auf [1] gibt es...")]
        mock_response.model = "claude-sonnet-4-20250514"
        servicer._anthropic_client.messages.create = AsyncMock(return_value=mock_response)

        request = MagicMock()
        request.technology = "Quantum Computing"
        request.user_message = "Welche Patente gibt es?"
        request.language = "de"
        request.request_id = "test-3"
        request.context_documents = [
            MagicMock(title="Patent A", text_snippet="...", source="patent", source_id="1"),
        ]
        prev_msg = MagicMock()
        prev_msg.role = "user"
        prev_msg.content = "Hallo"
        request.history = [prev_msg]
        request.panel_context_json = ""

        ctx = MagicMock()
        result = await servicer.Chat(request, ctx)

        call_args = servicer._anthropic_client.messages.create.call_args
        messages = call_args.kwargs["messages"]
        # History + aktuelle Nachricht = mindestens 2 Messages
        assert len(messages) >= 2

    async def test_chat_includes_system_prompt(self, servicer: MagicMock) -> None:
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="Antwort")]
        mock_response.model = "claude-sonnet-4-20250514"
        servicer._anthropic_client.messages.create = AsyncMock(return_value=mock_response)

        request = MagicMock()
        request.technology = "Quantum Computing"
        request.user_message = "Was ist QC?"
        request.language = "de"
        request.request_id = "test-3b"
        request.context_documents = []
        request.history = []
        request.panel_context_json = ""

        ctx = MagicMock()
        await servicer.Chat(request, ctx)

        call_args = servicer._anthropic_client.messages.create.call_args
        system_prompt = call_args.kwargs["system"]
        assert "Quantum Computing" in system_prompt

    async def test_chat_sources_in_response(self, servicer: MagicMock) -> None:
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="Antwort mit Quellen")]
        mock_response.model = "claude-sonnet-4-20250514"
        servicer._anthropic_client.messages.create = AsyncMock(return_value=mock_response)

        request = MagicMock()
        request.technology = "QC"
        request.user_message = "Test"
        request.language = "de"
        request.request_id = "test-3c"
        request.context_documents = [
            MagicMock(title="Doc A", text_snippet="...", source="patent"),
            MagicMock(title="Doc B", text_snippet="...", source="project"),
        ]
        request.history = []
        request.panel_context_json = ""

        ctx = MagicMock()
        result = await servicer.Chat(request, ctx)

        sources = list(_get(result, "sources"))
        assert len(sources) == 2
        assert "[1] Doc A" in sources[0]
        assert "[2] Doc B" in sources[1]

    async def test_chat_no_provider(self) -> None:
        servicer = _make_servicer_no_provider()

        request = MagicMock()
        request.technology = "QC"
        request.user_message = "Test"
        request.language = "de"
        request.request_id = "test-4"
        request.context_documents = []
        request.history = []
        request.panel_context_json = ""

        ctx = MagicMock()
        result = await servicer.Chat(request, ctx)

        # Sollte Fallback-Nachricht zurueckgeben, nicht crashen
        assert "Kein LLM-Provider konfiguriert" in _get(result, "answer")
        assert _get(result, "model_used") == "none"

    async def test_chat_error_graceful(self, servicer: MagicMock) -> None:
        servicer._anthropic_client.messages.create = AsyncMock(
            side_effect=Exception("Rate limit")
        )

        request = MagicMock()
        request.technology = "QC"
        request.user_message = "Test"
        request.language = "de"
        request.request_id = "test-5"
        request.context_documents = []
        request.history = []
        request.panel_context_json = ""

        ctx = MagicMock()
        result = await servicer.Chat(request, ctx)

        assert "Fehler" in _get(result, "answer")
        assert _get(result, "model_used") == "none"

    async def test_chat_openai_fallback(self) -> None:
        servicer = _make_servicer_with_openai_mock()

        mock_choice = MagicMock()
        mock_choice.message.content = "OpenAI Antwort"
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        mock_response.model = "gpt-4o"
        servicer._openai_client.chat.completions.create = AsyncMock(
            return_value=mock_response
        )

        request = MagicMock()
        request.technology = "QC"
        request.user_message = "Test"
        request.language = "de"
        request.request_id = "test-6"
        request.context_documents = []
        request.history = []
        request.panel_context_json = ""

        ctx = MagicMock()
        result = await servicer.Chat(request, ctx)

        assert _get(result, "answer") == "OpenAI Antwort"
        assert _get(result, "model_used") == "gpt-4o"

        # OpenAI bekommt system-Nachricht als erstes Element
        call_args = servicer._openai_client.chat.completions.create.call_args
        full_messages = call_args.kwargs["messages"]
        assert full_messages[0]["role"] == "system"

    async def test_chat_includes_panel_context(self, servicer: MagicMock) -> None:
        """Panel-Kontext wird in den Prompt eingebaut."""
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="Die S-Kurve zeigt...")]
        mock_response.model = "claude-sonnet-4-20250514"
        servicer._anthropic_client.messages.create = AsyncMock(return_value=mock_response)

        request = MagicMock()
        request.technology = "Quantum Computing"
        request.user_message = "Was bedeutet der R²-Wert?"
        request.language = "de"
        request.request_id = "test-panel-ctx"
        request.context_documents = []
        request.history = []
        request.panel_context_json = '{"active_panel": "maturity", "data": {"phase": "growth", "r_squared": 0.94}}'

        ctx = MagicMock()
        result = await servicer.Chat(request, ctx)

        # Panel-Daten muessen im Prompt an das LLM erscheinen
        call_args = servicer._anthropic_client.messages.create.call_args
        messages = call_args.kwargs["messages"]
        last_user_msg = messages[-1]["content"]
        assert "0.94" in last_user_msg

    async def test_chat_without_panel_context(self, servicer: MagicMock) -> None:
        """Chat funktioniert auch ohne Panel-Kontext (Graceful Degradation)."""
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="Antwort ohne Panel")]
        mock_response.model = "claude-sonnet-4-20250514"
        servicer._anthropic_client.messages.create = AsyncMock(return_value=mock_response)

        request = MagicMock()
        request.technology = "QC"
        request.user_message = "Was ist QC?"
        request.language = "de"
        request.request_id = "test-no-panel"
        request.context_documents = []
        request.history = []
        request.panel_context_json = ""

        ctx = MagicMock()
        result = await servicer.Chat(request, ctx)

        assert _get(result, "answer") == "Antwort ohne Panel"


# ---------------------------------------------------------------------------
# Tests: format_panel_context
# ---------------------------------------------------------------------------


class TestFormatPanelContext:
    """Panel-Kontext-Formatierung fuer Analyse-bewussten Chat."""

    def test_formats_panel_data(self) -> None:
        from src.prompts import format_panel_context
        panel_json = '{"active_panel": "maturity", "data": {"phase": "growth", "r_squared": 0.94}}'
        result = format_panel_context(panel_json)
        assert "Reifegrad" in result or "UC2" in result
        assert "growth" in result
        assert "0.94" in result

    def test_empty_panel_context(self) -> None:
        from src.prompts import format_panel_context
        assert format_panel_context("") == ""
        assert format_panel_context("{}") == ""

    def test_invalid_json_returns_raw(self) -> None:
        from src.prompts import format_panel_context
        result = format_panel_context("not json")
        assert "not json" in result
