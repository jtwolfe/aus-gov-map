-- Generated from data/fixtures/seed.json by infra/postgres/render_seed.py
-- Do not edit by hand; re-run the renderer after changing the fixture.

INSERT INTO committees (id, slug, name, chamber, kind, aph_url) VALUES
    ('11111111-1111-4111-8111-111111111001', 'finance-public-administration', 'Finance and Public Administration', 'Senate', 'legislation', 'https://www.aph.gov.au/Parliamentary_Business/Committees/Senate/Finance_and_Public_Administration'),
    ('11111111-1111-4111-8111-111111111002', 'legal-constitutional-affairs', 'Legal and Constitutional Affairs', 'Senate', 'legislation', 'https://www.aph.gov.au/Parliamentary_Business/Committees/Senate/Legal_and_Constitutional_Affairs'),
    ('11111111-1111-4111-8111-111111111003', 'rural-regional-affairs-transport', 'Rural and Regional Affairs and Transport', 'Senate', 'legislation', 'https://www.aph.gov.au/Parliamentary_Business/Committees/Senate/Rural_and_Regional_Affairs_and_Transport')
ON CONFLICT (id) DO NOTHING;

INSERT INTO people (id, slug, name, role_title, party, portfolio, organisation, aph_url, bio) VALUES
    ('33333333-3333-4333-8333-333333333001', 'katy-gallagher', 'Senator the Hon Katy Gallagher', 'Minister for Finance', 'Australian Labor Party', 'Finance', 'Australian Senate', 'https://www.aph.gov.au/Senators_and_Members', 'Minister representing the Finance portfolio at Senate Estimates.'),
    ('33333333-3333-4333-8333-333333333002', 'james-paterson', 'Senator James Paterson', 'Senator', 'Liberal Party of Australia', NULL, 'Australian Senate', 'https://www.aph.gov.au/Senators_and_Members', 'Opposition senator appearing on Finance and Public Administration estimates.'),
    ('33333333-3333-4333-8333-333333333003', 'deborah-oneill', 'Senator Deborah O''Neill', 'Chair', 'Australian Labor Party', NULL, 'Senate Finance and Public Administration Legislation Committee', 'https://www.aph.gov.au/Senators_and_Members', 'Chair of the Finance and Public Administration Legislation Committee.'),
    ('33333333-3333-4333-8333-333333333004', 'paul-scarr', 'Senator Paul Scarr', 'Senator', 'Liberal National Party', NULL, 'Australian Senate', 'https://www.aph.gov.au/Senators_and_Members', 'Senator appearing on Legal and Constitutional Affairs estimates.'),
    ('33333333-3333-4333-8333-333333333005', 'glyn-davis', 'Professor Glyn Davis AC', 'Secretary', NULL, 'Prime Minister and Cabinet', 'Department of the Prime Minister and Cabinet', NULL, 'Departmental secretary appearing as an official witness.'),
    ('33333333-3333-4333-8333-333333333006', 'katherine-jones', 'Katherine Jones PSM', 'Secretary', NULL, 'Attorney-General''s', 'Attorney-General''s Department', NULL, 'Departmental secretary appearing as an official witness.'),
    ('33333333-3333-4333-8333-333333333007', 'bridget-mckenzie', 'Senator the Hon Bridget McKenzie', 'Senator', 'The Nationals', NULL, 'Australian Senate', 'https://www.aph.gov.au/Senators_and_Members', 'Senator appearing on Rural and Regional Affairs and Transport.')
ON CONFLICT (id) DO NOTHING;

