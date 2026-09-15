.PHONY: up down logs seed web ingest install compose-app help ingest-backfill-files

TRANSCRIPT_DIR := services/ingest/fixtures/live/transcripts

help:
	@echo "aus-gov-map Stage 1"
	@echo "  make up                     Start Postgres+pgvector and Neo4j"
	@echo "  make down                   Stop compose stack"
	@echo "  make seed                   Load fixture seed via ingest CLI"
	@echo "  make web                    Run Next.js dev server"
	@echo "  make ingest                 Show ingest CLI help"
	@echo "  make ingest-backfill-files  Dry-run Official JSON under $(TRANSCRIPT_DIR)"
	@echo "  make install                Install web + ingest deps"

up:
	docker compose up -d postgres neo4j neo4j-init

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
	cd services/ingest && python3 -m aus_gov_ingest seed

web:
	cd apps/web && npm run dev

ingest:
	cd services/ingest && python3 -m aus_gov_ingest --help

# Offline Official backfill: aph_transcript_file over committed Hansard JSON.
# Persist with: make ingest-backfill-files BACKFILL_FLAGS=
ingest-backfill-files:
	cd services/ingest && python3 -m aus_gov_ingest run --source aph_transcript_file \
	  --path fixtures/live/transcripts $(or $(BACKFILL_FLAGS),--dry-run)
