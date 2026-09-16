.PHONY: up down logs seed web ingest install compose-app help db-up db-apply ingest-live-files ingest-backfill-files ingest-laws web-dev verify verify-atlas verify-laws

# Default local URL used by db-up / ingest-live-files / web-dev docs.
DATABASE_URL ?= postgresql://ausgov:ausgov@localhost:5432/ausgov
TRANSCRIPT_DIR := services/ingest/fixtures/live/transcripts

help:
	@echo "aus-gov-map Stage 2"
	@echo "  make db-up                  Start Postgres+pgvector (and print DATABASE_URL)"
	@echo "  make up                     Start Postgres+pgvector and Neo4j"
	@echo "  make db-apply               Apply analytics, handbook, accountability, laws, demo board"
	@echo "  make ingest-laws            Dry-run legislation / TVFY / judgments fixtures"
	@echo "  make ingest-live-files      Persist committed APH Official JSON into Postgres"
	@echo "  make ingest-backfill-files  Dry-run Official JSON under $(TRANSCRIPT_DIR)"
	@echo "  make web-dev                Next.js dev server (prefers DATABASE_URL)"
	@echo "  make seed                   Load fixture seed via ingest CLI"
	@echo "  make verify                 Search + pins verification script"
	@echo "  make verify-atlas           Atlas query + HTTP verification"
	@echo "  make down                   Stop compose stack"
	@echo "  make ingest                 Show ingest CLI help"
	@echo "  make install                Install web + ingest deps"

up:
	docker compose up -d postgres neo4j neo4j-init

db-up:
	docker compose up -d postgres
	@echo ""
	@echo "Postgres is starting. Point the web app and ingest at:"
	@echo "  DATABASE_URL=$(DATABASE_URL)"
	@echo "Copy .env.example → .env or export that URL before make web-dev / ingest-live-files."
	@echo "Existing volumes keep data; new volumes load infra/postgres/001–013."

down:
	docker compose down

logs:
	docker compose logs -f postgres neo4j

compose-app:
	docker compose --profile app up --build

install:
	cd apps/web && npm install
	cd services/ingest && python3 -m pip install -e ".[dev]"

seed:
	cd services/ingest && DATABASE_URL=$(DATABASE_URL) python3 -m aus_gov_ingest seed

db-apply:
	cd services/ingest && DATABASE_URL=$(DATABASE_URL) python3 -m aus_gov_ingest apply-schema
	cd services/ingest && DATABASE_URL=$(DATABASE_URL) python3 -m aus_gov_ingest seed-demo-board

# Persist every committed Official under fixtures/live/transcripts (21+ Hansard JSON).
ingest-live-files:
	@echo "Ingesting committed Officials via aph_transcript_file ($(TRANSCRIPT_DIR))"
	@echo "DATABASE_URL=$(DATABASE_URL)"
	cd services/ingest && DATABASE_URL=$(DATABASE_URL) python3 -m aus_gov_ingest run --source aph_transcript_file --no-graph
	cd services/ingest && DATABASE_URL=$(DATABASE_URL) python3 -m aus_gov_ingest seed-demo-board

# Offline Official backfill: aph_transcript_file over committed Hansard JSON.
# Persist with: make ingest-backfill-files BACKFILL_FLAGS=
ingest-backfill-files:
	cd services/ingest && python3 -m aus_gov_ingest run --source aph_transcript_file \
	  --path fixtures/live/transcripts $(or $(BACKFILL_FLAGS),--dry-run)

web-dev:
	@echo "Next.js prefers DATABASE_URL when Postgres is reachable."
	@echo "DATABASE_URL=$(DATABASE_URL)"
	@echo "Unset DATABASE_URL to force the bundled fixture seed."
	cd apps/web && DATABASE_URL=$(DATABASE_URL) npm run dev

web:
	cd apps/web && npm run dev

ingest:
	cd services/ingest && python3 -m aus_gov_ingest --help

verify:
	DATABASE_URL=$(DATABASE_URL) python3 scripts/verify_search_pins.py

verify-atlas:
	python3 scripts/verify_atlas.py
	@if [ -n "$(DATABASE_URL)" ]; then DATABASE_URL=$(DATABASE_URL) python3 scripts/verify_atlas.py; fi

verify-laws:
	python3 scripts/verify_laws.py
	@if [ -n "$(DATABASE_URL)" ]; then DATABASE_URL=$(DATABASE_URL) python3 scripts/verify_laws.py; fi

# Offline law ingest (fixtures). Persist with: make ingest-laws DRY_RUN=
ingest-laws:
	cd services/ingest && python3 -m aus_gov_ingest run --source legislation \
	  --path fixtures/live/legislation $(or $(DRY_RUN),--dry-run) --no-graph
	cd services/ingest && python3 -m aus_gov_ingest run --source theyvoteforyou \
	  --path fixtures/live/tvfy $(or $(DRY_RUN),--dry-run) --no-graph
	cd services/ingest && python3 -m aus_gov_ingest run --source judgments \
	  --path fixtures/live/judgments $(or $(DRY_RUN),--dry-run) --no-graph
