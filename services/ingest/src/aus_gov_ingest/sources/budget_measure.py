"""Budget / PBS measure ingest (first pass).

Live (structured, not PDF):
  - Budget Paper No. 2 measures DOCX on budget.gov.au
  - data.gov.au PBS program-expense CSV (2025–26 line items)

PDF Budget Papers are documented as follow-up. Amounts are stored as
published; unit often follows the source table (PBS commonly $'000).
"""

from __future__ import annotations

import csv
import io
import json
import re
from pathlib import Path
from zipfile import ZipFile

from aus_gov_ingest.http import AphClient
from aus_gov_ingest.models import InstrumentIn, SourceBatch
from aus_gov_ingest.sources.util import (
    decode_bytes,
    fixture_live_dir,
    parse_amount,
    slug,
)

BUDGET_HOME = "https://budget.gov.au"
BP2_INDEX = f"{BUDGET_HOME}/content/bp2/index.htm"
BP2_DOCX = f"{BUDGET_HOME}/content/bp2/download/bp2_02_receipt_payment.docx"
PBS_INDEX = "https://www.finance.gov.au/publications/portfolio-budget-statements"
CKAN_PACKAGE = (
    "https://data.gov.au/data/api/3/action/package_show"
    "?id=budget-2025-2026-and-portfolio-budget-statements-pbs-tables-and-data"
)
PBS_CSV = (
    "https://data.gov.au/data/dataset/4f025f38-0c70-45e2-8106-4c29a5e48637"
    "/resource/7cc8640f-b5d4-41de-a665-3197739b965f"
    "/download/2025-26-pbs-program-expense-line-items-final-2025-03-26.csv"
)

ENDPOINTS = {
    "budget": BUDGET_HOME,
    "bp2": BP2_INDEX,
    "bp2_docx": BP2_DOCX,
    "pbs": PBS_INDEX,
    "treasury_budget": "https://treasury.gov.au/publication",
    "data_gov": "https://data.gov.au/data/organization/department-of-the-treasury",
    "pbs_package": CKAN_PACKAGE,
    "pbs_csv": PBS_CSV,
}

LICENSE_NOTE = (
    "© Commonwealth of Australia. Budget Papers / Portfolio Budget Statements. "
    "Typically CC BY. Attribute the Australian Government."
)

_SKIP_MEASURE = {
    "portfolio total",
    "total impact of receipt measures",
    "total impact of payment measures",
    "decisions taken but not yet announced and not for publication (nfp)",
    "related payments",
    "receipts",
}
_YEAR_LINE = re.compile(r"^20\d{2}-?\d{2}$")
_AMOUNT_TOKEN = re.compile(r"^(?:-|\.|nfp|\.\.|[\d,.\-]+)$", re.I)
_AGENCY_HINT = re.compile(
    r"^(Department of|Australian |National |Various Agencies|Office of |Services Australia|"
    r"NBN |Snowy |Housing Australia|Reserve Bank)",
    re.I,
)


def default_budget_dir() -> Path:
    return fixture_live_dir("budget")


class BudgetMeasureSource:
    name = "budget_measure"
    HOME = BUDGET_HOME
    ENDPOINTS = ENDPOINTS

    def __init__(
        self,
        *,
        path: Path | str | None = None,
        client: AphClient | None = None,
    ) -> None:
        self.path = Path(path) if path else None
        self.client = client or AphClient()

    def fetch(self, *, limit: int = 0, incremental_keys: set[str] | None = None) -> SourceBatch:
        errors: list[str] = []
        transport = "budget_structured"
        records: list[dict] = []

        if self.path:
            records, transport = load_budget_path(self.path)
        else:
            try:
                records = self._fetch_live(limit=limit or 40)
            except Exception as exc:
                errors.append(f"budget_live: {exc}")
                try:
                    records, transport = load_budget_path(default_budget_dir())
                    transport = f"fixture_fallback:{transport}"
                except Exception as fallback_exc:
                    errors.append(f"fixture: {fallback_exc}")

        known = incremental_keys or set()
        instruments: list[InstrumentIn] = []
        seen: set[str] = set()
        for row in records:
            item = instrument_from_budget_row(row)
            if not item or item.source_key in known or item.source_key in seen:
                continue
            seen.add(item.source_key)
            instruments.append(item)
            if limit and len(instruments) >= limit:
                break

        kinds = _counts(instruments, key=lambda i: i.kind)
        return SourceBatch(
            source=self.name,
            instruments=instruments,
            meta={
                "status": "ok" if instruments else "empty",
                "home": self.HOME,
                "transport": transport,
                "license_note": LICENSE_NOTE,
                "limit": limit,
                "skipped_existing": len(known),
                "errors": errors,
                "instruments": len(instruments),
                "by_kind": kinds,
                "endpoints": ENDPOINTS,
                "schema": "infra/postgres/007_accountability.sql (instruments)",
                "follow_up": (
                    "Full Budget Paper PDF parsing (BP2 PDF tables, entity PBS PDFs) "
                    "is not in this pass. Structured HTML/CSV/JSON/DOCX only."
                ),
                "note": (
                    "PBS program-expense CSV and/or BP2 measures DOCX into instruments "
                    "(type measure|program). Amounts as published; no invented figures."
                ),
            },
        )

    def _fetch_live(self, *, limit: int) -> list[dict]:
        records: list[dict] = []
        errors: list[str] = []
        try:
            response = self.client.get(BP2_DOCX, referer=BP2_INDEX)
            response.raise_for_status()
            records.extend(parse_bp2_docx(response.content, year="2026-27"))
        except Exception as exc:
            errors.append(f"bp2_docx: {exc}")
        try:
            response = self.client.get(PBS_CSV, referer="https://data.gov.au/")
            response.raise_for_status()
            records.extend(parse_pbs_csv(decode_bytes(response.content)))
        except Exception as exc:
            errors.append(f"pbs_csv: {exc}")
        if not records:
            raise RuntimeError("Budget structured sources empty: " + "; ".join(errors))
        return records[: max(limit, 1) * 4]  # extra headroom before unique-key filter


