-- Instruments lacking an accountable minister and/or responsible official.
-- A gap is missing sourced edges — not a finding of fault.
-- Safe to re-run: CREATE OR REPLACE VIEW.

CREATE OR REPLACE VIEW v_accountability_chain_completeness AS
SELECT
    i.id,
    i.slug,
    i.title,
    i.instrument_type,
    i.agency_id,
    a.slug AS agency_slug,
    a.name AS agency_name,
    i.announced_on,
    i.commenced_on,
    i.source,
    i.source_url,
    EXISTS (
        SELECT 1 FROM instrument_links il
        WHERE il.instrument_id = i.id AND il.link_kind = 'accountable_for'
    ) AS has_accountable_minister,
    EXISTS (
        SELECT 1 FROM instrument_links il
        WHERE il.instrument_id = i.id AND il.link_kind = 'responsible_official'
    ) AS has_responsible_official,
    (
        NOT EXISTS (
            SELECT 1 FROM instrument_links il
            WHERE il.instrument_id = i.id AND il.link_kind = 'accountable_for'
        )
        OR NOT EXISTS (
            SELECT 1 FROM instrument_links il
            WHERE il.instrument_id = i.id AND il.link_kind = 'responsible_official'
        )
    ) AS chain_incomplete
FROM instruments i
LEFT JOIN agencies a ON a.id = i.agency_id;
