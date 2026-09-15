"""Parliamentary Handbook ingest (parliamentarians, tenure, ministries, party).

Live: handbookapi.aph.gov.au OData (browser-like UA).
Fallback: committed fixtures under fixtures/live/handbook/.

Does **not** invent officials. APS secretaries are out of scope — the
Handbook covers parliamentarians only.

Target tables (existing foundation):
  - handbook_entries / handbook_roles / handbook_tenure (provenance)
  - people (shared person key)
  - roles / person_roles (promoted occupancy)
"""

from __future__ import annotations

from pathlib import Path

from aus_gov_ingest.http import AphClient
from aus_gov_ingest.models import (
    HandbookEntryIn,
    HandbookRoleIn,
    HandbookTenureIn,
    PersonIn,
    SourceBatch,
)
from aus_gov_ingest.people import canonical_slug, slug as slugify
from aus_gov_ingest.sources.util import parse_flexible_date

HANDBOOK_HOME = "https://handbook.aph.gov.au"
HANDBOOK_API = "https://handbookapi.aph.gov.au"
INDIVIDUALS_URL = f"{HANDBOOK_API}/api/individuals"
MINISTRY_URL = f"{HANDBOOK_API}/api/ministryrecords"
MINISTRY_RECORDS_URL = MINISTRY_URL
SHADOW_MINISTRY_URL = f"{HANDBOOK_API}/api/shadowministryrecords"
MINISTRIES_URL = f"{HANDBOOK_API}/api/StatisticalInformation/Ministries"
SITTING_DAYS_URL = f"{HANDBOOK_API}/api/StatisticalInformation/SittingDaysForYear"
APH_PARLIAMENTARIAN_URL = "https://www.aph.gov.au/api/parliamentarian/?q=&mem=0&page=1"
APH_MEMBER_URL = "https://www.aph.gov.au/Senators_and_Members/Parliamentarian?MPID={phid}"

ENDPOINTS = {
    "home": HANDBOOK_HOME,
    "individuals": INDIVIDUALS_URL,
    "ministry_records": MINISTRY_RECORDS_URL,
    "shadow_ministry_records": SHADOW_MINISTRY_URL,
    "ministries": MINISTRIES_URL,
    "sitting_days": SITTING_DAYS_URL,
    "aph_parliamentarian": APH_PARLIAMENTARIAN_URL,
}

LICENSE_NOTE = (
    "© Commonwealth of Australia. Parliamentary Handbook. "
    "Attribute the Parliament of Australia; research / non-commercial."
)


def default_handbook_dir() -> Path:
    here = Path(__file__).resolve()
    for parent in here.parents:
        candidate = parent / "fixtures" / "live" / "handbook"
        if candidate.is_dir():
            return candidate
    return here.parents[3] / "fixtures" / "live" / "handbook"


def parse_individuals_odata(payload: object) -> list[PersonIn]:
    """Map Handbook OData ``{value: [...]}`` (or a bare list) to PersonIn.

    Only fields present on the payload are used. No invented names.
    """
    if payload is None:
        return []
    rows = payload.get("value") if isinstance(payload, dict) else payload
    if not isinstance(rows, list):
        return []
    people: list[PersonIn] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        name = (row.get("DisplayName") or "").strip()
        phid = row.get("PHID")
        if not name or not phid:
            continue
        chamber = None
        electorate = (row.get("Electorate") or "").strip() or None
        senate_state = (row.get("SenateState") or row.get("StateAbbrev") or "").strip()
        if electorate:
            chamber = "House"
        elif senate_state or row.get("SenateState"):
            chamber = "Senate"
        people.append(
            PersonIn(
                slug=slugify(name) or slugify(str(phid)),
                name=name,
                party=(row.get("Party") or None),
                portfolio=None,
                organisation=None,
                role_title="Senator" if chamber == "Senate" else ("MP" if chamber == "House" else None),
                aph_url=f"{HANDBOOK_HOME}/",
                bio=None,
            )
        )
    return people


