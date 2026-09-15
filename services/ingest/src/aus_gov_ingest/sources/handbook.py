"""Parliamentary Handbook ingest (Stage 2).

Do not invent officials. Default ``fetch()`` is an empty batch that documents
real endpoints. Set ``HANDBOOK_LIVE=1`` to probe Handbook OData and map
*returned* individuals onto existing ``people`` slugs (no fake rows).

Public site:
  https://handbook.aph.gov.au

OData (as used by ausPH and OpenSanctions; subject to change):
  https://handbookapi.aph.gov.au/api/individuals
  https://handbookapi.aph.gov.au/api/ministryrecords
  https://handbookapi.aph.gov.au/api/shadowministryrecords
  https://handbookapi.aph.gov.au/api/StatisticalInformation/Ministries
  https://handbookapi.aph.gov.au/api/StatisticalInformation/SittingDaysForYear?year=YYYY

Current parliamentarians (APH, not the Handbook extract):
  https://www.aph.gov.au/api/parliamentarian/?q=&mem=0&page=1

Target tables (empty until a live extract is persisted):
  - handbook_entries.person_id → people.id   (shared person key; no parallel table)
  - handbook_roles / handbook_tenure (provenance)
  - roles / person_roles (promoted occupancy)

See infra/postgres/005_handbook.sql and 007_accountability.sql.
"""

from __future__ import annotations

import os
from typing import Any

from aus_gov_ingest.models import PersonIn, SourceBatch
from aus_gov_ingest.people import slug as slugify

HANDBOOK_HOME = "https://handbook.aph.gov.au"
HANDBOOK_API = "https://handbookapi.aph.gov.au"
INDIVIDUALS_URL = (
    f"{HANDBOOK_API}/api/individuals"
    "?$orderby=FamilyName,GivenName&$skip=0&$count=false"
    "&$select=PHID,DisplayName,Gender,DateOfBirth,State,StateAbbrev,"
    "SenateState,Electorate,Party"
)
MINISTRY_RECORDS_URL = f"{HANDBOOK_API}/api/ministryrecords"
SHADOW_MINISTRY_URL = f"{HANDBOOK_API}/api/shadowministryrecords"
MINISTRIES_URL = f"{HANDBOOK_API}/api/StatisticalInformation/Ministries"
SITTING_DAYS_URL = f"{HANDBOOK_API}/api/StatisticalInformation/SittingDaysForYear"
APH_PARLIAMENTARIAN_URL = "https://www.aph.gov.au/api/parliamentarian/?q=&mem=0&page=1"

ENDPOINTS = {
    "home": HANDBOOK_HOME,
    "individuals": INDIVIDUALS_URL,
    "ministry_records": MINISTRY_RECORDS_URL,
    "shadow_ministry_records": SHADOW_MINISTRY_URL,
    "ministries": MINISTRIES_URL,
    "sitting_days": SITTING_DAYS_URL,
    "aph_parliamentarian": APH_PARLIAMENTARIAN_URL,
}


def _live_enabled() -> bool:
    return os.environ.get("HANDBOOK_LIVE", "").strip().lower() in {"1", "true", "yes"}


def parse_individuals_odata(payload: Any) -> list[PersonIn]:
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
    """Handbook adapter — empty unless HANDBOOK_LIVE=1 and OData answers."""

    name = "handbook"
    HOME = HANDBOOK_HOME
    ENDPOINTS = ENDPOINTS

    def fetch(self, *, limit: int = 0, incremental_keys: set[str] | None = None) -> SourceBatch:
        meta: dict = {
            "status": "not_implemented",
            "home": self.HOME,
            "endpoints": ENDPOINTS,
            "note": (
                "Stage 2: Handbook OData parser is wired. Default fetch does not "
                "invent officials. Set HANDBOOK_LIVE=1 to probe "
                "handbookapi.aph.gov.au/api/individuals and map returned rows "
                "onto people (shared key; promote into person_roles later)."
            ),
            "schema": "infra/postgres/005_handbook.sql + 007_accountability.sql",
            "limit": limit,
            "skipped_existing": len(incremental_keys or []),
            "live": _live_enabled(),
        }
        if not _live_enabled():
            return SourceBatch(source=self.name, hearings=[], people=[], meta=meta)
        try:
            people = self._fetch_individuals(limit=limit)
        except Exception as exc:  # network / WAF / schema drift — never invent
            meta["status"] = "unavailable"
            meta["error"] = str(exc)
            return SourceBatch(source=self.name, hearings=[], people=[], meta=meta)
        cap = limit if limit and limit > 0 else None
        if cap:
            people = people[:cap]
        meta["status"] = "ok" if people else "empty"
        meta["records"] = len(people)
        return SourceBatch(source=self.name, hearings=[], people=people, meta=meta)

    def _fetch_individuals(self, *, limit: int = 0) -> list[PersonIn]:
        from aus_gov_ingest.http import AphClient

        top = limit if limit and limit > 0 else 25
        url = INDIVIDUALS_URL + f"&$top={top}"
        with AphClient(timeout=min(12.0, 20.0)) as client:
            payload = client.get_json(url, referer=self.HOME)
        return parse_individuals_odata(payload)
