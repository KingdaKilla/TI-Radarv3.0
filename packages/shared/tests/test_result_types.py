"""Tests fuer shared.domain.result_types — slotted dataclasses."""
import pytest
from shared.domain.result_types import (
    ActorScore,
    CountryCount,
    CpcCount,
    FundingYear,
    TimeSeriesEntry,
    YearCount,
)


class TestYearCount:
    def test_creation(self):
        yc = YearCount(year=2020, count=150)
        assert yc.year == 2020
        assert yc.count == 150

    def test_frozen(self):
        yc = YearCount(year=2020, count=150)
        with pytest.raises(AttributeError):
            yc.year = 2021

    def test_slots_no_dict(self):
        yc = YearCount(year=2020, count=150)
        assert not hasattr(yc, "__dict__")


class TestCountryCount:
    def test_creation(self):
        cc = CountryCount(country="DE", count=500)
        assert cc.country == "DE"
        assert cc.count == 500


class TestCpcCount:
    def test_creation(self):
        cpc = CpcCount(code="H04W", description="Wireless", count=1200)
        assert cpc.code == "H04W"


class TestFundingYear:
    def test_creation(self):
        fy = FundingYear(year=2022, funding=1_500_000.50, count=12)
        assert fy.funding == 1_500_000.50


class TestTimeSeriesEntry:
    def test_defaults(self):
        ts = TimeSeriesEntry(year=2020)
        assert ts.patents == 0
        assert ts.projects == 0
        assert ts.publications == 0
        assert ts.funding_eur == 0.0


class TestActorScore:
    def test_creation(self):
        a = ActorScore(name="SIEMENS AG", country_code="DE", patent_count=500, project_count=30, share=0.12)
        assert a.name == "SIEMENS AG"

    def test_total_property(self):
        a = ActorScore(name="TEST", country_code="", patent_count=100, project_count=50, share=0.0)
        assert a.total == 150
