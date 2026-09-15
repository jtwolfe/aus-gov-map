"""Senate Estimates Questions on Notice (EQON) ingest.

Live: POST /api/qon/getestimatesdata on www.aph.gov.au (browser-like UA).
Fallback: committed JSON under fixtures/live/qon/.

OpenAustralia does not publish Estimates QoN. ParlInfo remains WAF-gated.
Bulk ZIP downloads require My Parliament sign-in — we use the public search API
and single-question JSON instead.
"""

from __future__ import annotations

import json
from pathlib import Path

from aus_gov_ingest.http import AphClient
from aus_gov_ingest.models import QuestionOnNoticeIn, SourceBatch
from aus_gov_ingest.sources.util import parse_flexible_date, slug

EQON_HOME = "https://www.aph.gov.au/Parliamentary_Business/Senate_Estimates/eqon"
EQON_SEARCH = "https://www.aph.gov.au/api/qon/getestimatesdata"
EQON_QUESTION = "https://www.aph.gov.au/api/qon/getestimatesquestion"
EQON_DOWNLOAD = "https://www.aph.gov.au/api/qon/downloadestimatesquestions/EstimatesQuestion"

ENDPOINTS = {
    "estimates_hub": "https://www.aph.gov.au/Parliamentary_Business/Senate_estimates",
    "eqon": EQON_HOME,
    "eqon_search": EQON_SEARCH,
    "eqon_question": EQON_QUESTION,
    "parlinfo": "https://parlinfo.aph.gov.au/",
    "house_questions": "https://www.aph.gov.au/Parliamentary_Business/Chamber_documents/HoR/Questions_and_Answers",
}

LICENSE_NOTE = (
    "© Commonwealth of Australia. Senate Estimates Questions on Notice. "
    "Typically CC BY-NC-ND — attribute the Parliament of Australia."
)

_QON_COLUMNS = [
    "Number",
    "Senators",
    "Committee",
    "EstimatesRoundName",
    "Portfolio",
    "BroadTopic",
    "Agency",
    "Status",
    "AskedDate",
    "Overdue",
    "IsMultiPortfolioQuestion",
    "IsTransferred",
    "ProofHansardPage",
    "PortfolioQuestionNumber",
    "QuestionText",
    "AnswerText",
    "",
]


def default_qon_dir() -> Path:
    here = Path(__file__).resolve()
    for parent in here.parents:
        candidate = parent / "fixtures" / "live" / "qon"
        if candidate.is_dir():
            return candidate
    return here.parents[3] / "fixtures" / "live" / "qon"


class QonSource:
    name = "qon"
    HOME = EQON_HOME
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
        transport = "eqon_api"
        rows: list[dict] = []

        if self.path:
            rows, transport = self._from_path(self.path)
        else:
            try:
                rows = self._fetch_live(limit=limit or 20)
            except Exception as exc:
                errors.append(f"eqon_api: {exc}")
                try:
                    rows, transport = self._from_path(default_qon_dir())
                    transport = f"fixture_fallback:{transport}"
                except Exception as fallback_exc:
                    errors.append(f"fixture: {fallback_exc}")

        known = incremental_keys or set()
        questions: list[QuestionOnNoticeIn] = []
        for row in rows:
            item = question_from_eqon(row)
            if not item or item.source_key in known:
                continue
            questions.append(item)
            if limit and len(questions) >= limit:
                break

        return SourceBatch(
            source=self.name,
            questions=questions,
            meta={
                "status": "ok" if questions else "empty",
                "home": self.HOME,
                "transport": transport,
                "license_note": LICENSE_NOTE,
                "research": {
                    "aph_eqon": EQON_HOME,
                    "aph_search_api": EQON_SEARCH,
                    "openaustralia": "no Estimates QoN feed",
                    "bulk_zip": "My Parliament sign-in required",
                },
                "limit": limit,
                "skipped_existing": len(known),
                "errors": errors,
                "by_portfolio": counts_by_portfolio(questions),
                "by_status": counts_by_status(questions),
                "endpoints": ENDPOINTS,
                "schema": "infra/postgres/007_accountability.sql (qons)",
                "note": (
                    "Senate Estimates EQON search into foundation qons. "
                    "No invented answers; fixture fallback if the live API is blocked."
                ),
            },
        )

    def _fetch_live(self, *, limit: int) -> list[dict]:
        page = max(limit, 1)
        data = _search_form(start=0, length=page)
        payload = self.client.post_form(
            EQON_SEARCH,
            data,
            referer=EQON_HOME,
        )
        inner = payload
        if isinstance(payload.get("Message"), str):
            inner = json.loads(payload["Message"])
        rows = inner.get("data") or []
        # Hydrate empty search rows from the per-question JSON when IDs exist.
        hydrated: list[dict] = []
        for row in rows:
            if row.get("QuestionText") or not row.get("CommitteeId"):
                hydrated.append(row)
                continue
            try:
                detail = self.client.get_json(
                    (
                        f"{EQON_QUESTION}?committeeid={row.get('CommitteeId')}"
                        f"&estimatesroundid={row.get('EstimatesRoundId')}"
                        f"&portfolioid={row.get('PortfolioId')}"
                        f"&number={row.get('Number')}"
                    ),
                    referer=EQON_HOME,
                )
                if isinstance(detail, dict) and detail.get("Id"):
                    hydrated.append({**row, **detail})
                else:
                    hydrated.append(row)
            except Exception:
                hydrated.append(row)
        return hydrated

    def _from_path(self, path: Path) -> tuple[list[dict], str]:
        if not path.exists():
            raise FileNotFoundError(f"QoN path not found: {path}")
        files = [path] if path.is_file() else sorted(p for p in path.glob("*.json") if p.is_file())
        if not files:
            raise FileNotFoundError(f"No QoN JSON in {path}")
        rows: list[dict] = []
        for file in files:
            payload = json.loads(file.read_text(encoding="utf-8"))
            if isinstance(payload, list):
                rows.extend(r for r in payload if isinstance(r, dict))
            elif isinstance(payload, dict) and isinstance(payload.get("data"), list):
                rows.extend(r for r in payload["data"] if isinstance(r, dict))
            elif isinstance(payload, dict) and (
                payload.get("PortfolioQuestionNumber") or payload.get("Number") or payload.get("Id")
            ):
                rows.append(payload)
        return rows, f"qon_file:{path}"


