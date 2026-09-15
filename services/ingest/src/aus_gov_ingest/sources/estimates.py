from __future__ import annotations

from urllib.parse import urljoin

from bs4 import BeautifulSoup

from aus_gov_ingest.config import settings
from aus_gov_ingest.http import AphClient
from aus_gov_ingest.models import CommitteeIn, HearingIn, SourceBatch
from aus_gov_ingest.sources.fixture import FixtureSource
from aus_gov_ingest.sources.hansard import (
    CHI_ESTIMATES,
    HansardApi,
    hearing_from_transcript,
)
from aus_gov_ingest.sources.util import parse_date, slug

# Re-export helpers used by senate_committee / tests.
_parse_date = parse_date
_slug = slug

ESTIMATES_HOME = "https://www.aph.gov.au/Parliamentary_Business/Senate_estimates"

# Legislation committees that examine Estimates. Paths match the live APH nav
# (Education and Employment moved from /eet to /ee).
COMMITTEE_PAGES = {
    "ca": (
        "Community Affairs",
        "https://www.aph.gov.au/Parliamentary_Business/Senate_estimates/ca",
    ),
    "economics": (
        "Economics",
        "https://www.aph.gov.au/Parliamentary_Business/Senate_estimates/Economics",
    ),
    "ee": (
        "Education and Employment",
        "https://www.aph.gov.au/Parliamentary_Business/Senate_estimates/ee",
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


class EstimatesSource:
    """Live Senate Estimates via the official APH Hansard JSON API.

    Primary path: Hansard Search (chi=5) + GET /api/hansard/transcript
    (full Official HTML on www.aph.gov.au). ParlInfo XML/PDF remains
    WAF-gated from some IPs; the APH API is the structured source.

    Committee landing pages are a listing fallback when the API is empty.
    """

    name = "estimates"

    def __init__(
        self,
        *,
        fallback_fixture: bool | None = None,
        client: AphClient | None = None,
        include_transcripts: bool | None = None,
    ) -> None:
        self.fallback_fixture = (
            settings.ingest_fallback_fixture if fallback_fixture is None else fallback_fixture
        )
        self.include_transcripts = (
            settings.ingest_include_transcripts
            if include_transcripts is None
            else include_transcripts
        )
        self.client = client or AphClient()
        self.hansard = HansardApi(self.client)

    def fetch(self, *, limit: int = 0, incremental_keys: set[str] | None = None) -> SourceBatch:
        known = incremental_keys or set()
        hearings: list[HearingIn] = []
        committees: dict[str, CommitteeIn] = {}
        errors: list[str] = []
        meta: dict = {
            "home": ESTIMATES_HOME,
            "transport": "aph_hansard_api",
            "transcript_api": True,
            "parlinfo_direct": "waf_js_challenge",
        }

        try:
            hearings, committees, errors = self._from_hansard(limit=limit, known=known)
            meta["live"] = bool(hearings)
            meta["errors"] = errors
        except Exception as exc:
            errors.append(f"hansard_api: {exc}")
            meta["errors"] = errors

        if not hearings:
            try:
                listed, listed_committees, listed_errors = self._from_committee_pages(
                    limit=limit, known=known
                )
                hearings.extend(listed)
                committees.update(listed_committees)
                errors.extend(listed_errors)
                meta["transport"] = "aph_html_listings" if listed else meta["transport"]
                meta["live"] = bool(hearings)
            except Exception as exc:
                errors.append(f"html_listings: {exc}")
            meta["errors"] = errors

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
            people=[p.person for h in hearings for p in h.people if p.person],
            committees=list(committees.values()),
            meta=meta,
        )

    def _from_hansard(
        self, *, limit: int, known: set[str]
    ) -> tuple[list[HearingIn], dict[str, CommitteeIn], list[str]]:
        hearings: list[HearingIn] = []
        committees: dict[str, CommitteeIn] = {}
        errors: list[str] = []
        hits = self.hansard.search(chi=CHI_ESTIMATES, kinds=("estimate",), limit=limit)
        for hit in hits:
            source_key = f"hansard:{hit.bid.strip('/')}"
            if source_key in known:
                continue
            try:
                payload = (
                    self.hansard.fetch_transcript(hit) if self.include_transcripts else {}
                )
                hearing = hearing_from_transcript(
                    hit, payload or {}, source="estimates", hearing_type="estimates"
                )
            except Exception as exc:
                errors.append(f"{hit.bid}: {exc}")
                continue
            hearings.append(hearing)
            if hearing.committee:
                committees[hearing.committee.slug] = hearing.committee
            if limit and len(hearings) >= limit:
                break
        return hearings, committees, errors

    def _from_committee_pages(
        self, *, limit: int, known: set[str]
    ) -> tuple[list[HearingIn], dict[str, CommitteeIn], list[str]]:
        hearings: list[HearingIn] = []
        committees: dict[str, CommitteeIn] = {}
        errors: list[str] = []
        try:
            html = self.client.get_text(ESTIMATES_HOME)
            if "Estimates committees" not in html and "Senate estimates" not in html:
                errors.append("home: landing page did not look like Senate Estimates")
        except Exception as exc:
            errors.append(f"home: {exc}")

        pages = list(COMMITTEE_PAGES.items())
        if limit:
            pages = pages[: max(1, min(limit, len(pages)))]

        for code, (name, url) in pages:
            committee = CommitteeIn(
                slug=slug(name),
                name=name,
                chamber="Senate",
                kind="legislation",
                aph_url=url,
            )
            committees[committee.slug] = committee
            try:
                page = self.client.get_text(url, referer=ESTIMATES_HOME)
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
        return hearings, committees, errors

    def _hearings_from_committee(
        self, code: str, committee: CommitteeIn, page_url: str, html: str
    ) -> list[HearingIn]:
        soup = BeautifulSoup(html, "lxml")
        hearings: list[HearingIn] = []
        seen: set[str] = set()
        content = soup.select_one("#main_0_content_0_divContent") or soup

        for anchor in content.find_all("a", href=True):
            href = anchor["href"]
            label = " ".join(anchor.get_text(" ", strip=True).split())
            if not label:
                continue
            lowered = href.lower() + " " + label.lower()
            if "estimate" not in lowered:
                continue
            if not any(token in lowered for token in ("budget", "supplementary", "additional")):
                if "estimates" not in label.lower():
                    continue
            if href.lower().startswith("mailto:"):
                continue
            absolute = urljoin(page_url, href)
            parent_text = anchor.parent.get_text(" ", strip=True) if anchor.parent else ""
            held_on = parse_date(label) or parse_date(parent_text)
            key_date = held_on.isoformat() if held_on else slug(label)[:48]
            source_key = f"estimates:{code}:{key_date}:{slug(label)[:40]}"
            if source_key in seen:
                continue
            seen.add(source_key)
            hearing_slug = slug(f"{code}-{label}")[:80]
            hearings.append(
                HearingIn(
                    slug=hearing_slug,
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
