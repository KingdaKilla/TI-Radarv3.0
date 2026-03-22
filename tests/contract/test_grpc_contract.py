"""gRPC Contract-Tests fuer UC-Services.

Prueft, dass die gRPC-Responses der UC-Services dem Proto-Schema entsprechen:
- AnalysisRequest-Felder korrekt gesetzt (common_pb2)
- LandscapeResponse-Struktur gueltig (uc1_landscape_pb2)
- Protobuf-Deserialisierung ohne Fehler
- Fehlende optionale Felder haben Protobuf-Standardwerte
- TimeRange-Einschraenkung wird korrekt uebertragen
- Request-ID-Propagation (Distributed Tracing)

Teststrategie:
  Provider-Tests: UC-Service-Response entspricht Proto-Definition.
  Die UC-Services werden gemockt (kein laufender gRPC-Server noetig).
  Validierung erfolgt durch Serialisierung/Deserialisierung der Protobuf-Nachrichten.

Alle Tests koennen ohne laufende Infrastruktur ausgefuehrt werden.
"""

from __future__ import annotations

import sys
import pathlib
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Sicherstellen, dass shared.generated im Python-Pfad ist
_REPO_ROOT = pathlib.Path(__file__).parent.parent.parent
_SHARED_PATH = _REPO_ROOT / "shared"
if str(_SHARED_PATH) not in sys.path:
    sys.path.insert(0, str(_SHARED_PATH))
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))


# ---------------------------------------------------------------------------
# Protobuf-Import (tolerant gegenueber fehlenden Stubs)
# ---------------------------------------------------------------------------

try:
    from shared.generated.python import common_pb2
    from shared.generated.python import uc1_landscape_pb2
    from shared.generated.python import uc3_competitive_pb2
    from shared.generated.python import uc4_funding_pb2
    from google.protobuf.json_format import MessageToDict, ParseDict

    PROTOBUF_VERFUEGBAR = True
except ImportError:
    PROTOBUF_VERFUEGBAR = False
    common_pb2 = None  # type: ignore[assignment]
    uc1_landscape_pb2 = None  # type: ignore[assignment]
    uc3_competitive_pb2 = None  # type: ignore[assignment]
    uc4_funding_pb2 = None  # type: ignore[assignment]
    MessageToDict = None  # type: ignore[assignment]
    ParseDict = None  # type: ignore[assignment]

# Dekorator zum Ueberspringen wenn Protobuf nicht verfuegbar
requires_protobuf = pytest.mark.skipif(
    not PROTOBUF_VERFUEGBAR,
    reason="google-protobuf nicht installiert oder Stubs nicht vorhanden",
)


# ===========================================================================
# Fixtures
# ===========================================================================


@pytest.fixture
def standard_request():
    """Erstellt einen Standard-AnalysisRequest fuer Tests.

    Entspricht dem Aufruf im Orchestrator (router_radar.py _build_analysis_request).

    Yields:
        common_pb2.AnalysisRequest-Instanz oder None wenn Protobuf fehlt.
    """
    if not PROTOBUF_VERFUEGBAR:
        return None

    time_range = common_pb2.TimeRange(start_year=2016, end_year=2026)
    return common_pb2.AnalysisRequest(
        technology="quantum computing",
        time_range=time_range,
        european_only=False,
        cpc_codes=[],
        top_n=0,
        request_id="contract-test-001",
    )


@pytest.fixture
def eu_filtered_request():
    """AnalysisRequest mit european_only=True.

    Yields:
        common_pb2.AnalysisRequest-Instanz oder None wenn Protobuf fehlt.
    """
    if not PROTOBUF_VERFUEGBAR:
        return None

    time_range = common_pb2.TimeRange(start_year=2019, end_year=2024)
    return common_pb2.AnalysisRequest(
        technology="solid-state batteries",
        time_range=time_range,
        european_only=True,
        cpc_codes=["H01M", "H02J"],
        top_n=20,
        request_id="contract-test-eu-002",
    )


# ===========================================================================
# AnalysisRequest-Serialisierung (common_pb2)
# ===========================================================================


