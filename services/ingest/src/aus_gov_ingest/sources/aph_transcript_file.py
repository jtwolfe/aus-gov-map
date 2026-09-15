from __future__ import annotations

import json
from pathlib import Path

from aus_gov_ingest.config import settings
from aus_gov_ingest.models import HearingIn, SourceBatch
from aus_gov_ingest.sources.hansard import (
    hearing_from_transcript,
    hit_from_transcript_payload,
)


def default_transcript_dir() -> Path:
    here = Path(__file__).resolve()
    for parent in here.parents:
        candidate = parent / "fixtures" / "live" / "transcripts"
        if candidate.is_dir():
            return candidate
    return here.parents[3] / "fixtures" / "live" / "transcripts"


class AphTranscriptFileSource:
    """Load saved APH `/api/hansard/transcript` JSON (offline Official ingest).

    Accepts a file or a directory of `*.json` objects that include `TalkText`.
    Reuses `hearing_from_transcript` so keys match live Estimates ingest
    (`hansard:committees/estimate/{id}`).
    """

    name = "aph_transcript_file"

    def __init__(self, path: Path | str | None = None) -> None:
        if path is not None:
            self.path = Path(path)
        elif settings.aus_gov_transcript_path:
            self.path = Path(settings.aus_gov_transcript_path)
        else:
            self.path = default_transcript_dir()

    def fetch(self, *, limit: int = 0, incremental_keys: set[str] | None = None) -> SourceBatch:
        known = incremental_keys or set()
        hearings: list[HearingIn] = []
        errors: list[str] = []
        files = self._files()
        for file in files:
            try:
                payload = self._load_payload(file)
                hit = hit_from_transcript_payload(payload, filename=file.name)
                source, hearing_type = _source_for_kind(hit.kind)
                hearing = hearing_from_transcript(
                    hit, payload, source=source, hearing_type=hearing_type
                )
            except Exception as exc:
                errors.append(f"{file.name}: {exc}")
                continue
            if hearing.source_key in known:
                continue
            hearings.append(hearing)
            if limit and len(hearings) >= limit:
                break
        return SourceBatch(
            source=self.name,
            hearings=hearings,
            people=[p.person for h in hearings for p in h.people if p.person],
            committees=[h.committee for h in hearings if h.committee],
            meta={
                "path": str(self.path),
                "files": [f.name for f in files],
                "transport": "aph_transcript_file",
                "errors": errors,
            },
        )

    def _files(self) -> list[Path]:
        path = self.path
        if not path.exists():
            raise FileNotFoundError(f"Transcript path not found: {path}")
        if path.is_file():
            return [path]
        files = sorted(p for p in path.glob("*.json") if p.is_file())
        if not files:
            raise FileNotFoundError(f"No *.json transcripts in {path}")
        return files

    @staticmethod
    def _load_payload(path: Path) -> dict:
        text = path.read_text(encoding="utf-8")
        stripped = text.lstrip()
        if stripped.startswith("<!") or stripped[:5].lower() == "<html":
            raise ValueError(f"{path.name} looks like HTML, not APH transcript JSON")
        payload = json.loads(text)
        if not isinstance(payload, dict):
            raise ValueError(f"{path.name} is not a JSON object")
        if not payload.get("TalkText"):
            raise ValueError(f"{path.name} is missing TalkText")
        return payload


def _source_for_kind(kind: str) -> tuple[str, str]:
    if kind == "estimate":
        return "estimates", "estimates"
    return "senate_committee", "committee"
