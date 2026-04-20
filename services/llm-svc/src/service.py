"""LLM Analysis Servicer — duenner gRPC-Adapter.

Empfaengt gRPC-Requests, delegiert Business-Logik an die Use-Case-Klassen
in use_case.py und baut gRPC-Responses.

Die eigentliche Analyse-Logik (Prompt-Rendering, LLM-Aufrufe,
Key-Findings-Extraktion) liegt in use_case.py.
"""

from __future__ import annotations

import time
from typing import Any

import structlog

# --- gRPC-Imports (try/except, da Stubs noch nicht generiert) ---
try:
    import grpc
    from grpc import aio as grpc_aio
except ImportError:
    grpc = None  # type: ignore[assignment]
    grpc_aio = None  # type: ignore[assignment]

try:
    from shared.generated.python import llm_pb2
    from shared.generated.python import llm_pb2_grpc
except ImportError:
    llm_pb2 = None  # type: ignore[assignment]
    llm_pb2_grpc = None  # type: ignore[assignment]

from src.config import Settings
from src.domain.ports import FaithfulnessPort, LLMProviderPort
from src.infrastructure.faithfulness import LLMFaithfulnessChecker
from src.use_case import AnalyzePanel, AnalyzePanelWithContext, ChatWithContext

logger = structlog.get_logger(__name__)


def _resolve_provider_type(provider_name: str) -> str:
    """Provider-Typ ableiten: 'local' fuer Ollama, sonst 'cloud'.

    Relevant fuer EU AI Act Transparenz (Art. 50(2)).
    """
    return "local" if provider_name.lower() == "ollama" else "cloud"


# ---------------------------------------------------------------------------
# LLM Provider Implementierungen (Infrastruktur-Adapter)
# ---------------------------------------------------------------------------


class _AnthropicProvider(LLMProviderPort):
    """Anthropic Claude LLM-Provider."""

    def __init__(self, client: Any, settings: Settings) -> None:
        self._client = client
        self._settings = settings

    async def generate(
        self, system_prompt: str, user_prompt: str
    ) -> tuple[str, str]:
        """Anthropic Claude API fuer Single-Turn-Generierung aufrufen."""
        response = await self._client.messages.create(
            model=self._settings.model_name,
            max_tokens=self._settings.max_tokens,
            temperature=self._settings.temperature,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )
        text = response.content[0].text if response.content else ""
        model_used = response.model or self._settings.model_name
        return text, model_used

    async def chat(
        self, system_prompt: str, messages: list[dict[str, str]]
    ) -> tuple[str, str]:
        """Anthropic Claude API fuer Chat-Completion aufrufen."""
        response = await self._client.messages.create(
            model=self._settings.model_name,
            max_tokens=self._settings.max_tokens,
            temperature=self._settings.temperature,
            system=system_prompt,
            messages=messages,
        )
        text = response.content[0].text if response.content else ""
        model_used = response.model or self._settings.model_name
        return text, model_used


