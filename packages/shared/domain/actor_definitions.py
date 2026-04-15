"""Master-Definitionen fuer Akteurs-Zaehlungen (Bug CRIT-3).

Hintergrund: UC8 (Temporal), UC9 (Tech-Cluster) und UC11 (Actor-Type) lieferten
im Live-System drei unterschiedliche Akteurs-Zahlen (Faktor bis 100). Dieses
Modul legt drei kanonische Scopes fest, auf die alle Services verweisen.

Scope-Mapping zu Query-Tabellen (dokumentarisch):
    ACTIVE_IN_WINDOW → ``entity_schema.unified_actors`` JOIN CORDIS/EPO/Publikations-
                       Aktivitaet im Zeitfenster. Genutzt von UC8.
    CLUSTER_MEMBER   → ``entity_schema.unified_actors`` JOIN einem Tech-Cluster
                       (Louvain/Leiden-Zuordnung). Genutzt von UC9.
    CLASSIFIED       → ``entity_schema.unified_actors`` mit gesetzter Typ-Klassi-
                       fikation (akademisch/industriell/oeffentlich). Genutzt von
                       UC11.

Plausibilitaet: Fuer gleiche Tech + gleiches Zeitfenster gilt i.d.R.
``CLUSTER_MEMBER <= ACTIVE_IN_WINDOW <= CLASSIFIED`` — da klassifiziert alle
jemals kategorisierten Organisationen zaehlt, aktiv nur die im Fenster, und
Cluster-Mitglied nur die durch Co-Occurrence-Analyse verbundenen.
"""

from __future__ import annotations

from enum import Enum


class ActorScope(Enum):
    """Kanonischer Scope fuer Akteurs-Zaehlungen."""

    ACTIVE_IN_WINDOW = "active_in_window"
    CLUSTER_MEMBER = "cluster_member"
    CLASSIFIED = "classified"


_LABELS: dict[ActorScope, str] = {
    ActorScope.ACTIVE_IN_WINDOW: "aktive Akteure im Zeitfenster",
    ActorScope.CLUSTER_MEMBER: "Cluster-Mitglieder",
    ActorScope.CLASSIFIED: "klassifizierte Organisationen",
}


def canonical_actor_label(scope: ActorScope) -> str:
    """Kurzes deutsches Label fuer UI/Logs.

    Args:
        scope: Element des ``ActorScope``-Enums.

    Returns:
        Lesbares Label (z.B. "aktive Akteure im Zeitfenster").

    Raises:
        TypeError: wenn ``scope`` kein ``ActorScope`` ist.
    """
    if not isinstance(scope, ActorScope):
        raise TypeError(
            f"scope muss ActorScope sein, nicht {type(scope).__name__}"
        )
    return _LABELS[scope]


__all__ = [
    "ActorScope",
    "canonical_actor_label",
]
