"""Agency / department stub source.

Loads the committed official-name list (Directory / AAO). Does not scrape
Wikipedia. Secretaries are not included — see Handbook gaps.
"""

from __future__ import annotations

import json
from pathlib import Path

from aus_gov_ingest.models import AgencyIn, SourceBatch


def default_agencies_path() -> Path:
    here = Path(__file__).resolve()
    for parent in here.parents:
        candidate = parent / "fixtures" / "live" / "agencies.json"
        if candidate.is_file():
            return candidate
    return here.parents[3] / "fixtures" / "live" / "agencies.json"


class AgenciesSource:
    name = "agencies"

    def __init__(self, *, path: Path | str | None = None) -> None:
        self.path = Path(path) if path else default_agencies_path()

    def fetch(self, *, limit: int = 0, incremental_keys: set[str] | None = None) -> SourceBatch:
        path = self.path
        if path.is_dir():
            candidate = path / "agencies.json"
            path = candidate if candidate.is_file() else next(path.glob("*.json"))
        raw = json.loads(path.read_text(encoding="utf-8"))
        rows = raw.get("agencies") if isinstance(raw, dict) else raw
        known = incremental_keys or set()
        agencies: list[AgencyIn] = []
        for row in rows or []:
            slug = row.get("slug")
            if not slug or f"agency:{slug}" in known:
                continue
            agencies.append(AgencyIn.model_validate(row))
            if limit and len(agencies) >= limit:
                break
        return SourceBatch(
            source=self.name,
            agencies=agencies,
            meta={
                "status": "ok",
                "path": str(self.path),
                "source_url": raw.get("source_url") if isinstance(raw, dict) else None,
                "note": raw.get("note") if isinstance(raw, dict) else None,
                "license_note": raw.get("license_note") if isinstance(raw, dict) else None,
                "gaps": (
                    "Secretaries / SES are not seeded. Parliamentary Handbook is "
                    "parliamentarians only; use directory.gov.au or an APS source."
                ),
            },
        )
