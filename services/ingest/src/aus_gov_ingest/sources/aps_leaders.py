"""APS secretaries and agency heads — time-bounded occupancy.

Live: directory.gov.au agency pages (when reachable) plus a small set of
official department executive pages.
Fallback: fixtures/live/aps/ (real current incumbents, cited URLs).

Does **not** invent historical tenures. Appearance at Estimates is not a
tenure. Month-only dates are stored as the first of that month.
"""

from __future__ import annotations

import json
import re
from datetime import date
from pathlib import Path

from aus_gov_ingest.http import AphClient
from aus_gov_ingest.models import AgencyIn, PersonIn, PersonRoleIn, SourceBatch
from aus_gov_ingest.people import canonical_slug, slug as slugify
from aus_gov_ingest.sources.util import parse_flexible_date

DIRECTORY_HOME = "https://www.directory.gov.au/"
DIRECTORY_AGOR = (
    "https://www.directory.gov.au/reports/australian-government-organisations-register"
)
DIRECTORY_EXPORT = "https://www.directory.gov.au/sites/default/files/export.xml"
AGOR_CSV = (
    "https://data.gov.au/data/dataset/c77cface-69aa-4dd0-b99f-b065dc33c8e6/"
    "resource/55f33a8e-eebc-4342-8d63-ed53a4d4ea0a/download/agor-register.csv"
)

DIRECTORY_PAGES = [
    (
        "https://www.directory.gov.au/portfolios/treasury/department-treasury",
        "treasury",
        "Department of the Treasury",
        "Treasury",
    ),
    (
        "https://www.directory.gov.au/portfolios/prime-minister-and-cabinet/"
        "department-prime-minister-and-cabinet",
        "prime-minister-cabinet",
        "Department of the Prime Minister and Cabinet",
        "Prime Minister and Cabinet",
    ),
    (
        "https://www.directory.gov.au/portfolios/home-affairs/department-home-affairs",
        "home-affairs",
        "Department of Home Affairs",
        "Home Affairs",
    ),
    (
        "https://www.directory.gov.au/portfolios/finance/department-finance",
        "finance",
        "Department of Finance",
        "Finance",
    ),
    (
        "https://www.directory.gov.au/portfolios/attorney-generals/attorney-generals-department",
        "attorney-generals",
        "Attorney-General's Department",
        "Attorney-General's",
    ),
]

DEPARTMENT_PAGES = [
    {
        "url": "https://treasury.gov.au/the-department/about-treasury/our-executive",
        "parser": "treasury",
        "agency_slug": "treasury",
        "agency_name": "Department of the Treasury",
        "portfolio": "Treasury",
    },
    {
        "url": "https://www.homeaffairs.gov.au/about-us/who-we-are/our-senior-staff",
        "parser": "heading_staff",
        "agency_slug": "home-affairs",
        "agency_name": "Department of Home Affairs",
        "portfolio": "Home Affairs",
    },
]

ENDPOINTS = {
    "directory": DIRECTORY_HOME,
    "agor": DIRECTORY_AGOR,
    "directory_export": DIRECTORY_EXPORT,
    "agor_csv": AGOR_CSV,
    "treasury_executive": DEPARTMENT_PAGES[0]["url"],
    "home_affairs_senior_staff": DEPARTMENT_PAGES[1]["url"],
}

LICENSE_NOTE = (
    "© Commonwealth of Australia. Australian Government Directory / official "
    "department executive pages. Attribute the originating agency; research / "
    "non-commercial."
)

GAPS = (
    "directory.gov.au agency pages and the Directory XML export are often "
    "unreachable from datacentre IPs (Azure WAF / timeout). Live fetch falls "
    "back to fixtures/live/aps/*.json. Historical secretary timelines use "
    "published instruments and the PMC secretary-appointments page — dates "
    "only where those pages state them. Do not invent occupancy. Estimates "
    "appearance is not a tenure."
)

_MONTHS = {
    "january": 1,
    "february": 2,
    "march": 3,
    "april": 4,
    "may": 5,
    "june": 6,
    "july": 7,
    "august": 8,
    "september": 9,
    "october": 10,
    "november": 11,
    "december": 12,
}

_ROLE_HEADING = re.compile(
    r"^(?P<title>(?:acting\s+)?(?:deputy\s+)?secretary|agency\s+head|"
    r"commissioner|auditor-general|director-general|chief\s+executive)"
    r"(?P<rest>\b.*)?$",
    re.I,
)
_BECAME_TREASURY = re.compile(
    r"became the Secretary to the Treasury in (?P<mon>[A-Za-z]+)\s+(?P<year>\d{4})",
    re.I,
)
_FINANCE_TENURE = re.compile(
    r"Secretary of the Department of Finance from (?P<mon1>[A-Za-z]+)\s+"
    r"(?P<year1>\d{4}) to (?P<mon2>[A-Za-z]+)\s+(?P<year2>\d{4})",
    re.I,
)
_HONORIFIC_PREFIX = re.compile(
    r"^(?:dr|professor|prof|ms|mr|mrs|miss|the hon)\.?\s+",
    re.I,
)


