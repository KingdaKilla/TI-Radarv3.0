"""Port-Interfaces fuer LLM-Service (Hexagonal Architecture).

Definiert abstrakte Schnittstellen fuer:
- LLMProviderPort: LLM-Aufrufe (Anthropic, OpenAI, etc.)
- FaithfulnessPort: Faithfulness-Pruefung (Task 16)

Sowie Ergebnis-Datenklassen:
- AnalysisResult: Ergebnis einer Panel-Analyse
- ChatResult: Ergebnis einer Chat-Antwort
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class AnalysisResult:
    """Ergebnis einer LLM-Analyse."""

    analysis_text: str
    model_used: str
    processing_time_ms: int
    key_findings: list[str]
    confidence: float


@dataclass(frozen=True, slots=True)
class ChatResult:
    """Ergebnis einer Chat-Antwort."""

    answer: str
    sources: list[str]
    key_findings: list[str]
    model_used: str
    processing_time_ms: int


class LLMProviderPort(ABC):
    """Abstraktes Interface fuer LLM-Aufrufe.

    Implementierungen kapseln die Kommunikation mit einem konkreten
    LLM-Provider (Anthropic Claude, OpenAI GPT, etc.).
    """

    @abstractmethod
    async def generate(
        self, system_prompt: str, user_prompt: str
    ) -> tuple[str, str]:
        """LLM aufrufen fuer Single-Turn-Generierung.

        Args:
            system_prompt: System-Kontext fuer das LLM.
            user_prompt: Benutzer-Prompt mit Daten und Anweisungen.

        Returns:
            Tuple aus (generierter_text, modell_name).
        """

    @abstractmethod
    async def chat(
        self, system_prompt: str, messages: list[dict[str, str]]
    ) -> tuple[str, str]:
        """Chat-Completion mit Nachrichtenverlauf.

        Args:
            system_prompt: System-Kontext fuer das LLM.
            messages: Liste von Nachrichten mit 'role' und 'content'.

        Returns:
            Tuple aus (antwort_text, modell_name).
        """


class FaithfulnessPort(ABC):
    """Abstraktes Interface fuer Faithfulness-Pruefung (Task 16).

    Prueft ob LLM-Antworten im bereitgestellten Kontext begruendet sind
    (EU AI Act 2024/1689 Compliance).
    """

    @abstractmethod
    async def check_sufficiency(
        self, context: str, question: str
    ) -> str:
        """Prueft ob der Kontext die Frage beantworten kann.

        Args:
            context: Zusammengefasster Kontext aus Retrieval-Dokumenten.
            question: Die Benutzerfrage.

        Returns:
            Einer von: 'SUFFICIENT', 'PARTIAL', 'INSUFFICIENT'.
        """

    @abstractmethod
    async def check_faithfulness(
        self, context: str, answer: str
    ) -> tuple[float, list[str]]:
        """Prueft ob die Antwort im Kontext begruendet ist.

        Args:
            context: Zusammengefasster Kontext aus Retrieval-Dokumenten.
            answer: Die LLM-generierte Antwort.

        Returns:
            Tuple aus (faithfulness_score 0.0-1.0, liste_ungestuetzter_aussagen).
        """
