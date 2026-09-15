"""Parse Official Hansard TalkText into Estimates segments.

Derived structure only — same Official text, not a second Hansard.
"""

from __future__ import annotations

import re
from collections import Counter

from aus_gov_ingest.chunking import Chunk, extract_speaker
from aus_gov_ingest.models import HearingSegmentIn

_TAKEN_ON_NOTICE = re.compile(
    r"\b(?:take|takes|taking|taken)\s+(?:that\s+|this\s+|the\s+question\s+|it\s+)?"
    r"on\s+notice\b|\bquestions?\s+on\s+notice\b|\bQoN\b",
    re.I,
)
_PORTFOLIO_HEADER = re.compile(
    r"^(?P<name>[A-Z][A-Z0-9 &/'(),.-]{3,80})\s+PORTFOLIO$",
)
_AGENCY_LINE = re.compile(
    r"^(?:Department of |Australian |National |Parliamentary )",
    re.I,
)
_SKIP_HEADERS = {
    "in attendance",
    "committee met",
    "committee adjourned",
    "proceedings",
    "evidence was taken",
}


def tidy_line(text: str) -> str:
    return " ".join((text or "").split()).strip()


def tidy_portfolio(text: str) -> str:
    raw = tidy_line(text)
    raw = re.sub(r"\s+PORTFOLIO$", "", raw, flags=re.I)
    if raw.isupper() and len(raw) > 3:
        return raw.title()
    return raw


def is_taken_on_notice(text: str) -> bool:
    return bool(_TAKEN_ON_NOTICE.search(text or ""))


def looks_like_html(text: str) -> bool:
    stripped = (text or "").lstrip()
    return stripped.startswith("<") and ("<p" in stripped[:2000].lower() or "<div" in stripped[:400].lower())


def parse_official_segments(html_or_text: str, *, fallback_text: str | None = None) -> list[HearingSegmentIn]:
    """Parse Official HTML (preferred) or plain text into ordered segments."""
    if looks_like_html(html_or_text):
        segments = _from_html(html_or_text)
        if segments:
            return segments
    return _from_text(fallback_text if fallback_text is not None else html_or_text)


def _from_html(html: str) -> list[HearingSegmentIn]:
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "lxml")
    segments: list[HearingSegmentIn] = []
    portfolio: str | None = None
    agency: str | None = None
    cursor = 0
    for tag in soup.find_all("p"):
        text = tidy_line(tag.get_text(" ", strip=True))
        if not text or _skip_header(text):
            cursor += len(text) + 1
            continue
        classes = set(tag.get("class") or [])
        kind = "other"
        speaker = None
        if "HPS-Debate" in classes:
            portfolio = tidy_portfolio(text)
            kind = "portfolio_header"
        elif "HPS-SubSubDebate" in classes:
            agency = text
            kind = "agency_header"
        else:
            speaker = extract_speaker(text)
            if speaker:
                kind = "speaker_turn"
            elif _PORTFOLIO_HEADER.match(text):
                portfolio = tidy_portfolio(text)
                kind = "portfolio_header"
            elif _looks_like_agency(text):
                agency = text
                kind = "agency_header"
        ton = is_taken_on_notice(text)
        if ton and kind == "other":
            kind = "taken_on_notice"
        meta: dict = {}
        if ton:
            meta["taken_on_notice"] = True
        start = cursor
        end = cursor + len(text)
        segments.append(
            HearingSegmentIn(
                kind=kind,  # type: ignore[arg-type]
                speaker_name=speaker,
                portfolio=portfolio,
                agency=agency,
                content=text,
                char_start=start,
                char_end=end,
                metadata=meta,
            )
        )
        if ton and kind == "speaker_turn":
            segments.append(
                HearingSegmentIn(
                    kind="taken_on_notice",
                    speaker_name=speaker,
                    portfolio=portfolio,
                    agency=agency,
                    content=text,
                    char_start=start,
                    char_end=end,
                    metadata={"from_speaker_turn": True},
                )
            )
        cursor = end + 1
    return segments


