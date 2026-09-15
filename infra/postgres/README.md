# Postgres schema

Numbered files in this directory are applied **once** by Docker on first volume init (`/docker-entrypoint-initdb.d`).

| File | Role |
| --- | --- |
| `001_extensions.sql` | uuid-ossp, pg_trgm, vector |
| `002_schema.sql` | Stage 1 tables |
| `003_seed.sql` | Fixture hearings / people / sample Official |
| `004_analytics.sql` | Unique pins + inefficiency views |
| `005_handbook.sql` | Handbook extract tables (empty; linked to `people`) |
| `006_demo_board.sql` | FOI / procurement demo board from chunk hits |
| `007_accountability.sql` | Stage 2 duty map: agencies, roles, person_roles, instruments, scrutiny, QoNs, claims, outcomes + views |
| `008_hearing_segments.sql` | Additive: hearing_segments, instrument status/confidence, QoN portfolio alias view |
| `009_source_adapters.sql` | Additive: outcome confidence / source_key / agency + scrutiny FKs for ANAO / Budget / AusTender |
| `010_aps_leaders.sql` | Additive: person_roles.source_key, claims.qon_id, agency-head view, QoN debt + responsible official |

Readable copies of the views also live in `analytics/` (`001_views.sql` and `accountability_*.sql`).

## Existing volumes

```bash
make db-apply
# or:
python -m aus_gov_ingest apply-schema
python -m aus_gov_ingest seed-demo-board
```

`DATABASE_URL` defaults to `postgresql://ausgov:ausgov@localhost:5432/ausgov`.

`007` is additive: it does not drop Stage 1 tables. `people` remains the only person key. Handbook `handbook_roles` / `handbook_tenure` stay the provenance store and can promote into `person_roles`.