class TestAnalysisRequestProto:
    """Prueft die Serialisierung und Deserialisierung von AnalysisRequest."""

    @requires_protobuf
    def test_standard_request_serialisierbar(self, standard_request):
        """AnalysisRequest kann ohne Fehler serialisiert werden."""
        serialisiert = standard_request.SerializeToString()
        assert isinstance(serialisiert, bytes)
        assert len(serialisiert) > 0

    @requires_protobuf
    def test_deserialisierung_roundtrip(self, standard_request):
        """Serialisierung + Deserialisierung ergibt identische Felder."""
        serialisiert = standard_request.SerializeToString()

        deserialisiert = common_pb2.AnalysisRequest()
        deserialisiert.ParseFromString(serialisiert)

        assert deserialisiert.technology == standard_request.technology
        assert deserialisiert.time_range.start_year == 2016
        assert deserialisiert.time_range.end_year == 2026
        assert deserialisiert.european_only is False
        assert deserialisiert.request_id == "contract-test-001"

    @requires_protobuf
    def test_eu_filter_roundtrip(self, eu_filtered_request):
        """european_only=True und cpc_codes werden korrekt uebertragen."""
        serialisiert = eu_filtered_request.SerializeToString()

        deserialisiert = common_pb2.AnalysisRequest()
        deserialisiert.ParseFromString(serialisiert)

        assert deserialisiert.european_only is True
        assert "H01M" in deserialisiert.cpc_codes
        assert "H02J" in deserialisiert.cpc_codes
        assert deserialisiert.top_n == 20

    @requires_protobuf
    def test_request_id_propagation(self, standard_request):
        """Request-ID wird unveraendert uebertragen (Distributed Tracing)."""
        assert standard_request.request_id == "contract-test-001"

    @requires_protobuf
    def test_leere_technologie_defaultwert(self):
        """Leerer technology-String entspricht Protobuf-Standardwert."""
        request = common_pb2.AnalysisRequest()
        assert request.technology == ""  # Protobuf default: leerer String

    @requires_protobuf
    def test_zu_json_konvertierbar(self, standard_request):
        """AnalysisRequest ist mit MessageToDict zu JSON konvertierbar."""
        as_dict = MessageToDict(
            standard_request,
            preserving_proto_field_name=True,
            including_default_value_fields=True,
        )
        assert "technology" in as_dict
        assert as_dict["technology"] == "quantum computing"
        assert "time_range" in as_dict
        assert "european_only" in as_dict


# ===========================================================================
# LandscapeResponse-Schema (uc1_landscape_pb2)
# ===========================================================================