def _search_form(*, start: int, length: int) -> dict[str, str]:
    data = {
        "draw": "1",
        "order[0][column]": "0",
        "order[0][dir]": "desc",
        "start": str(start),
        "length": str(length),
        "search[value]": "",
        "search[regex]": "false",
        "questionTextId": "",
        "fieldKeywords": "",
        "fieldCommittee": "x",
        "fieldEstimatesRound": "x",
        "fieldSenator": "x",
        "fieldPortfolio": "x",
        "fieldAgency": "x",
        "fieldQuestionNumber": "",
        "fieldPortfolioQuestionNumber": "",
        "fieldDateFrom": "",
        "fieldDateTo": "",
        "fieldStatus": "0",
    }
    for i, col in enumerate(_QON_COLUMNS):
        data[f"columns[{i}][data]"] = col
        data[f"columns[{i}][name]"] = ""
        data[f"columns[{i}][searchable]"] = "true"
        data[f"columns[{i}][orderable]"] = "true" if i <= 9 else "false"
        data[f"columns[{i}][search][value]"] = ""
        data[f"columns[{i}][search][regex]"] = "false"
    return data


def question_from_eqon(row: dict) -> QuestionOnNoticeIn | None:
    number = row.get("Number")
    pq = row.get("PortfolioQuestionNumber") or ""
    qid = row.get("Id")
    if not any((number, pq, qid)):
        return None
    committee_id = row.get("CommitteeId")
    round_id = row.get("EstimatesRoundId")
    portfolio_id = row.get("PortfolioId")
    source_key = f"qon:eqon:{qid or pq or number}"
    source_url = None
    if committee_id and round_id and portfolio_id and number is not None:
        source_url = (
            f"{EQON_QUESTION}?committeeid={committee_id}"
            f"&estimatesroundid={round_id}&portfolioid={portfolio_id}&number={number}"
        )
    asked_by = _senator_label(row.get("Senators"))
    agency_name = (row.get("Agency") or None) or None
    question_text = _html_to_text(row.get("QuestionText") or row.get("BroadTopic") or "")
    answer_text = _html_to_text(row.get("AnswerText") or "")
    return QuestionOnNoticeIn(
        source_key=source_key,
        qon_number=str(number) if number is not None else None,
        portfolio_question_number=pq or None,
        portfolio=row.get("Portfolio") or None,
        agency_slug=slug(agency_name)[:80] if agency_name else None,
        agency_name=agency_name,
        asked_by=asked_by,
        asked_on=parse_flexible_date(row.get("AskedDate")),
        due_on=parse_flexible_date(row.get("DueDate")),
        answered_on=parse_flexible_date(row.get("AnsweredDate")),
        status=map_qon_status(row),
        question_text=question_text or None,
        answer_text=answer_text or None,
        source_url=source_url or row.get("_source_url"),
        committee_name=row.get("Committee") or None,
        estimates_round=row.get("EstimatesRoundName") or None,
        metadata={
            "eqon_id": qid,
            "overdue": row.get("Overdue"),
            "aph_status": row.get("Status"),
            "broad_topic": row.get("BroadTopic"),
            "download_url": row.get("_download_url"),
            "license_note": LICENSE_NOTE,
        },
    )


def map_qon_status(row: dict) -> str:
    status = str(row.get("Status") or "").strip().lower()
    overdue = str(row.get("Overdue") or "").strip().lower()
    if overdue in {"yes", "true", "1"} and status not in {"answered", "withdrawn"}:
        return "overdue"
    if status == "overdue":
        return "overdue"
    if status == "answered" or row.get("Answered") is True:
        return "answered"
    if status in {"unanswered", "open", "pending"}:
        return "open"
    if status in {"withdrawn", ""}:
        return "unknown"
    return "unknown"


def counts_by_portfolio(questions: list[QuestionOnNoticeIn]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in questions:
        key = item.portfolio or "(unspecified)"
        counts[key] = counts.get(key, 0) + 1
    return dict(sorted(counts.items(), key=lambda kv: (-kv[1], kv[0])))


def counts_by_status(questions: list[QuestionOnNoticeIn]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in questions:
        counts[item.status] = counts.get(item.status, 0) + 1
    return counts


def _senator_label(senators) -> str | None:
    if not senators:
        return None
    names = []
    for row in senators:
        if not isinstance(row, dict):
            continue
        title = (row.get("Title") or "Senator").strip()
        first = (row.get("FirstName") or "").strip()
        last = (row.get("Surname") or "").strip()
        label = " ".join(p for p in (title, first, last) if p)
        if label:
            names.append(label)
    return "; ".join(names) or None


def _html_to_text(value: str) -> str:
    if not value:
        return ""
    if "<" not in value:
        return " ".join(value.split())
    from aus_gov_ingest.sources.hansard import html_to_text

    return html_to_text(value)