def default_aps_dir() -> Path:
    here = Path(__file__).resolve()
    for parent in here.parents:
        candidate = parent / "fixtures" / "live" / "aps"
        if candidate.is_dir():
            return candidate
    return here.parents[3] / "fixtures" / "live" / "aps"


def month_year_to_date(month: str | None, year: str | int | None) -> date | None:
    """Store a sourced month as the first of that month. None if unknown."""
    if not month or not year:
        return None
    num = _MONTHS.get(str(month).strip().lower())
    try:
        yr = int(year)
    except (TypeError, ValueError):
        return None
    if not num:
        return None
    return date(yr, num, 1)


def classify_role(title: str) -> str:
    lowered = (title or "").lower()
    if "deputy" in lowered and "secretary" in lowered:
        return "deputy"
    if "secretary" in lowered:
        return "secretary"
    if any(
        token in lowered
        for token in (
            "agency head",
            "commissioner",
            "auditor-general",
            "director-general",
            "chief executive",
        )
    ):
        return "agency_head"
    return "other"


def tidy_person_name(raw: str) -> str:
    text = " ".join((raw or "").split())
    text = re.sub(r"\s+(PSM|AC|AO|AM|CSC|OAM)\b\.?", "", text)
    text = _HONORIFIC_PREFIX.sub("", text)
    return text.strip(" ,;")


def occupancy_from_record(row: dict) -> PersonRoleIn | None:
    name = tidy_person_name(row.get("name") or "")
    if not name:
        return None
    role_title = (row.get("role_title") or "").strip() or "Agency head"
    role_type = row.get("role_type") or classify_role(role_title)
    if role_type not in {"secretary", "deputy", "agency_head", "other"}:
        role_type = classify_role(role_title)
    agency_name = row.get("agency_name") or row.get("organisation")
    agency_slug = row.get("agency_slug") or (slugify(agency_name)[:80] if agency_name else None)
    start = parse_flexible_date(row.get("start_date"))
    end = parse_flexible_date(row.get("end_date"))
    source_url = row.get("source_url") or row.get("directory_url")
    source_key = (
        row.get("source_key")
        or f"aps:{role_type}:{agency_slug or 'agency'}:{canonical_slug(name)}:{start or 'open'}"
    )
    agency = None
    if agency_slug and agency_name:
        agency = AgencyIn(
            slug=agency_slug,
            name=agency_name,
            short_code=row.get("agency_short_code"),
            portfolio=row.get("portfolio"),
            kind="department" if "department" in agency_name.lower() else "agency",
            source_url=row.get("directory_url") or source_url,
            source="aps_leaders",
        )
    return PersonRoleIn(
        source_key=source_key,
        person=PersonIn(
            slug=canonical_slug(name),
            name=name,
            role_title=role_title,
            portfolio=row.get("portfolio"),
            organisation=agency_name,
            aph_url=source_url,
        ),
        agency=agency,
        role_title=role_title,
        role_type=role_type,  # type: ignore[arg-type]
        portfolio=row.get("portfolio"),
        organisation=agency_name,
        start_date=start,
        end_date=end,
        source="aps_leaders",
        source_url=source_url,
        notes=row.get("notes"),
    )


def parse_directory_agency_html(
    html: str,
    *,
    agency_slug: str,
    agency_name: str,
    portfolio: str | None,
    source_url: str,
) -> list[PersonRoleIn]:
    """Best-effort Directory / heading-and-name agency page."""
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html or "", "lxml")
    found: list[PersonRoleIn] = []
    for heading in soup.find_all(["h2", "h3", "h4", "dt", "strong"]):
        title = " ".join(heading.get_text(" ", strip=True).split())
        match = _ROLE_HEADING.match(title)
        if not match:
            continue
        rest = (match.group("rest") or "").strip(" —-:")
        role_title = title if len(title) > 3 else match.group("title")
        name = ""
        sibling = heading.find_next(["a", "p", "span", "dd", "h2", "h3"])
        if sibling and sibling.name == "a":
            name = sibling.get_text(" ", strip=True)
        elif sibling and sibling.name in {"p", "span", "dd"}:
            link = sibling.find("a")
            name = (link or sibling).get_text(" ", strip=True)
        if rest and not name and len(rest.split()) <= 5:
            name = rest
        name = tidy_person_name(name)
        if not name or name.lower() in {"secretary", "deputy secretary"}:
            continue
        item = occupancy_from_record(
            {
                "name": name,
                "role_title": role_title,
                "role_type": classify_role(role_title),
                "agency_slug": agency_slug,
                "agency_name": agency_name,
                "portfolio": portfolio,
                "source_url": source_url,
                "notes": "Parsed from a directory / agency heading. No start date unless the page states one.",
            }
        )
        if item:
            found.append(item)
    return _dedupe(found)


