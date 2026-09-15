#!/usr/bin/env python3
"""Discover Senate Estimates Official IDs via Hansard Search (chi=5) and save JSON.

Uses AphClient (browser-like UA on www.aph.gov.au). Does not invent IDs and
does not follow ParlInfo XML/PDF redirects.

Default windows cover Budget 2026–27, Additional 2025–26, Supplementary
2025–26, and nearby Additional 2024–25.

Example:
  python3 scripts/fetch_estimates_transcripts.py
  python3 scripts/fetch_estimates_transcripts.py --per-round 4 --dry-discover
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path

# Allow `python3 scripts/fetch_estimates_transcripts.py` from services/ingest.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from aus_gov_ingest.http import AphClient  # noqa: E402
from aus_gov_ingest.sources.hansard import (  # noqa: E402
    APH_ORIGIN,
    CHI_ESTIMATES,
    HANSARD_SEARCH,
    TRANSCRIPT_API,
    HansardHit,
    document_id,
    parse_search_hits,
)

DEFAULT_OUT = Path(__file__).resolve().parents[1] / "fixtures" / "live" / "transcripts"


@dataclass(frozen=True)
class RoundWindow:
    slug: str
    label: str
    date_from: str  # dd/mm/yyyy
    date_to: str


# Recent Estimates rounds visible on Hansard Search as of 2026-09-15.
# Budget 2025–26 hearings were not listed (2025 election caretaker window).
DEFAULT_ROUNDS = (
    RoundWindow("budget-2026-27", "Budget Estimates 2026–27", "01/05/2026", "15/06/2026"),
    RoundWindow("additional-2025-26", "Additional Estimates 2025–26", "01/02/2026", "15/03/2026"),
    RoundWindow("supplementary-2025-26", "Supplementary Budget Estimates 2025–26", "01/10/2025", "15/11/2025"),
    RoundWindow("additional-2024-25", "Additional Estimates 2024–25 (nearby)", "01/02/2025", "31/03/2025"),
)


def _committee_key(title: str) -> str:
    head = title.split(";")[0].split(" - ")[0].strip().lower()
    return head


def search_round(
    client: AphClient,
    window: RoundWindow,
    *,
    per_round: int,
    page_size: int = 50,
    max_pages: int = 4,
) -> list[HansardHit]:
    hits: list[HansardHit] = []
    seen: set[str] = set()
    committees: set[str] = set()
    for page in range(1, max_pages + 1):
        url = (
            f"{HANSARD_SEARCH}?expand=1&q=&ps={page_size}"
            f"&drt=1&drv=0&drvH=0&hto=1"
            f"&from={window.date_from}&to={window.date_to}"
            f"&pnu=0&pnuH=0&pi=0&chi={CHI_ESTIMATES}&coi=0&st=1"
        )
        if page > 1:
            url += f"&page={page}"
        html = client.get_text(url, referer=f"{APH_ORIGIN}/Parliamentary_Business/Hansard")
        page_hits = parse_search_hits(html, kinds=("estimate",))
        # Prefer a new committee when possible so the backfill is not one portfolio.
        ranked = sorted(
            page_hits,
            key=lambda h: (0 if _committee_key(h.title) not in committees else 1, h.title),
        )
        for hit in ranked:
            doc = document_id(hit.bid)
            if doc in seen:
                continue
            seen.add(doc)
            committees.add(_committee_key(hit.title))
            hits.append(hit)
            if len(hits) >= per_round:
                return hits
        if not page_hits:
            break
    return hits


def fetch_and_save(client: AphClient, hit: HansardHit, dest: Path) -> dict:
    system_id = f"{hit.bid}{hit.sid}"
    payload = client.get_json(
        f"{TRANSCRIPT_API}?id={system_id}",
        referer=hit.display_url,
    )
    if not isinstance(payload, dict) or not payload.get("TalkText"):
        raise ValueError(f"{system_id} missing TalkText (not Official JSON)")
    dest.write_text(
        json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )
    return payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT, help="Directory for {id}.json")
    parser.add_argument("--per-round", type=int, default=5, help="Max distinct Officials per date window")
    parser.add_argument("--skip-existing", action="store_true", default=True)
    parser.add_argument("--refresh", action="store_true", help="Re-download files that already exist")
    parser.add_argument("--dry-discover", action="store_true", help="Print IDs only; do not fetch JSON")
    args = parser.parse_args(argv)

    skip_existing = args.skip_existing and not args.refresh
    args.out.mkdir(parents=True, exist_ok=True)

    client = AphClient()
    selected: list[tuple[RoundWindow, HansardHit]] = []
    seen_ids: set[str] = set()
    try:
        for window in DEFAULT_ROUNDS:
            for hit in search_round(client, window, per_round=args.per_round):
                doc = document_id(hit.bid)
                if doc in seen_ids:
                    continue
                seen_ids.add(doc)
                selected.append((window, hit))
        print(f"discovered {len(selected)} distinct Estimates Officials via chi={CHI_ESTIMATES}", flush=True)
        for window, hit in selected:
            print(f"  {document_id(hit.bid)}\t{window.slug}\t{hit.held_on_text or '-'}\t{hit.title}", flush=True)
        if args.dry_discover:
            return 0

        saved = 0
        skipped = 0
        errors: list[str] = []
        for window, hit in selected:
            doc = document_id(hit.bid)
            dest = args.out / f"{doc}.json"
            if dest.exists() and skip_existing:
                print(f"skip existing {dest.name}", flush=True)
                skipped += 1
                continue
            try:
                payload = fetch_and_save(client, hit, dest)
                talk = payload.get("TalkText") or ""
                print(
                    f"saved {dest.name}  {payload.get('MainTitle')}  talk={len(talk)}",
                    flush=True,
                )
                saved += 1
            except Exception as exc:
                errors.append(f"{doc}: {exc}")
                print(f"ERROR {doc}: {exc}", file=sys.stderr, flush=True)
        print(f"done saved={saved} skipped={skipped} errors={len(errors)}", flush=True)
        return 1 if errors else 0
    finally:
        client.close()


if __name__ == "__main__":
    raise SystemExit(main())
