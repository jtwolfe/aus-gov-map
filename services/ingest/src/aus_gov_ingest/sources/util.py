from __future__ import annotations

import re
from datetime import datetime
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
