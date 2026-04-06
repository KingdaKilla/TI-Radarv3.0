-- =============================================================================
-- 006_citation_schema.sql — Patent-Zitationsnetzwerk fuer Forward/Backward Citation Analysis
-- =============================================================================
-- UC-F: Zitations-Analyse
--
-- Speichert Zitationsbeziehungen zwischen Patenten, extrahiert aus EPO DOCDB XML
-- (<references-cited> Element). Ermoeglicht Forward- und Backward-Citation-Analyse
-- zur Identifikation von Schluesselpatenten und Technologie-Trends.
--
-- Abhaengigkeiten:
--   - patent_schema (aus 002_schema.sql) muss existieren
--   - patent_schema.patents Tabelle als Referenz fuer patent IDs
-- =============================================================================

-- Zitationstabelle: Welches Patent zitiert welches andere Patent
CREATE TABLE IF NOT EXISTS patent_schema.patent_citations (
    citing_patent TEXT NOT NULL,           -- Zitierende Patentpublikation (z.B. EP1234567A1)
    cited_patent TEXT NOT NULL,            -- Zitiertes Patent
    citation_category TEXT,               -- 'X' (besonders relevant), 'Y' (relevant in Kombination), 'A' (Stand der Technik)
    cited_phase TEXT,                      -- 'search' (Rechercheamt), 'examination', 'opposition'
    citing_year INTEGER,                   -- Publikationsjahr des zitierenden Patents
    PRIMARY KEY (citing_patent, cited_patent)
);

-- Index fuer Backward-Citation-Abfragen (welche Patente zitieren dieses Patent?)
CREATE INDEX IF NOT EXISTS idx_citations_cited
    ON patent_schema.patent_citations (cited_patent);

-- Index fuer zeitliche Analysen
CREATE INDEX IF NOT EXISTS idx_citations_year
    ON patent_schema.patent_citations (citing_year);

-- Index fuer Kategorie-Filter (X/Y/A Relevanz-Stufen)
CREATE INDEX IF NOT EXISTS idx_citations_category
    ON patent_schema.patent_citations (citation_category)
    WHERE citation_category IS NOT NULL;

-- Kommentar fuer Dokumentation
COMMENT ON TABLE patent_schema.patent_citations IS
    'Patent-Zitationsnetzwerk — Forward/Backward Citations aus EPO DOCDB XML (UC-F)';
COMMENT ON COLUMN patent_schema.patent_citations.citation_category IS
    'EPO-Kategorie: X=besonders relevant, Y=relevant in Kombination, A=Stand der Technik, D=zitiert im Verfahren';
COMMENT ON COLUMN patent_schema.patent_citations.cited_phase IS
    'Verfahrensphase: search, examination, opposition';

-- TODO: Materialized View fuer Top-zitierte Patente pro Technologie (CPC-gefiltert)
-- Wird nach Import + Enrichment erstellt, z.B.:
--
-- CREATE MATERIALIZED VIEW IF NOT EXISTS patent_schema.mv_top_cited_patents AS
-- SELECT
--     pc.cited_patent,
--     p.title,
--     p.applicant_names,
--     p.publication_year,
--     COUNT(*) AS forward_citation_count,
--     MODE() WITHIN GROUP (ORDER BY pc.citation_category) AS dominant_category
-- FROM patent_schema.patent_citations pc
-- JOIN patent_schema.patents p ON p.publication_number = pc.cited_patent
-- GROUP BY pc.cited_patent, p.title, p.applicant_names, p.publication_year
-- HAVING COUNT(*) >= 5
-- ORDER BY forward_citation_count DESC;