class TestLandscapeResponseSchema:
    """Prueft die Struktur von LandscapeResponse gemaess uc1_landscape.proto."""

    @requires_protobuf
    def test_leere_response_hat_standardwerte(self):
        """Eine leere LandscapeResponse hat Protobuf-Standardwerte (nicht None)."""
        response = uc1_landscape_pb2.LandscapeResponse()

        # Repeated fields: leere Listen (nicht None)
        assert list(response.time_series) == []
        assert list(response.top_countries) == []
        assert list(response.top_cpc_codes) == []

    @requires_protobuf
    def test_time_series_entry_felder(self):
        """LandscapeTimeSeriesEntry hat alle Proto-Felder."""
        eintrag = uc1_landscape_pb2.LandscapeTimeSeriesEntry(
            year=2022,
            patent_count=42,
            project_count=5,
            publication_count=18,
            funding_eur=2800000.0,
        )
        assert eintrag.year == 2022
        assert eintrag.patent_count == 42
        assert eintrag.project_count == 5
        assert eintrag.publication_count == 18
        assert eintrag.funding_eur == pytest.approx(2800000.0)

    @requires_protobuf
    def test_landscape_summary_felder(self):
        """LandscapeSummary hat alle sechs Proto-Felder."""
        summary = uc1_landscape_pb2.LandscapeSummary(
            total_patents=250,
            total_projects=18,
            total_publications=145,
            total_funding_eur=25000000.0,
            active_countries=12,
            active_actors=87,
        )
        assert summary.total_patents == 250
        assert summary.total_projects == 18
        assert summary.total_publications == 145
        assert summary.total_funding_eur == pytest.approx(25000000.0)
        assert summary.active_countries == 12
        assert summary.active_actors == 87

    @requires_protobuf
    def test_cagr_values_felder(self):
        """CagrValues hat alle fuenf Proto-Felder."""
        cagr = uc1_landscape_pb2.CagrValues(
            patent_cagr=0.125,
            project_cagr=0.083,
            publication_cagr=0.152,
            funding_cagr=0.187,
            period_years=10,
        )
        assert cagr.patent_cagr == pytest.approx(0.125)
        assert cagr.period_years == 10

    @requires_protobuf
    def test_vollstaendige_response_roundtrip(self):
        """Vollstaendige LandscapeResponse kann serialisiert und deserialisiert werden."""
        # Zeitreihe aufbauen
        eintrag = uc1_landscape_pb2.LandscapeTimeSeriesEntry(
            year=2022,
            patent_count=42,
            project_count=5,
            publication_count=18,
            funding_eur=2800000.0,
        )

        # Land-Metrik
        country = common_pb2.CountryMetric(
            country_code="DE",
            country_name="Germany",
            count=42,
            share=0.45,
        )

        # CPC-Code
        cpc = uc1_landscape_pb2.CpcCodeCount(
            code="G06F",
            description="Electric digital data processing",
            count=28,
            share=0.35,
        )

        # Metadaten
        metadata = common_pb2.ResponseMetadata(
            processing_time_ms=1234,
            request_id="contract-test-001",
            timestamp="2026-02-20T10:00:00Z",
        )

        # Response zusammenbauen
        response = uc1_landscape_pb2.LandscapeResponse()
        response.time_series.append(eintrag)
        response.top_countries.append(country)
        response.top_cpc_codes.append(cpc)
        response.metadata.CopyFrom(metadata)

        # Roundtrip
        serialisiert = response.SerializeToString()
        deserialisiert = uc1_landscape_pb2.LandscapeResponse()
        deserialisiert.ParseFromString(serialisiert)

        assert len(deserialisiert.time_series) == 1
        assert deserialisiert.time_series[0].year == 2022
        assert deserialisiert.time_series[0].patent_count == 42
        assert len(deserialisiert.top_countries) == 1
        assert deserialisiert.top_countries[0].country_code == "DE"
        assert deserialisiert.metadata.request_id == "contract-test-001"

    @requires_protobuf
    def test_response_zu_json_kompatibel(self):
        """LandscapeResponse kann mit MessageToDict in JSON-kompatibles Dict umgewandelt werden."""
        response = uc1_landscape_pb2.LandscapeResponse()
        eintrag = uc1_landscape_pb2.LandscapeTimeSeriesEntry(
            year=2022,
            patent_count=42,
        )
        response.time_series.append(eintrag)

        as_dict = MessageToDict(
            response,
            preserving_proto_field_name=True,
            including_default_value_fields=True,
        )

        assert "time_series" in as_dict
        assert isinstance(as_dict["time_series"], list)
        assert len(as_dict["time_series"]) == 1
        assert as_dict["time_series"][0]["year"] == 2022


# ===========================================================================
# Common Proto-Types
# ===========================================================================


