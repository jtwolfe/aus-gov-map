# Postgres schema

Numbered files in this directory are applied **once** by Docker on first volume init (`/docker-entrypoint-initdb.d`).

| File | Role |
| --- | --- |
| `001_extensions.sql` | uuid-ossp, pg_trgm, vector |
| `002_schema.sql` | Stage 1 tables |
| `003_seed.sql` | Fixture hearings / people / sample Official |
| `004_analytics.sql` | Unique pins + inefficiency views |
| `005_handbook.sql` | Stage 2 Handbook tables (empty) |
| `006_demo_board.sql` | FOI / procurement demo board from chunk hits |

Readable copies of the views also live in `analytics/`.

## Existing volumes

```bash
make db-apply
# or:
python -m aus_gov_ingest apply-schema
python -m aus_gov_ingest seed-demo-board
```

`DATABASE_URL` defaults to `postgresql://ausgov:ausgov@localhost:5432/ausgov`.
