from __future__ import annotations

import re
from datetime import datetime
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup

from aus_gov_ingest.config import settings
from aus_gov_ingest.models import CommitteeIn, HearingIn, SourceBatch
from aus_gov_ingest.sources.fixture import FixtureSource

ESTIMATES_HOME = "https://www.aph.gov.au/Parliamentary_Business/Senate_estimates"

# Legislation committees that examine Estimates.
COMMITTEE_PAGES = {
    "ca": (
        "Community Affairs",
        "https://www.aph.gov.au/Parliamentary_Business/Senate_estimates/ca",
    ),
    "economics": (
        "Economics",
        "https://www.aph.gov.au/Parliamentary_Business/Senate_estimates/economics",
    ),
    "eet": (
        "Education and Employment",
        "https://www.aph.gov.au/Parliamentary_Business/Senate_estimates/eet",
    ),
    "ec": (
        "Environment and Communications",
        "https://www.aph.gov.au/Parliamentary_Business/Senate_estimates/ec",
    ),
    "fpa": (
        "Finance and Public Administration",
        "https://www.aph.gov.au/Parliamentary_Business/Senate_estimates/fpa",
    ),
    "fadt": (
        "Foreign Affairs, Defence and Trade",
        "https://www.aph.gov.au/Parliamentary_Business/Senate_estimates/fadt",
    ),
    "legcon": (
        "Legal and Constitutional Affairs",
        "https://www.aph.gov.au/Parliamentary_Business/Senate_estimates/legcon",
    ),
    "rrat": (
        "Rural and Regional Affairs and Transport",
        "https://www.aph.gov.au/Parliamentary_Business/Senate_estimates/rrat",
    ),
}

_DATE = re.compile(
    r"(?P<d>\d{1,2})\s+(?P<mon>January|February|March|April|May|June|July|August|September|October|November|December)\s+(?P<y>\d{4})",
    re.I,
)
_SLUG = re.compile(r"[^a-z0-9]+")


def _slug(text: str) -> str:
    return _SLUG.sub("-", text.lower()).strip("-")


def _parse_date(text: str):
    match = _DATE.search(text or "")
    if not match:
        return None
    try:
        return datetime.strptime(
            f"{match.group('d')} {match.group('mon')} {match.group('y')}", "%d %B %Y"
        ).date()
    except ValueError:
        return None


class EstimatesSource:
    """APH Senate Estimates landing + committee pages. Incremental on source_key."""

    name = "estimates"

    def __init__(self, *, fallback_fixture: bool | None = None) -> None:
        self.fallback_fixture = (
            settings.ingest_fallback_fixture if fallback_fixture is None else fallback_fixture
        )

    def fetch(self, *, limit: int = 0, incremental_keys: set[str] | None = None) -> SourceBatch:
        known = incremental_keys or set()
        hearings: list[HearingIn] = []
        committees: dict[str, CommitteeIn] = {}
        errors: list[str] = []

        try:
            html = self._get(ESTIMATES_HOME)
            self._note_home(html)
        except Exception as exc:
            errors.append(f"home: {exc}")
            html = ""

        pages = list(COMMITTEE_PAGES.items())
        if limit:
            pages = pages[: max(1, min(limit, len(pages)))]

        for code, (name, url) in pages:
            committee = CommitteeIn(
                slug=_slug(name),
                name=name,
                chamber="Senate",
                kind="legislation",
                aph_url=url,
            )
            committees[committee.slug] = committee
            try:
                page = self._get(url)
                found = self._hearings_from_committee(code, committee, url, page)
                for hearing in found:
                    if hearing.source_key in known:
                        continue
                    hearings.append(hearing)
                    if limit and len(hearings) >= limit:
                        break
            except Exception as exc:
                errors.append(f"{code}: {exc}")
            if limit and len(hearings) >= limit:
                break

        if not hearings and self.fallback_fixture:
            batch = FixtureSource().fetch(limit=limit, incremental_keys=incremental_keys)
            batch.source = "estimates"
            batch.meta = {
                **batch.meta,
                "live_empty": True,
                "fallback": "fixture",
                "errors": errors,
            }
            return batch

        return SourceBatch(
            source="estimates",
            hearings=hearings,
            committees=list(committees.values()),
            meta={"home": ESTIMATES_HOME, "errors": errors, "live": True},
        )

    def _get(self, url: str) -> str:
        headers = {"User-Agent": settings.ingest_user_agent, "Accept": "text/html"}
        with httpx.Client(timeout=settings.ingest_timeout_seconds, follow_redirects=True) as client:
            response = client.get(url, headers=headers)
            response.raise_for_status()
            return response.text

    def _note_home(self, html: str) -> None:
        # Presence check — the landing page lists the eight estimates committees.
        if "Estimates committees" not in html and "Senate estimates" not in html:
            raise RuntimeError("APH Estimates landing page did not look like the expected document")

    def _hearings_from_committee(
        self, code: str, committee: CommitteeIn, page_url: str, html: str
    ) -> list[HearingIn]:
        soup = BeautifulSoup(html, "lxml")
        hearings: list[HearingIn] = []
        seen: set[str] = set()

        for anchor in soup.find_all("a", href=True):
            href = anchor["href"]
            label = " ".join(anchor.get_text(" ", strip=True).split())
            if not label:
                continue
            lowered = href.lower() + " " + label.lower()
            if "estimate" not in lowered:
                continue
            if not any(token in lowered for token in ("budget", "supplementary", "additional")):
                # still keep committee estimates index links that name a round
                if "estimates" not in label.lower():
                    continue
            absolute = urljoin(page_url, href)
            held_on = _parse_date(label) or _parse_date(anchor.parent.get_text(" ", strip=True) if anchor.parent else "")
            key_date = held_on.isoformat() if held_on else _slug(label)[:48]
            source_key = f"estimates:{code}:{key_date}:{_slug(label)[:40]}"
            if source_key in seen:
                continue
            seen.add(source_key)
            slug = _slug(f"{code}-{label}")[:80]
            hearings.append(
                HearingIn(
                    slug=slug,
                    title=label if "estimate" in label.lower() else f"{committee.name} — {label}",
                    hearing_type="estimates",
                    held_on=held_on,
                    source="estimates",
                    source_url=absolute,
                    source_key=source_key,
                    status="listed",
                    summary=f"Listed on APH Senate Estimates page for {committee.name}.",
                    committee=committee,
                )
            )
        return hearings
