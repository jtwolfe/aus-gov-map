from __future__ import annotations

import json
from pathlib import Path

from aus_gov_ingest.http import AphClient
from aus_gov_ingest.sources.estimates import EstimatesSource
from aus_gov_ingest.sources.hansard import TRANSCRIPT_API
from aus_gov_ingest.sources.senate_committee import SenateCommitteeSource

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"


class FakeClient(AphClient):
    def __init__(self, pages: dict[str, object]) -> None:
        # Skip real httpx session.
        self.pages = pages
        self.timeout = 5
        self.rate_limit_seconds = 0
        self.max_retries = 1
        self.user_agents = ["test"]
        self._last_request_at = 0.0
        self._client = None  # type: ignore[assignment]

    def get_text(self, url: str, **kwargs):  # type: ignore[override]
        for key, value in self.pages.items():
            if key in url and isinstance(value, str):
                return value
        raise AssertionError(f"unexpected get_text {url}")

    def get_json(self, url: str, **kwargs):  # type: ignore[override]
        for key, value in self.pages.items():
            if key in url and isinstance(value, dict):
                return value
        raise AssertionError(f"unexpected get_json {url}")


def test_estimates_source_uses_hansard_api() -> None:
    search = (FIXTURES / "hansard_search_estimates.html").read_text()
    payload = json.loads((FIXTURES / "transcript_fpa_28778_excerpt.json").read_text())
    client = FakeClient(
        {
            "Hansard/Search": search,
            "estimate/29629/0000": {
                **payload,
                "MainTitle": "Community Affairs Legislation Committee - 05/06/2026 - Estimates",
                "Date": "05/06/2026",
                "SystemId": "committees/estimate/29629/0000",
            },
            "estimate/28778/0000": payload,
            TRANSCRIPT_API: payload,
        }
    )
    batch = EstimatesSource(client=client, fallback_fixture=False).fetch(limit=2)
    assert batch.source == "estimates"
    assert len(batch.hearings) == 2
    assert all(h.documents for h in batch.hearings)
    assert all(h.source_key.startswith("hansard:committees/estimate/") for h in batch.hearings)
    assert "Ngunnawal" in (batch.hearings[1].documents[0].content_text or "")
    assert batch.meta.get("transport") == "aph_hansard_api"


def test_senate_committee_filters_commsen() -> None:
    html = """
    <ul class="search-filter-results">
      <li>
        <p class="title"><a href="/Parliamentary_Business/Hansard/Hansard_Display?bid=committees/commjnt/29910/&amp;sid=0000">Joint Standing Committee on Treaties;14/09/2026</a></p>
        <dl><dt>DATE</dt><dd>14 Sep 2026</dd></dl>
      </li>
      <li>
        <p class="title"><a href="/Parliamentary_Business/Hansard/Hansard_Display?bid=committees/commsen/29898/&amp;sid=0000">Community Affairs Legislation Committee;11/09/2026;Private Health Insurance</a></p>
        <dl><dt>DATE</dt><dd>11 Sep 2026</dd></dl>
      </li>
    </ul>
    """
    payload = {
        "MainTitle": "Community Affairs Legislation Committee - 11/09/2026 - Private Health Insurance",
        "TalkText": "<p>In Attendance</p><p>Senator Brown, Chair</p><p>Committee met at 09:00</p><p>CHAIR: The committee is inquiring into the bill.</p>",
        "Date": "11/09/2026",
        "SystemId": "committees/commsen/29898/0000",
        "Chamber": "Committee",
    }
    client = FakeClient({"Hansard/Search": html, "commsen/29898/0000": payload})
    batch = SenateCommitteeSource(client=client, fallback_fixture=False).fetch(limit=2)
    assert len(batch.hearings) == 1
    assert batch.hearings[0].hearing_type == "committee"
    assert "commsen/29898" in batch.hearings[0].source_key
    assert batch.hearings[0].documents
