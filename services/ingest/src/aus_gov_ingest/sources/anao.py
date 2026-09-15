"""ANAO (Auditor-General) performance-audit ingest.

Live: public work / reports index on anao.gov.au (browser-like UA).
Fallback: committed metadata under fixtures/live/anao/.

Writes ``scrutiny_items`` (type anao). Light ``outcomes`` are created only
when recommendation / finding language is present on the page or fixture
excerpt — never invented. Optional program-named ``instruments`` when the
title itself names a Program / Fund / Scheme.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from aus_gov_ingest.http import AphClient
from aus_gov_ingest.models import InstrumentIn, OutcomeIn, ScrutinyItemIn, SourceBatch
from aus_gov_ingest.sources.util import (
    fixture_live_dir,
    parse_flexible_date,
    slug,
    worse_signal,
)

ANAO_HOME = "https://www.anao.gov.au"
WORK_INDEX = f"{ANAO_HOME}/work"
PUBS_INDEX = f"{ANAO_HOME}/pubs/performance-audit"
PUBS_ALL = f"{ANAO_HOME}/pubs"

ENDPOINTS = {
    "home": ANAO_HOME,
    "work": WORK_INDEX,
    "pubs": PUBS_INDEX,
    "pubs_all": PUBS_ALL,
    "data_gov": "https://data.gov.au/data/organization/australian-national-audit-office",
}

LICENSE_NOTE = (
    "© Commonwealth of Australia. Auditor-General reports. "
    "Attribute the Australian National Audit Office."
)

LISTING_URLS = (
    f"{PUBS_INDEX}?items_per_page=30",
    WORK_INDEX,
    f"{PUBS_ALL}?items_per_page=30",
)

_REPORT_NO = re.compile(
    r"Auditor-General Report No\.?\s*(?P<num>\d+)\s+of\s+(?P<year>\d{4}\s*[–-]\s*\d{2})",
    re.I,
)
_PUBLISHED = re.compile(
    r"Published:?\s*(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)?\s*"
    r"(?P<d>\d{1,2}\s+\w+\s+\d{4})",
    re.I,
)
_NAMED_INSTRUMENT = re.compile(
    r"\b((?:The )?(?:National |Commonwealth |Australian )?[A-Z][A-Za-z0-9'’&-]+"
    r"(?:[ -][A-Z][A-Za-z0-9'’&-]+){0,8} "
    r"(?:Program|Programme|Fund|Facility|Scheme|Plan))\b"
)
_ADVERSE = re.compile(
    r"\b(?:not effective|ineffective|did not comply|non-compliant|unacceptable)\b",
    re.I,
)
_PARTIAL = re.compile(
    r"\b(?:partly effective|partly appropriate|partially effective|agreed in principle)\b",
    re.I,
)
_MET = re.compile(r"\b(?:fully effective|largely effective)\b", re.I)


def default_anao_dir() -> Path:
    return fixture_live_dir("anao")


class AnaoSource:
    name = "anao"
    HOME = ANAO_HOME
    ENDPOINTS = ENDPOINTS

    def __init__(
        self,
        *,
        path: Path | str | None = None,
        client: AphClient | None = None,
    ) -> None:
        self.path = Path(path) if path else None
        # anao.gov.au often stalls or WAF-blocks datacentre IPs — fail fast, then fixtures.
        self.client = client or AphClient(timeout=12, max_retries=1)

    def fetch(self, *, limit: int = 0, incremental_keys: set[str] | None = None) -> SourceBatch:
        errors: list[str] = []
        transport = "anao_index"
        records: list[dict] = []

        if self.path:
            records, transport = load_anao_path(self.path)
        else:
            try:
                records = self._fetch_live(limit=limit or 20)
            except Exception as exc:
                errors.append(f"anao_live: {exc}")
                try:
                    records, transport = load_anao_path(default_anao_dir())
                    transport = f"fixture_fallback:{transport}"
                except Exception as fallback_exc:
                    errors.append(f"fixture: {fallback_exc}")

        known = incremental_keys or set()
        scrutiny: list[ScrutinyItemIn] = []
        outcomes: list[OutcomeIn] = []
        instruments: list[InstrumentIn] = []
        seen: set[str] = set()
        for record in records:
            item = item_from_record(record)
            if not item or item.source_key in known or item.source_key in seen:
                continue
            seen.add(item.source_key)
            scrutiny.append(item)
            instrument = named_instrument_from_title(item)
            if instrument:
                instruments.append(instrument)
            outcome = outcome_from_record(record, item, instrument)
            if outcome:
                outcomes.append(outcome)
            if limit and len(scrutiny) >= limit:
                break

        return SourceBatch(
            source=self.name,
            scrutiny_items=scrutiny,
            outcomes=outcomes,
            instruments=instruments,
            meta={
                "status": "ok" if scrutiny else "empty",
                "home": self.HOME,
                "transport": transport,
                "license_note": LICENSE_NOTE,
                "limit": limit,
                "skipped_existing": len(known),
                "errors": errors,
                "scrutiny_items": len(scrutiny),
                "outcomes": len(outcomes),
                "instruments": len(instruments),
                "endpoints": ENDPOINTS,
                "schema": "infra/postgres/007_accountability.sql (scrutiny_items, outcomes)",
                "note": (
                    "ANAO performance-audit listings into scrutiny_items (type anao). "
                    "Outcomes only when finding language is parseable. No invented findings."
                ),
            },
        )

    def _fetch_live(self, *, limit: int) -> list[dict]:
        errors: list[str] = []
        for url in LISTING_URLS:
            try:
                html = self.client.get_text(url, referer=ANAO_HOME)
            except Exception as exc:
                errors.append(f"{url}: {exc}")
                continue
            records = parse_listing_html(html, base_url=url)
            if records:
                cap = max(limit, 1)
                return records[:cap]
        raise RuntimeError("ANAO listing empty or blocked: " + ("; ".join(errors) or "no rows"))


def load_anao_path(path: Path) -> tuple[list[dict], str]:
    if not path.exists():
        raise FileNotFoundError(f"ANAO path not found: {path}")
    files: list[Path]
    if path.is_file():
        files = [path]
    else:
        files = sorted(p for p in path.glob("*.json") if p.is_file())
        files += sorted(p for p in path.glob("*.html") if p.is_file())
    if not files:
        raise FileNotFoundError(f"No ANAO fixtures in {path}")
    records: list[dict] = []
    for file in files:
        if file.suffix.lower() == ".html":
            records.extend(parse_listing_html(file.read_text(encoding="utf-8"), base_url=ANAO_HOME))
            continue
        payload = json.loads(file.read_text(encoding="utf-8"))
        if isinstance(payload, list):
            records.extend(r for r in payload if isinstance(r, dict))
        elif isinstance(payload, dict) and isinstance(payload.get("reports"), list):
            records.extend(r for r in payload["reports"] if isinstance(r, dict))
        elif isinstance(payload, dict) and (payload.get("title") or payload.get("source_url")):
            records.append(payload)
    # JSON first so listing HTML does not hide richer excerpts.
    seen: set[str] = set()
    unique: list[dict] = []
    for record in records:
        key = record.get("source_url") or record.get("title") or ""
        if key in seen:
            continue
        seen.add(key)
        unique.append(record)
    return unique, f"anao_file:{path}"


def parse_listing_html(html: str, *, base_url: str = ANAO_HOME) -> list[dict]:
    """Best-effort Drupal listing: work / pubs performance-audit pages."""
    soup = BeautifulSoup(html or "", "lxml")
    records: list[dict] = []
    seen: set[str] = set()
    for anchor in soup.select('a[href*="/work/performance-audit/"], a[href*="/work/"]'):
        href = (anchor.get("href") or "").strip()
        title = " ".join(anchor.get_text(" ", strip=True).split())
        if not href or not title or len(title) < 12:
            continue
        if any(skip in title.lower() for skip in ("work program", "in-progress", "subscribe")):
            continue
        url = urljoin(base_url, href)
        if "/work/" not in url or url in seen:
            continue
        parent = anchor.find_parent(["article", "li", "div"]) or anchor.parent
        block = parent.get_text("\n", strip=True) if parent else ""
        record = _record_from_block(title=title, url=url, block=block)
        if record["source_url"] in seen:
            continue
        seen.add(record["source_url"])
        records.append(record)
    if records:
        return records
    # Fallback: heading + published/entity text even without useful links.
    text = soup.get_text("\n", strip=True)
    for match in _REPORT_NO.finditer(text):
        window = text[match.start() : match.start() + 600]
        title_line = next(
            (
                line.strip()
                for line in window.splitlines()
                if line.strip() and "auditor-general" not in line.lower() and "published" not in line.lower()
            ),
            None,
        )
        if not title_line:
            continue
        records.append(_record_from_block(title=title_line, url=base_url, block=window))
    return records


def _record_from_block(*, title: str, url: str, block: str) -> dict:
    report = _REPORT_NO.search(block) or _REPORT_NO.search(title)
    published = _PUBLISHED.search(block)
    entity = _field_after(block, "Entity")
    portfolio = _field_after(block, "Portfolio")
    return {
        "title": title,
        "source_url": url,
        "report_number": report.group(0).strip() if report else None,
        "report_no": report.group("num") if report else None,
        "report_year": re.sub(r"\s+", "", report.group("year")) if report else None,
        "published_on": published.group("d") if published else None,
        "entity": entity,
        "portfolio": portfolio,
        "excerpt": block[:2000] if block else None,
        "work_type": "performance_audit",
    }


def _field_after(text: str, label: str) -> str | None:
    match = re.search(rf"{label}\s+([^\n]+)", text or "", re.I)
    if not match:
        return None
    value = match.group(1).strip()
    if value.lower() in {"contact", "please direct enquiries through our contact page."}:
        return None
    return value or None


def item_from_record(row: dict) -> ScrutinyItemIn | None:
    title = (row.get("title") or "").strip()
    url = row.get("source_url") or row.get("url")
    if not title:
        return None
    report_number = row.get("report_number") or row.get("report")
    report_no = row.get("report_no")
    report_year = row.get("report_year")
    if not report_number and report_no and report_year:
        report_number = f"Auditor-General Report No. {report_no} of {report_year}"
    key_bit = slug(report_number or url or title)[:80]
    agency_name = row.get("entity") or row.get("agency_name")
    return ScrutinyItemIn(
        source_key=f"anao:{key_bit}",
        item_type="anao",
        title=title,
        published_on=parse_flexible_date(row.get("published_on") or row.get("published")),
        source="anao",
        source_url=url,
        summary=(row.get("summary") or row.get("objective") or "")[:500] or None,
        agency_name=agency_name or None,
        agency_slug=slug(agency_name)[:80] if agency_name else None,
        portfolio=row.get("portfolio") or None,
        confidence=0.9 if url else 0.6,
        identifiers={
            "report_number": report_number,
            "report_no": report_no,
            "report_year": report_year,
            "work_type": row.get("work_type") or "performance_audit",
            "entity": agency_name,
            "license_note": LICENSE_NOTE,
        },
    )


def named_instrument_from_title(item: ScrutinyItemIn) -> InstrumentIn | None:
    """Only when the ANAO title itself names a program / fund / scheme."""
    match = _NAMED_INSTRUMENT.search(item.title)
    if not match:
        return None
    title = match.group(1)
    if title.lower().startswith("the "):
        title = title[4:]
    if len(title.split()) < 2:
        return None
    return InstrumentIn(
        source_key=f"instrument:anao:{slug(title)[:80]}",
        title=title,
        kind="program",
        status="sourced",
        confidence=0.55,
        agency_name=item.agency_name,
        agency_slug=item.agency_slug,
        portfolio=item.portfolio,
        announced_on=item.published_on,
        source="anao",
        source_url=item.source_url,
        notes="Named in an ANAO report title. Not a Budget Paper row.",
        identifiers={"named_in_scrutiny": item.source_key, "report_title": item.title},
    )


def outcome_from_record(
    row: dict,
    item: ScrutinyItemIn,
    instrument: InstrumentIn | None,
) -> OutcomeIn | None:
    text = " ".join(
        part
        for part in (
            row.get("excerpt"),
            row.get("findings"),
            row.get("summary"),
            row.get("recommendations"),
        )
        if part
    )
    signal, confidence, notes = parse_audit_signal(text)
    if confidence <= 0:
        return None
    return OutcomeIn(
        source_key=f"outcome:{item.source_key}",
        outcome_type="audit_finding",
        signal=signal,  # type: ignore[arg-type]
        occurred_on=item.published_on,
        source="anao",
        source_url=item.source_url,
        notes=notes,
        confidence=confidence,
        instrument_source_key=instrument.source_key if instrument else None,
        scrutiny_source_key=item.source_key,
        agency_name=item.agency_name,
        agency_slug=item.agency_slug,
        identifiers={"phrases": notes, "report_number": item.identifiers.get("report_number")},
    )


def parse_audit_signal(text: str) -> tuple[str, float, str]:
    """Map parseable ANAO finding language. Empty text → unknown / no outcome."""
    if not (text or "").strip():
        return "unknown", 0.0, ""
    phrases: list[str] = []
    signal = "unknown"
    for match in _ADVERSE.finditer(text):
        phrases.append(match.group(0).lower())
        signal = worse_signal(signal, "adverse")
    for match in _PARTIAL.finditer(text):
        phrases.append(match.group(0).lower())
        signal = worse_signal(signal, "partial")
    for match in _MET.finditer(text):
        phrases.append(match.group(0).lower())
        signal = worse_signal(signal, "met")
    if signal == "unknown" or not phrases:
        return "unknown", 0.0, ""
    confidence = 0.74 if signal in {"partial", "adverse"} else 0.62
    # Deduplicate while keeping order.
    seen: set[str] = set()
    unique = []
    for phrase in phrases:
        if phrase not in seen:
            seen.add(phrase)
            unique.append(phrase)
    return signal, confidence, "; ".join(unique)