def load_budget_path(path: Path) -> tuple[list[dict], str]:
    if not path.exists():
        raise FileNotFoundError(f"Budget path not found: {path}")
    files = [path] if path.is_file() else sorted(
        p for p in path.iterdir() if p.is_file() and p.suffix.lower() in {".json", ".csv", ".docx"}
    )
    if not files:
        raise FileNotFoundError(f"No Budget fixtures in {path}")
    records: list[dict] = []
    for file in files:
        suffix = file.suffix.lower()
        if suffix == ".csv":
            records.extend(parse_pbs_csv(decode_bytes(file.read_bytes())))
        elif suffix == ".docx":
            records.extend(parse_bp2_docx(file.read_bytes()))
        else:
            payload = json.loads(file.read_text(encoding="utf-8"))
            if isinstance(payload, list):
                records.extend(r for r in payload if isinstance(r, dict))
            elif isinstance(payload, dict) and isinstance(payload.get("measures"), list):
                records.extend(r for r in payload["measures"] if isinstance(r, dict))
            elif isinstance(payload, dict) and payload.get("title"):
                records.append(payload)
    return records, f"budget_file:{path}"


def parse_pbs_csv(text: str) -> list[dict]:
    reader = csv.DictReader(io.StringIO(text))
    grouped: dict[tuple[str, str, str], dict] = {}
    for raw in reader:
        row = { (k or "").strip(): (v or "").strip() for k, v in raw.items() }
        portfolio = row.get("Portfolio") or ""
        agency = row.get("Department/Agency") or row.get("Department/Entity") or ""
        program = row.get("Program") or row.get("Description") or ""
        if not program or not agency:
            continue
        key = (portfolio, agency, program)
        year_amounts = {
            year: parse_amount(row.get(year))
            for year in ("2024-25", "2025-26", "2026-27", "2027-28", "2028-29")
            if row.get(year) not in (None, "")
        }
        existing = grouped.get(key)
        if existing:
            for year, amount in year_amounts.items():
                if amount is None:
                    continue
                prev = existing["year_amounts"].get(year)
                existing["year_amounts"][year] = amount if prev is None else prev + amount
            continue
        grouped[key] = {
            "title": program,
            "kind": "program",
            "portfolio": portfolio or None,
            "agency_name": agency,
            "year": "2025-26",
            "year_amounts": {k: v for k, v in year_amounts.items() if v is not None},
            "source_document": row.get("Source_document") or row.get("Source document"),
            "source_table": row.get("Source_table") or row.get("Source table"),
            "source_url": PBS_CSV,
            "citation": "2025-26 PBS program expense line items (data.gov.au CSV)",
        }
    return list(grouped.values())


def parse_bp2_docx(data: bytes, *, year: str = "2026-27") -> list[dict]:
    paragraphs = docx_paragraphs(data)
    return parse_bp2_paragraphs(paragraphs, year=year, source_url=BP2_DOCX)


def docx_paragraphs(data: bytes) -> list[str]:
    with ZipFile(io.BytesIO(data)) as archive:
        xml = archive.read("word/document.xml")
    paragraphs: list[str] = []
    for block in re.findall(rb"<w:p[ >].*?</w:p>", xml, re.S):
        texts = re.findall(rb"<w:t[^>]*>([^<]*)</w:t>", block)
        line = "".join(part.decode("utf-8") for part in texts).strip()
        if line:
            paragraphs.append(line)
    return paragraphs


