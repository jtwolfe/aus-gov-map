from __future__ import annotations

import re
from dataclasses import dataclass
from html import unescape
from pathlib import Path
from typing import Iterable
from urllib.parse import parse_qs, urljoin, urlparse

from bs4 import BeautifulSoup

from aus_gov_ingest.http import AphClient
from aus_gov_ingest.models import AppearanceIn, CommitteeIn, DocumentIn, HearingIn, PersonIn
from aus_gov_ingest.people import (
    canonical_slug,
    infer_role,
    should_skip_person,
    split_name_and_role,
)
from aus_gov_ingest.sources.util import parse_date, slug

APH_ORIGIN = "https://www.aph.gov.au"
HANSARD_SEARCH = f"{APH_ORIGIN}/Parliamentary_Business/Hansard/Search"
TRANSCRIPT_API = f"{APH_ORIGIN}/api/hansard/transcript"

CHI_ESTIMATES = 5
CHI_COMMITTEES = 6

LICENSE_NOTE = (
    "© Commonwealth of Australia. Official Hansard. Typically CC BY-NC-ND — "
    "attribute the Parliament of Australia; research / non-commercial."
)

_BID = re.compile(
    r"bid=(?P<bid>committees/(?P<kind>estimate|commsen|commjnt)/[^/&]+/?)&(?:amp;)?sid=(?P<sid>\d+)",
    re.I,
)
_ATTEND = re.compile(
    r"^(?P<title>Senator(?:\s+the\s+Hon(?:ourable)?)?|The\s+Hon(?:ourable)?|"
    r"Prof(?:essor|\.)?|Dr\.?|Ms\.?|Mr\.?|Mrs\.?|Miss)\s+"
    r"(?P<name>.+)$",
    re.I,
)
_CHAIR_INLINE = re.compile(
    r"^(?P<label>CHAIR|DEPUTY\s+CHAIR|ACTING\s+CHAIR)\s*\((?P<inner>[^)]+)\)",
    re.I,
)


@dataclass(frozen=True)
class HansardHit:
    title: str
    bid: str
    sid: str
    kind: str  # estimate | commsen | commjnt
    display_url: str
    held_on_text: str | None = None


def _normalise_bid(bid: str) -> str:
    bid = unescape(bid).strip()
    if not bid.endswith("/"):
        bid += "/"
    return bid


def document_id(bid: str) -> str:
    return _normalise_bid(bid).strip("/").split("/")[-1]


def hit_from_transcript_payload(payload: dict, *, filename: str | None = None) -> HansardHit:
    """Rebuild a HansardHit from a saved /api/hansard/transcript JSON object."""
    system_id = str(payload.get("SystemId") or "").strip().strip("/")
    parts = [p for p in system_id.split("/") if p]
    if len(parts) >= 3 and parts[0].lower() == "committees":
        kind = parts[1].lower()
        doc_id = parts[2]
        sid = parts[3].zfill(4) if len(parts) > 3 else "0000"
        bid = _normalise_bid(f"committees/{kind}/{doc_id}")
    elif filename:
        stem = Path(filename).stem
        kind = "estimate"
        bid = _normalise_bid(f"committees/estimate/{stem}")
        sid = "0000"
    else:
        raise ValueError(f"Cannot derive Hansard bid from SystemId={system_id!r}")
    title = (payload.get("MainTitle") or payload.get("Title") or "").strip()
    date_text = payload.get("Date")
    display_url = (
        f"{APH_ORIGIN}/Parliamentary_Business/Hansard/Hansard_Display"
        f"?bid={bid}&sid={sid}"
    )
    return HansardHit(
        title=title,
        bid=bid,
        sid=sid,
        kind=kind,
        display_url=display_url,
        held_on_text=str(date_text) if date_text else None,
    )