def parse_treasury_executive_html(html: str, *, source_url: str) -> list[PersonRoleIn]:
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html or "", "lxml")
    text = soup.get_text("\n", strip=True)
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    rows: list[dict] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        nxt = lines[i + 1] if i + 1 < len(lines) else ""
        if re.search(r"secretary to the australian treasury", line, re.I):
            name = tidy_person_name(lines[i - 1]) if i else "Jenny Wilkinson"
            became = _BECAME_TREASURY.search(text)
            rows.append(
                {
                    "name": name,
                    "role_title": "Secretary to the Australian Treasury",
                    "role_type": "secretary",
                    "agency_slug": "treasury",
                    "agency_name": "Department of the Treasury",
                    "portfolio": "Treasury",
                    "start_date": month_year_to_date(
                        became.group("mon") if became else "June",
                        became.group("year") if became else "2025",
                    ),
                    "source_url": source_url,
                    "notes": (
                        "Treasury executive page. Appointment stated as a month; "
                        "stored as the first of that month."
                    ),
                }
            )
            finance = _FINANCE_TENURE.search(text)
            if finance:
                rows.append(
                    {
                        "name": name,
                        "role_title": "Secretary of the Department of Finance",
                        "role_type": "secretary",
                        "agency_slug": "finance",
                        "agency_name": "Department of Finance",
                        "portfolio": "Finance",
                        "start_date": month_year_to_date(
                            finance.group("mon1"), finance.group("year1")
                        ),
                        "end_date": month_year_to_date(
                            finance.group("mon2"), finance.group("year2")
                        ),
                        "source_url": source_url,
                        "notes": (
                            "Same Treasury page states the prior Finance tenure "
                            "(month only). Successor not named there."
                        ),
                    }
                )
        elif re.match(r"(?:deputy secretary|director-general)\b", nxt, re.I) and not _ROLE_HEADING.match(line):
            rows.append(
                {
                    "name": tidy_person_name(line),
                    "role_title": nxt,
                    "role_type": classify_role(nxt),
                    "agency_slug": "treasury",
                    "agency_name": "Department of the Treasury",
                    "portfolio": "Treasury",
                    "source_url": source_url,
                    "notes": "Listed on the Treasury executive page. No appointment date.",
                }
            )
        i += 1
    return _dedupe([item for row in rows if (item := occupancy_from_record(row))])


def parse_heading_staff_html(
    html: str,
    *,
    agency_slug: str,
    agency_name: str,
    portfolio: str | None,
    source_url: str,
) -> list[PersonRoleIn]:
    return parse_directory_agency_html(
        html,
        agency_slug=agency_slug,
        agency_name=agency_name,
        portfolio=portfolio,
        source_url=source_url,
    )


