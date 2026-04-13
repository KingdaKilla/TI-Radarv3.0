-- ==========================================================================
-- Hotfix: Fehlende GRANT-Statements nach Dump-Restore
-- Ausfuehren als tip_admin:
--   docker exec -i ti-radar-db psql -U tip_admin -d ti_radar < fix_grants.sql
-- ==========================================================================

-- --------------------------------------------------------------------------
-- Schema USAGE grants
-- --------------------------------------------------------------------------

GRANT USAGE ON SCHEMA patent_schema  TO svc_landscape, svc_maturity, svc_competitive,
    svc_cpc_flow, svc_geographic, svc_temporal, svc_tech_cluster, svc_actor_type,
    svc_patent_grant, svc_export, svc_entity_resolution,
    importer_epo, tip_readonly;

GRANT USAGE ON SCHEMA cordis_schema  TO svc_landscape, svc_competitive, svc_funding,
    svc_geographic, svc_research_impact, svc_temporal, svc_tech_cluster, svc_actor_type,
    svc_euroscivoc, svc_publication, svc_export, svc_entity_resolution,
    importer_cordis, tip_readonly;

GRANT USAGE ON SCHEMA cross_schema   TO svc_landscape, svc_maturity, svc_competitive,
    svc_funding, svc_cpc_flow, svc_geographic, svc_temporal, svc_tech_cluster,
    svc_actor_type, svc_patent_grant, svc_euroscivoc, svc_export,
    importer_epo, importer_cordis, tip_readonly;

GRANT USAGE ON SCHEMA research_schema TO svc_research_impact, svc_landscape, svc_export,
    tip_readonly;

GRANT USAGE ON SCHEMA entity_schema  TO svc_competitive, svc_geographic, svc_temporal,
    svc_actor_type, svc_entity_resolution, svc_export, tip_readonly;

GRANT USAGE ON SCHEMA export_schema  TO svc_export, svc_landscape, svc_maturity,
    svc_competitive, svc_funding, svc_cpc_flow, svc_geographic,
    svc_research_impact, svc_temporal, tip_readonly;

-- --------------------------------------------------------------------------
-- Table-level READ grants
-- --------------------------------------------------------------------------

-- UC1 Landscape
GRANT SELECT ON ALL TABLES IN SCHEMA patent_schema TO svc_landscape;
GRANT SELECT ON ALL TABLES IN SCHEMA cordis_schema TO svc_landscape;
GRANT SELECT ON ALL TABLES IN SCHEMA cross_schema TO svc_landscape;
GRANT SELECT ON ALL TABLES IN SCHEMA research_schema TO svc_landscape;
GRANT INSERT, UPDATE, DELETE ON research_schema.openaire_cache TO svc_landscape;
GRANT USAGE ON ALL SEQUENCES IN SCHEMA research_schema TO svc_landscape;

-- UC2 Maturity
GRANT SELECT ON ALL TABLES IN SCHEMA patent_schema TO svc_maturity;
GRANT SELECT ON ALL TABLES IN SCHEMA cross_schema TO svc_maturity;

-- UC3 Competitive
GRANT SELECT ON ALL TABLES IN SCHEMA patent_schema TO svc_competitive;
GRANT SELECT ON ALL TABLES IN SCHEMA cordis_schema TO svc_competitive;
GRANT SELECT ON ALL TABLES IN SCHEMA cross_schema TO svc_competitive;
GRANT SELECT ON ALL TABLES IN SCHEMA entity_schema TO svc_competitive;

-- UC4 Funding
GRANT SELECT ON ALL TABLES IN SCHEMA cordis_schema TO svc_funding;
GRANT SELECT ON ALL TABLES IN SCHEMA cross_schema TO svc_funding;

-- UC5 CPC Flow
GRANT SELECT ON ALL TABLES IN SCHEMA patent_schema TO svc_cpc_flow;
GRANT SELECT ON ALL TABLES IN SCHEMA cross_schema TO svc_cpc_flow;

-- UC6 Geographic
GRANT SELECT ON ALL TABLES IN SCHEMA patent_schema TO svc_geographic;
GRANT SELECT ON ALL TABLES IN SCHEMA cordis_schema TO svc_geographic;
GRANT SELECT ON ALL TABLES IN SCHEMA cross_schema TO svc_geographic;
GRANT SELECT ON ALL TABLES IN SCHEMA entity_schema TO svc_geographic;

-- UC7 Research Impact
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA research_schema TO svc_research_impact;
GRANT USAGE ON ALL SEQUENCES IN SCHEMA research_schema TO svc_research_impact;
GRANT SELECT ON ALL TABLES IN SCHEMA cordis_schema TO svc_research_impact;