def parse_search_hits(html: str, *, kinds: Iterable[str] | None = None) -> list[HansardHit]:
    """Parse APH Hansard Search HTML. Prefer whole-document hits (sid=0000)."""
    allowed = {k.lower() for k in kinds} if kinds else None
    soup = BeautifulSoup(html, "lxml")
    hits: list[HansardHit] = []
    seen: set[str] = set()
    for anchor in soup.select("ul.search-filter-results p.title a[href]"):
        href = unescape(anchor.get("href") or "")
        label = " ".join(anchor.get_text(" ", strip=True).split())
        match = _BID.search(href) or _BID.search(unescape(str(anchor)))
        if not match:
            parsed = urlparse(href)
            qs = parse_qs(parsed.query)
            if "bid" not in qs or "sid" not in qs:
                continue
            bid = _normalise_bid(qs["bid"][0])
            sid = qs["sid"][0].zfill(4)
            kind = bid.split("/")[1] if "/" in bid else ""
        else:
            bid = _normalise_bid(match.group("bid"))
            sid = match.group("sid").zfill(4)
            kind = match.group("kind").lower()
        if allowed and kind not in allowed:
            continue
        if sid != "0000":
            # Fragments of the same Official — ingest the full document once.
            continue
        key = f"{bid}{sid}"
        if key in seen:
            continue
        seen.add(key)
        display_url = urljoin(APH_ORIGIN, f"/Parliamentary_Business/Hansard/Hansard_Display?bid={bid}&sid={sid}")
        date_text = None
        parent = anchor.find_parent("li")
        if parent:
            for dt in parent.find_all("dt"):
                if "DATE" in dt.get_text(" ", strip=True).upper():
                    dd = dt.find_next_sibling("dd")
                    if dd:
                        date_text = dd.get_text(" ", strip=True)
                        break
        hits.append(
            HansardHit(
                title=label,
                bid=bid,
                sid=sid,
                kind=kind,
                display_url=display_url,
                held_on_text=date_text,
            )
        )
    return hits


def html_to_text(html: str) -> str:
    if not html:
        return ""
    soup = BeautifulSoup(html, "lxml")
    text = soup.get_text("\n")
    lines = [" ".join(line.split()) for line in text.splitlines()]
    return "\n".join(line for line in lines if line)


def _committee_from_title(title: str, *, kind: str, aph_url: str | None = None) -> CommitteeIn:
    head = title.split(";")[0].split(" - ")[0].strip()
    head = re.sub(r"\s+Legislation Committee$", "", head, flags=re.I)
    head = re.sub(r"\s+References Committee$", "", head, flags=re.I)
    name = head or title[:80]
    chamber = "Senate"
    if kind == "commjnt" or "joint" in name.lower():
        chamber = "Joint"
    return CommitteeIn(
        slug=slug(name)[:80],
        name=name,
        chamber=chamber,
        kind="legislation" if "legislation" in title.lower() else "committee",
        aph_url=aph_url,
    )


def _people_from_official(text: str) -> list[AppearanceIn]:
    appearances: list[AppearanceIn] = []
    seen: set[str] = set()
    block = text
    if "In Attendance" in text:
        after = text.split("In Attendance", 1)[1]
        block = after.split("Committee met", 1)[0]
    for raw_line in block.splitlines():
        line = " ".join(raw_line.split())
        if not line:
            continue
        chair = _CHAIR_INLINE.match(line)
        if chair:
            line = chair.group("inner").strip()
            forced_role = "chair"
        else:
            forced_role = None
        match = _ATTEND.match(line)
        if match:
            title = match.group("title").strip()
            rest = match.group("name").strip()
            name_part, role_title = split_name_and_role(rest)
            display = f"{title} {name_part}".strip()
        else:
            name_part, role_title = split_name_and_role(line)
            if should_skip_person(name_part):
                continue
            # Unprefixed lines are only kept when they look like "Name, Agency title"
            if not role_title:
                continue
            title = None
            display = name_part
        if should_skip_person(display):
            continue
        person_slug = canonical_slug(display)
        if not person_slug or person_slug in seen:
            continue
        seen.add(person_slug)
        role = forced_role or infer_role(title, role_title)
        appearances.append(
            AppearanceIn(
                person=PersonIn(
                    slug=person_slug,
                    name=display,
                    role_title=role_title,
                    organisation=None,
                ),
                person_slug=person_slug,
                role=role,  # type: ignore[arg-type]
            )
        )
        if len(appearances) >= 24:
            break
    if len(appearances) < 24:
        for raw_line in text.splitlines():
            chair = _CHAIR_INLINE.match(" ".join(raw_line.split()))
            if not chair:
                continue
            inner = chair.group("inner").strip()
            match = _ATTEND.match(inner)
            display = inner if not match else f"{match.group('title').strip()} {split_name_and_role(match.group('name'))[0]}".strip()
            person_slug = canonical_slug(display)
            if not person_slug or person_slug in seen or should_skip_person(display):
                continue
            seen.add(person_slug)
            appearances.append(
                AppearanceIn(
                    person=PersonIn(slug=person_slug, name=display, role_title="Chair"),
                    person_slug=person_slug,
                    role="chair",
                )
            )
            break
    return appearances


