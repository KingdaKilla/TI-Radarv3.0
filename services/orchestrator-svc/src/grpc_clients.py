"""Async gRPC Channel-Pool-Manager fuer die 12 UC-Services.

Verwaltet eine gRPC-Channel-Verbindung pro UC-Service mit:
- Lazy Connection (Channel wird erst beim ersten Aufruf erzeugt)
- Health-Monitoring via gRPC Channel-Connectivity-States
- Graceful Shutdown (alle Channels bei Anwendungsende schliessen)
- Konfigurierbare maximale Nachrichtengroesse

Die Channels werden waehrend der FastAPI-Lifespan geoeffnet und
am Ende wieder geschlossen. Jeder Channel ist thread-safe und kann
von mehreren Coroutines gleichzeitig genutzt werden.
"""

from __future__ import annotations

import asyncio
import time
from typing import TYPE_CHECKING, Any

import grpc
import structlog

from src.config import Settings, UCServiceConfig

if TYPE_CHECKING:
    from grpc.aio import Channel

logger = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# gRPC Stub-Importe (Placeholder bis Protobuf-Kompilierung)
# ---------------------------------------------------------------------------
# Nach der Proto-Kompilierung werden die generierten Stubs aus dem
# shared-Paket importiert. Bis dahin: try/except mit None-Fallback.

try:
    from shared.generated.python import (
        uc1_landscape_pb2_grpc,
        uc2_maturity_pb2_grpc,
        uc3_competitive_pb2_grpc,
        uc4_funding_pb2_grpc,
        uc5_cpc_flow_pb2_grpc,
        uc6_geographic_pb2_grpc,
        uc7_research_impact_pb2_grpc,
        uc8_temporal_pb2_grpc,
        uc9_tech_cluster_pb2_grpc,
        uc11_actor_type_pb2_grpc,
        uc12_patent_grant_pb2_grpc,
        uc10_euroscivoc_pb2_grpc,
        uc_c_publications_pb2_grpc,
    )
except ImportError:
    # Stubs noch nicht generiert — werden nach proto-Kompilierung verfuegbar
    uc1_landscape_pb2_grpc = None  # type: ignore[assignment]
    uc2_maturity_pb2_grpc = None  # type: ignore[assignment]
    uc3_competitive_pb2_grpc = None  # type: ignore[assignment]
    uc4_funding_pb2_grpc = None  # type: ignore[assignment]
    uc5_cpc_flow_pb2_grpc = None  # type: ignore[assignment]
    uc6_geographic_pb2_grpc = None  # type: ignore[assignment]
    uc7_research_impact_pb2_grpc = None  # type: ignore[assignment]
    uc8_temporal_pb2_grpc = None  # type: ignore[assignment]
    uc9_tech_cluster_pb2_grpc = None  # type: ignore[assignment]
    uc11_actor_type_pb2_grpc = None  # type: ignore[assignment]
    uc12_patent_grant_pb2_grpc = None  # type: ignore[assignment]
    uc10_euroscivoc_pb2_grpc = None  # type: ignore[assignment]
    uc_c_publications_pb2_grpc = None  # type: ignore[assignment]

try:
    from shared.generated.python import common_pb2
except ImportError:
    common_pb2 = None  # type: ignore[assignment]


# ---------------------------------------------------------------------------
# Mapping: UC-Name -> (Stub-Modul, Stub-Klasse, RPC-Methodenname)
# ---------------------------------------------------------------------------
UC_STUB_REGISTRY: dict[str, tuple[Any, str, str]] = {
    "landscape":       (uc1_landscape_pb2_grpc, "LandscapeServiceStub", "AnalyzeLandscape"),
    "maturity":        (uc2_maturity_pb2_grpc, "MaturityServiceStub", "AnalyzeMaturity"),
    "competitive":     (uc3_competitive_pb2_grpc, "CompetitiveServiceStub", "AnalyzeCompetitive"),
    "funding":         (uc4_funding_pb2_grpc, "FundingServiceStub", "AnalyzeFunding"),
    "cpc_flow":        (uc5_cpc_flow_pb2_grpc, "CpcFlowServiceStub", "AnalyzeCpcFlow"),
    "geographic":      (uc6_geographic_pb2_grpc, "GeographicServiceStub", "AnalyzeGeographic"),
    "research_impact": (uc7_research_impact_pb2_grpc, "ResearchImpactServiceStub", "AnalyzeResearchImpact"),
    "temporal":        (uc8_temporal_pb2_grpc, "TemporalServiceStub", "AnalyzeTemporal"),
    "tech_cluster":    (uc9_tech_cluster_pb2_grpc, "TechClusterServiceStub", "AnalyzeTechCluster"),
    "actor_type":      (uc11_actor_type_pb2_grpc, "ActorTypeServiceStub", "AnalyzeActorTypes"),
    "patent_grant":    (uc12_patent_grant_pb2_grpc, "PatentGrantServiceStub", "AnalyzePatentGrant"),
    "euroscivoc":      (uc10_euroscivoc_pb2_grpc, "EuroSciVocServiceStub", "AnalyzeEuroSciVoc"),
    "publication":     (uc_c_publications_pb2_grpc, "PublicationAnalyticsServiceStub", "AnalyzePublications"),
}