INSERT INTO hearings (id, slug, committee_id, title, hearing_type, portfolio, held_on, location, source, source_url, source_key, status, summary) VALUES
    ('22222222-2222-4222-8222-222222222001', 'fpa-supp-estimates-2025-10-07', '11111111-1111-4111-8111-111111111001', 'Supplementary Budget Estimates 2025–26 — Finance and Public Administration', 'estimates', 'Prime Minister and Cabinet; Finance', '2025-10-07', 'Parliament House, Canberra', 'estimates', 'https://www.aph.gov.au/Parliamentary_Business/Senate_estimates/fpa/2025-26_Supplementary_Budget_estimates', 'estimates:fpa:2025-10-07', 'published', 'Senate Estimates examination of PM&C and Finance, including APS capability, procurement, and FOI processing.'),
    ('22222222-2222-4222-8222-222222222002', 'lca-budget-estimates-2025-03-27', '11111111-1111-4111-8111-111111111002', 'Budget Estimates 2025–26 — Legal and Constitutional Affairs', 'estimates', 'Home Affairs; Attorney-General''s', '2025-03-27', 'Parliament House, Canberra', 'estimates', 'https://www.aph.gov.au/Parliamentary_Business/Senate_estimates/legcon/2025-26_Budget_estimates', 'estimates:legcon:2025-03-27', 'published', 'Estimates for Home Affairs and Attorney-General''s, covering FOI, integrity frameworks, and legislative drafting capacity.'),
    ('22222222-2222-4222-8222-222222222003', 'rrat-regional-aviation-2024-11-18', '11111111-1111-4111-8111-111111111003', 'Inquiry hearing — Regional aviation access', 'committee', 'Infrastructure, Transport, Regional Development', '2024-11-18', 'Parliament House, Canberra', 'senate_committee', 'https://www.aph.gov.au/Parliamentary_Business/Committees/Senate/Rural_and_Regional_Affairs_and_Transport', 'senate_committee:rrat:regional-aviation:2024-11-18', 'published', 'Committee hearing on regional aviation access, community service obligations, and aerodrome funding.')
ON CONFLICT (id) DO NOTHING;

INSERT INTO hearing_people (hearing_id, person_id, role) VALUES
    ('22222222-2222-4222-8222-222222222001', '33333333-3333-4333-8333-333333333003', 'chair'),
    ('22222222-2222-4222-8222-222222222001', '33333333-3333-4333-8333-333333333001', 'minister'),
    ('22222222-2222-4222-8222-222222222001', '33333333-3333-4333-8333-333333333002', 'senator'),
    ('22222222-2222-4222-8222-222222222001', '33333333-3333-4333-8333-333333333005', 'official'),
    ('22222222-2222-4222-8222-222222222002', '33333333-3333-4333-8333-333333333004', 'senator'),
    ('22222222-2222-4222-8222-222222222002', '33333333-3333-4333-8333-333333333006', 'official'),
    ('22222222-2222-4222-8222-222222222003', '33333333-3333-4333-8333-333333333007', 'senator'),
    ('22222222-2222-4222-8222-222222222003', '33333333-3333-4333-8333-333333333004', 'senator')
ON CONFLICT DO NOTHING;

INSERT INTO topics (id, slug, name) VALUES
    ('44444444-4444-4444-8444-444444444001', 'aps-capability', 'APS capability'),
    ('44444444-4444-4444-8444-444444444002', 'procurement', 'Procurement'),
    ('44444444-4444-4444-8444-444444444003', 'foi', 'Freedom of information'),
    ('44444444-4444-4444-8444-444444444004', 'integrity', 'Integrity'),
    ('44444444-4444-4444-8444-444444444005', 'regional-aviation', 'Regional aviation')
ON CONFLICT (id) DO NOTHING;

INSERT INTO hearing_topics (hearing_id, topic_id) VALUES
    ('22222222-2222-4222-8222-222222222001', '44444444-4444-4444-8444-444444444001'),
    ('22222222-2222-4222-8222-222222222001', '44444444-4444-4444-8444-444444444002'),
    ('22222222-2222-4222-8222-222222222001', '44444444-4444-4444-8444-444444444003'),
    ('22222222-2222-4222-8222-222222222002', '44444444-4444-4444-8444-444444444003'),
    ('22222222-2222-4222-8222-222222222002', '44444444-4444-4444-8444-444444444004'),
    ('22222222-2222-4222-8222-222222222003', '44444444-4444-4444-8444-444444444005')
