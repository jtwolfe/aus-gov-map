FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY services/ingest /app/services/ingest
COPY data/fixtures /app/data/fixtures
COPY infra/neo4j /app/infra/neo4j

WORKDIR /app/services/ingest
RUN pip install --no-cache-dir -e .

ENV PYTHONUNBUFFERED=1
ENV AUS_GOV_FIXTURE_PATH=/app/data/fixtures/seed.json

ENTRYPOINT ["python", "-m", "aus_gov_ingest"]
CMD ["run", "--source", "fixture"]
