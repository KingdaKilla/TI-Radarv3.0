"""Pytest-Fixtures fuer Integrations-Tests mit PostgreSQL Testcontainer.

Stellt folgende Session-scoped Fixtures bereit:
- ``postgres_container``: laufender PostgreSQL 17-Testcontainer
- ``db_pool``: asyncpg Connection-Pool gegen den Container
- ``populated_db``: Pool mit vorab eingefuegten Testdaten

Ablauf:
1. PostgreSQL 17-Container starten (testcontainers-python)
2. Extensions anlegen (001_extensions.sql)
3. Schema anlegen (002_schema.sql)
4. Optimierungen *nicht* ausfuehren (003 enthaelt ALTER SYSTEM — nur in Produktion)
5. Testdaten einfuegen (populated_db)

Hinweis: Die materialized Views aus 002_schema.sql setzen Daten in den
Basis-Tabellen voraus. Daher werden sie *nach* dem Einfuegen der
Testdaten per REFRESH aktualisiert (nur dann nicht-leer).
"""

from __future__ import annotations

import asyncio
import datetime
import pathlib
import re

import asyncpg
import pytest
import pytest_asyncio

# ---------------------------------------------------------------------------
# Pfade zu den SQL-Init-Skripten
# ---------------------------------------------------------------------------

_REPO_ROOT = pathlib.Path(__file__).parent.parent.parent
_SQL_DIR = _REPO_ROOT / "database" / "sql"

_SQL_001_EXTENSIONS = _SQL_DIR / "001_extensions.sql"
_SQL_002_SCHEMA = _SQL_DIR / "002_schema.sql"
# 003 enthaelt nur ALTER SYSTEM — wird beim Test uebersprungen
# 004 enthaelt nur Query-Beispiele — wird beim Test uebersprungen


# ---------------------------------------------------------------------------
# Hilfsfunktionen
# ---------------------------------------------------------------------------


def _strip_alter_system(sql: str) -> str:
    """Entfernt ALTER SYSTEM-Anweisungen aus dem SQL.

    ALTER SYSTEM erfordert Superuser und persistiert in postgresql.auto.conf.
    In Testcontainern nicht noetig; runtime-Parameter werden ohnehin ignoriert.
    """
    return re.sub(r"ALTER SYSTEM SET[^;]+;", "", sql, flags=re.IGNORECASE | re.DOTALL)


def _strip_mv_with_data(sql: str) -> str:
    """Ersetzt 'WITH DATA' durch 'WITH NO DATA' bei Materialized Views.

    Die MVs greifen auf Basis-Tabellen zu, die beim Schema-Aufbau noch leer
    sind. 'WITH NO DATA' verhindert einen Fehler beim initialen CREATE.
    Die MVs werden in 'populated_db' nach dem Einfuegen der Testdaten
    explizit per REFRESH befuellt.
    """
    return re.sub(
        r"\bWITH DATA\b",
        "WITH NO DATA",
        sql,
        flags=re.IGNORECASE,
    )


async def _execute_sql_file(conn: asyncpg.Connection, path: pathlib.Path) -> None:
    """Fuehrt eine SQL-Datei als einzelnen Block aus.

    Semikolon-getrenntes Ausfuehren wuerde bei DO $$...$$-Bloecken versagen,
    da Semikolons im PL/pgSQL-Body vorkommen. asyncpg akzeptiert den gesamten
    Block wenn er keinen Rueckgabewert hat.
    """
    raw_sql = path.read_text(encoding="utf-8")
    cleaned = _strip_alter_system(raw_sql)
    cleaned = _strip_mv_with_data(cleaned)
    await conn.execute(cleaned)


# ---------------------------------------------------------------------------
# Session-scoped: PostgreSQL Container
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def postgres_container():
    """Startet einen PostgreSQL 17-Testcontainer fuer die gesamte Test-Session.

    Verwendet testcontainers-python. Der Container wird nach der Session
    automatisch gestoppt und geloescht.

    Yields:
        testcontainers.postgres.PostgresContainer-Instanz mit laufendem PG17.
    """
    from testcontainers.postgres import PostgresContainer

    container = PostgresContainer(
        image="pgvector/pgvector:pg17",
        username="ti_test",
        password="ti_test_password",
        dbname="ti_radar_test",
        # Port 0 = beliebiger freier Port auf dem Host
        port=5432,
    )

    # Zusaetzliche PostgreSQL-Konfiguration fuer Tests
    container.with_env("POSTGRES_INITDB_ARGS", "--encoding=UTF8 --locale=C")

    with container as pg:
        yield pg


