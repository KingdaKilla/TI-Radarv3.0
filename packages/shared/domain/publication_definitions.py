"""Master-Definitionen fuer Publikations-Zaehlungen (Bug CRIT-1).

Hintergrund: Header-Summary (`total_publications` in UC1), Top-Autor-Publikationen
(UC7) und Projekt-Publikationen (UC13) lieferten im Live-System drei voellig
verschiedene Zahlen (Faktor bis 1580). Dieses Modul legt eine kanonische
Scope-Enum fest, auf die alle Services verweisen.

Die eigentliche SQL-Implementierung bleibt bei den Service-Repositories — dieses
Modul dokumentiert ausschliesslich die *Semantik* jedes Scopes, damit divergente
Interpretationen strukturell unmoeglich werden.

Scope-Mapping zu Query-Tabellen (dokumentarisch):
    CORDIS_LINKED        → ``publication_schema.publications`` JOIN
                           ``cordis_schema.project_publications`` ON project_id
                           — d.h. Publikationen, die direkt aus einem CORDIS-Projekt
                           hervorgehen. Header-Summary und UC13 nutzen diesen Scope.
    OPENAIRE_MATCHED     → ``publication_schema.openaire_matches`` mit Filter auf
                           den Tech-Keyword-Space. Breitester Scope — enthaelt auch
                           Publikationen ohne direkten CORDIS-Link.
    SEMANTIC_SCHOLAR_TOP → ``publication_schema.top_author_publications`` fuer die
                           Top-N-Autoren aus UC7 (Research Impact). Kleinster Scope.
"""

from __future__ import annotations

from enum import Enum


class PublicationScope(Enum):
    """Kanonischer Scope fuer Publikationszaehlungen."""

    CORDIS_LINKED = "cordis_linked"
    OPENAIRE_MATCHED = "openaire_matched"
    SEMANTIC_SCHOLAR_TOP = "semantic_scholar_top"


_LABELS: dict[PublicationScope, str] = {
    PublicationScope.CORDIS_LINKED: "CORDIS-Projekt-Publikationen",
    PublicationScope.OPENAIRE_MATCHED: "OpenAIRE Tech-Treffer",
    PublicationScope.SEMANTIC_SCHOLAR_TOP: "Top-Autor-Publikationen",
}


def canonical_publication_label(scope: PublicationScope) -> str:
    """Kurzes deutsches Label fuer UI/Logs.

    Args:
        scope: Element des ``PublicationScope``-Enums.

    Returns:
        Lesbares Label (z.B. "CORDIS-Projekt-Publikationen").

    Raises:
        KeyError: wenn ``scope`` kein ``PublicationScope`` ist.
    """
    if not isinstance(scope, PublicationScope):
        raise TypeError(
            f"scope muss PublicationScope sein, nicht {type(scope).__name__}"
        )
    return _LABELS[scope]


__all__ = [
    "PublicationScope",
    "canonical_publication_label",
]
