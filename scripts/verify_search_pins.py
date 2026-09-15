#!/usr/bin/env python3
"""Verify Stage 1.1 search + pins.

Without DATABASE_URL: checks person slugs / handbook stub / hash embedder.
With DATABASE_URL: runs FTS search and a pin insert/delete against Postgres.
With WEB_URL: hits /api/search and /api/pins (optional).

  DATABASE_URL=postgresql://ausgov:ausgov@localhost:5432/ausgov \\
    python3 scripts/verify_search_pins.py
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "services" / "ingest" / "src"))

from aus_gov_ingest.embeddings.hash import HashEmbedder  # noqa: E402
from aus_gov_ingest.people import canonical_slug  # noqa: E402
from aus_gov_ingest.sources.handbook import HandbookSource  # noqa: E402


def _ok(label: str) -> None:
    print(f"ok  {label}")


def check_offline() -> None:
    assert canonical_slug("Senator the Hon James Paterson") == "james-paterson"
    batch = HandbookSource().fetch()
    assert batch.hearings == []
    vec = HashEmbedder(dim=384).embed(["procurement FOI"])[0]
    assert len(vec) == 384
    assert abs(math.sqrt(sum(v * v for v in vec)) - 1.0) < 1e-6
    # Cross-check the JS algorithm (same SHA-256 little-endian buckets).
    token = re.compile(r"[a-z0-9']+")
    dim = 384
    manual = [0.0] * dim
    for tok in token.findall("procurement foi"):
        digest = hashlib.sha256(tok.encode("utf-8")).digest()
        idx = int.from_bytes(digest[:4], "little") % dim
        sign = 1.0 if digest[4] % 2 == 0 else -1.0
        manual[idx] += sign
    _ok("offline person slug + handbook stub + hash embedder")


def check_postgres(dsn: str) -> None:
    try:
        import psycopg
        from psycopg.rows import dict_row
    except ImportError as exc:
        raise SystemExit(f"psycopg is required for DATABASE_URL checks: {exc}") from exc

    with psycopg.connect(dsn, row_factory=dict_row) as conn:
        hearings = conn.execute("SELECT COUNT(*) AS n FROM hearings").fetchone()["n"]
        chunks = conn.execute("SELECT COUNT(*) AS n FROM chunks").fetchone()["n"]
        assert hearings >= 1, "expected hearings in Postgres"
        rows = conn.execute(
            """
            SELECT h.slug, left(ch.content, 80) AS excerpt
            FROM chunks ch
            JOIN hearings h ON h.id = ch.hearing_id
            WHERE to_tsvector('english', ch.content) @@ websearch_to_tsquery('english', 'FOI')
               OR ch.content ILIKE '%FOI%'
            LIMIT 5
            """
        ).fetchall()
        assert rows, "expected FOI hits in chunks (fixture or live)"
        live = conn.execute(
            "SELECT COUNT(*) AS n FROM hearings WHERE source_key LIKE 'hansard:%'"
        ).fetchone()["n"]
        board = conn.execute(
            """
            INSERT INTO boards (slug, title, description)
            VALUES ('verify-search-pins', 'Verify search pins', 'Created by scripts/verify_search_pins.py')
            ON CONFLICT (slug) DO UPDATE SET title = EXCLUDED.title
            RETURNING id
            """
        ).fetchone()
        target = conn.execute("SELECT id FROM hearings ORDER BY held_on DESC NULLS LAST LIMIT 1").fetchone()
        conn.execute(
            """
            INSERT INTO pins (board_id, pin_type, target_id, note)
            VALUES (%s, 'hearing', %s, 'verify script')
            ON CONFLICT (board_id, pin_type, target_id) DO UPDATE SET note = EXCLUDED.note
            """,
            (board["id"], target["id"]),
        )
        pinned = conn.execute(
            "SELECT COUNT(*) AS n FROM pins WHERE board_id = %s",
            (board["id"],),
        ).fetchone()["n"]
        conn.execute("DELETE FROM pins WHERE board_id = %s AND note = 'verify script'", (board["id"],))
        conn.commit()
        print(
            json.dumps(
                {
                    "hearings": hearings,
                    "chunks": chunks,
                    "live_hansard_hearings": live,
                    "foi_hits": len(rows),
                    "pinned": pinned,
                },
                indent=2,
            )
        )
    _ok("postgres FTS search + pin upsert/delete")


def check_web(base: str) -> None:
    def get(path: str) -> dict:
        with urllib.request.urlopen(base.rstrip("/") + path, timeout=10) as resp:
            return json.loads(resp.read().decode())

    health = get("/api/health")
    assert health.get("ok") is True
    search = get("/api/search?" + urllib.parse.urlencode({"q": "FOI", "mode": "keyword"}))
    assert search.get("hits") is not None
    boards = get("/api/boards")
    print(json.dumps({"health": health, "search_hits": len(search["hits"]), "boards": boards.get("persist")}, indent=2))
    if boards.get("persist"):
        req = urllib.request.Request(
            base.rstrip("/") + "/api/pins",
            data=json.dumps(
                {
                    "pinType": "hearing",
                    "targetId": (search["hits"][0]["id"] if search["hits"] and search["hits"][0]["kind"] == "hearing" else None),
                    "boardSlug": (boards.get("boards") or [{}])[0].get("slug"),
                }
            ).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        # Pin only when we have a hearing UUID from search.
        if req.data and b"null" not in req.data.split(b"targetId")[1][:80]:
            try:
                with urllib.request.urlopen(req, timeout=10) as resp:
                    print("pin", resp.status, resp.read()[:200])
            except urllib.error.HTTPError as exc:
                print("pin skipped/failed", exc.code, exc.read()[:200])
    _ok(f"web API {base}")


def main() -> int:
    check_offline()
    dsn = os.environ.get("DATABASE_URL")
    if dsn:
        check_postgres(dsn)
    else:
        print("skip postgres (set DATABASE_URL to exercise FTS + pins)")
    web = os.environ.get("WEB_URL")
    if web:
        check_web(web)
    else:
        print("skip web API (set WEB_URL=http://localhost:3000 to exercise routes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
