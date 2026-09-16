"""Attach Estimates QoNs to hearings from sourced evidence only.

A QoN may name a hearing when:

* fixture metadata already states ``hearing_source_key``, or
* portfolio + asked date + committee uniquely match one Estimates hearing.

Never invent a link. Ambiguous or weak matches are skipped and recorded.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

from aus_gov_ingest.models import QuestionOnNoticeIn

# Same sitting week is typical for Estimates; do not stretch further.
MAX_DATE_DELTA_DAYS = 3
MIN_ACCEPT_SCORE = 6

_COMMITTEE_NOISE = (
    "legislation committee",
    "references committee",
    "standing committee",
    "select committee",
    "joint committee",
    "committee",
    "senate",
    "the",
)

_PORTFOLIO_ALIASES = {
    "home affairs": {"home affairs", "immigration", "immigration and border protection"},
    "attorney-general's": {"attorney-general's", "attorney-general", "attorney generals", "ag"},
    "finance": {"finance", "public administration"},
    "parliamentary departments": {"parliamentary departments", "parliament"},
    "health, disability and ageing": {
        "health, disability and ageing",
        "health",
        "health and aged care",
        "disability",
        "ndis",
    },
    "education": {"education", "education and training", "education and employment"},
    "defence": {"defence", "veterans", "veterans' affairs"},
    "prime minister and cabinet": {"prime minister and cabinet", "pmc", "pm&c"},
}


@dataclass(frozen=True)
class HearingCandidate:
    source_key: str
    held_on: date | None
    title: str = ""
    portfolio: str | None = None
    committee_name: str | None = None
    hearing_type: str = "estimates"
    segment_portfolio: str | None = None
    hearing_id: str | None = None


@dataclass(frozen=True)
class HearingMatch:
    hearing_source_key: str
    hearing_id: str | None
    confidence: float
    score: int
    reason: str
    source: str


def normalize_committee(name: str | None) -> str:
    text = " ".join((name or "").lower().replace("&", " and ").split())
    for noise in _COMMITTEE_NOISE:
        text = text.replace(noise, " ")
    return " ".join(text.split())


def committees_match(left: str | None, right: str | None) -> bool:
    a, b = normalize_committee(left), normalize_committee(right)
    if not a or not b:
        return False
    return a == b or a in b or b in a


def _portfolio_keys(name: str | None) -> set[str]:
    raw = " ".join((name or "").lower().replace("&", " and ").split())
    if not raw:
        return set()
    keys = {raw}
    for canonical, aliases in _PORTFOLIO_ALIASES.items():
        if raw == canonical or raw in aliases or canonical in raw:
            keys.update(aliases)
            keys.add(canonical)
    return keys


def portfolios_match(left: str | None, right: str | None) -> bool:
    a, b = _portfolio_keys(left), _portfolio_keys(right)
    return bool(a and b and a & b)


def _date_score(asked_on: date | None, held_on: date | None) -> int:
    if not asked_on or not held_on:
        return 0
    delta = abs((asked_on - held_on).days)
    if delta == 0:
        return 4
    if delta == 1:
        return 3
    if delta <= MAX_DATE_DELTA_DAYS:
        return 2
    return 0


def match_qon_to_hearing(
    question: QuestionOnNoticeIn,
    hearings: list[HearingCandidate],
) -> HearingMatch | None:
    """Return a unique sourced match, or None.

    Fixture ``hearing_source_key`` wins when that hearing is in the candidate
    list. Otherwise require committee + date window, and portfolio when both
    sides name one.
    """
    explicit = (question.hearing_source_key or "").strip()
    if explicit:
        hit = next((h for h in hearings if h.source_key == explicit), None)
        if hit:
            return HearingMatch(
                hearing_source_key=hit.source_key,
                hearing_id=hit.hearing_id,
                confidence=0.99,
                score=12,
                reason="fixture_hearing_source_key",
                source="qon_fixture",
            )
        # Named but not in this candidate set — still record the key so persist
        # can look it up by source_key. Caller treats this as a hint.
        return HearingMatch(
            hearing_source_key=explicit,
            hearing_id=None,
            confidence=0.95,
            score=10,
            reason="fixture_hearing_source_key_unresolved",
            source="qon_fixture",
        )

    if not question.asked_on or not (question.committee_name or question.portfolio):
        return None

    scored: list[tuple[int, HearingCandidate, str]] = []
    for hearing in hearings:
        if hearing.hearing_type and hearing.hearing_type not in {"estimates", "committee"}:
            continue
        if hearing.hearing_type != "estimates" and "estimate" not in (hearing.title or "").lower():
            continue
        date_pts = _date_score(question.asked_on, hearing.held_on)
        if date_pts == 0:
            continue
        committee_ok = committees_match(question.committee_name, hearing.committee_name) or (
            question.committee_name and committees_match(question.committee_name, hearing.title)
        )
        hearing_portfolio = hearing.portfolio or hearing.segment_portfolio
        portfolio_ok = portfolios_match(question.portfolio, hearing_portfolio) or (
            question.portfolio and portfolios_match(question.portfolio, hearing.title)
        )
        if not committee_ok:
            continue
        # Portfolio is required when the QoN names one and the hearing names one.
        if question.portfolio and hearing_portfolio and not portfolio_ok:
            continue
        score = date_pts + (3 if committee_ok else 0) + (3 if portfolio_ok else 0)
        if score < MIN_ACCEPT_SCORE:
            continue
        bits = ["committee", f"date±{abs((question.asked_on - hearing.held_on).days) if hearing.held_on else '?'}"]
        if portfolio_ok:
            bits.append("portfolio")
        scored.append((score, hearing, "+".join(bits)))

    if not scored:
        return None
    scored.sort(key=lambda row: (-row[0], row[1].source_key))
    best_score, best, reason = scored[0]
    ties = [row for row in scored if row[0] == best_score]
    if len(ties) > 1:
        return None
    confidence = 0.9 if best_score >= 10 else 0.75 if best_score >= 8 else 0.65
    return HearingMatch(
        hearing_source_key=best.source_key,
        hearing_id=best.hearing_id,
        confidence=confidence,
        score=best_score,
        reason=reason,
        source="qon_hearing_match",
    )


def apply_hearing_match(question: QuestionOnNoticeIn, match: HearingMatch | None) -> QuestionOnNoticeIn:
    if not match:
        return question
    meta = {
        **(question.metadata or {}),
        "hearing_match": {
            "hearing_source_key": match.hearing_source_key,
            "confidence": match.confidence,
            "score": match.score,
            "reason": match.reason,
            "source": match.source,
        },
    }
    return question.model_copy(
        update={
            "hearing_source_key": match.hearing_source_key,
            "metadata": meta,
        }
    )


def sitting_window(asked_on: date, *, days: int = MAX_DATE_DELTA_DAYS) -> tuple[date, date]:
    delta = timedelta(days=days)
    return asked_on - delta, asked_on + delta
