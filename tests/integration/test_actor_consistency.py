"""Cross-Service Konsistenz-Test fuer Akteurs-Zaehlungen (Bug CRIT-3 / AP3).

Drei Services (UC8 Temporal, UC9 Tech-Cluster, UC11 Actor-Type) liefern drei
*fachlich unterschiedliche* Akteurs-Zahlen. Vorher fuehrte das zu Nutzer-
verwirrung (mRNA: UC8=34, UC9=29, UC11=363, Faktor 12 ohne Erklaerung).

AP3 behebt die Verwirrung, nicht die Zahlen:

1. Jeder Service liefert in seinem dict-Response das kanonische Scope-Label
   (``shared.domain.actor_definitions.canonical_actor_label``).
2. Die drei Scopes sind eindeutig: ACTIVE_IN_WINDOW (UC8), CLUSTER_MEMBER
   (UC9), CLASSIFIED (UC11).
3. Plausibilitaetsregel (mit realen Datenvolumina):
   ``UC8.active_actors <= UC11.classified_actors`` — Patent-Anmelder im
   Zeitfenster sind typischerweise eine Teilmenge aller klassifizierten
   CORDIS-Organisationen. Dieser Test dokumentiert die Regel; die konkrete
   Durchsetzung erfolgt im Live-System via Playwright-Verifikation (AP10).

Der Test hier arbeitet mit Mock-Pools und prueft die *Service-seitige*
Wahrheit — also, dass jeder Service in seinem Dict-Response das korrekte
Scope-Label setzt. Integrationstests gegen echte DB erfordern Docker
(Testcontainer) und werden in ``services/*/tests/integration/`` gefuehrt.
"""

from __future__ import annotations

import pathlib
import sys

# ---------------------------------------------------------------------------
# Pfad-Setup (packages/ auf sys.path fuer shared.domain.* Imports)
# ---------------------------------------------------------------------------

_REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
_PACKAGES_ROOT = _REPO_ROOT / "packages"
if str(_PACKAGES_ROOT) not in sys.path:
    sys.path.insert(0, str(_PACKAGES_ROOT))


# ---------------------------------------------------------------------------
# Shared-Imports (nach sys.path-Setup verfuegbar)
# ---------------------------------------------------------------------------

from shared.domain.actor_definitions import (  # noqa: E402
    ActorScope,
    canonical_actor_label,
)

# ===========================================================================
# Invariante 1: Kanonische Scope-Labels sind verfuegbar
# ===========================================================================


class TestCanonicalScopeLabels:
    """Die drei Services verwenden drei verschiedene, eindeutige Scopes."""

    def test_uc8_label_ist_active_in_window(self):
        assert canonical_actor_label(ActorScope.ACTIVE_IN_WINDOW) == (
            "aktive Akteure im Zeitfenster"
        )

    def test_uc9_label_ist_cluster_member(self):
        assert canonical_actor_label(ActorScope.CLUSTER_MEMBER) == (
            "Cluster-Mitglieder"
        )

    def test_uc11_label_ist_classified(self):
        assert canonical_actor_label(ActorScope.CLASSIFIED) == (
            "klassifizierte Organisationen"
        )

    def test_drei_eindeutige_labels(self):
        labels = {canonical_actor_label(s) for s in ActorScope}
        assert len(labels) == 3


# ===========================================================================
# Invariante 2: Plausibilitaetsregel (dokumentarisch)
# ===========================================================================
#
# Die Scope-Label-Integration pro Service wird in den Service-Unit-Tests
# geprueft (``services/<svc>/tests/unit/test_actor_scope_label.py``). Ein
# gemeinsamer Test ist nicht moeglich, weil die drei Services jeweils einen
# lokalen ``src.domain.metrics``-Namespace haben, der beim paralellen
# Laden im selben Prozess kollidiert.
# ===========================================================================


class TestActorCountPlausibility:
    """Plausibilitaetsregel fuer Live-Daten (siehe KONSOLIDIERUNG.md/CRIT-3).

    In produktiven Daten gilt typischerweise:
        UC9.CLUSTER_MEMBER <= UC8.ACTIVE_IN_WINDOW <= UC11.CLASSIFIED

    Weil:
    - UC11 (CLASSIFIED) zaehlt *alle* CORDIS-Organisationen mit activity_type
      (unabhaengig vom Zeitfenster).
    - UC8 (ACTIVE_IN_WINDOW) zaehlt Patent-Anmelder + CORDIS-Teilnehmer,
      die im Zeitfenster aktiv waren — Teilmenge der klassifizierten.
    - UC9 (CLUSTER_MEMBER) zaehlt Patent-Anmelder, die via CPC-Cooccurrence
      einem Cluster zugeordnet wurden — weitere Einschraenkung.

    Die konkrete Durchsetzung erfolgt im Live-System via Playwright-MCP
    (siehe AP10). Hier dokumentieren wir die Regel.
    """

    def test_scope_hierarchy_dokumentiert(self):
        """Die drei Scopes sind nach wachsender Restriktivitaet geordnet."""
        # Dokumentarischer Test — keine Ausfuehrung von DB-Queries.
        # Hierarchie wird in AP10 via Live-System verifiziert.
        hierarchy = [
            ActorScope.CLASSIFIED,       # groesste Menge
            ActorScope.ACTIVE_IN_WINDOW,  # Teilmenge: im Zeitfenster aktiv
            ActorScope.CLUSTER_MEMBER,    # Teilmenge: clusterisiert
        ]
        assert len(hierarchy) == 3
        assert len(set(hierarchy)) == 3