class GrpcChannelManager:
    """Verwaltet gRPC-Channels zu allen UC-Services.

    Erzeugt pro Service genau einen aio.Channel mit konfigurierbaren
    Optionen. Channels werden lazy initialisiert und bei close()
    graceful heruntergefahren.
    """

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._uc_configs = settings.get_uc_configs()
        self._channels: dict[str, Channel] = {}
        self._stubs: dict[str, Any] = {}
        self._lock = asyncio.Lock()

    # -----------------------------------------------------------------
    # Channel-Erzeugung
    # -----------------------------------------------------------------

    def _create_channel(self, uc_name: str, config: UCServiceConfig) -> Channel:
        """Erzeugt einen gRPC aio.Channel mit Standard-Optionen."""
        options: list[tuple[str, Any]] = [
            ("grpc.max_receive_message_length", self._settings.grpc_max_message_size),
            ("grpc.max_send_message_length", self._settings.grpc_max_message_size),
            # Keepalive: 5 Minuten Intervall (Server-Default min_recv_ping = 300s)
            ("grpc.keepalive_time_ms", 300_000),
            ("grpc.keepalive_timeout_ms", 10_000),
            ("grpc.keepalive_permit_without_calls", 0),
            # Sofortige Fehlererkennung bei Verbindungsverlust
            ("grpc.enable_retries", 1),
            ("grpc.initial_reconnect_backoff_ms", 500),
            ("grpc.max_reconnect_backoff_ms", 5_000),
        ]
        channel = grpc.aio.insecure_channel(config.address, options=options)
        logger.info(
            "grpc_channel_erstellt",
            uc=uc_name,
            address=config.address,
            timeout=config.timeout,
        )
        return channel

    # -----------------------------------------------------------------
    # Lazy Stub-Erzeugung
    # -----------------------------------------------------------------

    async def get_stub(self, uc_name: str) -> Any | None:
        """Gibt den gRPC-Stub fuer den angegebenen UC-Service zurueck.

        Erstellt Channel + Stub lazy beim ersten Zugriff. Gibt None
        zurueck, wenn die Stubs noch nicht generiert sind.
        """
        if uc_name in self._stubs:
            return self._stubs[uc_name]

        async with self._lock:
            # Double-check nach Lock-Erwerb
            if uc_name in self._stubs:
                return self._stubs[uc_name]

            config = self._uc_configs.get(uc_name)
            if config is None:
                logger.error("unbekannter_uc_service", uc=uc_name)
                return None

            # Stub-Registry pruefen
            registry_entry = UC_STUB_REGISTRY.get(uc_name)
            if registry_entry is None or registry_entry[0] is None:
                logger.warning(
                    "grpc_stubs_nicht_verfuegbar",
                    uc=uc_name,
                    hint="Proto-Kompilierung ausfuehren: make proto-gen",
                )
                return None

            stub_module, stub_class_name, _rpc_method = registry_entry

            # Channel erzeugen
            channel = self._create_channel(uc_name, config)
            self._channels[uc_name] = channel

            # Stub instanziieren
            stub_class = getattr(stub_module, stub_class_name)
            stub = stub_class(channel)
            self._stubs[uc_name] = stub

            logger.info("grpc_stub_erzeugt", uc=uc_name, stub=stub_class_name)
            return stub

    # -----------------------------------------------------------------
    # RPC-Aufruf mit Timeout und Fehlerbehandlung
    # -----------------------------------------------------------------

    async def call_uc(
        self,
        uc_name: str,
        request: Any,
        timeout: float | None = None,
    ) -> Any:
        """Fuehrt den gRPC-RPC-Aufruf fuer einen UC-Service aus.

        Args:
            uc_name: Name des UC-Service (z.B. "landscape").
            request: Protobuf AnalysisRequest.
            timeout: Timeout in Sekunden (None = Konfigurierter Default).

        Returns:
            Protobuf-Response des UC-Service.

        Raises:
            grpc.RpcError: Bei gRPC-Fehlern.
            asyncio.TimeoutError: Bei Timeout.
            RuntimeError: Wenn Stubs nicht verfuegbar sind.
        """
        stub = await self.get_stub(uc_name)
        if stub is None:
            raise RuntimeError(
                f"gRPC-Stub fuer '{uc_name}' nicht verfuegbar. "
                f"Proto-Kompilierung ausfuehren."
            )

        # RPC-Methodenname aus Registry holen
        registry_entry = UC_STUB_REGISTRY[uc_name]
        rpc_method_name = registry_entry[2]
        rpc_method = getattr(stub, rpc_method_name)

        # Timeout bestimmen
        if timeout is None:
            config = self._uc_configs.get(uc_name)
            timeout = config.timeout if config else 10.0

        # RPC-Aufruf mit gRPC-eigenem Timeout
        response = await rpc_method(request, timeout=timeout)
        return response

    # -----------------------------------------------------------------
    # Health-Check: Channel-Konnektivitaet pruefen
    # -----------------------------------------------------------------

    async def check_health(self, uc_name: str) -> tuple[bool, int, str]:
        """Prueft die Konnektivitaet eines UC-Service-Channels.

        Returns:
            Tuple (healthy, latency_ms, error_message).
        """
        t0 = time.monotonic()

        try:
            config = self._uc_configs.get(uc_name)
            if config is None:
                return False, 0, f"Unbekannter UC-Service: {uc_name}"

            # Channel lazy erzeugen falls noch nicht vorhanden
            if uc_name not in self._channels:
                channel = self._create_channel(uc_name, config)
                self._channels[uc_name] = channel

            channel = self._channels[uc_name]

            # Konnektivitaet mit kurzem Timeout pruefen
            try:
                await asyncio.wait_for(
                    channel.channel_ready(),
                    timeout=3.0,
                )
                latency_ms = int((time.monotonic() - t0) * 1000)
                return True, latency_ms, ""
            except asyncio.TimeoutError:
                latency_ms = int((time.monotonic() - t0) * 1000)
                return False, latency_ms, "Connection timeout (3s)"

        except Exception as exc:
            latency_ms = int((time.monotonic() - t0) * 1000)
            return False, latency_ms, f"{type(exc).__name__}: {exc}"

    async def check_all_health(self) -> dict[str, tuple[bool, int, str]]:
        """Prueft alle UC-Services parallel auf Konnektivitaet."""
        tasks = {
            uc_name: self.check_health(uc_name)
            for uc_name in self._uc_configs
        }
        results: dict[str, tuple[bool, int, str]] = {}
        health_results = await asyncio.gather(
            *tasks.values(), return_exceptions=True,
        )
        for uc_name, result in zip(tasks.keys(), health_results):
            if isinstance(result, BaseException):
                results[uc_name] = (False, 0, f"{type(result).__name__}: {result}")
            else:
                results[uc_name] = result
        return results

    # -----------------------------------------------------------------
    # Lifecycle: Graceful Shutdown
    # -----------------------------------------------------------------

    async def close(self) -> None:
        """Schliesst alle gRPC-Channels graceful."""
        for uc_name, channel in self._channels.items():
            try:
                await channel.close()
                logger.info("grpc_channel_geschlossen", uc=uc_name)
            except Exception as exc:
                logger.warning(
                    "grpc_channel_close_fehler",
                    uc=uc_name,
                    error=str(exc),
                )
        self._channels.clear()
        self._stubs.clear()
        logger.info("alle_grpc_channels_geschlossen")

    # -----------------------------------------------------------------
    # Hilfsmethoden
    # -----------------------------------------------------------------

    @property
    def uc_names(self) -> list[str]:
        """Liste aller konfigurierten UC-Service-Namen."""
        return list(self._uc_configs.keys())

    def get_timeout(self, uc_name: str) -> float:
        """Gibt den konfigurierten Timeout fuer einen UC-Service zurueck."""
        config = self._uc_configs.get(uc_name)
        return config.timeout if config else 10.0