# ---------------------------------------------------------------------------
# Session-scoped: asyncpg Pool mit Schema-Aufbau
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture(scope="session")
async def db_pool(postgres_container):
    """Erstellt einen asyncpg Connection-Pool und baut das vollstaendige Schema auf.

    Fuehrt in Reihenfolge aus:
    1. 001_extensions.sql — pg_trgm, vector, uuid-ossp, unaccent
    2. 002_schema.sql    — alle Tabellen, Indexes, Trigger, Materialized Views

    Der Pool wird fuer alle Integrations-Tests der Session wiederverwendet.

    Yields:
        asyncpg.Pool mit aufgebautem Schema, aber ohne Testdaten.
    """
    dsn = postgres_container.get_connection_url()
    # testcontainers liefert SQLAlchemy-DSN; asyncpg benoetigt postgres:// Schema
    dsn = dsn.replace("postgresql+psycopg2://", "postgresql://")
    dsn = dsn.replace("postgresql+asyncpg://", "postgresql://")

    pool = await asyncpg.create_pool(
        dsn=dsn,
        min_size=1,
        max_size=5,
        command_timeout=60.0,
    )
    async with pool.acquire() as conn:
        if _SQL_001_EXTENSIONS.exists():
            await _execute_sql_file(conn, _SQL_001_EXTENSIONS)
        if _SQL_002_SCHEMA.exists():
            await _execute_sql_file(conn, _SQL_002_SCHEMA)

    yield pool
    await pool.close()


# ---------------------------------------------------------------------------
# Session-scoped: Testdaten einfuegen und MVs refreshen
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture(scope="session")
async def populated_db(db_pool):
    """Befuellt den Pool mit repraesentativen Testdaten.

    Fuegt in alle relevanten Schemas Beispieldatensaetze ein:
    - patent_schema.patents (inkl. Trigger fuer search_vector)
    - patent_schema.patent_cpc
    - cordis_schema.projects
    - cordis_schema.organizations

    Anschliessend werden alle Materialized Views per REFRESH befuellt,
    sodass MV-basierte Queries in Tests funktionieren.

    Yields:
        asyncpg.Pool mit Schema + Testdaten + befuellten MVs.
    """

    async def _insert() -> None:
        async with db_pool.acquire() as conn:
            async with conn.transaction():
                await _insert_cpc_descriptions(conn)
                await _insert_test_patents(conn)
                await _insert_test_cordis_data(conn)

        # Materialized Views refreshen (benoetigt eigene Transaktion)
        async with db_pool.acquire() as conn:
            await _refresh_materialized_views(conn)

    await _insert()
    yield db_pool


async def _insert_cpc_descriptions(conn: asyncpg.Connection) -> None:
    """Fuegt statische CPC-Code-Beschreibungen ein (Referenzdaten)."""
    await conn.executemany(
        """
        INSERT INTO patent_schema.cpc_descriptions
            (code, section, class_code, description_en, description_de)
        VALUES ($1, $2, $3, $4, $5)
        ON CONFLICT (code) DO NOTHING
        """,
        [
            ("H01M", "H", "H01", "Electrochemical processes or apparatus", "Elektrochemische Verfahren"),
            ("H04W", "H", "H04", "Wireless communication networks", "Drahtlose Kommunikationsnetzwerke"),
            ("C12N", "C", "C12", "Microorganisms or enzymes", "Mikroorganismen oder Enzyme"),
            ("G06F", "G", "G06", "Electric digital data processing", "Elektrische digitale Datenverarbeitung"),
            ("B60L", "B", "B60", "Vehicles in general", "Fahrzeuge allgemein"),
            ("H02J", "H", "H02", "Circuit arrangements for electric power supply", "Schaltungen fuer Stromversorgung"),
        ],
    )


