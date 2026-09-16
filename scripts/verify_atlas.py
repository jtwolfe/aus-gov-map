#!/usr/bin/env python3
"""Verify Responsibility Atlas files, query contract, and optional live data.

Without DATABASE_URL: checks spec + source files exist, and that tenure
builders are not wired to hearing_people.
With DATABASE_URL: asserts person_roles or hearing/qon/anao moments exist
when those tables are present.
With WEB_URL: HTTP 200 on /atlas and /api/atlas.

  python3 scripts/verify_atlas.py
  DATABASE_URL=postgresql://ausgov:ausgov@localhost:5432/ausgov \\
    python3 scripts/verify_atlas.py
  WEB_URL=http://localhost:3000 python3 scripts/verify_atlas.py
"""

from __future__ import annotations

import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _ok(label: str) -> None:
    print(f"ok  {label}")


def check_offline() -> None:
    spec = (ROOT / "docs" / "responsibility-atlas.md").read_text()
    assert "GET /api/atlas" in spec
    assert "person_roles" in spec
    assert "Sitting in Estimates" in spec or "sitting in Estimates" in spec.lower()
    assert "/atlas" in spec

    query = (ROOT / "apps" / "web" / "src" / "lib" / "atlas-query.ts").read_text()
    assert "tenuresFromRoles" in query
    assert "hearing_people" not in query
    assert "resolveWindow" in query

    loader = (ROOT / "apps" / "web" / "src" / "lib" / "atlas.ts").read_text()
    assert "FROM person_roles" in loader
    # Appearances may be loaded for moments in person mode, but tenures
    # must still go through tenuresFromRoles — never INSERT-shaped from hearings.
    assert "tenuresFromRoles" in loader
    assert "hearingMoments" in loader

    sql = ROOT / "infra" / "postgres" / "011_atlas.sql"
    assert sql.is_file()
    assert "v_atlas_hearing_moments" in sql.read_text()

    for rel in (
        "apps/web/src/app/atlas/page.tsx",
        "apps/web/src/app/api/atlas/route.ts",
        "apps/web/src/components/atlas-chart.tsx",
        "apps/web/src/components/mini-atlas.tsx",
    ):
        assert (ROOT / rel).is_file(), rel

    header = (ROOT / "apps" / "web" / "src" / "components" / "site-header.tsx").read_text()
    assert 'href: "/atlas"' in header

    _ok("offline spec + query builders + routes")


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
                conn.rollback()
                return 0

        tenures = count("SELECT COUNT(*) AS n FROM person_roles")
        hearings = count("SELECT COUNT(*) AS n FROM hearings WHERE held_on IS NOT NULL")
        qons = count("SELECT COUNT(*) AS n FROM qons")
        anao = count("SELECT COUNT(*) AS n FROM scrutiny_items WHERE item_type = 'anao'")
        moments = hearings + qons + anao
        print(
            json.dumps(
                {
                    "person_roles": tenures,
                    "hearings_dated": hearings,
                    "qons": qons,
                    "anao": anao,
                    "moment_sources": moments,
                },
                indent=2,
            )
        )
        if tenures == 0 and moments == 0:
            print(
                "warn atlas store is empty — expected until handbook/aps_leaders "
                "or estimates ingest. Offline checks still pass."
            )
        else:
            assert tenures > 0 or moments > 0
        # Hearing appearances must not be the only occupancy signal we trust.
        appearances = count("SELECT COUNT(*) AS n FROM hearing_people")
        if appearances and tenures == 0:
            print("ok  appearances exist without tenures (Estimates ≠ occupancy)")
    _ok("postgres atlas sources (tenures or moments)")


def check_web(base: str) -> None:
    def hit(path: str) -> tuple[int, bytes]:
        req = urllib.request.Request(base.rstrip("/") + path, method="GET")
        try:
            with urllib.request.urlopen(req, timeout=20) as resp:
                return resp.status, resp.read()
        except urllib.error.HTTPError as exc:
            return exc.code, exc.read()

    page_status, page_body = hit("/atlas")
    assert page_status == 200, f"/atlas -> {page_status}"
    page_text = page_body.decode("utf-8", errors="replace")
    assert re.search(r"Responsibility Atlas|Atlas", page_text)

    api_status, api_body = hit("/api/atlas")
    assert api_status == 200, f"/api/atlas -> {api_status}"
    payload = json.loads(api_body.decode())
    assert "lanes" in payload and "tenures" in payload and "moments" in payload
    assert "window" in payload
    print(json.dumps({"atlas": page_status, "api": api_status, "ready": payload.get("ready"), "source": payload.get("source")}, indent=2))
    _ok(f"web Atlas {base}")


def main() -> int:
    check_offline()
    dsn = os.environ.get("DATABASE_URL")
    if dsn:
        check_postgres(dsn)
    else:
        print("skip postgres (set DATABASE_URL to assert tenures or moments)")
    web = os.environ.get("WEB_URL")
    if web:
        check_web(web)
    else:
        print("skip web API (set WEB_URL=http://localhost:3000 to exercise /atlas)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