class HandbookSource:
    """Fetch current parliamentarians and time-bounded roles from the Handbook API."""

    name = "handbook"
    HOME = HANDBOOK_HOME
    ENDPOINTS = ENDPOINTS

    def __init__(
        self,
        *,
        path: Path | str | None = None,
        client: AphClient | None = None,
        current_only: bool = True,
    ) -> None:
        self.path = Path(path) if path else None
        self.client = client or AphClient()
        self.current_only = current_only

    def fetch(self, *, limit: int = 0, incremental_keys: set[str] | None = None) -> SourceBatch:
        errors: list[str] = []
        transport = "handbookapi"
        individuals: list[dict] = []
        ministries: list[dict] = []

        if self.path:
            individuals, ministries, transport = self._from_path(self.path)
        else:
            try:
                individuals = self._fetch_individuals(limit=limit)
                ministries = self._fetch_ministries(individuals)
            except Exception as exc:
                errors.append(f"handbookapi: {exc}")
                try:
                    individuals, ministries, transport = self._from_path(default_handbook_dir())
                    transport = f"fixture_fallback:{transport}"
                except Exception as fallback_exc:
                    errors.append(f"fixture: {fallback_exc}")

        known = incremental_keys or set()
        entries: list[HandbookEntryIn] = []
        by_phid: dict[str, list[dict]] = {}
        for row in ministries:
            by_phid.setdefault(str(row.get("PHID") or ""), []).append(row)

        for row in individuals:
            phid = str(row.get("PHID") or "").strip()
            if not phid:
                continue
            key = f"handbook:{phid}"
            if key in known:
                continue
            entry = entry_from_individual(row, ministries=by_phid.get(phid, []))
            if entry:
                entries.append(entry)
            if limit and len(entries) >= limit:
                break

        return SourceBatch(
            source=self.name,
            people=[e.person for e in entries],
            handbook_entries=entries,
            meta={
                "status": "ok" if entries else "empty",
                "home": self.HOME,
                "api": HANDBOOK_API,
                "transport": transport,
                "license_note": LICENSE_NOTE,
                "gaps": (
                    "APS secretaries and other non-parliamentarians are not in the "
                    "Handbook. Use directory.gov.au / an APS source for agency heads."
                ),
                "limit": limit,
                "skipped_existing": len(known),
                "errors": errors,
                "people": len(entries),
                "roles": sum(len(e.roles) for e in entries),
                "tenure": sum(len(e.tenure) for e in entries),
                "schema": "infra/postgres/005_handbook.sql + 007_accountability.sql",
                "endpoints": ENDPOINTS,
                "note": (
                    "Live Handbook OData plus fixture fallback. Does not invent "
                    "officials. Promote tenures into person_roles on persist."
                ),
            },
        )

    def _fetch_individuals(self, *, limit: int) -> list[dict]:
        page_size = 50 if not limit else min(50, max(limit, 1))
        rows: list[dict] = []
        skip = 0
        filt = "InCurrentParliament eq 'True'" if self.current_only else None
        while True:
            url = f"{INDIVIDUALS_URL}?$top={page_size}&$skip={skip}&$orderby=FamilyName,GivenName"
            if filt:
                url += f"&$filter={filt}"
            payload = self.client.get_json(url, referer=HANDBOOK_HOME)
            batch = payload.get("value") or []
            if not batch:
                break
            rows.extend(batch)
            skip += len(batch)
            if limit and len(rows) >= limit:
                return rows[:limit]
            if len(batch) < page_size:
                break
            if skip > 2500:
                break
        return rows

    def _fetch_ministries(self, individuals: list[dict]) -> list[dict]:
        # Current ministries (open-ended RDateEnd) plus per-PHID history when few people.
        rows: list[dict] = []
        try:
            payload = self.client.get_json(
                f"{MINISTRY_URL}?$filter=RDateEnd eq ''&$top=400",
                referer=HANDBOOK_HOME,
            )
            rows.extend(payload.get("value") or [])
        except Exception:
            pass
        if len(individuals) <= 20:
            seen = {(r.get("PHID"), r.get("Role"), r.get("RDateStart"), r.get("Entity")) for r in rows}
            for person in individuals:
                phid = person.get("PHID")
                if not phid:
                    continue
                try:
                    extra = self.client.get_json(
                        f"{MINISTRY_URL}?$filter=PHID eq '{phid}'&$top=40",
                        referer=HANDBOOK_HOME,
                    )
                except Exception:
                    continue
                for row in extra.get("value") or []:
                    key = (row.get("PHID"), row.get("Role"), row.get("RDateStart"), row.get("Entity"))
                    if key in seen:
                        continue
                    seen.add(key)
                    rows.append(row)
        return rows

    def _from_path(self, path: Path) -> tuple[list[dict], list[dict], str]:
        if not path.exists():
            raise FileNotFoundError(f"Handbook path not found: {path}")
        individuals: list[dict] = []
        ministries: list[dict] = []
        files = [path] if path.is_file() else sorted(path.glob("*.json"))
        if not files:
            raise FileNotFoundError(f"No Handbook JSON in {path}")
        import json

        for file in files:
            payload = json.loads(file.read_text(encoding="utf-8"))
            rows = payload.get("value") if isinstance(payload, dict) else payload
            if not isinstance(rows, list):
                continue
            if file.name.startswith("ministry") or (rows and "Role" in rows[0] and "PHID" in rows[0]):
                ministries.extend(rows)
            else:
                individuals.extend(rows)
        return individuals, ministries, f"handbook_file:{path}"


