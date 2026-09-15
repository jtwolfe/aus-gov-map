"""Lightweight proposed-instrument extractor.

Candidates are **proposed** only (low confidence). Not asserted facts.
"""

from __future__ import annotations

import hashlib
import re

from aus_gov_ingest.chunking import Chunk
from aus_gov_ingest.models import InstrumentIn
from aus_gov_ingest.people import slug

_BILL = re.compile(
    r"\b([A-Z][A-Za-z0-9][A-Za-z0-9 ,''()\-]{6,90}? (?:Amendment )?(?:\(.*?\) )?Bill 20\d{2})\b"
)
_PROGRAM = re.compile(
    r"\b((?:The )?(?:National |Commonwealth |Australian )?[A-Z][A-Za-z]+(?:[ -][A-Z][A-Za-z]+){0,6} (?:Program|Programme|Scheme|Fund|Plan))\b"
)
_CONTRACT = re.compile(
    r"\b((?:contract|consultancy|procurement)s?\s+(?:with|for|of|to)\s+[A-Z][A-Za-z0-9&.' \-]{2,60})",
    re.I,
)
_GRANT = re.compile(
    r"\b((?:grant|grants)\s+(?:to|for|under)\s+[A-Z][A-Za-z0-9&.' \-]{2,60})",
    re.I,
)

_SKIP = {
    "in attendance",
    "committee met",
    "hansard",
    "estimates",
    "question on notice",
}


def propose_instruments(
    chunks: list[Chunk],
    *,
    hearing_source_key: str | None = None,
    document_source_key: str | None = None,
) -> list[InstrumentIn]:
    """Scan chunk text for bill / program / contract / grant candidates."""
    seen: set[str] = set()
    out: list[InstrumentIn] = []
    for chunk in chunks:
        chunk_key = (
            f"chunk:{document_source_key}:{chunk.index}"
            if document_source_key is not None
            else None
        )
        for kind, match, confidence in _candidates(chunk.content):
            title = _clean_title(match)
            if not title or title.lower() in _SKIP:
                continue
            key = f"{kind}:{slug(title)[:80]}"
            if key in seen:
                continue
            seen.add(key)
            digest = hashlib.sha1(
                f"{hearing_source_key or ''}|{chunk_key or ''}|{key}".encode()
            ).hexdigest()[:12]
            out.append(
                InstrumentIn(
                    source_key=f"instrument:{digest}:{key}",
                    title=title,
                    kind=kind,  # type: ignore[arg-type]
                    status="proposed",
                    confidence=confidence,
                    source_chunk_key=chunk_key,
                    hearing_source_key=hearing_source_key,
                    evidence_text=chunk.content[:400],
                    notes=(
                        "Proposed from Estimates text. Low confidence. "
                        "Human review required — not an asserted decision object."
                    ),
                    metadata={
                        "extractor": "regex_v1",
                        "speaker_name": chunk.speaker_name,
                        "portfolio": chunk.portfolio,
                        "agency": chunk.agency,
                    },
                )
            )
    return out


def _candidates(text: str) -> list[tuple[str, str, float]]:
    found: list[tuple[str, str, float]] = []
    for match in _BILL.finditer(text):
        found.append(("bill", match.group(1), 0.45))
    for match in _PROGRAM.finditer(text):
        title = match.group(1)
        if title.lower().startswith("the "):
            title = title[4:]
        if len(title.split()) < 2:
            continue
        found.append(("program", title, 0.28))
    for match in _CONTRACT.finditer(text):
        found.append(("contract", match.group(1), 0.22))
    for match in _GRANT.finditer(text):
        found.append(("grant", match.group(1), 0.22))
    return found


def _clean_title(text: str) -> str:
    title = " ".join((text or "").split()).strip(" ,;:.")
    return title[:160]
