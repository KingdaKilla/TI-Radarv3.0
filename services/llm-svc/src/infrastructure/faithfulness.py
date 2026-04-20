"""LLM-basierte Faithfulness-Pruefung.

Implementiert:
- Context-Sufficiency-Check (CRAG, Yan et al. 2024)
- Faithfulness-Self-Check (Self-RAG, Asai et al. 2023)

Die Pruefung nutzt einen (idealerweise leichtgewichtigen) LLM-Provider
um Kontext-Suffizienz und Antwort-Treue zu bewerten.
"""

from __future__ import annotations

import re

import structlog

from src.domain.ports import FaithfulnessPort, LLMProviderPort

logger = structlog.get_logger(__name__)

SUFFICIENCY_PROMPT = """Given the following context and question, determine if the context \
contains enough information to answer the question.

Context:
{context}

Question: {question}

Respond with exactly one word: SUFFICIENT, PARTIAL, or INSUFFICIENT."""

FAITHFULNESS_PROMPT = """Given the following context and answer, extract the key factual claims \
from the answer and check each against the context.

Context:
{context}

Answer:
{answer}

For each claim, write one line in the format:
CLAIM: <claim text> | VERDICT: SUPPORTED
or
CLAIM: <claim text> | VERDICT: UNSUPPORTED

List all claims."""

# Ordered longest-first to avoid substring matching issues
# ("INSUFFICIENT" contains "SUFFICIENT" as substring)
VALID_SUFFICIENCY = ("INSUFFICIENT", "SUFFICIENT", "PARTIAL")


class LLMFaithfulnessChecker(FaithfulnessPort):
    """Faithfulness-Pruefung via LLM-Aufrufe.

    Nutzt einen LLMProviderPort fuer zwei Pruefungen:
    1. Sufficiency-Check: Kann der Kontext die Frage beantworten?
    2. Faithfulness-Check: Ist die Antwort im Kontext begruendet?

    Fail-open Strategie: Bei Fehlern wird PARTIAL bzw. 0.0 zurueckgegeben,
    damit der Hauptprozess nicht blockiert wird.
    """

    def __init__(self, llm: LLMProviderPort) -> None:
        self._llm = llm

    async def check_sufficiency(self, context: str, question: str) -> str:
        """Prueft ob der Kontext die Frage beantworten kann.

        Args:
            context: Zusammengefasster Kontext aus Retrieval-Dokumenten.
            question: Die Benutzerfrage.

        Returns:
            Einer von: 'SUFFICIENT', 'PARTIAL', 'INSUFFICIENT'.
            Bei Fehlern: 'PARTIAL' (fail-open).
        """
        try:
            text, _ = await self._llm.generate(
                "",
                SUFFICIENCY_PROMPT.format(context=context, question=question),
            )
            result = text.strip().upper()
            # Extract the verdict even if there's extra text
            for keyword in VALID_SUFFICIENCY:
                if keyword in result:
                    return keyword
            logger.warning("sufficiency_malformed", response=text[:100])
            return "PARTIAL"  # fail-open
        except Exception as exc:
            logger.warning("sufficiency_check_fehler", error=str(exc))
            return "PARTIAL"  # fail-open

    async def check_faithfulness(
        self, context: str, answer: str
    ) -> tuple[float, list[str]]:
        """Prueft ob die Antwort im Kontext begruendet ist.

        Extrahiert Claims aus der Antwort und prueft jeden einzelnen
        gegen den bereitgestellten Kontext.

        Args:
            context: Zusammengefasster Kontext aus Retrieval-Dokumenten.
            answer: Die LLM-generierte Antwort.

        Returns:
            Tuple aus (faithfulness_score 0.0-1.0, liste_ungestuetzter_aussagen).
            Bei Fehlern: (0.0, []).
        """
        try:
            text, _ = await self._llm.generate(
                "",
                FAITHFULNESS_PROMPT.format(context=context, answer=answer),
            )
            claims = _parse_claims(text)
            if not claims:
                return 0.0, []
            supported = sum(1 for _, v in claims if v == "SUPPORTED")
            unsupported_texts = [c for c, v in claims if v == "UNSUPPORTED"]
            score = supported / len(claims)
            return score, unsupported_texts
        except Exception as exc:
            logger.warning("faithfulness_check_fehler", error=str(exc))
            return 0.0, []


def _parse_claims(text: str) -> list[tuple[str, str]]:
    """Parses 'CLAIM: ... | VERDICT: SUPPORTED/UNSUPPORTED' lines.

    Args:
        text: LLM-Antwort mit CLAIM/VERDICT-Zeilen.

    Returns:
        Liste von (claim_text, verdict) Tupeln.
    """
    claims: list[tuple[str, str]] = []
    pattern = r"CLAIM:\s*(.+?)\s*\|\s*VERDICT:\s*(SUPPORTED|UNSUPPORTED)"
    for match in re.finditer(pattern, text, re.IGNORECASE):
        claim_text = match.group(1).strip()
        verdict = match.group(2).strip().upper()
        claims.append((claim_text, verdict))
    return claims