def entry_from_individual(row: dict, *, ministries: list[dict] | None = None) -> HandbookEntryIn | None:
    phid = str(row.get("PHID") or "").strip()
    if not phid:
        return None
    display = (row.get("DisplayName") or "").strip()
    name = _person_name(row)
    party = (row.get("Party") or None) or None
    electorate = (row.get("Electorate") or None) or None
    chamber = _chamber(row)
    person = PersonIn(
        slug=canonical_slug(name),
        name=name,
        role_title=_role_title(row, ministries or []),
        party=party,
        portfolio=_current_portfolio(ministries or []),
        organisation="Parliament of Australia",
        aph_url=APH_MEMBER_URL.format(phid=phid),
        bio=None,
    )
    roles = _roles_from_individual(row, ministries or [])
    tenure = _tenure_from_individual(row)
    return HandbookEntryIn(
        handbook_key=phid,
        person=person,
        display_name=display or name,
        chamber=chamber,
        electorate=electorate or (row.get("SenateState") or None),
        party=party,
        aph_url=f"{HANDBOOK_HOME}/parliamentarian/{phid}",
        roles=roles,
        tenure=tenure,
    )


def _person_name(row: dict) -> str:
    given = " ".join(
        p for p in [(row.get("GivenName") or "").strip(), (row.get("MiddleNames") or "").strip()] if p
    )
    family = (row.get("FamilyName") or "").strip().title()
    display = (row.get("DisplayName") or "").strip()
    built = f"{given} {family}".strip()
    return built or display or "Unknown"


def _chamber(row: dict) -> str:
    kinds = row.get("MPorSenator") or []
    if isinstance(kinds, str):
        kinds = [kinds]
    kinds_l = {str(k).lower() for k in kinds}
    if "senator" in kinds_l and "member" not in kinds_l:
        return "Senate"
    if row.get("SenateState") and not row.get("Electorate"):
        return "Senate"
    if "member" in kinds_l:
        return "House of Representatives"
    return "Senate" if row.get("SenateState") else "House of Representatives"


def _role_title(row: dict, ministries: list[dict]) -> str | None:
    current = [m for m in ministries if not parse_flexible_date(m.get("RDateEnd"), open_if_today=True)]
    if current:
        return _ministry_title(current[0])
    kinds = row.get("MPorSenator") or []
    if isinstance(kinds, list) and kinds:
        return str(kinds[0])
    return None


def _current_portfolio(ministries: list[dict]) -> str | None:
    for row in ministries:
        if parse_flexible_date(row.get("RDateEnd"), open_if_today=True):
            continue
        entity = (row.get("Entity") or "").strip()
        if entity:
            return entity
    return None


def _ministry_title(row: dict) -> str:
    role = (row.get("Role") or "Minister").strip()
    prep = (row.get("Prep") or "").strip()
    entity = (row.get("Entity") or "").strip()
    parts = [role]
    if prep and entity:
        parts.append(f"{prep} {entity}")
    elif entity:
        parts.append(entity)
    return " ".join(parts)


