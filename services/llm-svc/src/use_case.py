"""LLM Use Cases — Business Logic fuer Panel-Analyse, RAG-Analyse und Chat.

Enthaelt die drei Kern-Use-Cases des LLM-Service:
- AnalyzePanel: Panel-Daten analysieren (ohne RAG-Kontext)
- AnalyzePanelWithContext: RAG-gestuetzte Panel-Analyse mit Kontext-Dokumenten
- ChatWithContext: Interaktiver Chat mit RAG-Kontext und Historie

Sowie Modul-Level-Hilfsfunktionen:
- truncate_data: Panel-Daten auf maximale Zeichenzahl kuerzen
- extract_key_findings: Kernaussagen aus Analysetext extrahieren
"""

from __future__ import annotations

import json
import re
import time
from typing import Any

import structlog

from src.domain.ports import AnalysisResult, ChatResult, FaithfulnessPort, LLMProviderPort
from src.prompts import (
    CHAT_SYSTEM_PROMPT,
    CHAT_USER_TEMPLATE,
    RAG_CONTEXT_TEMPLATE,
    SYSTEM_PROMPT,
    UC_PROMPTS,
    format_context_block,
    format_panel_context,
)

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Use Case: Panel-Analyse (ohne RAG)
# ---------------------------------------------------------------------------


class AnalyzePanel:
    """Panel-Daten analysieren (ohne RAG-Kontext).

    Waehlt das passende Prompt-Template fuer den UC-Key, ruft das LLM auf
    und extrahiert Kernaussagen aus der Analyse.
    """

    def __init__(
        self, llm: LLMProviderPort, default_language: str = "de"
    ) -> None:
        self._llm = llm
        self._default_language = default_language

    async def execute(
        self,
        technology: str,
        use_case_key: str,
        panel_data_json: str,
        language: str | None = None,
        llm_override: LLMProviderPort | None = None,
    ) -> AnalysisResult:
        """Panel-Analyse ausfuehren.

        Args:
            technology: Technologie-Suchbegriff.
            use_case_key: UC-Schluessel (z.B. 'landscape', 'maturity').
            panel_data_json: Serialisierte Panel-Daten als JSON-String.
            language: Sprache der Analyse (default: 'de').
            llm_override: Optionaler LLM-Provider-Override fuer diesen Request.

        Returns:
            AnalysisResult mit Analysetext, Modell, Findings und Konfidenz.
        """
        t0 = time.monotonic()
        language = language or self._default_language
        llm = llm_override or self._llm

        # --- Validierung ---
        if not technology or not technology.strip():
            return AnalysisResult("", "", 0, [], 0.0)

        if use_case_key not in UC_PROMPTS:
            logger.warning(
                "unbekannter_uc_key",
                use_case_key=use_case_key,
                verfuegbar=list(UC_PROMPTS.keys()),
            )
            processing_time_ms = int((time.monotonic() - t0) * 1000)
            return AnalysisResult("", "", processing_time_ms, [], 0.0)

        # --- Prompt zusammenbauen ---
        prompt_template = UC_PROMPTS[use_case_key]
        user_prompt = prompt_template.format(
            technology=technology,
            data=truncate_data(panel_data_json),
        )

        # --- LLM aufrufen ---
        analysis_text, model_used, key_findings, confidence = await self._call_llm(
            user_prompt, llm=llm
        )

        processing_time_ms = int((time.monotonic() - t0) * 1000)
        return AnalysisResult(
            analysis_text, model_used, processing_time_ms, key_findings, confidence
        )

    async def _call_llm(
        self,
        user_prompt: str,
        llm: LLMProviderPort | None = None,
    ) -> tuple[str, str, list[str], float]:
        """LLM aufrufen und Ergebnis mit Findings zurueckgeben."""
        llm = llm or self._llm
        try:
            text, model = await llm.generate(SYSTEM_PROMPT, user_prompt)
            if text:
                return text, model, extract_key_findings(text), 0.85
            return "", model, [], 0.0
        except Exception as e:
            logger.error("llm_aufruf_fehlgeschlagen", fehler=str(e))
            return "", "", [], 0.0


# ---------------------------------------------------------------------------
# Use Case: RAG-gestuetzte Panel-Analyse
# ---------------------------------------------------------------------------


