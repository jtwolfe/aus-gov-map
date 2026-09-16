"""Federal Register of Legislation ingest (Bills / Acts as instruments).

Live: FRL title pages / browse HTML when reachable (browser-like UA).
Fallback: committed metadata under fixtures/live/legislation/.

Writes ``instruments`` type ``bill`` or ``act`` with FRL identifiers.
Idempotent on ``source_key`` (typically ``frl:{frl_id}``). Does not invent
commencement dates — only dates present on the record.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from aus_gov_ingest.http import AphClient
from aus_gov_ingest.models import InstrumentIn, SourceBatch
from aus_gov_ingest.sources.util import fixture_live_dir, parse_flexible_date, slug

FRL_HOME = "https://www.legislation.gov.au"
LICENSE_NOTE = (
    "© Commonwealth of Australia. Federal Register of Legislation. "
    "Attribute the Office of Parliamentary Counsel / FRL."
)

ENDPOINTS = {
    "home": FRL_HOME,
    "acts": f"{FRL_HOME}/Browse/Results/ByTitle/Acts/InForce/A/0",
    "bills": f"{FRL_HOME}/Browse/Results/ByTitle/Bills/Current/A/0",
    "developer": f"{FRL_HOME}/developer",
}

# Seed Register ids we always try to resolve (live page, then fixture).
SEED_FRL_IDS = (
    "C2013A00123",
    "C2004A02562",
    "C2004A05248",
    "C2022A00088",
    "C2004A05251",
    "C1958A00062",
)

_FRL_ID = re.compile(r"\b(C\d{4}[ABC]\d{5})\b", re.I)
_TITLE_HEADING = re.compile(
    r"(?P<title>(?:[A-Z][^<\n]{8,160}? (?:Act|Bill)(?:\s+\d{4}(?:-\d{2,4})?)?))",
)
_NO_YEAR = re.compile(r"No\.?\s*(?P<num>\d+),?\s*(?P<year>\d{4})", re.I)


def default_legislation_dir() -> Path:
    return fixture_live_dir("legislation")


class LegislationSource:
    name = "legislation"
    HOME = FRL_HOME
    ENDPOINTS = ENDPOINTS

    def __init__(
        self,
        *,
        path: Path | str | None = None,
        client: AphClient | None = None,
    ) -> None:
        self.path = Path(path) if path else None
        self.client = client or AphClient(timeout=12, max_retries=1)

    def fetch(self, *, limit: int = 0, incremental_keys: set[str] | None = None) -> SourceBatch:
        errors: list[str] = []
        transport = "frl"
        records: list[dict] = []

        if self.path:
            records, transport = load_legislation_path(self.path)
        else:
            try:
                records = self._fetch_live(limit=limit or 12)
            except Exception as exc:
                errors.append(f"frl_live: {exc}")
                try:
                    records, transport = load_legislation_path(default_legislation_dir())
                    transport = f"fixture_fallback:{transport}"
                except Exception as fallback_exc:
                    errors.append(f"fixture: {fallback_exc}")

        known = incremental_keys or set()
        instruments: list[InstrumentIn] = []
        seen: set[str] = set()
        for record in records:
            item = instrument_from_frl(record)
            if not item or item.source_key in known or item.source_key in seen:
                continue
            seen.add(item.source_key)
            instruments.append(item)
            if limit and len(instruments) >= limit:
                break

        return SourceBatch(
            source=self.name,
            instruments=instruments,
            meta={
                "status": "ok" if instruments else "empty",
                "home": self.HOME,
                "transport": transport,
                "license_note": LICENSE_NOTE,
                "limit": limit,
                "skipped_existing": len(known),
                "errors": errors,
                "instruments": len(instruments),
                "endpoints": ENDPOINTS,
                "schema": "infra/postgres/012_laws.sql (instruments type bill|act)",
                "note": (
                    "FRL Bills/Acts into instruments. Identifiers include FRL id, "
                    "series, year, number. Dates only when the source states them."
                ),
            },
        )

    def _fetch_live(self, *, limit: int) -> list[dict]:
        errors: list[str] = []
        records: list[dict] = []
        for frl_id in SEED_FRL_IDS:
            url = f"{FRL_HOME}/{frl_id}"
            try:
                html = self.client.get_text(url, referer=FRL_HOME)
            except Exception as exc:
                errors.append(f"{frl_id}: {exc}")
                continue
            record = parse_frl_title_html(html, frl_id=frl_id, url=url)
            if record:
                records.append(record)
            if limit and len(records) >= limit:
                return records
        if records:
            return records
        raise RuntimeError("FRL title pages empty or blocked: " + ("; ".join(errors) or "no rows"))


def load_legislation_path(path: Path) -> tuple[list[dict], str]:
    if not path.exists():
        raise FileNotFoundError(f"Legislation path not found: {path}")
    files = [path] if path.is_file() else sorted(p for p in path.glob("*.json") if p.is_file())
    if not files:
        raise FileNotFoundError(f"No legislation JSON in {path}")
    records: list[dict] = []
    for file in files:
        payload = json.loads(file.read_text(encoding="utf-8"))
        if isinstance(payload, list):
            records.extend(r for r in payload if isinstance(r, dict))
        elif isinstance(payload, dict) and isinstance(payload.get("titles"), list):
            records.extend(r for r in payload["titles"] if isinstance(r, dict))
        elif isinstance(payload, dict) and (payload.get("title") or payload.get("frl_id")):
            records.append(payload)
    return records, f"legislation_file:{path}"


def parse_frl_title_html(html: str, *, frl_id: str, url: str) -> dict | None:
    """Best-effort title page: heading + No./year when present."""
    text = re.sub(r"<[^>]+>", " ", html or "")
    text = " ".join(text.split())
    if not text:
        return None
    title = None
    for match in _TITLE_HEADING.finditer(text):
        candidate = match.group("title").strip()
        if "federal register" in candidate.lower():
            continue
        if "act" in candidate.lower() or "bill" in candidate.lower():
            title = candidate[:200]
            break
    if not title:
        return None
    number_year = _NO_YEAR.search(text)
    kind = "bill" if "bill" in title.lower() and "act" not in title.lower() else "act"
    return {
        "frl_id": frl_id,
        "title": title,
        "collection": "Bill" if kind == "bill" else "Act",
        "instrument_type": kind,
        "status": "in_force" if kind == "act" else "introduced",
        "year": int(number_year.group("year")) if number_year else _year_from_frl(frl_id),
        "number": int(number_year.group("num")) if number_year else None,
        "source_url": url,
        "series": "C",
    }


def instrument_from_frl(row: dict) -> InstrumentIn | None:
    title = (row.get("title") or "").strip()
    if not title:
        return None
    frl_id = (row.get("frl_id") or "").strip() or None
    if not frl_id:
        found = _FRL_ID.search(row.get("source_url") or "")
        frl_id = found.group(1).upper() if found else None
    source_key = row.get("source_key") or (f"frl:{frl_id}" if frl_id else f"frl:bill:{slug(title)[:60]}")
    kind = (row.get("instrument_type") or row.get("collection") or "act").lower()
    if kind not in {"bill", "act"}:
        kind = "bill" if "bill" in title.lower() and "act" not in title.lower() else "act"
    announced = parse_flexible_date(
        row.get("as_made_on") or row.get("announced_on") or row.get("introduced_on")
    )
    commenced = parse_flexible_date(row.get("commenced_on"))
    ended = parse_flexible_date(row.get("ended_on") or row.get("repealed_on"))
    year = row.get("year")
    if year is not None:
        try:
            year = int(year)
        except (TypeError, ValueError):
            year = _year_from_frl(frl_id) if frl_id else None
    elif frl_id:
        year = _year_from_frl(frl_id)
    number = row.get("number")
    if number is not None:
        try:
            number = int(number)
        except (TypeError, ValueError):
            number = None
    status = (row.get("status") or ("in_force" if kind == "act" else "introduced")).lower()
    agency = row.get("agency_name")
    return InstrumentIn(
        source_key=source_key,
        title=title[:240],
        kind=kind,  # type: ignore[arg-type]
        status=status,
        confidence=0.92 if frl_id else 0.7,
        agency_name=agency,
        agency_slug=slug(agency)[:80] if agency else None,
        portfolio=row.get("portfolio"),
        announced_on=announced,
        commenced_on=commenced,
        ended_on=ended,
        source="legislation",
        source_url=row.get("source_url") or (f"{FRL_HOME}/{frl_id}" if frl_id else None),
        notes=LICENSE_NOTE,
        identifiers={
            "frl_id": frl_id,
            "series": row.get("series") or ("C" if frl_id else None),
            "year": year,
            "number": number,
            "collection": row.get("collection") or ("Bill" if kind == "bill" else "Act"),
            "compilation": bool(row.get("compilation")),
            "related_frl_id": row.get("related_frl_id"),
            "related_bill_key": row.get("related_bill_key"),
            "license_note": LICENSE_NOTE,
        },
        metadata={"summary_source": "frl"},
        evidence_text=(row.get("summary") or "")[:500] or None,
    )


def _year_from_frl(frl_id: str | None) -> int | None:
    if not frl_id or len(frl_id) < 5:
        return None
    try:
        return int(frl_id[1:5])
    except ValueError:
        return None