-- UC8 Temporal
GRANT SELECT ON ALL TABLES IN SCHEMA patent_schema TO svc_temporal;
GRANT SELECT ON ALL TABLES IN SCHEMA cordis_schema TO svc_temporal;
GRANT SELECT ON ALL TABLES IN SCHEMA cross_schema TO svc_temporal;

-- UC9 Tech Cluster
GRANT SELECT ON ALL TABLES IN SCHEMA patent_schema TO svc_tech_cluster;
GRANT SELECT ON ALL TABLES IN SCHEMA cordis_schema TO svc_tech_cluster;
GRANT SELECT ON ALL TABLES IN SCHEMA cross_schema TO svc_tech_cluster;

-- UC10 EuroSciVoc
GRANT SELECT ON ALL TABLES IN SCHEMA cordis_schema TO svc_euroscivoc;
GRANT SELECT ON ALL TABLES IN SCHEMA cross_schema TO svc_euroscivoc;

-- UC11 Actor Type
GRANT SELECT ON ALL TABLES IN SCHEMA patent_schema TO svc_actor_type;
GRANT SELECT ON ALL TABLES IN SCHEMA cordis_schema TO svc_actor_type;
GRANT SELECT ON ALL TABLES IN SCHEMA cross_schema TO svc_actor_type;
GRANT SELECT ON ALL TABLES IN SCHEMA entity_schema TO svc_actor_type;
GRANT INSERT, UPDATE ON entity_schema.gleif_cache TO svc_actor_type;

-- UC12 Patent Grant
GRANT SELECT ON ALL TABLES IN SCHEMA patent_schema TO svc_patent_grant;
GRANT SELECT ON ALL TABLES IN SCHEMA cross_schema TO svc_patent_grant;

-- UC-C Publication
GRANT SELECT ON ALL TABLES IN SCHEMA cordis_schema TO svc_publication;

-- Export service
GRANT SELECT ON ALL TABLES IN SCHEMA patent_schema TO svc_export;
GRANT SELECT ON ALL TABLES IN SCHEMA cordis_schema TO svc_export;
GRANT SELECT ON ALL TABLES IN SCHEMA cross_schema TO svc_export;
GRANT SELECT ON ALL TABLES IN SCHEMA research_schema TO svc_export;
GRANT SELECT ON ALL TABLES IN SCHEMA entity_schema TO svc_export;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA export_schema TO svc_export;
GRANT USAGE ON ALL SEQUENCES IN SCHEMA export_schema TO svc_export;

-- Entity resolution
GRANT SELECT ON ALL TABLES IN SCHEMA patent_schema TO svc_entity_resolution;
GRANT SELECT ON ALL TABLES IN SCHEMA cordis_schema TO svc_entity_resolution;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA entity_schema TO svc_entity_resolution;
GRANT USAGE ON ALL SEQUENCES IN SCHEMA entity_schema TO svc_entity_resolution;

-- Importers
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA patent_schema TO importer_epo;
GRANT USAGE ON ALL SEQUENCES IN SCHEMA patent_schema TO importer_epo;
GRANT SELECT, INSERT, UPDATE ON cross_schema.import_log TO importer_epo;
GRANT USAGE ON SEQUENCE cross_schema.import_log_id_seq TO importer_epo;

GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA cordis_schema TO importer_cordis;
GRANT USAGE ON ALL SEQUENCES IN SCHEMA cordis_schema TO importer_cordis;
GRANT SELECT, INSERT, UPDATE ON cross_schema.import_log TO importer_cordis;
GRANT USAGE ON SEQUENCE cross_schema.import_log_id_seq TO importer_cordis;

-- Read-only
GRANT SELECT ON ALL TABLES IN SCHEMA patent_schema TO tip_readonly;
GRANT SELECT ON ALL TABLES IN SCHEMA cordis_schema TO tip_readonly;
GRANT SELECT ON ALL TABLES IN SCHEMA cross_schema TO tip_readonly;
GRANT SELECT ON ALL TABLES IN SCHEMA research_schema TO tip_readonly;
GRANT SELECT ON ALL TABLES IN SCHEMA entity_schema TO tip_readonly;
GRANT SELECT ON ALL TABLES IN SCHEMA export_schema TO tip_readonly;

-- Ergebnis pruefen
DO $$ BEGIN RAISE NOTICE 'Alle GRANT-Statements erfolgreich ausgefuehrt.'; END $$;
