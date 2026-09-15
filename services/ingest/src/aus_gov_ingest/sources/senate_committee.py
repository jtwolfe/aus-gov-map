from __future__ import annotations

from urllib.parse import urljoin

from bs4 import BeautifulSoup

from aus_gov_ingest.config import settings
from aus_gov_ingest.http import AphClient
from aus_gov_ingest.models import CommitteeIn, HearingIn, SourceBatch
from aus_gov_ingest.sources.fixture import FixtureSource
from aus_gov_ingest.sources.hansard import (
    CHI_COMMITTEES,
    HansardApi,
    hearing_from_transcript,
)
from aus_gov_ingest.sources.util import parse_date, slug

COMMITTEES_HOME = "https://www.aph.gov.au/Parliamentary_Business/Committees/Senate"


class SenateCommitteeSource:
    """Senate committee Hansard via APH /api/hansard (chi=6, commsen).

    Falls back to the Senate committees HTML index (listings only) and,
    if that is empty, the invented fixture.
    """

    name = "senate_committee"

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
        errors: list[str] = []
        meta: dict = {
            "home": COMMITTEES_HOME,
            "transport": "aph_hansard_api",
            "parlinfo_direct": "waf_js_challenge",
        }

        try:
            hits = self.hansard.search(chi=CHI_COMMITTEES, kinds=("commsen",), limit=limit)
            for hit in hits:
                source_key = f"hansard:{hit.bid.strip('/')}"
                if source_key in known:
                    continue
                try:
                    payload = (
                        self.hansard.fetch_transcript(hit) if self.include_transcripts else {}
                    )
                    hearing = hearing_from_transcript(
                        hit, payload or {}, source="senate_committee", hearing_type="committee"
                    )
                except Exception as exc:
                    errors.append(f"{hit.bid}: {exc}")
                    continue
                hearings.append(hearing)
                if limit and len(hearings) >= limit:
                    break
            meta["live"] = bool(hearings)
        except Exception as exc:
            errors.append(f"hansard_api: {exc}")

        if not hearings:
            try:
                hearings.extend(self._from_index(limit=limit, known=known))
                if hearings:
                    meta["transport"] = "aph_html_index"
                    meta["live"] = True
            except Exception as exc:
                errors.append(str(exc))

        if not hearings and self.fallback_fixture:
            batch = FixtureSource().fetch(limit=limit, incremental_keys=incremental_keys)
            committee_only = [h for h in batch.hearings if h.hearing_type == "committee"]
            if committee_only:
                batch.hearings = committee_only
            batch.source = "senate_committee"
            batch.meta = {**batch.meta, "fallback": "fixture", "errors": errors}
            return batch

        return SourceBatch(
            source="senate_committee",
            hearings=hearings,
            people=[p.person for h in hearings for p in h.people if p.person],
            committees=[h.committee for h in hearings if h.committee],
            meta={**meta, "errors": errors, "live": bool(hearings)},
        )

    def _from_index(self, *, limit: int, known: set[str]) -> list[HearingIn]:
        html = self.client.get_text(COMMITTEES_HOME)
        soup = BeautifulSoup(html, "lxml")
        hearings: list[HearingIn] = []
        seen_url: set[str] = set()
        for anchor in soup.find_all("a", href=True):
            href = anchor["href"]
            label = " ".join(anchor.get_text(" ", strip=True).split())
            if "/Committees/Senate/" not in href or not label or len(label) > 80:
                continue
            url = urljoin(COMMITTEES_HOME, href)
            if url in seen_url:
                continue
            seen_url.add(url)
            committee = CommitteeIn(
                slug=slug(label),
                name=label,
                chamber="Senate",
                aph_url=url,
            )
            source_key = f"senate_committee:index:{slug(label)}"
            if source_key in known:
                continue
            hearings.append(
                HearingIn(
                    slug=slug(f"committee-index-{label}")[:80],
                    title=f"Senate committee index — {label}",
                    hearing_type="committee",
                    source="senate_committee",
                    source_url=url,
                    source_key=source_key,
                    status="listed",
                    summary="Listed on the Senate committees index (no Official attached).",
                    committee=committee,
                    held_on=parse_date(label),
                )
            )
            if limit and len(hearings) >= limit:
                break
        return hearings