class AnalyzePanelWithContext:
    """RAG-gestuetzte Panel-Analyse mit Kontext-Dokumenten.

    Erhaelt zusaetzlich zu den Panel-Daten eine Liste von Kontext-Dokumenten,
    die als Quellen in den Prompt eingebaut werden.

    Optional: Faithfulness-Guards (Task 16, Asai et al. 2023, Yan et al. 2024).
    Wenn ein FaithfulnessPort uebergeben wird:
    - Vor Generierung: Context-Sufficiency-Check (CRAG)
    - Nach Generierung: Faithfulness-Self-Check -> dynamische Konfidenz
    """

    # Threshold-Hierarchie: INSUFFICIENT < PARTIAL < SUFFICIENT
    _SUFFICIENCY_LEVELS = {"INSUFFICIENT": 0, "PARTIAL": 1, "SUFFICIENT": 2}

    def __init__(
        self,
        llm: LLMProviderPort,
        faithfulness: FaithfulnessPort | None = None,
        sufficiency_threshold: str = "PARTIAL",
    ) -> None:
        self._llm = llm
        self._faithfulness = faithfulness
        self._sufficiency_threshold = sufficiency_threshold

    async def execute(
        self,
        technology: str,
        use_case_key: str,
        panel_data_json: str,
        context_documents: list[Any],
        llm_override: LLMProviderPort | None = None,
    ) -> AnalysisResult:
        """RAG-Analyse ausfuehren.

        Args:
            technology: Technologie-Suchbegriff.
            use_case_key: UC-Schluessel.
            panel_data_json: Serialisierte Panel-Daten als JSON-String.
            context_documents: Liste von RetrievedDocument-Objekten.
            llm_override: Optionaler LLM-Provider-Override fuer diesen Request.

        Returns:
            AnalysisResult mit quellenbasierter Analyse.
        """
        t0 = time.monotonic()
        llm = llm_override or self._llm

        context_block = format_context_block(context_documents)
        user_prompt = RAG_CONTEXT_TEMPLATE.format(
            context_block=context_block,
            panel_data=truncate_data(panel_data_json),
            use_case_key=use_case_key,
            technology=technology,
        )

        # --- Pre-Generation: Context-Sufficiency-Check ---
        if self._faithfulness is not None:
            sufficiency = await self._faithfulness.check_sufficiency(
                context=context_block, question=user_prompt
            )
            if not self._meets_threshold(sufficiency):
                logger.info(
                    "kontext_unzureichend",
                    sufficiency=sufficiency,
                    threshold=self._sufficiency_threshold,
                )
                processing_time_ms = int((time.monotonic() - t0) * 1000)
                return AnalysisResult("", "", processing_time_ms, [], 0.0)

        analysis_text = ""
        model_used = ""
        key_findings: list[str] = []
        confidence = 0.0

        try:
            text, model = await llm.generate(SYSTEM_PROMPT, user_prompt)
            analysis_text = text
            model_used = model
            if analysis_text:
                key_findings = extract_key_findings(analysis_text)
                # --- Post-Generation: Faithfulness-Self-Check ---
                if self._faithfulness is not None:
                    faith_score, _unsupported = (
                        await self._faithfulness.check_faithfulness(
                            context=context_block, answer=analysis_text
                        )
                    )
                    confidence = faith_score
                else:
                    confidence = 0.85
        except Exception as exc:
            logger.warning("rag_analyse_fehler", error=str(exc))
            analysis_text = ""
            confidence = 0.0

        processing_time_ms = int((time.monotonic() - t0) * 1000)
        return AnalysisResult(
            analysis_text, model_used, processing_time_ms, key_findings, confidence
        )

    def _meets_threshold(self, sufficiency: str) -> bool:
        """Prueft ob die Sufficiency das konfigurierte Threshold erreicht.

        Threshold-Hierarchie: INSUFFICIENT(0) < PARTIAL(1) < SUFFICIENT(2).
        - threshold="PARTIAL": akzeptiert PARTIAL und SUFFICIENT
        - threshold="SUFFICIENT": akzeptiert nur SUFFICIENT
        """
        level = self._SUFFICIENCY_LEVELS.get(sufficiency, 1)
        threshold_level = self._SUFFICIENCY_LEVELS.get(
            self._sufficiency_threshold, 1
        )
        return level >= threshold_level


# ---------------------------------------------------------------------------
# Use Case: Interaktiver Chat mit RAG-Kontext
# ---------------------------------------------------------------------------