def parse_bp2_paragraphs(
    paragraphs: list[str],
    *,
    year: str = "2026-27",
    source_url: str = BP2_DOCX,
) -> list[dict]:
    portfolio: str | None = None
    agency: str | None = None
    records: list[dict] = []
    i = 0
    while i < len(paragraphs):
        line = paragraphs[i].strip()
        lowered = line.lower()
        if _YEAR_LINE.match(line) or line in {"$m", "Part 1: Receipt Measures", "Part 2: Payment Measures"}:
            i += 1
            continue
        if lowered.startswith("table ") or lowered.startswith("part "):
            i += 1
            continue
        if line.isupper() and len(line) > 4 and not line.startswith("$"):
            portfolio = line.title()
            agency = None
            i += 1
            continue
        if lowered in _SKIP_MEASURE or lowered.startswith("total impact"):
            i += 1
            # skip following amount tokens
            while i < len(paragraphs) and _is_amount_token(paragraphs[i]):
                i += 1
            continue
        if _looks_like_agency(line):
            agency = line
            i += 1
            continue
        if _looks_like_measure_title(line):
            title = re.sub(r"\([a-z]\)$", "", line).strip()
            amounts: list[float | None] = []
            j = i + 1
            while j < len(paragraphs) and _is_amount_token(paragraphs[j]) and len(amounts) < 5:
                amounts.append(parse_amount(paragraphs[j]))
                j += 1
            if len(amounts) >= 3:
                years = ["2025-26", "2026-27", "2027-28", "2028-29", "2029-30"]
                year_amounts = {
                    y: amt for y, amt in zip(years, amounts, strict=False) if amt is not None
                }
                records.append(
                    {
                        "title": title,
                        "kind": "measure",
                        "portfolio": portfolio,
                        "agency_name": agency,
                        "year": year,
                        "year_amounts": year_amounts,
                        "source_document": f"Budget Paper No. 2 {year}",
                        "source_table": "Receipt / payment measures",
                        "source_url": source_url,
                        "citation": f"{BP2_INDEX} — Budget Paper No. 2 measures DOCX",
                    }
                )
                i = j
                continue
        i += 1
    return records


def _is_amount_token(line: str) -> bool:
    return bool(_AMOUNT_TOKEN.match((line or "").strip()))


def _looks_like_agency(line: str) -> bool:
    if "–" in line or " - " in line:
        return False
    if line.startswith("Department of") or line == "Various Agencies":
        return True
    if _AGENCY_HINT.match(line):
        return True
    return bool(re.search(r"\b(Agency|Commission|Authority|Office|Corporation|Company)\b", line))


def _looks_like_measure_title(line: str) -> bool:
    if not line or _is_amount_token(line) or line.isupper():
        return False
    if line.lower() in _SKIP_MEASURE:
        return False
    if len(line) < 8 or line.startswith("20"):
        return False
    return any(ch.isalpha() for ch in line)


def instrument_from_budget_row(row: dict) -> InstrumentIn | None:
    title = (row.get("title") or row.get("Program") or "").strip()
    if not title:
        return None
    agency_name = row.get("agency_name") or row.get("agency")
    year = row.get("year") or "2025-26"
    kind = row.get("kind") or "measure"
    if kind not in {"measure", "program"}:
        kind = "program" if "program" in title.lower() else "measure"
    year_amounts = row.get("year_amounts") or {}
    amount = year_amounts.get(year) or year_amounts.get("2025-26") or year_amounts.get("2026-27")
    if amount is None:
        amount = parse_amount(row.get("amount_aud") or row.get("amount"))
    key = f"budget:{year}:{slug(title)[:50]}:{slug(agency_name or '')[:20]}"
    return InstrumentIn(
        source_key=key,
        title=title,
        kind=kind,  # type: ignore[arg-type]
        status="sourced",
        confidence=0.8 if kind == "measure" else 0.7,
        agency_name=agency_name,
        agency_slug=slug(agency_name)[:80] if agency_name else None,
        portfolio=row.get("portfolio"),
        announced_on=None,
        amount_aud=float(amount) if amount is not None else None,
        source="budget_measure",
        source_url=row.get("source_url") or BP2_INDEX,
        notes=row.get("citation") or row.get("notes"),
        identifiers={
            "year": year,
            "year_amounts": year_amounts,
            "source_document": row.get("source_document"),
            "source_table": row.get("source_table"),
            "citation": row.get("citation"),
            "amount_note": (
                "Amount as published in the cited table. PBS line items are often $'000; "
                "BP2 summary tables are $m. Do not treat this as a converted dollar figure."
            ),
            "license_note": LICENSE_NOTE,
        },
    )


def _counts(items: list[InstrumentIn], *, key) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in items:
        label = key(item)
        counts[label] = counts.get(label, 0) + 1
    return dict(sorted(counts.items(), key=lambda kv: (-kv[1], kv[0])))
