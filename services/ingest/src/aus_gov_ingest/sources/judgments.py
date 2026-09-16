"""High Court / Federal Court judgments that cite mapped Acts (MVP).

Fixture-first: Jade / AustLII / court-site HTML is unstable and we do
not republish reasons. Live fetch is not attempted in this pass.

Writes ``scrutiny_items`` (type judgment), optional ``outcomes``
(``court_holding``, signal unknown unless sourced), and
``instrument_links`` (construes / invalidates / upholds).
"""

from __future__ import annotations

import json
from pathlib import Path

from aus_gov_ingest.models import InstrumentLinkIn, OutcomeIn, ScrutinyItemIn, SourceBatch
from aus_gov_ingest.sources.util import fixture_live_dir, parse_flexible_date, slug

LICENSE_NOTE = (
    "Published court catchwords / headnotes. Attribute the Commonwealth courts. "
    "Citations via Jade, AustLII, or court sites. Not a republication of reasons. "
    "Not a guilt label."
)

ENDPOINTS = {
    "hcourt": "https://www.hcourt.gov.au",
    "eresources": "https://eresources.hcourt.gov.au",
    "jade": "https://jade.io",
    "austlii": "https://www.austlii.edu.au",
    "federal_court": "https://www.fedcourt.gov.au",
}

ALLOWED_LINKS = {"construes", "invalidates", "upholds"}


def default_judgments_dir() -> Path:
    return fixture_live_dir("judgments")


class JudgmentsSource:
    name = "judgments"
    HOME = ENDPOINTS["hcourt"]
    ENDPOINTS = ENDPOINTS

    def __init__(self, *, path: Path | str | None = None) -> None:
        self.path = Path(path) if path else default_judgments_dir()

    def fetch(self, *, limit: int = 0, incremental_keys: set[str] | None = None) -> SourceBatch:
        records, transport = load_judgments_path(self.path)
        known = incremental_keys or set()
        scrutiny: list[ScrutinyItemIn] = []
        outcomes: list[OutcomeIn] = []
        links: list[InstrumentLinkIn] = []
        seen: set[str] = set()
        for record in records:
            item = item_from_record(record)
            if not item or item.source_key in known or item.source_key in seen:
                continue
            seen.add(item.source_key)
            scrutiny.append(item)
            for link in links_from_record(record, item):
                links.append(link)
            outcome = outcome_from_record(record, item)
            if outcome:
                outcomes.append(outcome)
            if limit and len(scrutiny) >= limit:
                break

        return SourceBatch(
            source=self.name,
            scrutiny_items=scrutiny,
            outcomes=outcomes,
            instrument_links=links,
            meta={
                "status": "ok" if scrutiny else "empty",
                "home": self.HOME,
                "transport": transport,
                "license_note": LICENSE_NOTE,
                "limit": limit,
                "skipped_existing": len(known),
                "errors": [],
                "scrutiny_items": len(scrutiny),
                "outcomes": len(outcomes),
                "instrument_links": len(links),
                "endpoints": ENDPOINTS,
                "schema": "infra/postgres/013_precedent.sql (judgment + construes/upholds/invalidates)",
                "note": (
                    "Fixture MVP of High Court / Federal Court decisions that cite "
                    "mapped Acts. Link verbs only when the published holding supports "
                    "them. No automated guilt labels."
                ),
            },
        )


def load_judgments_path(path: Path) -> tuple[list[dict], str]:
    if not path.exists():
        raise FileNotFoundError(f"Judgments path not found: {path}")
    files = [path] if path.is_file() else sorted(p for p in path.glob("*.json") if p.is_file())
    if not files:
        raise FileNotFoundError(f"No judgment JSON in {path}")
    records: list[dict] = []
    for file in files:
        payload = json.loads(file.read_text(encoding="utf-8"))
        if isinstance(payload, list):
            records.extend(r for r in payload if isinstance(r, dict))
        elif isinstance(payload, dict) and isinstance(payload.get("judgments"), list):
            records.extend(r for r in payload["judgments"] if isinstance(r, dict))
        elif isinstance(payload, dict) and (payload.get("citation") or payload.get("title")):
            records.append(payload)
    return records, f"judgments_file:{path}"


def item_from_record(row: dict) -> ScrutinyItemIn | None:
    title = (row.get("title") or row.get("citation") or "").strip()
    citation = (row.get("citation") or "").strip()
    if not title:
        return None
    key = slug(citation or title)[:80]
    published = parse_flexible_date(row.get("published_on") or row.get("date"))
    url = row.get("source_url") or row.get("austlii_url") or row.get("jade_url")
    court = row.get("court") or "High Court of Australia"
    return ScrutinyItemIn(
        source_key=f"judgment:{key}",
        item_type="judgment",
        title=title[:300],
        published_on=published,
        source=row.get("source") or "judgment",
        source_url=url,
        summary=(row.get("summary") or "")[:800] or None,
        identifiers={
            "citation": citation or None,
            "court": court,
            "jade_url": row.get("jade_url"),
            "austlii_url": row.get("austlii_url"),
            "license_note": LICENSE_NOTE,
        },
        confidence=0.85,
    )


def links_from_record(row: dict, item: ScrutinyItemIn) -> list[InstrumentLinkIn]:
    out: list[InstrumentLinkIn] = []
    for raw in row.get("links") or []:
        if not isinstance(raw, dict):
            continue
        kind = str(raw.get("link_kind") or "").lower()
        instrument_key = raw.get("instrument_source_key")
        if kind not in ALLOWED_LINKS or not instrument_key:
            continue
        out.append(
            InstrumentLinkIn(
                instrument_source_key=instrument_key,
                link_kind=kind,  # type: ignore[arg-type]
                target_kind="scrutiny",
                target_source_key=item.source_key,
                source=item.source or "judgment",
                notes=(raw.get("notes") or "")[:400] or None,
            )
        )
    return out


def outcome_from_record(row: dict, item: ScrutinyItemIn) -> OutcomeIn | None:
    if not (row.get("summary") or row.get("links")):
        return None
    first_instrument = None
    for raw in row.get("links") or []:
        if isinstance(raw, dict) and raw.get("instrument_source_key"):
            first_instrument = raw["instrument_source_key"]
            break
    return OutcomeIn(
        source_key=f"outcome:{item.source_key}",
        outcome_type="court_holding",
        signal="unknown",
        occurred_on=item.published_on,
        source=item.source or "judgment",
        source_url=item.source_url,
        notes="Sourced court holding. Not a guilt or liability label.",
        confidence=0.4,
        instrument_source_key=first_instrument,
        scrutiny_source_key=item.source_key,
        identifiers={"citation": (item.identifiers or {}).get("citation")},
    )