class _OpenAIProvider(LLMProviderPort):
    """OpenAI GPT LLM-Provider."""

    def __init__(self, client: Any, settings: Settings) -> None:
        self._client = client
        self._settings = settings

    async def generate(
        self, system_prompt: str, user_prompt: str
    ) -> tuple[str, str]:
        """OpenAI API fuer Single-Turn-Generierung aufrufen."""
        response = await self._client.chat.completions.create(
            model=self._settings.model_name,
            max_tokens=self._settings.max_tokens,
            temperature=self._settings.temperature,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        text = ""
        if response.choices and response.choices[0].message.content:
            text = response.choices[0].message.content
        model_used = response.model or self._settings.model_name
        return text, model_used

    async def chat(
        self, system_prompt: str, messages: list[dict[str, str]]
    ) -> tuple[str, str]:
        """OpenAI API fuer Chat-Completion aufrufen."""
        full_messages = [{"role": "system", "content": system_prompt}] + messages
        response = await self._client.chat.completions.create(
            model=self._settings.model_name,
            max_tokens=self._settings.max_tokens,
            temperature=self._settings.temperature,
            messages=full_messages,
        )
        text = ""
        if response.choices and response.choices[0].message.content:
            text = response.choices[0].message.content
        model_used = response.model or self._settings.model_name
        return text, model_used


class _GeminiProvider(LLMProviderPort):
    """Google Gemini LLM-Provider (google-generativeai SDK).

    System-Instructions werden pro Aufruf als neues GenerativeModel gesetzt,
    da Gemini system_instruction auf Model-Ebene definiert.
    """

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def _make_model(self, system_prompt: str) -> Any:
        """Erstellt ein GenerativeModel mit system_instruction."""
        import google.generativeai as genai

        return genai.GenerativeModel(
            self._settings.model_name,
            system_instruction=system_prompt if system_prompt else None,
        )

    def _gen_config(self) -> Any:
        """Erstellt die GenerationConfig."""
        from google.generativeai.types import GenerationConfig

        return GenerationConfig(
            temperature=self._settings.temperature,
            max_output_tokens=self._settings.max_tokens,
        )

    async def generate(
        self, system_prompt: str, user_prompt: str
    ) -> tuple[str, str]:
        """Gemini API fuer Single-Turn-Generierung aufrufen."""
        model = self._make_model(system_prompt)
        response = await model.generate_content_async(
            user_prompt,
            generation_config=self._gen_config(),
        )
        text = response.text if response.text else ""
        return text, self._settings.model_name

    async def chat(
        self, system_prompt: str, messages: list[dict[str, str]]
    ) -> tuple[str, str]:
        """Gemini API fuer Chat-Completion aufrufen."""
        model = self._make_model(system_prompt)

        # Gemini: "assistant" -> "model" fuer Rollen-Mapping
        history = [
            {
                "role": "model" if msg["role"] == "assistant" else msg["role"],
                "parts": [msg["content"]],
            }
            for msg in messages[:-1]
        ]
        chat = model.start_chat(history=history)

        last_message = messages[-1]["content"] if messages else ""
        response = await chat.send_message_async(
            last_message,
            generation_config=self._gen_config(),
        )
        text = response.text if response.text else ""
        return text, self._settings.model_name


class _OllamaProvider(LLMProviderPort):
    """Lokaler LLM-Provider via Ollama (OpenAI-kompatible API)."""

    def __init__(self, client: Any, settings: Settings) -> None:
        self._client = client
        self._settings = settings

    async def generate(
        self, system_prompt: str, user_prompt: str
    ) -> tuple[str, str]:
        """Ollama API fuer Single-Turn-Generierung aufrufen."""
        response = await self._client.chat.completions.create(
            model=self._settings.model_name,
            max_tokens=self._settings.max_tokens,
            temperature=self._settings.temperature,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        text = ""
        if response.choices and response.choices[0].message.content:
            text = response.choices[0].message.content
        model_used = response.model or self._settings.model_name
        return text, model_used

    async def chat(
        self, system_prompt: str, messages: list[dict[str, str]]
    ) -> tuple[str, str]:
        """Ollama API fuer Chat-Completion aufrufen."""
        full_messages = [{"role": "system", "content": system_prompt}] + messages
        response = await self._client.chat.completions.create(
            model=self._settings.model_name,
            max_tokens=self._settings.max_tokens,
            temperature=self._settings.temperature,
            messages=full_messages,
        )
        text = ""
        if response.choices and response.choices[0].message.content:
            text = response.choices[0].message.content
        model_used = response.model or self._settings.model_name
        return text, model_used


class _NullProvider(LLMProviderPort):
    """Null-Provider wenn kein LLM konfiguriert ist (Graceful Degradation)."""

    async def generate(
        self, system_prompt: str, user_prompt: str
    ) -> tuple[str, str]:
        """Gibt leere Ergebnisse zurueck."""
        return "", ""

    async def chat(
        self, system_prompt: str, messages: list[dict[str, str]]
    ) -> tuple[str, str]:
        """Gibt leere Ergebnisse zurueck."""
        return "", ""


# ---------------------------------------------------------------------------
# Helper: Basis-Klasse ermitteln (gRPC Servicer oder object)
# ---------------------------------------------------------------------------


def _get_base_class() -> type:
    """Gibt die gRPC-Servicer-Basisklasse zurueck, oder object als Fallback."""
    if llm_pb2_grpc is not None:
        return llm_pb2_grpc.LlmAnalysisServiceServicer  # type: ignore[return-value]
    return object


class LlmAnalysisServicer(_get_base_class()):  # type: ignore[misc]
    """Duenner gRPC-Adapter fuer LLM-Analyse.

    Delegiert Business-Logik an Use-Case-Klassen:
    - AnalyzePanel -> use_case.AnalyzePanel
    - AnalyzePanelWithContext -> use_case.AnalyzePanelWithContext
    - Chat -> use_case.ChatWithContext

    Unterstuetzt drei LLM-Provider:
    - Google Gemini (Standard)
    - Anthropic Claude
    - OpenAI GPT

    Graceful Degradation: Bei Fehler wird leere Analyse zurueckgegeben.
    """

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or Settings()
        self._anthropic_client: Any = None
        self._openai_client: Any = None
        self._gemini_configured: bool = False
        self._ollama_client: Any = None
        self._init_client()

        # --- Multi-Provider-Pool erstellen ---
        self._providers: dict[str, LLMProviderPort] = {}
        self._default_provider_key: str = self._settings.llm_provider.lower()

        if self._gemini_configured:
            self._providers["gemini"] = _GeminiProvider(self._settings)
        if self._anthropic_client is not None:
            self._providers["anthropic"] = _AnthropicProvider(
                self._anthropic_client, self._settings
            )
        if self._openai_client is not None:
            self._providers["openai"] = _OpenAIProvider(
                self._openai_client, self._settings
            )
        if self._ollama_client is not None:
            self._providers["ollama"] = _OllamaProvider(
                self._ollama_client, self._settings
            )

        # Default-Provider (bestehende Rueckwaertskompatibilitaet)
        self._provider: LLMProviderPort = self._providers.get(
            self._default_provider_key, _NullProvider()
        )

        # EU AI Act Transparenz
        self._provider_type: str = _resolve_provider_type(
            self._default_provider_key
        )

        logger.info(
            "provider_pool_initialisiert",
            verfuegbar=list(self._providers.keys()),
            default=self._default_provider_key,
            provider_type=self._provider_type,
        )

        # --- Faithfulness-Guard (optional) ---
        faithfulness: FaithfulnessPort | None = None
        if self._settings.faithfulness_enabled:
            faithfulness = LLMFaithfulnessChecker(self._provider)
            logger.info(
                "faithfulness_guard_aktiviert",
                threshold=self._settings.sufficiency_threshold,
            )

        # --- Use Cases initialisieren ---
        self._analyze_panel = AnalyzePanel(
            self._provider, self._settings.default_language
        )
        self._analyze_panel_with_context = AnalyzePanelWithContext(
            self._provider,
            faithfulness=faithfulness,
            sufficiency_threshold=self._settings.sufficiency_threshold,
        )
        self._chat_with_context = ChatWithContext(
            self._provider, self._settings.default_language
        )

    def _init_client(self) -> None:
        """Alle LLM-Clients initialisieren, fuer die API-Keys vorliegen.

        Versucht jeden Provider unabhaengig zu initialisieren, damit zur
        Laufzeit zwischen allen verfuegbaren Providern gewechselt werden kann.
        """
        # --- Anthropic ---
        if self._settings.anthropic_api_key:
            try:
                import anthropic

                self._anthropic_client = anthropic.AsyncAnthropic(
                    api_key=self._settings.anthropic_api_key,
                    timeout=self._settings.llm_timeout_s,
                )
                logger.info(
                    "llm_client_initialisiert",
                    provider="anthropic",
                )
            except ImportError:
                logger.warning(
                    "anthropic_sdk_nicht_installiert",
                    hinweis="pip install anthropic",
                )

        # --- OpenAI ---
        if self._settings.openai_api_key:
            try:
                import openai

                self._openai_client = openai.AsyncOpenAI(
                    api_key=self._settings.openai_api_key,
                    timeout=self._settings.llm_timeout_s,
                )
                logger.info(
                    "llm_client_initialisiert",
                    provider="openai",
                )
            except ImportError:
                logger.warning(
                    "openai_sdk_nicht_installiert",
                    hinweis="pip install openai",
                )

        # --- Gemini ---
        if self._settings.gemini_api_key:
            try:
                import google.generativeai as genai

                genai.configure(api_key=self._settings.gemini_api_key)
                self._gemini_configured = True
                logger.info(
                    "llm_client_initialisiert",
                    provider="gemini",
                )
            except ImportError:
                logger.warning(
                    "google_generativeai_sdk_nicht_installiert",
                    hinweis="pip install google-generativeai",
                )

        # --- Ollama (lokal) ---
        if self._settings.ollama_base_url and self._settings.llm_provider.lower() == "ollama":
            try:
                import openai

                self._ollama_client = openai.AsyncOpenAI(
                    base_url=self._settings.ollama_base_url,
                    api_key="ollama",
                    timeout=self._settings.ollama_timeout_s,
                )
                logger.info(
                    "llm_client_initialisiert",
                    provider="ollama",
                    base_url=self._settings.ollama_base_url,
                )
            except ImportError:
                logger.warning(
                    "openai_sdk_nicht_installiert",
                    hinweis="pip install openai (fuer Ollama-Kompatibilitaet)",
                )

        if not (self._anthropic_client or self._openai_client or self._gemini_configured or self._ollama_client):
            logger.warning(
                "kein_llm_provider_konfiguriert",
                hinweis="API-Keys setzen oder LLM_PROVIDER=ollama",
            )

    def _get_provider(self, provider_override: str = "") -> LLMProviderPort:
        """Waehlt Provider: override -> default -> NullProvider.

        Args:
            provider_override: Optionaler Provider-Name (z.B. 'anthropic').
                               Leer = Default-Provider verwenden.

        Returns:
            LLMProviderPort-Instanz.
        """
        if provider_override:
            provider = self._providers.get(provider_override.lower())
            if provider is not None:
                return provider
            logger.warning(
                "provider_override_unbekannt",
                angefragt=provider_override,
                verfuegbar=list(self._providers.keys()),
            )
        return self._provider

    # -------------------------------------------------------------------
    # gRPC-Methoden (duenne Adapter)
    # -------------------------------------------------------------------

    async def AnalyzePanel(
        self,
        request: Any,
        context: Any,
    ) -> Any:
        """Panel-Daten analysieren und textuelle Interpretation zurueckgeben.

        Args:
            request: tip.llm.AnalyzePanelRequest Protobuf-Message
            context: gRPC ServicerContext (fuer Fehlerbehandlung)

        Returns:
            tip.llm.AnalyzePanelResponse Protobuf-Message
        """
        technology = request.technology
        use_case_key = request.use_case_key
        language = request.language or self._settings.default_language
        request_id = request.request_id or ""

        logger.info(
            "llm_analyse_gestartet",
            technology=technology,
            use_case_key=use_case_key,
            language=language,
            request_id=request_id,
        )

        # --- gRPC-Validierung (Abort bei ungueltigem Request) ---
        if not technology or not technology.strip():
            if context is not None and grpc is not None:
                await context.abort(
                    grpc.StatusCode.INVALID_ARGUMENT,
                    "Feld 'technology' darf nicht leer sein",
                )
            return self._build_response(
                analysis_text="",
                model_used="",
                processing_time_ms=0,
                key_findings=[],
                confidence=0.0,
            )

        if use_case_key not in _get_uc_prompts_keys():
            if context is not None and grpc is not None:
                await context.abort(
                    grpc.StatusCode.INVALID_ARGUMENT,
                    f"Unbekannter use_case_key: '{use_case_key}'. "
                    f"Verfügbar: {', '.join(_get_uc_prompts_keys())}",
                )

        # --- Provider-Override ermitteln ---
        provider_override = getattr(request, "provider_override", "") or ""
        provider = self._get_provider(provider_override)

        # --- An Use Case delegieren ---
        result = await self._analyze_panel.execute(
            technology=technology,
            use_case_key=use_case_key,
            panel_data_json=request.panel_data_json,
            language=language,
            llm_override=provider if provider_override else None,
        )

        logger.info(
            "llm_analyse_abgeschlossen",
            technology=technology,
            use_case_key=use_case_key,
            model_used=result.model_used,
            dauer_ms=result.processing_time_ms,
            text_laenge=len(result.analysis_text),
            findings_anzahl=len(result.key_findings),
        )

        return self._build_response(
            analysis_text=result.analysis_text,
            model_used=result.model_used,
            processing_time_ms=result.processing_time_ms,
            key_findings=result.key_findings,
            confidence=result.confidence,
        )

    async def AnalyzePanelWithContext(
        self,
        request: Any,
        context: Any,
    ) -> Any:
        """Panel-Analyse mit RAG-Kontext-Dokumenten.

        Args:
            request: tip.llm.AnalyzePanelWithContextRequest Protobuf-Message
            context: gRPC ServicerContext

        Returns:
            tip.llm.AnalyzePanelResponse Protobuf-Message
        """
        technology = request.technology
        use_case_key = request.use_case_key
        request_id = getattr(request, "request_id", "")

        logger.info(
            "rag_analyse_gestartet",
            technology=technology,
            use_case_key=use_case_key,
            context_docs=len(list(request.context_documents)),
            request_id=request_id,
        )

        # --- Provider-Override ermitteln ---
        provider_override = getattr(request, "provider_override", "") or ""
        provider = self._get_provider(provider_override)

        # --- An Use Case delegieren ---
        result = await self._analyze_panel_with_context.execute(
            technology=technology,
            use_case_key=use_case_key,
            panel_data_json=request.panel_data_json,
            context_documents=list(request.context_documents),
            llm_override=provider if provider_override else None,
        )

        logger.info(
            "rag_analyse_abgeschlossen",
            technology=technology,
            use_case_key=use_case_key,
            model_used=result.model_used,
            dauer_ms=result.processing_time_ms,
        )

        return self._build_response(
            analysis_text=result.analysis_text,
            model_used=result.model_used,
            processing_time_ms=result.processing_time_ms,
            key_findings=result.key_findings,
            confidence=result.confidence,
        )

    async def Chat(
        self,
        request: Any,
        context: Any,
    ) -> Any:
        """Interaktiver Chat mit RAG-Kontext.

        Args:
            request: tip.llm.ChatRequest Protobuf-Message
            context: gRPC ServicerContext

        Returns:
            tip.llm.ChatResponse Protobuf-Message
        """
        technology = request.technology
        user_message = request.user_message
        language = request.language or self._settings.default_language
        request_id = getattr(request, "request_id", "")

        logger.info(
            "chat_gestartet",
            technology=technology,
            message_laenge=len(user_message),
            history_laenge=len(list(request.history)),
            context_docs=len(list(request.context_documents)),
            request_id=request_id,
        )

        # --- Provider-Override ermitteln ---
        provider_override = getattr(request, "provider_override", "") or ""
        provider = self._get_provider(provider_override)

        # --- An Use Case delegieren ---
        panel_ctx = getattr(request, "panel_context_json", "") or ""
        result = await self._chat_with_context.execute(
            technology=technology,
            user_message=user_message,
            context_documents=list(request.context_documents),
            history=list(request.history),
            language=language,
            panel_context_json=panel_ctx,
            llm_override=provider if provider_override else None,
        )

        logger.info(
            "chat_abgeschlossen",
            technology=technology,
            model_used=result.model_used,
            dauer_ms=result.processing_time_ms,
            antwort_laenge=len(result.answer),
        )

        return self._build_chat_response(
            answer=result.answer,
            sources=result.sources,
            key_findings=result.key_findings,
            model_used=result.model_used,
            processing_time_ms=result.processing_time_ms,
        )

    # -------------------------------------------------------------------
    # gRPC Response Builder (Infrastruktur-Concerns)
    # -------------------------------------------------------------------

    def _build_response(
        self,
        *,
        analysis_text: str,
        model_used: str,
        processing_time_ms: int,
        key_findings: list[str],
        confidence: float,
    ) -> Any:
        """AnalyzePanelResponse bauen.

        Wenn gRPC-Stubs nicht verfuegbar sind, wird ein dict zurueckgegeben.
        """
        if llm_pb2 is not None:
            return llm_pb2.AnalyzePanelResponse(
                analysis_text=analysis_text,
                model_used=model_used,
                processing_time_ms=processing_time_ms,
                key_findings=key_findings,
                confidence=confidence,
            )

        # Fallback: dict (fuer Tests und Entwicklung ohne Stubs)
        return {
            "analysis_text": analysis_text,
            "model_used": model_used,
            "processing_time_ms": processing_time_ms,
            "key_findings": key_findings,
            "confidence": confidence,
        }

    def _build_empty_response(self, t0: float) -> Any:
        """Leere Response bei ungueltigem Request."""
        processing_time_ms = int((time.monotonic() - t0) * 1000)
        return self._build_response(
            analysis_text="",
            model_used="",
            processing_time_ms=processing_time_ms,
            key_findings=[],
            confidence=0.0,
        )

    def _build_chat_response(
        self,
        *,
        answer: str,
        sources: list[str],
        key_findings: list[str],
        model_used: str,
        processing_time_ms: int,
    ) -> Any:
        """ChatResponse bauen.

        Wenn gRPC-Stubs nicht verfuegbar sind, wird ein dict zurueckgegeben.
        """
        if llm_pb2 is not None:
            return llm_pb2.ChatResponse(
                answer=answer,
                sources=sources,
                key_findings=key_findings,
                model_used=model_used,
                processing_time_ms=processing_time_ms,
            )

        # Fallback: dict (fuer Tests und Entwicklung ohne Stubs)
        return {
            "answer": answer,
            "sources": sources,
            "key_findings": key_findings,
            "model_used": model_used,
            "processing_time_ms": processing_time_ms,
        }


def _get_uc_prompts_keys() -> list[str]:
    """UC_PROMPTS Keys abrufen (lazy import um zirkulaere Imports zu vermeiden)."""
    from src.prompts import UC_PROMPTS

    return list(UC_PROMPTS.keys())