class ChatWithContext:
    """Interaktiver Chat mit RAG-Kontext.

    Beantwortet Benutzerfragen zur Technologie unter Einbeziehung
    von Retrieval-Kontext-Dokumenten und Chat-Historie.
    """

    def __init__(
        self, llm: LLMProviderPort, default_language: str = "de"
    ) -> None:
        self._llm = llm
        self._default_language = default_language

    async def execute(
        self,
        technology: str,
        user_message: str,
        context_documents: list[Any],
        history: list[Any],
        language: str | None = None,
        panel_context_json: str = "",
        llm_override: LLMProviderPort | None = None,
    ) -> ChatResult:
        """Chat-Antwort generieren.

        Args:
            technology: Technologie-Suchbegriff.
            user_message: Aktuelle Benutzernachricht.
            context_documents: Liste von RetrievedDocument-Objekten.
            history: Bisheriger Chat-Verlauf (Protobuf ChatMessage-Objekte).
            language: Sprache der Antwort (default: 'de').
            panel_context_json: Serialisierte Panel-Daten (JSON) der
                aktuell angezeigten Analyse. Leer wenn nicht verfuegbar.
            llm_override: Optionaler LLM-Provider-Override fuer diesen Request.

        Returns:
            ChatResult mit Antwort, Quellen, Findings und Modell.
        """
        t0 = time.monotonic()
        language = language or self._default_language
        llm = llm_override or self._llm

        # --- System-Prompt mit Technologie und Sprache ---
        system = CHAT_SYSTEM_PROMPT.format(
            technology=technology,
            language=language,
        )

        # --- Kontext-Dokumente formatieren ---
        sources_block = format_context_block(context_documents)

        # --- Panel-Kontext formatieren (Analyse-Daten) ---
        panel_block = format_panel_context(panel_context_json)
        if panel_block:
            panel_block = f"Aktuelle Analyse-Ergebnisse:\n{panel_block}\n\n---\n"

        user_content = CHAT_USER_TEMPLATE.format(
            panel_block=panel_block,
            sources_block=sources_block,
            user_message=user_message,
        )

        # --- Chat-Historie aufbauen ---
        messages: list[dict[str, str]] = []
        for msg in history:
            messages.append({"role": msg.role, "content": msg.content})
        messages.append({"role": "user", "content": user_content})

        # --- LLM aufrufen ---
        answer = ""
        model_used = ""

        try:
            answer, model_used = await llm.chat(system, messages)
        except Exception as exc:
            logger.warning("chat_fehler", error=str(exc))
            answer = "Entschuldigung, es ist ein Fehler aufgetreten."
            model_used = "none"

        if not answer and not model_used:
            answer = "Kein LLM-Provider konfiguriert."
            model_used = "none"

        # --- Quellen-Labels bauen ---
        sources = [
            f"[{i + 1}] {getattr(doc, 'title', '')}"
            for i, doc in enumerate(context_documents)
        ]

        key_findings = extract_key_findings(answer) if answer else []

        processing_time_ms = int((time.monotonic() - t0) * 1000)
        return ChatResult(
            answer, sources, key_findings, model_used, processing_time_ms
        )


# ---------------------------------------------------------------------------
# Modul-Level Hilfsfunktionen
# ---------------------------------------------------------------------------


def truncate_data(panel_data_json: str, max_chars: int = 16000) -> str:
    """Panel-Daten auf maximale Zeichenzahl kuerzen.

    Verhindert, dass zu grosse Payloads das Token-Limit ueberschreiten.
    Versucht die JSON-Struktur zu erhalten.

    Args:
        panel_data_json: JSON-String mit Panel-Daten.
        max_chars: Maximale Zeichenanzahl (default: 8000).

    Returns:
        Gekuerzter oder unveraenderter JSON-String.
    """
    if len(panel_data_json) <= max_chars:
        return panel_data_json

    try:
        data = json.loads(panel_data_json)
        truncated = _truncate_nested(data, max_items=20)
        result = json.dumps(truncated, ensure_ascii=False, indent=2)
        if len(result) <= max_chars:
            return result
    except (json.JSONDecodeError, TypeError):
        pass

    # Fallback: Einfaches Abschneiden mit Hinweis
    return panel_data_json[:max_chars] + "\n... [gekürzt]"


def extract_key_findings(text: str) -> list[str]:
    """Kernaussagen aus dem Analysetext extrahieren (max 5).

    Splittet den Text an Satzenden und gibt die laengeren Saetze
    als Stichpunkte zurueck.

    Args:
        text: Analysetext oder Chat-Antwort.

    Returns:
        Liste von maximal 5 Kernaussagen (Saetze > 15 Zeichen).
    """
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    findings = [s.strip() for s in sentences if s.strip() and len(s.strip()) > 15]
    return findings[:5]


def _truncate_nested(data: Any, max_items: int = 20) -> Any:
    """Verschachtelte Datenstrukturen kuerzen (Listen auf max_items).

    Behaelt die Struktur bei, kuerzt aber grosse Listen um
    das Token-Limit nicht zu ueberschreiten.
    """
    if isinstance(data, dict):
        return {k: _truncate_nested(v, max_items) for k, v in data.items()}
    if isinstance(data, list):
        truncated = [_truncate_nested(item, max_items) for item in data[:max_items]]
        if len(data) > max_items:
            truncated.append(f"... ({len(data) - max_items} weitere Einträge)")
        return truncated
    return data