async def _insert_test_patents(conn: asyncpg.Connection) -> None:
    """Fuegt Testpatente mit CPC-Codes und Anmelderlaendern ein.

    Die Trigger auf patent_schema.patents befuellen automatisch:
    - search_vector (aus title + cpc_codes)
    - publication_year (aus publication_date)
    """
    # Testpatente: Quantum Computing (DE, FR) + Solid State Batteries (DE, US, JP)
    await conn.executemany(
        """
        INSERT INTO patent_schema.patents (
            publication_number, country, doc_number, kind,
            title, publication_date, publication_year, family_id,
            applicant_names, applicant_countries, cpc_codes
        ) VALUES ($1, $2, $3, $4, $5, $6, EXTRACT(YEAR FROM $6::DATE)::SMALLINT, $7, $8, $9, $10)
        ON CONFLICT (publication_number, publication_year) DO NOTHING
        """,
        [
            # Quantum Computing Patente
            (
                "DE102020001001A1", "DE", "102020001001", "A1",
                "Quantum computing error correction system",
                datetime.date(2020, 1, 15), "FAM001",
                "Quantum Systems GmbH",
                ["DE"], ["G06F", "H04W"],
            ),
            (
                "DE102020002001A1", "DE", "102020002001", "A1",
                "Quantum entanglement based communication device",
                datetime.date(2020, 3, 22), "FAM002",
                "TU Berlin",
                ["DE", "FR"], ["H04W", "G06F"],
            ),
            (
                "FR3100001A1", "FR", "3100001", "A1",
                "Quantum computing processor with error mitigation",
                datetime.date(2021, 6, 10), "FAM003",
                "CNRS",
                ["FR"], ["G06F"],
            ),
            (
                "DE102021001001A1", "DE", "102021001001", "A1",
                "Topological quantum computing architecture",
                datetime.date(2021, 9, 5), "FAM004",
                "Max Planck Institut",
                ["DE"], ["G06F", "H01M"],
            ),
            # Solid State Battery Patente
            (
                "DE102020003001A1", "DE", "102020003001", "A1",
                "Solid state battery with ceramic electrolyte",
                datetime.date(2020, 2, 28), "FAM010",
                "BASF SE",
                ["DE"], ["H01M", "H02J"],
            ),
            (
                "DE102021002001A1", "DE", "102021002001", "A1",
                "Solid state lithium ion battery manufacturing process",
                datetime.date(2021, 4, 14), "FAM011",
                "BASF SE",
                ["DE", "US"], ["H01M"],
            ),
            (
                "FR3110001A1", "FR", "3110001", "A1",
                "Solid state battery for electric vehicle applications",
                datetime.date(2021, 11, 30), "FAM012",
                "Renault SA",
                ["FR"], ["H01M", "B60L"],
            ),
            (
                "DE102022001001A1", "DE", "102022001001", "A1",
                "Quantum computing qubit fabrication method",
                datetime.date(2022, 1, 20), "FAM005",
                "Infineon Technologies AG",
                ["DE"], ["G06F"],
            ),
            (
                "DE102022002001A1", "DE", "102022002001", "A1",
                "Quantum computing quantum computing algorithm optimization",
                datetime.date(2022, 7, 11), "FAM006",
                "Siemens AG",
                ["DE"], ["G06F", "H04W"],
            ),
            (
                "FR3120001A1", "FR", "3120001", "A1",
                "Quantum computing neural network accelerator",
                datetime.date(2022, 12, 1), "FAM007",
                "Airbus SE",
                ["FR", "DE"], ["G06F"],
            ),
        ],
    )

    # Patent-CPC-Verbindungen normalisiert eintragen
    await conn.executemany(
        """
        INSERT INTO patent_schema.patent_cpc (patent_id, cpc_code, pub_year)
        SELECT p.id, $2, p.publication_year
        FROM patent_schema.patents p
        WHERE p.publication_number = $1
        ON CONFLICT (patent_id, cpc_code, pub_year) DO NOTHING
        """,
        [
            ("DE102020001001A1", "G06F"),
            ("DE102020001001A1", "H04W"),
            ("DE102020002001A1", "H04W"),
            ("DE102020002001A1", "G06F"),
            ("FR3100001A1", "G06F"),
            ("DE102021001001A1", "G06F"),
            ("DE102021001001A1", "H01M"),
            ("DE102020003001A1", "H01M"),
            ("DE102020003001A1", "H02J"),
            ("DE102021002001A1", "H01M"),
            ("FR3110001A1", "H01M"),
            ("FR3110001A1", "B60L"),
            ("DE102022001001A1", "G06F"),
            ("DE102022002001A1", "G06F"),
            ("DE102022002001A1", "H04W"),
            ("FR3120001A1", "G06F"),
        ],
    )


