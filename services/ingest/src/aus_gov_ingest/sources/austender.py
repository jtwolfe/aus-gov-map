"""AusTender contract-notice ingest (first pass).

Prefers the public OCDS API on api.tenders.gov.au over HTML search.
Default window is recent published contracts, sorted high-value first,
capped by ``--limit``. Fixture fallback: fixtures/live/austender/.
"""

from __future__ import annotations

import json
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from aus_gov_ingest.http import AphClient
from aus_gov_ingest.models import InstrumentIn, SourceBatch
from aus_gov_ingest.sources.util import fixture_live_dir, parse_amount, parse_flexible_date, slug

AUSTENDER_HOME = "https://www.tenders.gov.au"
SEARCH = f"{AUSTENDER_HOME}/Search/CnAdvancedSearch"
WEEKLY = f"{AUSTENDER_HOME}/Reports/CnWeeklyExportList"
OCDS_DATES = "https://api.tenders.gov.au/ocds/findByDates/contractPublished/{start}/{end}"
DATA_GOV = "https://data.gov.au/data/dataset/austender-contract-notice-export"
DATA_GOV_HIST = "https://data.gov.au/data/dataset/historical-australian-government-contract-data"

ENDPOINTS = {
    "home": AUSTENDER_HOME,
    "search": SEARCH,
    "weekly_export": WEEKLY,
    "ocds": "https://api.tenders.gov.au/ocds/findByDates/contractPublished/",
    "data_gov": DATA_GOV,
    "data_gov_historical": DATA_GOV_HIST,
    "grantconnect": "https://www.grants.gov.au",
}

LICENSE_NOTE = (
    "© Commonwealth of Australia. AusTender contract notices. "
    "Typically CC BY 3.0 AU. Attribute the Department of Finance."
)

CN_PAGE = "https://www.tenders.gov.au/Cn/Show/{cn}"


def default_austender_dir() -> Path:
    return fixture_live_dir("austender")


class AustenderSource:
    name = "austender"
    HOME = AUSTENDER_HOME
    ENDPOINTS = ENDPOINTS

    def __init__(
        self,
        *,
        path: Path | str | None = None,
        client: AphClient | None = None,
        days: int = 7,
    ) -> None:
        self.path = Path(path) if path else None
        self.client = client or AphClient()
        self.days = days

    def fetch(self, *, limit: int = 0, incremental_keys: set[str] | None = None) -> SourceBatch:
        errors: list[str] = []
        transport = "ocds"
        records: list[dict] = []

        if self.path:
            records, transport = load_austender_path(self.path)
        else:
            try:
                records = self._fetch_live(limit=limit or 25)
            except Exception as exc:
                errors.append(f"ocds: {exc}")
                try:
                    records, transport = load_austender_path(default_austender_dir())
                    transport = f"fixture_fallback:{transport}"
                except Exception as fallback_exc:
                    errors.append(f"fixture: {fallback_exc}")

        known = incremental_keys or set()
        instruments: list[InstrumentIn] = []
        seen: set[str] = set()
        parsed = [item for item in (instrument_from_cn(row) for row in records) if item]
        parsed.sort(key=lambda item: item.amount_aud or 0, reverse=True)
        for item in parsed:
            if item.source_key in known or item.source_key in seen:
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
                "days": self.days,
                "skipped_existing": len(known),
                "errors": errors,
                "instruments": len(instruments),
                "high_value_first": True,
                "endpoints": ENDPOINTS,
                "schema": "infra/postgres/007_accountability.sql (instruments type contract)",
                "note": (
                    "AusTender OCDS contract notices into instruments (type contract). "
                    "Agency linked by name when possible. GrantConnect stays a sibling "
                    "for type grant. No invented CNs."
                ),
            },
        )

    def _fetch_live(self, *, limit: int) -> list[dict]:
        end = datetime.now(timezone.utc)
        start = end - timedelta(days=max(self.days, 1))
        url = OCDS_DATES.format(
            start=start.strftime("%Y-%m-%dT00:00:00Z"),
            end=end.strftime("%Y-%m-%dT23:59:59Z"),
        )
        payload = self.client.get_json(url, referer=AUSTENDER_HOME)
        releases = payload.get("releases") if isinstance(payload, dict) else payload
        if not isinstance(releases, list) or not releases:
            raise RuntimeError(f"OCDS empty at {url}")
        # Keep a bounded recent slice; high-value sort happens after parse.
        cap = max(limit * 4, 40)
        return [r for r in releases if isinstance(r, dict)][:cap]


