from __future__ import annotations

import re
from dataclasses import dataclass


_SPEAKER = re.compile(
    r"^(?P<speaker>"
    r"CHAIR(?:\s*\([^)]+\))?"
    r"|DEPUTY\s+CHAIR(?:\s*\([^)]+\))?"
    r"|ACTING\s+CHAIR(?:\s*\([^)]+\))?"
    r"|WITNESS"
    r"|Prof(?:essor|\.)?\s+[\w'-]+"
    r"|Dr\.?\s+[\w'-]+"
    r"|Ms\.?\s+[\w'-]+"
    r"|Mr\.?\s+[\w'-]+"
    r"|Mrs\.?\s+[\w'-]+"
    r"|Senator(?:\s+the\s+Hon(?:ourable)?)?\s+[\w'-]+"
    r"):\s*",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class Chunk:
    index: int
    content: str
    speaker_name: str | None
    token_count: int
    portfolio: str | None = None
    agency: str | None = None
    taken_on_notice: bool = False


def extract_speaker(text: str) -> str | None:
    """Return a speaker label from the start of an Official line, if any."""
    if not text:
        return None
    first = text.split("\n", 1)[0]
    match = _SPEAKER.match(first)
    if match:
        return re.sub(r"\s+", " ", match.group("speaker")).strip()
    if ":" in first:
        label = first.split(":", 1)[0].strip()
        if 1 < len(label) <= 80 and not label.lower().startswith("http"):
            # Avoid treating ordinary sentences as speakers.
            if _SPEAKER.match(label + ": ") or label.isupper() or label[:1].isupper():
                if len(label.split()) <= 8:
                    return label
    return None


def chunk_text(text: str, max_chars: int = 900, overlap: int = 80) -> list[Chunk]:
    """Split official-style text on blank lines, then pack to ~max_chars."""
    if not text or not text.strip():
        return []
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    packed: list[str] = []
    buf = ""
    for para in paragraphs:
        if buf and len(buf) + 2 + len(para) > max_chars:
            packed.append(buf)
            buf = (buf[-overlap:] + "\n\n" + para).strip() if overlap else para
        else:
            buf = f"{buf}\n\n{para}".strip() if buf else para
    if buf:
        packed.append(buf)

    chunks: list[Chunk] = []
    for idx, content in enumerate(packed):
        chunks.append(
            Chunk(
                index=idx,
                content=content,
                speaker_name=extract_speaker(content),
                token_count=max(1, len(content.split())),
            )
        )
    return chunks