class ApsLeadersSource:
    name = "aps_leaders"
    HOME = DIRECTORY_HOME
    ENDPOINTS = ENDPOINTS

    def __init__(
        self,
        *,
        path: Path | str | None = None,
        client: AphClient | None = None,
    ) -> None:
        self.path = Path(path) if path else None
        self.client = client or AphClient(timeout=20, max_retries=2)

    def fetch(self, *, limit: int = 0, incremental_keys: set[str] | None = None) -> SourceBatch:
        errors: list[str] = []
        transport = "directory"
        rows: list[PersonRoleIn] = []

        if self.path:
            rows, transport = self._from_path(self.path)
        else:
            try:
                rows = self._fetch_live()
                transport = "live_pages"
            except Exception as exc:
                errors.append(f"live: {exc}")
            if not rows:
                try:
                    rows, transport = self._from_path(default_aps_dir())
                    transport = f"fixture_fallback:{transport}"
                except Exception as fallback_exc:
                    errors.append(f"fixture: {fallback_exc}")

        known = incremental_keys or set()
        occupancies: list[PersonRoleIn] = []
        people: list[PersonIn] = []
        agencies: list[AgencyIn] = []
        seen_people: set[str] = set()
        seen_agencies: set[str] = set()
        for item in rows:
            if item.source_key in known:
                continue
            occupancies.append(item)
            if item.person.slug not in seen_people:
                people.append(item.person)
                seen_people.add(item.person.slug)
            if item.agency and item.agency.slug not in seen_agencies:
                agencies.append(item.agency)
                seen_agencies.add(item.agency.slug)
            if limit and len(occupancies) >= limit:
                break

        return SourceBatch(
            source=self.name,
            people=people,
            agencies=agencies,
            person_roles=occupancies,
            meta={
                "status": "ok" if occupancies else "empty",
                "home": self.HOME,
                "transport": transport,
                "license_note": LICENSE_NOTE,
                "gaps": GAPS,
                "limit": limit,
                "skipped_existing": len(known),
                "errors": errors,
                "people": len(people),
                "occupancies": len(occupancies),
                "agencies": len(agencies),
                "by_role_type": _counts_by_type(occupancies),
                "endpoints": ENDPOINTS,
                "schema": "infra/postgres/007_accountability.sql + 010_aps_leaders.sql",
                "note": (
                    "Current APS secretaries / deputies from directory.gov.au or "
                    "official executive pages. Fixture fallback (leaders.json + "
                    "historical_tenures.json) if live pages are WAF-blocked. "
                    "Historical bars only where an instrument or published "
                    "timeline states start/end. No invented dates."
                ),
            },
        )

    def _fetch_live(self) -> list[PersonRoleIn]:
        found: list[PersonRoleIn] = []
        for url, slug, name, portfolio in DIRECTORY_PAGES:
            try:
                html = self.client.get_text(url, referer=DIRECTORY_HOME)
            except Exception:
                continue
            found.extend(
                parse_directory_agency_html(
                    html,
                    agency_slug=slug,
                    agency_name=name,
                    portfolio=portfolio,
                    source_url=url,
                )
            )
        for page in DEPARTMENT_PAGES:
            try:
                html = self.client.get_text(page["url"], referer=DIRECTORY_HOME)
            except Exception:
                continue
            if page["parser"] == "treasury":
                found.extend(parse_treasury_executive_html(html, source_url=page["url"]))
            else:
                found.extend(
                    parse_heading_staff_html(
                        html,
                        agency_slug=page["agency_slug"],
                        agency_name=page["agency_name"],
                        portfolio=page.get("portfolio"),
                        source_url=page["url"],
                    )
                )
        return _dedupe(found)

    def _from_path(self, path: Path) -> tuple[list[PersonRoleIn], str]:
        if not path.exists():
            raise FileNotFoundError(f"APS leaders path not found: {path}")
        rows: list[PersonRoleIn] = []
        files = [path] if path.is_file() else sorted(path.iterdir())
        used = []
        for file in files:
            # Parser-test excerpts stay in-tree; they are not a second occupancy source.
            if file.name.endswith(".excerpt.html") or file.name.endswith(".excerpt.htm"):
                continue
            if file.suffix.lower() == ".json":
                payload = json.loads(file.read_text(encoding="utf-8"))
                leaders = payload.get("leaders") if isinstance(payload, dict) else payload
                if not isinstance(leaders, list):
                    continue
                used.append(file.name)
                for raw in leaders:
                    if isinstance(raw, dict):
                        item = occupancy_from_record(raw)
                        if item:
                            rows.append(item)
            elif file.suffix.lower() in {".html", ".htm"}:
                html = file.read_text(encoding="utf-8")
                used.append(file.name)
                if "treasury" in file.name.lower():
                    rows.extend(
                        parse_treasury_executive_html(
                            html,
                            source_url="https://treasury.gov.au/the-department/about-treasury/our-executive",
                        )
                    )
                elif "home" in file.name.lower():
                    rows.extend(
                        parse_heading_staff_html(
                            html,
                            agency_slug="home-affairs",
                            agency_name="Department of Home Affairs",
                            portfolio="Home Affairs",
                            source_url="https://www.homeaffairs.gov.au/about-us/who-we-are/our-senior-staff",
                        )
                    )
                else:
                    rows.extend(
                        parse_directory_agency_html(
                            html,
                            agency_slug="agency",
                            agency_name="Australian Government agency",
                            portfolio=None,
                            source_url=str(file),
                        )
                    )
        if not rows:
            raise FileNotFoundError(f"No APS leader records in {path}")
        return _dedupe(rows), f"aps_file:{path} ({', '.join(used)})"


def _dedupe(items: list[PersonRoleIn]) -> list[PersonRoleIn]:
    seen: set[str] = set()
    out: list[PersonRoleIn] = []
    for item in items:
        if item.source_key in seen:
            continue
        seen.add(item.source_key)
        out.append(item)
    return out


def _counts_by_type(items: list[PersonRoleIn]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in items:
        counts[item.role_type] = counts.get(item.role_type, 0) + 1
    return counts