def _from_text(text: str) -> list[HearingSegmentIn]:
    segments: list[HearingSegmentIn] = []
    portfolio: str | None = None
    agency: str | None = None
    cursor = 0
    for raw in (text or "").splitlines():
        line = tidy_line(raw)
        if not line:
            cursor += 1
            continue
        if _skip_header(line):
            cursor += len(line) + 1
            continue
        kind = "other"
        speaker = extract_speaker(line)
        if _PORTFOLIO_HEADER.match(line) or (line.isupper() and line.endswith("PORTFOLIO")):
            portfolio = tidy_portfolio(line)
            kind = "portfolio_header"
            speaker = None
        elif _looks_like_agency(line) and not speaker:
            agency = line
            kind = "agency_header"
        elif speaker:
            kind = "speaker_turn"
        ton = is_taken_on_notice(line)
        if ton and kind == "other":
            kind = "taken_on_notice"
        meta: dict = {}
        if ton:
            meta["taken_on_notice"] = True
        start = cursor
        end = cursor + len(line)
        segments.append(
            HearingSegmentIn(
                kind=kind,  # type: ignore[arg-type]
                speaker_name=speaker,
                portfolio=portfolio,
                agency=agency,
                content=line,
                char_start=start,
                char_end=end,
                metadata=meta,
            )
        )
        if ton and kind == "speaker_turn":
            segments.append(
                HearingSegmentIn(
                    kind="taken_on_notice",
                    speaker_name=speaker,
                    portfolio=portfolio,
                    agency=agency,
                    content=line,
                    char_start=start,
                    char_end=end,
                    metadata={"from_speaker_turn": True},
                )
            )
        cursor = end + 1
    return segments


def _skip_header(text: str) -> bool:
    lowered = text.lower().rstrip(".:")
    return any(lowered.startswith(skip) for skip in _SKIP_HEADERS)


def _looks_like_agency(text: str) -> bool:
    if extract_speaker(text):
        return False
    if len(text) > 120 or len(text) < 8:
        return False
    if text.endswith(":"):
        return False
    if _AGENCY_LINE.match(text):
        return True
    if re.search(
        r"\b(Commission|Office|Authority|Agency|Corporation|Service)\b",
        text,
    ) and not re.search(r"\b(I |we |the committee|senator)\b", text, re.I):
        return text[0].isupper() and text.count(" ") <= 10
    return False


def dominant_portfolio(segments: list[HearingSegmentIn]) -> str | None:
    names = [s.portfolio for s in segments if s.portfolio]
    if not names:
        return None
    return Counter(names).most_common(1)[0][0]


def annotate_chunks(chunks: list[Chunk], segments: list[HearingSegmentIn]) -> list[Chunk]:
    """Copy speaker / portfolio / agency / QoN flags onto packed chunks."""
    if not chunks:
        return []
    if not segments:
        return list(chunks)
    annotated: list[Chunk] = []
    last_portfolio = None
    last_agency = None
    seg_idx = 0
    for chunk in chunks:
        hay = " ".join(chunk.content.split())
        speaker = chunk.speaker_name
        portfolio = last_portfolio
        agency = last_agency
        taken = False
        kinds: list[str] = []
        while seg_idx < len(segments):
            seg = segments[seg_idx]
            needle = " ".join(seg.content.split())[:72]
            if needle and needle in hay:
                if seg.portfolio:
                    portfolio = seg.portfolio
                    last_portfolio = seg.portfolio
                if seg.agency:
                    agency = seg.agency
                    last_agency = seg.agency
                if seg.speaker_name:
                    speaker = speaker or seg.speaker_name
                if seg.kind == "taken_on_notice" or seg.metadata.get("taken_on_notice"):
                    taken = True
                kinds.append(seg.kind)
                seg_idx += 1
            elif seg.kind in {"portfolio_header", "agency_header"}:
                if seg.portfolio:
                    last_portfolio = seg.portfolio
                if seg.agency:
                    last_agency = seg.agency
                # Header may sit in an earlier chunk; keep walking only if it
                # cannot belong to this chunk.
                if needle and needle not in hay:
                    seg_idx += 1
                    continue
                break
            else:
                break
        # Also scan remaining nearby segments for overlap without consuming.
        for peek in segments[seg_idx : seg_idx + 8]:
            needle = " ".join(peek.content.split())[:72]
            if needle and needle in hay:
                if peek.portfolio:
                    portfolio = peek.portfolio
                if peek.agency:
                    agency = peek.agency
                if peek.speaker_name and not speaker:
                    speaker = peek.speaker_name
                if peek.kind == "taken_on_notice" or peek.metadata.get("taken_on_notice"):
                    taken = True
        if is_taken_on_notice(chunk.content):
            taken = True
        annotated.append(
            Chunk(
                index=chunk.index,
                content=chunk.content,
                speaker_name=speaker,
                token_count=chunk.token_count,
                portfolio=portfolio,
                agency=agency,
                taken_on_notice=taken,
            )
        )
    return annotated