async def _insert_test_cordis_data(conn: asyncpg.Connection) -> None:
    """Fuegt CORDIS-Testprojekte und -Organisationen ein."""
    # CORDIS-Projekte
    await conn.executemany(
        """
        INSERT INTO cordis_schema.projects (
            id, rcn, framework, acronym, title, objective, keywords,
            start_date, end_date, status,
            total_cost, ec_max_contribution, funding_scheme
        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)
        ON CONFLICT (id) DO NOTHING
        """,
        [
            # Quantum Computing Projekte
            (
                100001, 10001, "H2020", "QUANTCOMP",
                "Quantum computing for industrial applications",
                "Research on quantum computing algorithms for optimization in industrial contexts "
                "using superconducting qubits and error correction.",
                "quantum computing optimization qubits",
                datetime.date(2020, 1, 1), datetime.date(2023, 12, 31), "CLOSED",
                3_500_000.00, 2_800_000.00, "RIA",
            ),
            (
                100002, 10002, "H2020", "QNETWORK",
                "Quantum network communication protocols",
                "Development of quantum communication protocols for secure data transmission "
                "using quantum entanglement.",
                "quantum networking entanglement communication",
                datetime.date(2020, 6, 1), datetime.date(2024, 5, 31), "CLOSED",
                2_100_000.00, 1_680_000.00, "IA",
            ),
            (
                100003, 10003, "HORIZON", "QSOFTWARE",
                "Quantum computing software stack",
                "Open-source software toolkit for quantum computing algorithm development.",
                "quantum computing software algorithms",
                datetime.date(2021, 3, 1), datetime.date(2025, 2, 28), "ACTIVE",
                4_200_000.00, 3_360_000.00, "RIA",
            ),
            # Solid State Battery Projekte
            (
                200001, 20001, "H2020", "SOLIDBAT",
                "Solid state battery technology for electric vehicles",
                "Development of next-generation solid state batteries with ceramic electrolytes "
                "for electric vehicle applications.",
                "solid state battery electrolyte electric vehicle",
                datetime.date(2020, 4, 1), datetime.date(2023, 9, 30), "CLOSED",
                5_000_000.00, 4_000_000.00, "IA",
            ),
            (
                200002, 20002, "HORIZON", "NEXTBAT",
                "Next generation battery manufacturing process",
                "Scalable manufacturing processes for solid state lithium batteries.",
                "battery manufacturing solid state lithium",
                datetime.date(2021, 9, 1), datetime.date(2025, 8, 31), "ACTIVE",
                3_800_000.00, 3_040_000.00, "RIA",
            ),
            (
                200003, 20003, "H2020", "EVBATTERY",
                "Electric vehicle battery performance optimization",
                "Research on performance optimization for solid state batteries in electric vehicles.",
                "battery performance electric vehicle solid state",
                datetime.date(2019, 1, 1), datetime.date(2022, 12, 31), "CLOSED",
                2_500_000.00, 2_000_000.00, "CSA",
            ),
        ],
    )

    # Organisationen (Konsortien)
    await conn.executemany(
        """
        INSERT INTO cordis_schema.organizations (
            organisation_id, project_id, name, short_name,
            country, city, role, activity_type, sme, ec_contribution
        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
        """,
        [
            # QUANTCOMP (100001)
            (1001, 100001, "Technische Universitat Berlin", "TU Berlin", "DE", "Berlin", "coordinator", "HES", False, 1_000_000.00),
            (1002, 100001, "CNRS", "CNRS", "FR", "Paris", "participant", "REC", False, 900_000.00),
            (1003, 100001, "IBM Research GmbH", "IBM", "DE", "Stuttgart", "participant", "PRC", False, 900_000.00),
            # QNETWORK (100002)
            (1004, 100002, "Fraunhofer-Gesellschaft", "Fraunhofer", "DE", "Munich", "coordinator", "REC", False, 700_000.00),
            (1005, 100002, "Airbus SE", "Airbus", "FR", "Toulouse", "participant", "PRC", False, 630_000.00),
            (1006, 100002, "Quantum Networks Ltd", "QNL", "GB", "London", "participant", "PRC", True, 350_000.00),
            # QSOFTWARE (100003)
            (1007, 100003, "Technische Universitat Berlin", "TU Berlin", "DE", "Berlin", "coordinator", "HES", False, 1_200_000.00),
            (1008, 100003, "CNRS", "CNRS", "FR", "Paris", "participant", "REC", False, 960_000.00),
            (1009, 100003, "Infineon Technologies AG", "Infineon", "DE", "Munich", "participant", "PRC", False, 800_000.00),
            (1010, 100003, "QuTech BV", "QuTech", "NL", "Delft", "participant", "REC", False, 400_000.00),
            # SOLIDBAT (200001)
            (2001, 200001, "BASF SE", "BASF", "DE", "Ludwigshafen", "coordinator", "PRC", False, 1_600_000.00),
            (2002, 200001, "Renault SA", "Renault", "FR", "Paris", "participant", "PRC", False, 1_200_000.00),
            (2003, 200001, "Politecnico di Milano", "PoliMi", "IT", "Milan", "participant", "HES", False, 800_000.00),
            (2004, 200001, "BatteryTech GmbH", "BT", "DE", "Hamburg", "participant", "PRC", True, 400_000.00),
            # NEXTBAT (200002)
            (2005, 200002, "BASF SE", "BASF", "DE", "Ludwigshafen", "coordinator", "PRC", False, 1_300_000.00),
            (2006, 200002, "Volkswagen AG", "VW", "DE", "Wolfsburg", "participant", "PRC", False, 900_000.00),
            (2007, 200002, "CEA", "CEA", "FR", "Grenoble", "participant", "REC", False, 540_000.00),
            (2008, 200002, "Politecnico di Milano", "PoliMi", "IT", "Milan", "participant", "HES", False, 300_000.00),
            # EVBATTERY (200003)
            (2009, 200003, "Fraunhofer-Gesellschaft", "Fraunhofer", "DE", "Munich", "coordinator", "REC", False, 800_000.00),
            (2010, 200003, "Renault SA", "Renault", "FR", "Paris", "participant", "PRC", False, 700_000.00),
            (2011, 200003, "CNRS", "CNRS", "FR", "Paris", "participant", "REC", False, 500_000.00),
        ],
    )


async def _refresh_materialized_views(conn: asyncpg.Connection) -> None:
    """Refresht alle Materialized Views nach dem Einfuegen der Testdaten.

    REFRESH MATERIALIZED VIEW (ohne CONCURRENTLY) blockiert Reads kurz,
    ist aber in Tests kein Problem. CONCURRENTLY wuerde eine UNIQUE-Index
    voraussetzen, der bei 'WITH NO DATA' noch nicht befuellt ist.
    """
    views = [
        "cross_schema.mv_patent_counts_by_cpc_year",
        "cross_schema.mv_yearly_tech_counts",
        "cross_schema.mv_top_applicants",
        "cross_schema.mv_patent_country_distribution",
        "cross_schema.mv_project_counts_by_year",
        "cross_schema.mv_cordis_country_pairs",
        "cross_schema.mv_top_cordis_orgs",
        "cross_schema.mv_funding_by_instrument",
        # mv_cpc_cooccurrence erfordert ausreichend Daten fuer Top-200-Berechnung
        "cross_schema.mv_cpc_cooccurrence",
    ]
    for view in views:
        await conn.execute(f"REFRESH MATERIALIZED VIEW {view}")
