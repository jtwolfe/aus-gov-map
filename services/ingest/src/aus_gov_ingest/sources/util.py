from __future__ import annotations

import re
from datetime import date, datetime, timezone
from html import unescape

_DATE_LONG = re.compile(
    r"(?P<d>\d{1,2})\s+(?P<mon>January|February|March|April|May|June|July|"
    r"August|September|October|November|December)\s+(?P<y>\d{4})",
    re.I,
)
_DATE_SHORT = re.compile(
    r"(?P<d>\d{1,2})\s+(?P<mon>Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+(?P<y>\d{4})",
    re.I,
)
_DATE_DMY = re.compile(r"(?P<d>\d{1,2})/(?P<m>\d{1,2})/(?P<y>\d{4})")
_SLUG = re.compile(r"[^a-z0-9]+")


def slug(text: str) -> str:
    return _SLUG.sub("-", (text or "").lower()).strip("-")


def parse_date(text: str):
    raw = unescape(text or "")
    match = _DATE_LONG.search(raw)
    if match:
        try:
            return datetime.strptime(
                f"{match.group('d')} {match.group('mon')} {match.group('y')}", "%d %B %Y"
            ).date()
        except ValueError:
            pass
    match = _DATE_SHORT.search(raw)
    if match:
        try:
            return datetime.strptime(
                f"{match.group('d')} {match.group('mon')} {match.group('y')}", "%d %b %Y"
            ).date()
        except ValueError:
            pass
    match = _DATE_DMY.search(raw)
    if match:
        try:
            return datetime(
                int(match.group("y")), int(match.group("m")), int(match.group("d"))
            ).date()
        except ValueError:
            pass
    return None


_MS_DATE = re.compile(r"/Date\((?P<ms>-?\d+)\)/")
_SENTINEL_DATES = {date(1900, 1, 1), date(1, 1, 1)}


def parse_flexible_date(value, *, open_if_today: bool = False) -> date | None:
    """Parse Handbook / EQON dates (ISO, DMY, or .NET `/Date(ms)/`)."""
    if value in (None, "", 0):
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        parsed = value
    elif isinstance(value, datetime):
        parsed = value.date()
    else:
        raw = str(value).strip()
        match = _MS_DATE.search(raw)
        if match:
            parsed = datetime.fromtimestamp(int(match.group(1)) / 1000, tz=timezone.utc).date()
        elif "T" in raw:
            try:
                parsed = datetime.fromisoformat(raw.replace("Z", "+00:00")).date()
            except ValueError:
                parsed = parse_date(raw)
        else:
            parsed = parse_date(raw)
    if parsed is None or parsed in _SENTINEL_DATES:
        return None
    if open_if_today and parsed >= date.today():
        # Handbook often stamps "still serving" as today's date.
        return None
    return parsed
