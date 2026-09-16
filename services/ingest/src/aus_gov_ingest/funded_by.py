"""Sourced FUNDED_BY links: contract/grant → measure/program.

Only write a link when evidence is strong:

* fixture metadata names ``funded_by_source_key``, or
* the contract title/description contains a distinctive program/measure
  title **and** the agency matches **and** the published year/period overlaps.

Weak fuzzy title similarity is skipped. No invented CNs or measures.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date

from aus_gov_ingest.models import InstrumentIn, InstrumentLinkIn
from aus_gov_ingest.sources.util import slug

MIN_TITLE_LEN = 12
_PROGRAM_PREFIX = re.compile(r"^program\s+\d+(?:\.\d+)*:\s*", re.I)
_AGENCY_NOISE = re.compile(
    r"\b(department of|australian|the|commonwealth of australia)\b",
    re.I,
)


@dataclass(frozen=True)
class FundedByMatch:
    contract_source_key: str
    funder_source_key: str
    confidence: float
    reason: str
    evidence: str


def normalize_agency(name: str | None) -> str:
    text = _AGENCY_NOISE.sub(" ", (name or "").lower())
    return " ".join(text.split())


def agencies_match(left: str | None, right: str | None) -> bool:
    a, b = normalize_agency(left), normalize_agency(right)
    if not a or not b:
        return False
    return a == b or a in b or b in a or slug(a) == slug(b)


def distinctive_title(title: str | None) -> str:
    text = _PROGRAM_PREFIX.sub("", (title or "").strip())
    return " ".join(text.split())


def title_contained(haystack: str | None, needle: str | None) -> bool:
    hay = " ".join((haystack or "").lower().split())
    need = distinctive_title(needle).lower()
    if len(need) < MIN_TITLE_LEN:
        return False
    return need in hay


def _year_from_identifiers(item: InstrumentIn) -> str | None:
    ids = item.identifiers or {}
    year = ids.get("year")
    if year:
        return str(year)
    for field in (item.announced_on, item.commenced_on, item.ended_on):
        if field:
            return f"{field.year}-{str(field.year + 1)[-2:]}"
    return None


def _period_overlaps(contract: InstrumentIn, funder: InstrumentIn) -> bool:
    funder_year = _year_from_identifiers(funder)
    contract_dates = [d for d in (contract.announced_on, contract.commenced_on, contract.ended_on) if d]
    if funder_year and contract_dates:
        # PBS / BP2 years look like 2025-26.
        try:
            start_year = int(str(funder_year)[:4])
        except ValueError:
            start_year = None
        if start_year:
            window = (date(start_year, 7, 1), date(start_year + 1, 6, 30))
            return any(window[0] <= d <= window[1] for d in contract_dates)
    if contract.commenced_on and funder.ended_on and contract.commenced_on > funder.ended_on:
        return False
    if contract.ended_on and funder.announced_on and contract.ended_on < funder.announced_on:
        return False
    return True


def match_funded_by(
    contracts: list[InstrumentIn],
    funders: list[InstrumentIn],
) -> list[FundedByMatch]:
    """Return unique high-evidence contract → funder matches."""
    out: list[FundedByMatch] = []
    seen: set[tuple[str, str]] = set()
    funder_by_key = {f.source_key: f for f in funders if f.source_key}

    for contract in contracts:
        if contract.kind not in {"contract", "grant"}:
            continue
        explicit = (contract.identifiers or {}).get("funded_by_source_key")
        if explicit and explicit in funder_by_key:
            pair = (contract.source_key, str(explicit))
            if pair not in seen:
                seen.add(pair)
                funder = funder_by_key[str(explicit)]
                out.append(
                    FundedByMatch(
                        contract_source_key=contract.source_key,
                        funder_source_key=funder.source_key,
                        confidence=0.95,
                        reason="fixture_funded_by_source_key",
                        evidence=f"Fixture metadata on {contract.source_key} names {funder.source_key}.",
                    )
                )
            continue

        candidates: list[FundedByMatch] = []
        hay = " ".join(
            p
            for p in (
                contract.title,
                (contract.identifiers or {}).get("contract_title"),
                contract.evidence_text,
                contract.notes,
            )
            if p
        )
        for funder in funders:
            if funder.kind not in {"measure", "program"}:
                continue
            if funder.source_key == contract.source_key:
                continue
            if not title_contained(hay, funder.title):
                continue
            if not agencies_match(contract.agency_name, funder.agency_name):
                continue
            if not _period_overlaps(contract, funder):
                continue
            needle = distinctive_title(funder.title)
            candidates.append(
                FundedByMatch(
                    contract_source_key=contract.source_key,
                    funder_source_key=funder.source_key,
                    confidence=0.85,
                    reason="title+agency+period",
                    evidence=(
                        f"Contract title/description contains {needle!r}; "
                        f"agency {contract.agency_name} matches {funder.agency_name}."
                    ),
                )
            )
        if len(candidates) == 1:
            pair = (candidates[0].contract_source_key, candidates[0].funder_source_key)
            if pair not in seen:
                seen.add(pair)
                out.append(candidates[0])
        # Multiple funders matching the same contract → skip (do not guess).
    return out


def links_from_matches(matches: list[FundedByMatch]) -> list[InstrumentLinkIn]:
    return [
        InstrumentLinkIn(
            instrument_source_key=m.contract_source_key,
            link_kind="funded_by",
            target_kind="instrument",
            other_instrument_source_key=m.funder_source_key,
            source="funded_by",
            notes=f"{m.reason}; confidence={m.confidence:.2f}. {m.evidence}",
            confidence=m.confidence,
        )
        for m in matches
    ]