ON CONFLICT DO NOTHING;

INSERT INTO documents (id, hearing_id, title, doc_type, source_url, source_key, content_text, published_at, license_note) VALUES
    ('55555555-5555-4555-8555-555555555001', '22222222-2222-4222-8222-222222222001', 'Sample Official — FPA Supplementary Estimates 7 October 2025', 'hansard', 'https://www.aph.gov.au/Parliamentary_Business/Hansard', 'doc:fpa-supp-estimates-2025-10-07:hansard-sample', 'CHAIR: The committee will now examine the Department of the Prime Minister and Cabinet. Minister, welcome.

Senator GALLAGHER: Thank you, Chair. The government is happy to take questions on the public service workforce and the Finance portfolio.

Senator PATERSON: Secretary, I want to start with APS capability. How many SES roles are currently vacant across the portfolio, and what is the department doing about institutional knowledge as people leave?

Prof. DAVIS: Senator, we publish workforce metrics in the annual report. Vacancy rates move with machinery-of-government changes. We have a graduate program and a mobility scheme aimed at retaining specialist capability, particularly in procurement and evaluation.

Senator PATERSON: On procurement: the audit findings on panel arrangements suggested inconsistent documentation. Has PM&C issued new guidance to agencies?

Prof. DAVIS: We have. Finance leads the Commonwealth Procurement Rules. PM&C has circulated a reminder on conflict-of-interest declarations and record-keeping for limited tenders.

Senator GALLAGHER: If I may, the government has also funded additional training through the APS Academy on complex procurement.

Senator PATERSON: Freedom of information — the OAIC continues to report delays. What is the median time to finalise an FOI request in PM&C this financial year?

Prof. DAVIS: I will take the precise median on notice. We have reduced the backlog relative to last year, but complex requests involving cabinet-related material still take longer.

CHAIR: The committee will break and resume with Finance.', '2025-10-07', 'Fixture sample — not official Hansard. Official records © Commonwealth of Australia, typically CC BY-NC-ND.'),
    ('55555555-5555-4555-8555-555555555002', '22222222-2222-4222-8222-222222222002', 'Sample Official — LCA Budget Estimates 27 March 2025', 'hansard', 'https://www.aph.gov.au/Parliamentary_Business/Hansard', 'doc:lca-budget-estimates-2025-03-27:hansard-sample', 'Senator SCARR: Secretary, can you walk the committee through FOI processing times in the Attorney-General''s portfolio and whether the integrity framework reviews have changed how exemptions are claimed?

Ms JONES: Senator, FOI is administered in line with the Act. We have invested in case-management so that routine requests are not sitting behind more complex matters. Integrity reviews have reinforced that exemptions must be applied provision by provision, not as a blanket.

Senator SCARR: On legislative drafting capacity — the Office of Parliamentary Counsel has flagged workload pressure. Is that affecting the timing of integrity-related bills?

Ms JONES: Drafting priority is a matter for government. The department provides instructions and works with OPC on sequencing. We are not aware of a statutory deadline being missed for want of drafters, but the pipeline is full.

Senator SCARR: Thank you. I will place a question on notice about the number of FOI decisions set aside on review.', '2025-03-27', 'Fixture sample — not official Hansard. Official records © Commonwealth of Australia, typically CC BY-NC-ND.'),
    ('55555555-5555-4555-8555-555555555003', '22222222-2222-4222-8222-222222222003', 'Sample Official — RRAT regional aviation 18 November 2024', 'hansard', 'https://www.aph.gov.au/Parliamentary_Business/Hansard', 'doc:rrat-regional-aviation-2024-11-18:hansard-sample', 'Senator McKENZIE: The committee is interested in regional aviation access. Communities tell us that when a regular public transport service drops a frequency, the whole town feels it — GPs, freight, and family connections.

Senator SCARR: Could the department set out how community service obligation subsidies are allocated, and whether aerodrome upgrades are keeping pace with safety standards?

WITNESS: The regional aviation access program supports regulated routes where the market will not. We review frequencies annually. Aerodrome funding is a mix of Commonwealth, state, and local contributions; several remote strips are on a works program this year.

Senator McKENZIE: We will take further evidence on the interaction between fuel costs and thin routes.', '2024-11-18', 'Fixture sample — not official Hansard. Official records © Commonwealth of Australia, typically CC BY-NC-ND.')
ON CONFLICT (id) DO NOTHING;

-- Paragraph chunks (embeddings filled by ingest).
INSERT INTO chunks (id, document_id, hearing_id, chunk_index, content, token_count, speaker_name, source_key, metadata) VALUES
    ('f7a080b8-dda8-574d-8c9d-45013f5e91da', '55555555-5555-4555-8555-555555555001', '22222222-2222-4222-8222-222222222001', 0, 'CHAIR: The committee will now examine the Department of the Prime Minister and Cabinet. Minister, welcome.', 16, 'CHAIR', 'chunk:doc:fpa-supp-estimates-2025-10-07:hansard-sample:0', '{}'::jsonb),
    ('f475ad7c-f3a0-5b68-b99d-ccdc326d8f74', '55555555-5555-4555-8555-555555555001', '22222222-2222-4222-8222-222222222001', 1, 'Senator GALLAGHER: Thank you, Chair. The government is happy to take questions on the public service workforce and the Finance portfolio.', 21, 'Senator GALLAGHER', 'chunk:doc:fpa-supp-estimates-2025-10-07:hansard-sample:1', '{}'::jsonb),
    ('8b51ec1e-bede-5be8-8360-586b849e77ce', '55555555-5555-4555-8555-555555555001', '22222222-2222-4222-8222-222222222001', 2, 'Senator PATERSON: Secretary, I want to start with APS capability. How many SES roles are currently vacant across the portfolio, and what is the department doing about institutional knowledge as people leave?', 32, 'Senator PATERSON', 'chunk:doc:fpa-supp-estimates-2025-10-07:hansard-sample:2', '{}'::jsonb),
    ('5ddd8675-ac14-5e4b-908f-67d00892bdb3', '55555555-5555-4555-8555-555555555001', '22222222-2222-4222-8222-222222222001', 3, 'Prof. DAVIS: Senator, we publish workforce metrics in the annual report. Vacancy rates move with machinery-of-government changes. We have a graduate program and a mobility scheme aimed at retaining specialist capability, particularly in procurement and evaluation.', 36, 'Prof. DAVIS', 'chunk:doc:fpa-supp-estimates-2025-10-07:hansard-sample:3', '{}'::jsonb),
    ('e65f85ec-1ab3-5989-bbb3-584d07a022a5', '55555555-5555-4555-8555-555555555001', '22222222-2222-4222-8222-222222222001', 4, 'Senator PATERSON: On procurement: the audit findings on panel arrangements suggested inconsistent documentation. Has PM&C issued new guidance to agencies?', 20, 'Senator PATERSON', 'chunk:doc:fpa-supp-estimates-2025-10-07:hansard-sample:4', '{}'::jsonb),
    ('3f8c01b1-76ce-5e11-9e13-750ccff3e280', '55555555-5555-4555-8555-555555555001', '22222222-2222-4222-8222-222222222001', 5, 'Prof. DAVIS: We have. Finance leads the Commonwealth Procurement Rules. PM&C has circulated a reminder on conflict-of-interest declarations and record-keeping for limited tenders.', 23, 'Prof. DAVIS', 'chunk:doc:fpa-supp-estimates-2025-10-07:hansard-sample:5', '{}'::jsonb),
    ('883b04c3-39c3-5f40-baf9-8b51797beed2', '55555555-5555-4555-8555-555555555001', '22222222-2222-4222-8222-222222222001', 6, 'Senator GALLAGHER: If I may, the government has also funded additional training through the APS Academy on complex procurement.', 19, 'Senator GALLAGHER', 'chunk:doc:fpa-supp-estimates-2025-10-07:hansard-sample:6', '{}'::jsonb),
    ('1414ee41-2fbb-549c-8493-c040786485b9', '55555555-5555-4555-8555-555555555001', '22222222-2222-4222-8222-222222222001', 7, 'Senator PATERSON: Freedom of information — the OAIC continues to report delays. What is the median time to finalise an FOI request in PM&C this financial year?', 27, 'Senator PATERSON', 'chunk:doc:fpa-supp-estimates-2025-10-07:hansard-sample:7', '{}'::jsonb),
    ('01310ef5-6b1f-565d-ac65-4925aaf928b0', '55555555-5555-4555-8555-555555555001', '22222222-2222-4222-8222-222222222001', 8, 'Prof. DAVIS: I will take the precise median on notice. We have reduced the backlog relative to last year, but complex requests involving cabinet-related material still take longer.', 28, 'Prof. DAVIS', 'chunk:doc:fpa-supp-estimates-2025-10-07:hansard-sample:8', '{}'::jsonb),
    ('921e7f3f-8cf1-5d39-bba2-a937a5c8bc05', '55555555-5555-4555-8555-555555555001', '22222222-2222-4222-8222-222222222001', 9, 'CHAIR: The committee will break and resume with Finance.', 9, 'CHAIR', 'chunk:doc:fpa-supp-estimates-2025-10-07:hansard-sample:9', '{}'::jsonb),
    ('ec09ca11-4e0a-5e84-b247-00e8ff6674d0', '55555555-5555-4555-8555-555555555002', '22222222-2222-4222-8222-222222222002', 0, 'Senator SCARR: Secretary, can you walk the committee through FOI processing times in the Attorney-General''s portfolio and whether the integrity framework reviews have changed how exemptions are claimed?', 28, 'Senator SCARR', 'chunk:doc:lca-budget-estimates-2025-03-27:hansard-sample:0', '{}'::jsonb),
    ('60280ce1-b144-51af-bc87-b3761daecb17', '55555555-5555-4555-8555-555555555002', '22222222-2222-4222-8222-222222222002', 1, 'Ms JONES: Senator, FOI is administered in line with the Act. We have invested in case-management so that routine requests are not sitting behind more complex matters. Integrity reviews have reinforced that exemptions must be applied provision by provision, not as a blanket.', 43, 'Ms JONES', 'chunk:doc:lca-budget-estimates-2025-03-27:hansard-sample:1', '{}'::jsonb),
    ('78575a41-4164-5779-81c7-5dedffe220c7', '55555555-5555-4555-8555-555555555002', '22222222-2222-4222-8222-222222222002', 2, 'Senator SCARR: On legislative drafting capacity — the Office of Parliamentary Counsel has flagged workload pressure. Is that affecting the timing of integrity-related bills?', 24, 'Senator SCARR', 'chunk:doc:lca-budget-estimates-2025-03-27:hansard-sample:2', '{}'::jsonb),
    ('c4b92653-422b-5cb3-bea3-f4aec7fefdbe', '55555555-5555-4555-8555-555555555002', '22222222-2222-4222-8222-222222222002', 3, 'Ms JONES: Drafting priority is a matter for government. The department provides instructions and works with OPC on sequencing. We are not aware of a statutory deadline being missed for want of drafters, but the pipeline is full.', 38, 'Ms JONES', 'chunk:doc:lca-budget-estimates-2025-03-27:hansard-sample:3', '{}'::jsonb),
    ('c8037474-ad4f-5141-a6b5-e8aa8a7ffcab', '55555555-5555-4555-8555-555555555002', '22222222-2222-4222-8222-222222222002', 4, 'Senator SCARR: Thank you. I will place a question on notice about the number of FOI decisions set aside on review.', 21, 'Senator SCARR', 'chunk:doc:lca-budget-estimates-2025-03-27:hansard-sample:4', '{}'::jsonb),
    ('50e6114d-f0fd-5574-932b-3019292e8bff', '55555555-5555-4555-8555-555555555003', '22222222-2222-4222-8222-222222222003', 0, 'Senator McKENZIE: The committee is interested in regional aviation access. Communities tell us that when a regular public transport service drops a frequency, the whole town feels it — GPs, freight, and family connections.', 34, 'Senator McKENZIE', 'chunk:doc:rrat-regional-aviation-2024-11-18:hansard-sample:0', '{}'::jsonb),
    ('4e93a013-91f9-5c32-9348-9d563ec12fb4', '55555555-5555-4555-8555-555555555003', '22222222-2222-4222-8222-222222222003', 1, 'Senator SCARR: Could the department set out how community service obligation subsidies are allocated, and whether aerodrome upgrades are keeping pace with safety standards?', 24, 'Senator SCARR', 'chunk:doc:rrat-regional-aviation-2024-11-18:hansard-sample:1', '{}'::jsonb),
    ('6c0d486c-a768-5c9f-826a-58167ff4964b', '55555555-5555-4555-8555-555555555003', '22222222-2222-4222-8222-222222222003', 2, 'WITNESS: The regional aviation access program supports regulated routes where the market will not. We review frequencies annually. Aerodrome funding is a mix of Commonwealth, state, and local contributions; several remote strips are on a works program this year.', 39, 'WITNESS', 'chunk:doc:rrat-regional-aviation-2024-11-18:hansard-sample:2', '{}'::jsonb),
    ('c234d98c-0086-57ce-a476-b1697c951710', '55555555-5555-4555-8555-555555555003', '22222222-2222-4222-8222-222222222003', 3, 'Senator McKENZIE: We will take further evidence on the interaction between fuel costs and thin routes.', 16, 'Senator McKENZIE', 'chunk:doc:rrat-regional-aviation-2024-11-18:hansard-sample:3', '{}'::jsonb)
ON CONFLICT (id) DO NOTHING;

INSERT INTO boards (id, slug, title, description) VALUES
    ('66666666-6666-4666-8666-666666666001', 'aps-capability', 'APS capability & integrity', 'Stage 1 pinboard stub — hearings and people to revisit on public service capability, procurement, and FOI.'),
    ('66666666-6666-4666-8666-666666666002', 'estimates-watch', 'Estimates watchlist', 'Stage 1 pinboard stub — a place to pin upcoming or recent Estimates appearances.')
ON CONFLICT (id) DO NOTHING;

INSERT INTO pins (id, board_id, pin_type, target_id, note) VALUES
    ('77777777-7777-4777-8777-777777777001', '66666666-6666-4666-8666-666666666001', 'hearing', '22222222-2222-4222-8222-222222222001', 'APS capability and procurement exchange.'),
    ('77777777-7777-4777-8777-777777777002', '66666666-6666-4666-8666-666666666001', 'person', '33333333-3333-4333-8333-333333333005', 'Official witness on workforce metrics.'),
    ('77777777-7777-4777-8777-777777777003', '66666666-6666-4666-8666-666666666002', 'hearing', '22222222-2222-4222-8222-222222222002', 'FOI and integrity at LCA estimates.')
ON CONFLICT (id) DO NOTHING;

INSERT INTO ingest_runs (source, started_at, finished_at, status, records_fetched, records_upserted, meta)
VALUES ('fixture', now(), now(), 'success', 3, 3, '{"note": "loaded from 003_seed.sql"}'::jsonb);

