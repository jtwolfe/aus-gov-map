"""They Vote For You divisions → bills.

Live: theyvoteforyou.org.au JSON (optional THEYVOTEFORYOU_KEY).
Fallback: fixtures/live/tvfy/.

Stores ``divisions`` + ``division_votes``. People are **resolved at
persist time** against existing ``people`` rows — this adapter never
emits ``PersonIn`` rows, so it cannot invent MPs.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from aus_gov_ingest.http import AphClient
from aus_gov_ingest.models import DivisionIn, DivisionVoteIn, SourceBatch
from aus_gov_ingest.sources.util import fixture_live_dir, parse_flexible_date, slug

TVFY_HOME = "https://theyvoteforyou.org.au"
TVFY_API = f"{TVFY_HOME}"
LICENSE_NOTE = (
    "They Vote For You (OpenAustralia Foundation), citing Commonwealth Hansard. "
    "Attribute TVFY and the Parliament."
)

ENDPOINTS = {
    "home": TVFY_HOME,
    "help": f"{TVFY_HOME}/help/api",
    "divisions": f"{TVFY_HOME}/divisions.json",
}


def default_tvfy_dir() -> Path:
    return fixture_live_dir("tvfy")


class TheyVoteForYouSource:
    name = "theyvoteforyou"
    HOME = TVFY_HOME
    ENDPOINTS = ENDPOINTS

    def __init__(
        self,
        *,
        path: Path | str | None = None,
        client: AphClient | None = None,
        api_key: str | None = None,
    ) -> None:
        self.path = Path(path) if path else None
        self.client = client or AphClient(timeout=12, max_retries=1)
        self.api_key = api_key if api_key is not None else os.environ.get("THEYVOTEFORYOU_KEY", "")

    def fetch(self, *, limit: int = 0, incremental_keys: set[str] | None = None) -> SourceBatch:
        errors: list[str] = []
        transport = "tvfy"
        records: list[dict] = []

        if self.path:
            records, transport = load_tvfy_path(self.path)
        else:
            try:
                records = self._fetch_live(limit=limit or 8)
            except Exception as exc:
                errors.append(f"tvfy_live: {exc}")
                try:
                    records, transport = load_tvfy_path(default_tvfy_dir())
                    transport = f"fixture_fallback:{transport}"
                except Exception as fallback_exc:
                    errors.append(f"fixture: {fallback_exc}")

        known = incremental_keys or set()
        divisions: list[DivisionIn] = []
        seen: set[str] = set()
        for record in records:
            item = division_from_record(record)
            if not item or item.source_key in known or item.source_key in seen:
                continue
            seen.add(item.source_key)
            divisions.append(item)
            if limit and len(divisions) >= limit:
                break

        return SourceBatch(
            source=self.name,
            divisions=divisions,
            meta={
                "status": "ok" if divisions else "empty",
                "home": self.HOME,
                "transport": transport,
                "license_note": LICENSE_NOTE,
                "limit": limit,
                "skipped_existing": len(known),
                "errors": errors,
                "divisions": len(divisions),
                "named_votes": sum(len(d.votes) for d in divisions),
                "people_emitted": 0,
                "endpoints": ENDPOINTS,
                "schema": "infra/postgres/012_laws.sql (divisions, division_votes)",
                "note": (
                    "TVFY divisions linked to bill instruments when a source_key "
                    "or title matches. Votes store published names; person_id is "
                    "resolved only against existing people. No invented MPs."
                ),
            },
        )

    def _fetch_live(self, *, limit: int) -> list[dict]:
        params = ""
        if self.api_key:
            params = f"?key={self.api_key}"
        url = f"{ENDPOINTS['divisions']}{params}"
        payload = self.client.get_json(url, referer=TVFY_HOME)
        rows = payload if isinstance(payload, list) else payload.get("divisions") if isinstance(payload, dict) else None
        if not isinstance(rows, list) or not rows:
            raise RuntimeError(f"TVFY divisions empty at {url}")
        out: list[dict] = []
        for row in rows:
            if not isinstance(row, dict):
                continue
            detail = self._fetch_detail(row)
            out.append(detail or row)
            if limit and len(out) >= limit:
                break
        return out

    def _fetch_detail(self, row: dict) -> dict | None:
        house = (row.get("house") or "").lower()
        date = row.get("date")
        number = row.get("number")
        if not (house and date and number is not None):
            return None
        params = f"?key={self.api_key}" if self.api_key else ""
        url = f"{TVFY_HOME}/divisions/{house}/{date}/{number}.json{params}"
        try:
            payload = self.client.get_json(url, referer=TVFY_HOME)
        except Exception:
            return None
        return payload if isinstance(payload, dict) else None


def load_tvfy_path(path: Path) -> tuple[list[dict], str]:
    if not path.exists():
        raise FileNotFoundError(f"TVFY path not found: {path}")
    files = [path] if path.is_file() else sorted(p for p in path.glob("*.json") if p.is_file())
    if not files:
        raise FileNotFoundError(f"No TVFY JSON in {path}")
    records: list[dict] = []
    for file in files:
        payload = json.loads(file.read_text(encoding="utf-8"))
        if isinstance(payload, list):
            records.extend(r for r in payload if isinstance(r, dict))
        elif isinstance(payload, dict) and isinstance(payload.get("divisions"), list):
            records.extend(r for r in payload["divisions"] if isinstance(r, dict))
        elif isinstance(payload, dict) and (payload.get("name") or payload.get("title")):
            records.append(payload)
    return records, f"tvfy_file:{path}"


def division_from_record(row: dict) -> DivisionIn | None:
    title = (row.get("name") or row.get("title") or "").strip()
    if not title:
        return None
    house = _house(row.get("house"))
    divided_on = parse_flexible_date(row.get("date") or row.get("divided_on"))
    number = _int(row.get("number"))
    tvfy_id = row.get("id")
    key_bit = f"{house or 'other'}:{divided_on or 'undated'}:{number if number is not None else tvfy_id or slug(title)[:40]}"
    source_key = f"tvfy:{key_bit}"
    bills = row.get("bills") if isinstance(row.get("bills"), list) else []
    instrument_key = None
    for bill in bills:
        if not isinstance(bill, dict):
            continue
        instrument_key = bill.get("instrument_source_key") or instrument_key
        if not instrument_key and bill.get("title"):
            instrument_key = f"frl:bill:{slug(bill['title'])[:60]}"
    votes = [v for v in (vote_from_record(item) for item in _vote_rows(row)) if v]
    source_url = row.get("source_url") or (
        f"{TVFY_HOME}/divisions/{house}/{divided_on}/{number}" if house and divided_on and number is not None else None
    )
    return DivisionIn(
        source_key=source_key,
        title=title[:300],
        house=house,
        divided_on=divided_on,
        number=number,
        instrument_source_key=instrument_key,
        ayes=_int(row.get("aye_votes") or row.get("ayes")),
        noes=_int(row.get("no_votes") or row.get("noes")),
        abstentions=_int(row.get("abstentions") or row.get("abstain_votes")),
        possible_turnout=_int(row.get("possible_turnout")),
        source="theyvoteforyou",
        source_url=source_url,
        summary=(row.get("summary") or "")[:800] or None,
        identifiers={
            "tvfy_id": tvfy_id,
            "hansard_url": row.get("hansard_url"),
            "license_note": LICENSE_NOTE,
            "bills": [
                {k: b.get(k) for k in ("title", "official_id", "instrument_source_key") if isinstance(b, dict) and b.get(k)}
                for b in bills
            ],
        },
        votes=votes,
    )


def vote_from_record(row: dict) -> DivisionVoteIn | None:
    vote = _vote_value(row.get("vote") or row.get("vote_name"))
    if not vote:
        return None
    name = _person_name(row)
    if not name:
        return None
    member = row.get("member") if isinstance(row.get("member"), dict) else {}
    return DivisionVoteIn(
        person_name=name,
        vote=vote,
        party=row.get("party") or member.get("party"),
        electorate=row.get("electorate") or member.get("electorate"),
        identifiers={"tvfy_member_id": member.get("id") or row.get("member_id")},
    )


def _vote_rows(row: dict) -> list[dict]:
    votes = row.get("votes")
    if isinstance(votes, list):
        return [v for v in votes if isinstance(v, dict)]
    out: list[dict] = []
    for key, value in (("aye_voters", "aye"), ("no_voters", "no"), ("abstain_voters", "abstain")):
        block = row.get(key)
        if isinstance(block, list):
            for item in block:
                if isinstance(item, dict):
                    out.append({**item, "vote": item.get("vote") or value})
                elif isinstance(item, str):
                    out.append({"name": item, "vote": value})
    return out


def _person_name(row: dict) -> str | None:
    if row.get("name"):
        return str(row["name"]).strip() or None
    member = row.get("member") if isinstance(row.get("member"), dict) else {}
    name = member.get("name")
    if isinstance(name, dict):
        first = (name.get("first") or "").strip()
        last = (name.get("last") or "").strip()
        joined = " ".join(p for p in (first, last) if p)
        return joined or None
    if isinstance(name, str) and name.strip():
        return name.strip()
    person = member.get("person") if isinstance(member.get("person"), dict) else {}
    if person.get("name"):
        return str(person["name"]).strip() or None
    return None


def _vote_value(raw) -> str | None:
    text = str(raw or "").strip().lower()
    if text in {"aye", "yes", "for", "teller_aye"}:
        return "aye"
    if text in {"no", "nay", "against", "teller_no"}:
        return "no"
    if text in {"abstain", "abstention", "abstained"}:
        return "abstain"
    if text in {"absent", "pair", "paired"}:
        return "absent"
    return None


def _house(raw) -> str | None:
    text = str(raw or "").strip().lower()
    if text in {"representatives", "house", "reps", "hor"}:
        return "representatives"
    if text in {"senate"}:
        return "senate"
    return text or None


def _int(value) -> int | None:
    if value in (None, ""):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
