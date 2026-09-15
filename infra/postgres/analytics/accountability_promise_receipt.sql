-- Promise / assurance / taken-on-notice claims joined to instruments and outcomes.
-- Hansard spans are citations, not verdicts.
-- Safe to re-run: CREATE OR REPLACE VIEW.

CREATE OR REPLACE VIEW v_accountability_promise_receipt AS
SELECT
    c.id AS claim_id,
    c.claim_type,
    c.text_span,
    c.made_on,
    c.speaker_name,
    p.slug AS person_slug,
    p.name AS person_name,
    h.slug AS hearing_slug,
    h.title AS hearing_title,
    h.held_on AS hearing_held_on,
    i.id AS instrument_id,
    i.slug AS instrument_slug,
    i.title AS instrument_title,
    i.instrument_type,
    o.id AS outcome_id,
    o.outcome_type,
    o.signal,
    o.occurred_on AS outcome_on,
    o.source AS outcome_source
FROM claims c
LEFT JOIN people p ON p.id = c.person_id
LEFT JOIN hearings h ON h.id = c.hearing_id
LEFT JOIN instruments i ON i.id = c.instrument_id
LEFT JOIN outcomes o ON o.instrument_id = i.id
WHERE c.claim_type IN ('promise', 'assurance', 'taken_on_notice');