def load_austender_path(path: Path) -> tuple[list[dict], str]:
    if not path.exists():
        raise FileNotFoundError(f"AusTender path not found: {path}")
    files = [path] if path.is_file() else sorted(p for p in path.glob("*.json") if p.is_file())
    if not files:
        raise FileNotFoundError(f"No AusTender JSON in {path}")
    records: list[dict] = []
    for file in files:
        payload = json.loads(file.read_text(encoding="utf-8"))
        if isinstance(payload, list):
            records.extend(r for r in payload if isinstance(r, dict))
        elif isinstance(payload, dict) and isinstance(payload.get("releases"), list):
            records.extend(r for r in payload["releases"] if isinstance(r, dict))
        elif isinstance(payload, dict) and isinstance(payload.get("contracts"), list):
            records.extend(r for r in payload["contracts"] if isinstance(r, dict))
        elif isinstance(payload, dict) and (payload.get("CN ID") or payload.get("cn") or payload.get("id")):
            records.append(payload)
    return records, f"austender_file:{path}"


def instrument_from_cn(row: dict) -> InstrumentIn | None:
    """Map an OCDS release or a flat CN dict to InstrumentIn."""
    if row.get("awards") or row.get("contracts") or row.get("parties"):
        return _from_ocds_release(row)
    return _from_flat_cn(row)


def _from_ocds_release(row: dict) -> InstrumentIn | None:
    contracts = row.get("contracts") or []
    contract = contracts[0] if contracts else {}
    awards = row.get("awards") or []
    award = awards[0] if awards else {}
    cn = contract.get("id") or (award.get("id") or "").split("-")[0]
    if not cn:
        return None
    parties = row.get("parties") or []
    agency = _party_name(parties, ("procuringEntity", "buyer"))
    supplier = _party_name(parties, ("supplier",))
    if not supplier:
        suppliers = (award.get("suppliers") or []) if award else []
        if suppliers:
            supplier = suppliers[0].get("name")
    value = (contract.get("value") or {}).get("amount")
    period = contract.get("period") or {}
    title = (
        contract.get("description")
        or contract.get("title")
        or award.get("title")
        or f"Contract notice {cn}"
    )
    source_url = CN_PAGE.format(cn=cn)
    return InstrumentIn(
        source_key=f"austender:{cn}",
        title=str(title)[:240],
        kind="contract",
        status="sourced",
        confidence=0.85,
        agency_name=agency,
        agency_slug=slug(agency)[:80] if agency else None,
        announced_on=_date(contract.get("dateSigned") or row.get("date") or award.get("date")),
        commenced_on=_date(period.get("startDate")),
        ended_on=_date(period.get("endDate")),
        amount_aud=parse_amount(value),
        source="austender",
        source_url=source_url,
        supplier_name=supplier,
        notes=LICENSE_NOTE,
        identifiers={
            "CN": cn,
            "ocid": row.get("ocid"),
            "supplier": supplier,
            "currency": (contract.get("value") or {}).get("currency") or "AUD",
            "contract_title": contract.get("title"),
            "license_note": LICENSE_NOTE,
        },
    )


def _from_flat_cn(row: dict) -> InstrumentIn | None:
    cn = row.get("CN ID") or row.get("cn") or row.get("CN") or row.get("id")
    if not cn:
        return None
    cn = str(cn).strip()
    if not cn.upper().startswith("CN"):
        cn = f"CN{cn}"
    agency = row.get("agency") or row.get("agency_name") or row.get("Agency")
    supplier = row.get("supplier") or row.get("supplier_name") or row.get("Supplier Name")
    title = row.get("title") or row.get("description") or row.get("Category") or f"Contract notice {cn}"
    return InstrumentIn(
        source_key=f"austender:{cn}",
        title=str(title)[:240],
        kind="contract",
        status="sourced",
        confidence=0.8,
        agency_name=agency,
        agency_slug=slug(agency)[:80] if agency else None,
        announced_on=_date(row.get("publish_date") or row.get("published_on") or row.get("Start Date")),
        commenced_on=_date(row.get("start_date") or row.get("Start Date")),
        ended_on=_date(row.get("end_date") or row.get("End Date")),
        amount_aud=parse_amount(row.get("amount_aud") or row.get("value") or row.get("Value")),
        source="austender",
        source_url=row.get("source_url") or CN_PAGE.format(cn=cn),
        supplier_name=supplier,
        identifiers={
            "CN": cn,
            "supplier": supplier,
            "license_note": LICENSE_NOTE,
            **{k: row.get(k) for k in ("UNSPSC", "category", "funded_by_source_key") if row.get(k)},
        },
    )


def _party_name(parties: list[dict], roles: tuple[str, ...]) -> str | None:
    for party in parties:
        party_roles = party.get("roles") or []
        if any(role in party_roles for role in roles):
            name = party.get("name")
            if name:
                return name
    return None


def _date(value) -> date | None:
    return parse_flexible_date(value)
