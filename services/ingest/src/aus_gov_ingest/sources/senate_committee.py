from __future__ import annotations

from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup

from aus_gov_ingest.config import settings
from aus_gov_ingest.models import CommitteeIn, HearingIn, SourceBatch
from aus_gov_ingest.sources.estimates import _parse_date, _slug
from aus_gov_ingest.sources.fixture import FixtureSource

COMMITTEES_HOME = "https://www.aph.gov.au/Parliamentary_Business/Committees/Senate"


class SenateCommitteeSource:
    """Best-effort adapter toward APH Senate committee pages (inquiries / hearings)."""

    name = "senate_committee"

    def __init__(self, *, fallback_fixture: bool | None = None) -> None:
        self.fallback_fixture = (
            settings.ingest_fallback_fixture if fallback_fixture is None else fallback_fixture
        )

    def fetch(self, *, limit: int = 0, incremental_keys: set[str] | None = None) -> SourceBatch:
        known = incremental_keys or set()
        hearings: list[HearingIn] = []
        errors: list[str] = []
        try:
            html = self._get(COMMITTEES_HOME)
            soup = BeautifulSoup(html, "lxml")
            links: list[tuple[str, str]] = []
            for anchor in soup.find_all("a", href=True):
                href = anchor["href"]
                label = " ".join(anchor.get_text(" ", strip=True).split())
                if "/Committees/Senate/" in href and label and len(label) < 80:
                    links.append((label, urljoin(COMMITTEES_HOME, href)))
            # unique by url
            seen_url: set[str] = set()
            unique: list[tuple[str, str]] = []
            for label, url in links:
                if url in seen_url:
                    continue
                seen_url.add(url)
                unique.append((label, url))
            if limit:
                unique = unique[:limit]
            for label, url in unique:
                committee = CommitteeIn(
                    slug=_slug(label),
                    name=label,
                    chamber="Senate",
                    aph_url=url,
                )
                source_key = f"senate_committee:index:{_slug(label)}"
                if source_key in known:
                    continue
                hearings.append(
                    HearingIn(
                        slug=_slug(f"committee-index-{label}")[:80],
                        title=f"Senate committee index — {label}",
                        hearing_type="committee",
                        source="senate_committee",
                        source_url=url,
                        source_key=source_key,
                        status="listed",
                        summary="Stub hearing generated from the Senate committees index. Stage 1 does not backfill inquiry transcripts.",
                        committee=committee,
                        held_on=_parse_date(label),
                    )
                )
        except Exception as exc:
            errors.append(str(exc))

        if not hearings and self.fallback_fixture:
            batch = FixtureSource().fetch(limit=limit, incremental_keys=incremental_keys)
            # keep only committee-type fixture rows when possible
            committee_only = [h for h in batch.hearings if h.hearing_type == "committee"]
            if committee_only:
                batch.hearings = committee_only
            batch.source = "senate_committee"
            batch.meta = {**batch.meta, "fallback": "fixture", "errors": errors}
            return batch

        return SourceBatch(
            source="senate_committee",
            hearings=hearings,
            committees=[h.committee for h in hearings if h.committee],
            meta={"home": COMMITTEES_HOME, "errors": errors, "live": bool(hearings)},
        )

    def _get(self, url: str) -> str:
        headers = {"User-Agent": settings.ingest_user_agent, "Accept": "text/html"}
        with httpx.Client(timeout=settings.ingest_timeout_seconds, follow_redirects=True) as client:
            response = client.get(url, headers=headers)
            response.raise_for_status()
            return response.text