def _roles_from_individual(row: dict, ministries: list[dict]) -> list[HandbookRoleIn]:
    roles: list[HandbookRoleIn] = []
    seen: set[tuple] = set()

    def add(item: HandbookRoleIn) -> None:
        key = (item.role_title, item.started_on, item.role_kind)
        if key in seen or not item.role_title:
            return
        seen.add(key)
        roles.append(item)

    party = (row.get("Party") or "").strip()
    if party:
        add(
            HandbookRoleIn(
                role_title=party,
                role_kind="party",
                started_on=None,
                ended_on=None,
                notes="Current Handbook party field",
            )
        )
    for block in row.get("PartyParliamentaryService") or []:
        add(_role_from_service_block(block))
        for nested in block.get("SecondaryService") or []:
            add(_role_from_service_block(nested))
    for ministry in ministries:
        add(
            HandbookRoleIn(
                role_title=_ministry_title(ministry),
                role_kind="ministry",
                started_on=parse_flexible_date(ministry.get("RDateStart"), open_if_today=True),
                ended_on=parse_flexible_date(ministry.get("RDateEnd"), open_if_today=True),
                notes=ministry.get("Ministry") or None,
            )
        )
    return roles


def _role_from_service_block(block: dict) -> HandbookRoleIn:
    ros_type = (block.get("RoSType") or "").strip()
    value = (block.get("Value") or "").strip()
    kind = "parliamentary"
    title = value or ros_type
    if "party" in ros_type.lower():
        kind = "party"
        title = value or ros_type
    elif ros_type and ros_type != "Parliamentary Service":
        kind = slugish(ros_type)
        title = f"{ros_type}: {value}" if value and value != ros_type else (value or ros_type)
    return HandbookRoleIn(
        role_title=title[:240],
        role_kind=kind,
        started_on=parse_flexible_date(block.get("DateStart"), open_if_today=True),
        ended_on=parse_flexible_date(block.get("DateEnd"), open_if_today=True),
        notes=ros_type or None,
    )


def slugish(text: str) -> str:
    return re_sub_slug(text)


def re_sub_slug(text: str) -> str:
    import re

    return re.sub(r"[^a-z0-9]+", "-", (text or "").lower()).strip("-")[:40] or "role"


def _tenure_from_individual(row: dict) -> list[HandbookTenureIn]:
    tenure: list[HandbookTenureIn] = []
    parliaments = [int(p) for p in (row.get("RepresentedParliaments") or []) if str(p).isdigit()]
    latest = max(parliaments) if parliaments else None
    chamber = _chamber(row)
    for block in row.get("ElectorateService") or []:
        tenure.append(
            HandbookTenureIn(
                chamber="House of Representatives",
                electorate=block.get("Electorate") or None,
                parliament_number=latest,
                started_on=parse_flexible_date(block.get("ServiceStart"), open_if_today=True),
                ended_on=parse_flexible_date(block.get("ServiceEnd"), open_if_today=True),
            )
        )
    if chamber == "Senate":
        senate_starts = [
            parse_flexible_date(b.get("DateStart"), open_if_today=True)
            for b in (row.get("PartyParliamentaryService") or [])
            if (b.get("RoSType") or "") == "Parliamentary Service"
        ]
        senate_ends = [
            parse_flexible_date(b.get("DateEnd"), open_if_today=True)
            for b in (row.get("PartyParliamentaryService") or [])
            if (b.get("RoSType") or "") == "Parliamentary Service"
        ]
        tenure.append(
            HandbookTenureIn(
                chamber="Senate",
                electorate=row.get("SenateState") or None,
                parliament_number=latest,
                started_on=next((d for d in senate_starts if d), None),
                ended_on=next((d for d in reversed(senate_ends) if d), None),
            )
        )
    elif not tenure:
        tenure.append(
            HandbookTenureIn(
                chamber=chamber,
                electorate=row.get("Electorate") or row.get("SenateState") or None,
                parliament_number=latest,
                started_on=None,
                ended_on=None,
            )
        )
    return tenure
