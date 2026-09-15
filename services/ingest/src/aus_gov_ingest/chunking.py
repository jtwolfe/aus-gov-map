from __future__ import annotations

import re
from dataclasses import dataclass


_SPEAKER = re.compile(
    r"^(?P<speaker>CHAIR|WITNESS|Prof\.?\s+\w+|Ms\.?\s+\w+|Mr\.?\s+\w+|Senator(?:\s+the\s+Hon)?\s+[\w']+):\s*",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class Chunk:
    index: int
    content: str
    speaker_name: str | None
    token_count: int


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
        speaker = None
        match = _SPEAKER.match(content)
        if match:
            speaker = re.sub(r"\s+", " ", match.group("speaker")).strip()
        elif ":" in content.split("\n", 1)[0]:
            speaker = content.split(":", 1)[0].strip()[:80]
        chunks.append(
            Chunk(
                index=idx,
                content=content,
                speaker_name=speaker,
                token_count=max(1, len(content.split())),
            )
        )
    return chunks