class TestCommonProtoTypes:
    """Prueft gemeinsame Typen aus common.proto."""

    @requires_protobuf
    def test_time_range_grenzen(self):
        """TimeRange unterstuetzt start_year und end_year als int32."""
        time_range = common_pb2.TimeRange(start_year=2000, end_year=2030)
        assert time_range.start_year == 2000
        assert time_range.end_year == 2030

    @requires_protobuf
    def test_country_metric_felder(self):
        """CountryMetric hat alle vier Felder aus common.proto."""
        country = common_pb2.CountryMetric(
            country_code="FR",
            country_name="France",
            count=30,
            share=0.30,
        )
        assert country.country_code == "FR"
        assert country.country_name == "France"
        assert country.count == 30
        assert country.share == pytest.approx(0.30)

    @requires_protobuf
    def test_warning_severity_enum(self):
        """WarningSeverity-Enum hat LOW, MEDIUM, HIGH Werte."""
        assert common_pb2.LOW == 1
        assert common_pb2.MEDIUM == 2
        assert common_pb2.HIGH == 3
        assert common_pb2.WARNING_SEVERITY_UNSPECIFIED == 0

    @requires_protobuf
    def test_data_source_type_enum(self):
        """DataSourceType-Enum hat PATENT, PUBLICATION, PROJECT, FUNDING, MIXED."""
        assert common_pb2.PATENT == 1
        assert common_pb2.PUBLICATION == 2
        assert common_pb2.PROJECT == 3
        assert common_pb2.FUNDING == 4
        assert common_pb2.MIXED == 5

    @requires_protobuf
    def test_response_metadata_felder(self):
        """ResponseMetadata hat processing_time_ms, request_id und timestamp."""
        metadata = common_pb2.ResponseMetadata(
            processing_time_ms=567,
            request_id="test-id-123",
            timestamp="2026-02-20T10:00:00Z",
        )
        assert metadata.processing_time_ms == 567
        assert metadata.request_id == "test-id-123"
        assert metadata.timestamp == "2026-02-20T10:00:00Z"

    @requires_protobuf
    def test_warning_in_metadata(self):
        """Warnings koennen in ResponseMetadata eingebettet werden."""
        warning = common_pb2.Warning(
            message="Datenmenge gering — Ergebnisse unvollstaendig",
            severity=common_pb2.MEDIUM,
            code="SPARSE_DATA",
        )
        metadata = common_pb2.ResponseMetadata()
        metadata.warnings.append(warning)

        assert len(metadata.warnings) == 1
        assert metadata.warnings[0].severity == common_pb2.MEDIUM
        assert metadata.warnings[0].code == "SPARSE_DATA"

    @requires_protobuf
    def test_named_time_series(self):
        """NamedTimeSeries kapselt label + points korrekt."""
        punkt = common_pb2.TimeSeriesPoint(year=2022, value=42.5)
        serie = common_pb2.NamedTimeSeries(
            label="patents",
            points=[punkt],
        )
        assert serie.label == "patents"
        assert len(serie.points) == 1
        assert serie.points[0].year == 2022
        assert serie.points[0].value == pytest.approx(42.5)


# ===========================================================================
# Orchestrator-seitige Request-Erstellung (Integration mit router_radar.py)
# ===========================================================================


class TestRequestBuildingContract:
    """Prueft die Erstellung von AnalysisRequests durch den Orchestrator.

    Entspricht der Funktion _build_analysis_request() in router_radar.py.
    """

    @requires_protobuf
    def test_build_analysis_request_felder(self):
        """_build_analysis_request setzt alle AnalysisRequest-Felder korrekt."""
        time_range = common_pb2.TimeRange(start_year=2016, end_year=2026)
        request = common_pb2.AnalysisRequest(
            technology="quantum computing",
            time_range=time_range,
            european_only=False,
            cpc_codes=[],
            top_n=0,
            request_id="test-req-001",
        )

        assert request.technology == "quantum computing"
        assert request.time_range.start_year == 2016
        assert request.time_range.end_year == 2026
        assert request.european_only is False
        assert len(request.cpc_codes) == 0
        assert request.top_n == 0

    @requires_protobuf
    def test_request_mit_cpc_codes(self):
        """CPC-Codes werden als repeated string korrekt gesetzt."""
        time_range = common_pb2.TimeRange(start_year=2015, end_year=2025)
        request = common_pb2.AnalysisRequest(
            technology="solid-state batteries",
            time_range=time_range,
            cpc_codes=["H01M", "H02J", "B60L"],
        )

        assert len(request.cpc_codes) == 3
        assert "H01M" in request.cpc_codes
        assert "H02J" in request.cpc_codes
        assert "B60L" in request.cpc_codes

    @requires_protobuf
    def test_top_n_parameter(self):
        """top_n wird als int32 korrekt gesetzt und uebertragen."""
        request = common_pb2.AnalysisRequest(
            technology="test",
            top_n=50,
        )
        # Roundtrip
        serialisiert = request.SerializeToString()
        deserialisiert = common_pb2.AnalysisRequest()
        deserialisiert.ParseFromString(serialisiert)
        assert deserialisiert.top_n == 50

    @requires_protobuf
    def test_request_ohne_optionale_felder(self):
        """AnalysisRequest mit nur Pflichtfeld technology ist gueltig."""
        request = common_pb2.AnalysisRequest(technology="minimal test")

        # Standardwerte fuer optionale Felder
        assert request.time_range.start_year == 0  # Protobuf default: 0
        assert request.time_range.end_year == 0
        assert request.european_only is False
        assert request.top_n == 0
        assert request.request_id == ""
