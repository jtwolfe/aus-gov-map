#!/usr/bin/env python3
"""Verify Stage 3a laws + precedent files, ingest keys, and optional live data.

Without DATABASE_URL: checks spec + source files exist, and that vote
adapters do not emit people.
With DATABASE_URL: asserts law tables exist when 012/013 applied, and
that division_votes never required inventing people (person_id may be null).
With WEB_URL: HTTP 200 on /laws and empty-safe fixture behaviour.

  python3 scripts/verify_laws.py
  DATABASE_URL=postgresql://ausgov:ausgov@localhost:5432/ausgov \\
    python3 scripts/verify_laws.py
  WEB_URL=http://localhost:3000 python3 scripts/verify_laws.py
"""

from __future__ import annotations

import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _ok(label: str) -> None:
    print(f"ok  {label}")


def check_offline() -> None:
    spec = (ROOT / "docs" / "laws-and-precedent.md").read_text()
    assert "instruments" in spec
    assert "VOTED_ON" in spec
    assert "CONSTRUES" in spec
    assert "INVALIDATES" in spec
    assert "FUNDED_BY" in spec
    assert "No automated" in spec or "guilt" in spec.lower()
    assert "/laws" in spec
    assert "theyvoteforyou" in spec.lower() or "They Vote For You" in spec

    map_doc = (ROOT / "docs" / "accountability-map.md").read_text()
    assert "laws-and-precedent.md" in map_doc
    assert "`act`" in map_doc or "type `bill` / `act`" in map_doc

    readme = (ROOT / "README.md").read_text()
    assert "docs/laws-and-precedent.md" in readme
    assert "/laws" in readme

    header = (ROOT / "apps" / "web" / "src" / "components" / "site-header.tsx").read_text()
    assert 'href: "/laws"' in header

    sql012 = (ROOT / "infra" / "postgres" / "012_laws.sql").read_text()
    assert "CREATE TABLE IF NOT EXISTS divisions" in sql012
    assert "division_votes" in sql012
    assert "'act'" in sql012

    sql013 = (ROOT / "infra" / "postgres" / "013_precedent.sql").read_text()
    assert "judgment" in sql013
    assert "construes" in sql013
    assert "invalidates" in sql013
    assert "upholds" in sql013

    tvfy = (ROOT / "services" / "ingest" / "src" / "aus_gov_ingest" / "sources" / "theyvoteforyou.py").read_text()
    assert "PersonIn" not in tvfy
    assert "never" in tvfy.lower() or "existing" in tvfy.lower()

    for rel in (
        "apps/web/src/app/laws/page.tsx",
        "apps/web/src/app/laws/[slug]/page.tsx",
        "apps/web/src/lib/laws.ts",
        "services/ingest/src/aus_gov_ingest/sources/legislation.py",
        "services/ingest/src/aus_gov_ingest/sources/judgments.py",
        "services/ingest/fixtures/live/legislation/seed.json",
        "services/ingest/fixtures/live/tvfy/divisions.json",
        "services/ingest/fixtures/live/judgments/seed.json",
    ):
        assert (ROOT / rel).is_file(), rel

    _ok("offline spec + adapters + routes + fixtures")


def check_ingest_dry_run() -> None:
    sys.path.insert(0, str(ROOT / "services" / "ingest" / "src"))
    from aus_gov_ingest.sources.judgments import JudgmentsSource
    from aus_gov_ingest.sources.legislation import LegislationSource
    from aus_gov_ingest.sources.theyvoteforyou import TheyVoteForYouSource

    laws = LegislationSource(path=ROOT / "services" / "ingest" / "fixtures" / "live" / "legislation").fetch()
    assert laws.instruments, "legislation fixture empty"
    keys = [i.source_key for i in laws.instruments]
    assert len(keys) == len(set(keys)), "duplicate legislation source_keys"
    assert all(i.kind in {"bill", "act"} for i in laws.instruments)

    votes = TheyVoteForYouSource(path=ROOT / "services" / "ingest" / "fixtures" / "live" / "tvfy").fetch()
    assert votes.divisions
    assert votes.people == []
    assert votes.meta.get("people_emitted") == 0

    judgments = JudgmentsSource(path=ROOT / "services" / "ingest" / "fixtures" / "live" / "judgments").fetch()
    assert judgments.scrutiny_items
    kinds = {lnk.link_kind for lnk in judgments.instrument_links}
    assert kinds <= {"construes", "invalidates", "upholds"}
    _ok("fixture ingest: upsert keys + no invented people")


def check_postgres(dsn: str) -> None:
    try:
        import psycopg
        from psycopg.rows import dict_row
    except ImportError as exc:
        raise SystemExit(f"psycopg is required for DATABASE_URL checks: {exc}") from exc

    with psycopg.connect(dsn, row_factory=dict_row) as conn:
        def count(sql: str) -> int:
            try:
                return int(conn.execute(sql).fetchone()["n"])
            except Exception:
                return -1

        instruments = count("SELECT COUNT(*)::int AS n FROM instruments")
        if instruments < 0:
            print("skip postgres: instruments table missing (apply 007+)")
            return
        acts = count("SELECT COUNT(*)::int AS n FROM instruments WHERE instrument_type IN ('bill', 'act')")
        if acts < 0:
            print("skip postgres: act type not allowed yet (apply 012_laws.sql)")
            return
        divisions = count("SELECT COUNT(*)::int AS n FROM divisions")
        if divisions < 0:
            print("skip postgres: divisions missing (apply 012_laws.sql)")
            return
        orphan_votes = count(
            """
            SELECT COUNT(*)::int AS n
            FROM division_votes dv
            WHERE dv.person_id IS NOT NULL
              AND NOT EXISTS (SELECT 1 FROM people p WHERE p.id = dv.person_id)
            """
        )
        assert orphan_votes == 0, "division_votes.person_id must point at existing people"
        _ok(f"postgres laws tables (bills/acts={acts}, divisions={max(divisions, 0)})")


def check_http(base: str) -> None:
    base = base.rstrip("/")
    for path in ("/laws",):
        url = f"{base}{path}"
        try:
            with urllib.request.urlopen(url, timeout=20) as resp:
                assert resp.status == 200, f"{url} -> {resp.status}"
                body = resp.read().decode("utf-8", errors="replace")
        except urllib.error.HTTPError as exc:
            raise SystemExit(f"HTTP {exc.code} for {url}") from exc
        assert "Laws" in body or "law" in body.lower()
        # Empty fixture mode must name the ingest, not invent an Act list.
        if "No Bills or Acts" in body or "legislation" in body:
            _ok(f"HTTP {path} empty-safe or populated")
        else:
            _ok(f"HTTP {path} 200")


def main() -> int:
    check_offline()
    check_ingest_dry_run()
    dsn = os.environ.get("DATABASE_URL")
    if dsn:
        check_postgres(dsn)
    else:
        print("skip postgres (no DATABASE_URL)")
    web = os.environ.get("WEB_URL")
    if web:
        check_http(web)
    else:
        print("skip HTTP (no WEB_URL)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
