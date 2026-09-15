"""Person name normalisation and safer slug merge for ingest."""

from __future__ import annotations

import re

_SLUG = re.compile(r"[^a-z0-9]+")


def slug(text: str) -> str:
    return _SLUG.sub("-", (text or "").lower()).strip("-")


# Leading honorifics / forms of address commonly seen in Officials.
_HONORIFIC = re.compile(
    r"^(?:"
    r"senator(?:\s+the\s+hon(?:ourable)?)?|"
    r"the\s+hon(?:ourable)?|"
    r"hon(?:ourable)?|"
    r"prof(?:essor|\.)?|"
    r"dr\.?|"
    r"mr\.?|"
    r"ms\.?|"
    r"mrs\.?|"
    r"miss|"
    r"mx\.?"
    r")\s+",
    re.I,
)

# Chair/witness wrappers: "CHAIR (Senator Pratt)"
_WRAPPED = re.compile(
    r"^(?:chair|deputy\s+chair|acting\s+chair|witness)\s*\((.+)\)\s*$",
    re.I,
)

_POSTNOMINAL = re.compile(
    r"(?:,\s*|\s+)(?:PSM|AC|AO|AM|CSC|OAM|MBE|AO\s+CSC|MP|QC|SC|KC)\b\.?",
    re.I,
)

# Agency / APS titles that are roles, not names.
_ROLE_HINT = re.compile(
    r"\b("
    r"secretary|deputy secretary|acting deputy secretary|"
    r"first assistant secretary|assistant secretary|"
    r"chief(?:\s+\w+)?|commissioner|auditor(?:-general)?|"
    r"president of the senate|clerk|parliamentary counsel"
    r")\b",
    re.I,
)

_SKIP_NAMES = {
    "chair",
    "deputy chair",
    "acting chair",
    "witness",
    "committee",
    "in attendance",
}


def tidy(text: str) -> str:
    return " ".join((text or "").split()).strip(" ,;")


def unwrap_official_label(raw: str) -> str:
    text = tidy(raw)
    match = _WRAPPED.match(text)
    if match:
        return tidy(match.group(1))
    return text


def split_name_and_role(raw: str) -> tuple[str, str | None]:
    """Split 'Ms Jaala Hinchcliffe, Secretary' → (name, role)."""
    text = unwrap_official_label(raw)
    if "," not in text:
        return text, None
    name, rest = text.split(",", 1)
    role = tidy(rest) or None
    return tidy(name), role


def strip_honorifics(name: str) -> str:
    text = unwrap_official_label(name)
    if "," in text:
        text = text.split(",", 1)[0]
    text = tidy(text)
    text = _POSTNOMINAL.sub("", text)
    for _ in range(3):
        nxt = _HONORIFIC.sub("", text)
        if nxt == text:
            break
        text = tidy(nxt)
    return tidy(text)


def core_tokens(name: str) -> list[str]:
    return [t for t in re.split(r"[^a-z0-9']+", strip_honorifics(name).lower()) if t]


def canonical_slug(name: str) -> str:
    core = strip_honorifics(name)
    return (slug(core) or slug(name) or "person")[:80]


def should_skip_person(name: str) -> bool:
    core = strip_honorifics(name).lower()
    return not core or core in _SKIP_NAMES


def infer_role(title: str | None, role_title: str | None) -> str:
    lowered = f"{title or ''} {role_title or ''}".lower()
    if "chair" in lowered:
        return "chair"
    if "minister" in lowered:
        return "minister"
    if "senator" in lowered or (title or "").lower().startswith("senator"):
        return "senator"
    if _ROLE_HINT.search(role_title or "") or _ROLE_HINT.search(title or ""):
        return "official"
    if "witness" in lowered:
        return "witness"
    return "official" if title else "appeared"


def names_are_same_person(a: str, b: str) -> bool:
    """True when two labels clearly refer to the same person.

    Safer than slug-equality alone: last names must match, and one token
    set must be a subset of the other. Multiple-token disagreements refuse.
    """
    left = core_tokens(a)
    right = core_tokens(b)
    if not left or not right:
        return False
    if left[-1] != right[-1]:
        return False
    if left == right:
        return True
    shorter, longer = (left, right) if len(left) <= len(right) else (right, left)
    return set(shorter) <= set(longer)


def pick_display_name(existing: str, incoming: str) -> str:
    """Prefer the longer, more specific official-style label."""
    if names_are_same_person(existing, incoming):
        if len(tidy(incoming)) > len(tidy(existing)):
            return tidy(incoming)
        return tidy(existing)
    return tidy(existing) or tidy(incoming)