def hearing_from_transcript(
    hit: HansardHit,
    payload: dict,
    *,
    source: str,
    hearing_type: str,
) -> HearingIn:
    main_title = (payload.get("MainTitle") or hit.title or "").strip()
    date_text = payload.get("Date") or hit.held_on_text or main_title
    held_on = parse_date(str(date_text or "")) or parse_date(hit.title)
    talk_html = payload.get("TalkText") or ""
    content = html_to_text(talk_html)
    committee = _committee_from_title(main_title or hit.title, kind=hit.kind, aph_url=hit.display_url)
    doc_id = document_id(hit.bid)
    system_id = payload.get("SystemId") or f"{hit.bid}{hit.sid}"
    xml_link = payload.get("ViewSaveXMLLink")
    display_url = hit.display_url
    documents: list[DocumentIn] = []
    if content:
        documents.append(
            DocumentIn(
                title=main_title or hit.title,
                doc_type="hansard",
                source_url=display_url,
                source_key=f"hansard:{system_id}",
                content_text=content,
                published_at=held_on,
                license_note=LICENSE_NOTE,
            )
        )
    title = main_title or hit.title
    if hearing_type == "estimates" and "estimate" not in title.lower():
        title = f"{title} — Estimates"
    return HearingIn(
        slug=slug(f"{hit.kind}-{doc_id}-{title}")[:80],
        title=title,
        hearing_type=hearing_type,  # type: ignore[arg-type]
        held_on=held_on,
        source=source,
        source_url=display_url,
        source_key=f"hansard:{hit.bid.strip('/')}",
        status="published" if content else "listed",
        summary=(
            f"Official Hansard via APH /api/hansard/transcript ({system_id})."
            + (f" ParlInfo XML (WAF-gated from some IPs): {xml_link}" if xml_link else "")
        )[:500],
        committee=committee,
        people=_people_from_official(content),
        documents=documents,
    )


class HansardApi:
    """Official APH Hansard search + JSON transcript API on www.aph.gov.au."""

    def __init__(self, client: AphClient | None = None) -> None:
        self.client = client or AphClient()

    def search(
        self,
        *,
        chi: int,
        kinds: Iterable[str],
        limit: int = 0,
        page_size: int = 20,
        max_pages: int = 12,
    ) -> list[HansardHit]:
        hits: list[HansardHit] = []
        seen: set[str] = set()
        for page in range(1, max_pages + 1):
            url = (
                f"{HANSARD_SEARCH}?expand=1&q=&ps={page_size}&drt=2&drv=0&drvH=0"
                f"&pnu=0&pnuH=0&pi=0&chi={chi}&coi=0&st=1"
            )
            if page > 1:
                url += f"&page={page}"
            html = self.client.get_text(
                url, referer=f"{APH_ORIGIN}/Parliamentary_Business/Hansard"
            )
            page_hits = parse_search_hits(html, kinds=kinds)
            new = 0
            for hit in page_hits:
                key = hit.bid
                if key in seen:
                    continue
                seen.add(key)
                hits.append(hit)
                new += 1
                if limit and len(hits) >= limit:
                    return hits
            if not page_hits or new == 0:
                break
        return hits

    def fetch_transcript(self, hit: HansardHit) -> dict:
        system_id = f"{hit.bid}{hit.sid}"
        return self.client.get_json(
            f"{TRANSCRIPT_API}?id={system_id}",
            referer=hit.display_url,
        )
