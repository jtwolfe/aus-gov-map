from __future__ import annotations

from contextlib import contextmanager
from typing import Any, Iterator
from uuid import UUID, uuid4, uuid5, NAMESPACE_URL

from psycopg import Connection
from psycopg.rows import dict_row
from psycopg.types.json import Json

from aus_gov_ingest.chunking import Chunk
from aus_gov_ingest.config import settings
from aus_gov_ingest.models import (
    AppearanceIn,
    BoardIn,
    CommitteeIn,
    DocumentIn,
    HearingIn,
    PersonIn,
    PinIn,
    TopicIn,
)
from aus_gov_ingest.people import canonical_slug, names_are_same_person, pick_display_name


def _uuid(*parts: str) -> UUID:
    return uuid5(NAMESPACE_URL, "aus-gov-map:" + "|".join(parts))


def _split_sql(sql_text: str) -> list[str]:
    statements: list[str] = []
    buf: list[str] = []
    for raw_line in sql_text.splitlines():
        stripped = raw_line.strip()
        if stripped.startswith("\\"):
            continue
        buf.append(raw_line)
        if stripped.endswith(";"):
            stmt = "\n".join(buf).strip()
            if stmt:
                statements.append(stmt)
            buf = []
    tail = "\n".join(buf).strip()
    if tail:
        statements.append(tail)
    return statements


class PostgresStore:
    def __init__(self, dsn: str | None = None) -> None:
        self.dsn = dsn or settings.database_url
        if not self.dsn:
            raise RuntimeError("DATABASE_URL is not set")

    @contextmanager
    def connect(self) -> Iterator[Connection]:
        from psycopg import connect

        with connect(self.dsn, row_factory=dict_row) as conn:
            yield conn

    def existing_source_keys(self, source: str | None = None) -> set[str]:
        sql = "SELECT source_key FROM hearings"
        params: tuple[Any, ...] = ()
        if source:
            sql += " WHERE source = %s"
            params = (source,)
        with self.connect() as conn:
            rows = conn.execute(sql, params).fetchall()
        return {row["source_key"] for row in rows}

    def start_run(self, source: str, meta: dict | None = None) -> UUID:
        run_id = uuid4()
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO ingest_runs (id, source, status, meta)
                VALUES (%s, %s, 'running', %s)
                """,
                (run_id, source, Json(meta or {})),
            )
            conn.commit()
        return run_id

    def finish_run(
        self,
        run_id: UUID,
        *,
        status: str,
        fetched: int,
        upserted: int,
        error: str | None = None,
    ) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                UPDATE ingest_runs
                SET finished_at = now(), status = %s,
                    records_fetched = %s, records_upserted = %s, error = %s
                WHERE id = %s
                """,
                (status, fetched, upserted, error, run_id),
            )
            conn.commit()

    def upsert_committee(self, conn: Connection, item: CommitteeIn) -> UUID:
        cid = item.id or _uuid("committee", item.slug)
        conn.execute(
            """
            INSERT INTO committees (id, slug, name, chamber, kind, aph_url)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (slug) DO UPDATE SET
                name = EXCLUDED.name,
                chamber = EXCLUDED.chamber,
                kind = EXCLUDED.kind,
                aph_url = COALESCE(EXCLUDED.aph_url, committees.aph_url)
            """,
            (cid, item.slug, item.name, item.chamber, item.kind, item.aph_url),
        )
        row = conn.execute("SELECT id FROM committees WHERE slug = %s", (item.slug,)).fetchone()
        return row["id"] if row else cid

    def find_person_merge(self, conn: Connection, item: PersonIn) -> dict | None:
        wanted = canonical_slug(item.name) or item.slug
        row = conn.execute(
            "SELECT id, slug, name FROM people WHERE slug = %s OR slug = %s",
            (item.slug, wanted),
        ).fetchone()
        if row:
            return row
        tokens = [t for t in wanted.split("-") if t]
        if not tokens:
            return None
        last = tokens[-1]
        candidates = conn.execute(
            """
            SELECT id, slug, name FROM people
            WHERE slug LIKE %s OR name ILIKE %s
            """,
            (f"%{last}%", f"%{last}%"),
        ).fetchall()
        matches = [
            c
            for c in candidates
            if names_are_same_person(c["name"], item.name)
            or names_are_same_person(c["slug"].replace("-", " "), item.name)
        ]
        if len(matches) == 1:
            return matches[0]
        return None

    def upsert_person(self, conn: Connection, item: PersonIn) -> UUID:
        merge = self.find_person_merge(conn, item)
        if merge:
            display = pick_display_name(merge["name"], item.name)
            conn.execute(
                """
                UPDATE people SET
                    name = %s,
                    role_title = COALESCE(%s, role_title),
                    party = COALESCE(%s, party),
                    portfolio = COALESCE(%s, portfolio),
                    organisation = COALESCE(%s, organisation),
                    aph_url = COALESCE(%s, aph_url),
                    bio = COALESCE(%s, bio)
                WHERE id = %s
                """,
                (
                    display,
                    item.role_title,
                    item.party,
                    item.portfolio,
                    item.organisation,
                    item.aph_url,
                    item.bio,
                    merge["id"],
                ),
            )
            return merge["id"]

        slug = canonical_slug(item.name) or item.slug
        pid = item.id or _uuid("person", slug)
        conn.execute(
            """
            INSERT INTO people (id, slug, name, role_title, party, portfolio, organisation, aph_url, bio)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (slug) DO UPDATE SET
                name = EXCLUDED.name,
                role_title = COALESCE(EXCLUDED.role_title, people.role_title),
                party = COALESCE(EXCLUDED.party, people.party),
                portfolio = COALESCE(EXCLUDED.portfolio, people.portfolio),
                organisation = COALESCE(EXCLUDED.organisation, people.organisation),
                aph_url = COALESCE(EXCLUDED.aph_url, people.aph_url),
                bio = COALESCE(EXCLUDED.bio, people.bio)
            """,
            (
                pid,
                slug,
                item.name,
                item.role_title,
                item.party,
                item.portfolio,
                item.organisation,
                item.aph_url,
                item.bio,
            ),
        )
        row = conn.execute("SELECT id FROM people WHERE slug = %s", (slug,)).fetchone()
        return row["id"] if row else pid

    def apply_sql(self, sql_text: str) -> int:
        """Run a SQL file that may contain multiple statements (no psql meta)."""
        statements = _split_sql(sql_text)
        ran = 0
        with self.connect() as conn:
            for stmt in statements:
                conn.execute(stmt)
                ran += 1
            conn.commit()
        return ran

    def merge_duplicate_people(self) -> dict[str, int]:
        """Collapse people that share a canonical core name."""
        moved = 0
        deleted = 0
        with self.connect() as conn:
            rows = conn.execute("SELECT id, slug, name FROM people ORDER BY created_at, name").fetchall()
            groups: dict[str, list[dict]] = {}
            for row in rows:
                key = canonical_slug(row["name"]) or row["slug"]
                groups.setdefault(key, []).append(row)
            for members in groups.values():
                if len(members) < 2:
                    continue
                survivor = members[0]
                for extra in members[1:]:
                    if not names_are_same_person(survivor["name"], extra["name"]):
                        continue
                    conn.execute(
                        """
                        INSERT INTO hearing_people (hearing_id, person_id, role)
                        SELECT hearing_id, %s, role FROM hearing_people WHERE person_id = %s
                        ON CONFLICT DO NOTHING
                        """,
                        (survivor["id"], extra["id"]),
                    )
                    moved += conn.execute(
                        "SELECT COUNT(*) AS n FROM hearing_people WHERE person_id = %s",
                        (extra["id"],),
                    ).fetchone()["n"]
                    conn.execute("DELETE FROM hearing_people WHERE person_id = %s", (extra["id"],))
                    conn.execute("DELETE FROM people WHERE id = %s", (extra["id"],))
                    deleted += 1
            conn.commit()
        return {"merged_away": deleted, "appearance_rows_seen": moved}

    def upsert_topic(self, conn: Connection, item: TopicIn) -> UUID:
        tid = item.id or _uuid("topic", item.slug)
        conn.execute(
            """
            INSERT INTO topics (id, slug, name)
            VALUES (%s, %s, %s)
            ON CONFLICT (slug) DO UPDATE SET name = EXCLUDED.name
            """,
            (tid, item.slug, item.name),
        )
        row = conn.execute("SELECT id FROM topics WHERE slug = %s", (item.slug,)).fetchone()
        return row["id"] if row else tid

    def upsert_hearing(self, conn: Connection, item: HearingIn, committee_id: UUID | None) -> UUID:
        hid = item.id or _uuid("hearing", item.source_key)
        conn.execute(
            """
            INSERT INTO hearings (
                id, slug, committee_id, title, hearing_type, portfolio, held_on,
                location, source, source_url, source_key, status, summary, updated_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, now())
            ON CONFLICT (source_key) DO UPDATE SET
                title = EXCLUDED.title,
                committee_id = COALESCE(EXCLUDED.committee_id, hearings.committee_id),
                hearing_type = EXCLUDED.hearing_type,
                portfolio = COALESCE(EXCLUDED.portfolio, hearings.portfolio),
                held_on = COALESCE(EXCLUDED.held_on, hearings.held_on),
                location = COALESCE(EXCLUDED.location, hearings.location),
                source_url = COALESCE(EXCLUDED.source_url, hearings.source_url),
                status = EXCLUDED.status,
                summary = COALESCE(EXCLUDED.summary, hearings.summary),
                updated_at = now()
            """,
            (
                hid,
                item.slug,
                committee_id,
                item.title,
                item.hearing_type,
                item.portfolio,
                item.held_on,
                item.location,
                item.source,
                item.source_url,
                item.source_key,
                item.status,
                item.summary,
            ),
        )
        row = conn.execute(
            "SELECT id FROM hearings WHERE source_key = %s", (item.source_key,)
        ).fetchone()
        return row["id"] if row else hid

    def upsert_appearance(
        self, conn: Connection, hearing_id: UUID, person_id: UUID, role: str
    ) -> None:
        conn.execute(
            """
            INSERT INTO hearing_people (hearing_id, person_id, role)
            VALUES (%s, %s, %s)
            ON CONFLICT DO NOTHING
            """,
            (hearing_id, person_id, role),
        )

    def upsert_document(self, conn: Connection, hearing_id: UUID, item: DocumentIn) -> UUID:
        did = item.id or _uuid("document", item.source_key)
        conn.execute(
            """
            INSERT INTO documents (
                id, hearing_id, title, doc_type, source_url, source_key,
                content_text, published_at, license_note
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (source_key) DO UPDATE SET
                title = EXCLUDED.title,
                content_text = COALESCE(EXCLUDED.content_text, documents.content_text),
                source_url = COALESCE(EXCLUDED.source_url, documents.source_url),
                published_at = COALESCE(EXCLUDED.published_at, documents.published_at)
            """,
            (
                did,
                hearing_id,
                item.title,
                item.doc_type,
                item.source_url,
                item.source_key,
                item.content_text,
                item.published_at,
                item.license_note,
            ),
        )
        row = conn.execute(
            "SELECT id FROM documents WHERE source_key = %s", (item.source_key,)
        ).fetchone()
        return row["id"] if row else did

    def upsert_chunk(
        self,
        conn: Connection,
        *,
        document_id: UUID,
        hearing_id: UUID,
        chunk: Chunk,
        source_key: str,
        embedding: list[float] | None,
        metadata: dict | None = None,
    ) -> UUID:
        cid = _uuid("chunk", source_key)
        vector = None
        if embedding is not None:
            vector = "[" + ",".join(f"{x:.8f}" for x in embedding) + "]"
        conn.execute(
            """
            INSERT INTO chunks (
                id, document_id, hearing_id, chunk_index, content, token_count,
                speaker_name, embedding, metadata, source_key
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (source_key) DO UPDATE SET
                content = EXCLUDED.content,
                token_count = EXCLUDED.token_count,
                speaker_name = EXCLUDED.speaker_name,
                embedding = COALESCE(EXCLUDED.embedding, chunks.embedding),
                metadata = EXCLUDED.metadata
            """,
            (
                cid,
                document_id,
                hearing_id,
                chunk.index,
                chunk.content,
                chunk.token_count,
                chunk.speaker_name,
                vector,
                Json(metadata or {}),
                source_key,
            ),
        )
        return cid

    def upsert_board(self, conn: Connection, item: BoardIn) -> UUID:
        bid = item.id or _uuid("board", item.slug)
        conn.execute(
            """
            INSERT INTO boards (id, slug, title, description)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (slug) DO UPDATE SET
                title = EXCLUDED.title,
                description = COALESCE(EXCLUDED.description, boards.description)
            """,
            (bid, item.slug, item.title, item.description),
        )
        row = conn.execute("SELECT id FROM boards WHERE slug = %s", (item.slug,)).fetchone()
        return row["id"] if row else bid

    def upsert_pin(self, conn: Connection, item: PinIn, board_id: UUID) -> None:
        pid = item.id or _uuid("pin", str(board_id), item.pin_type, str(item.target_id))
        conn.execute(
            """
            INSERT INTO pins (id, board_id, pin_type, target_id, note)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (id) DO UPDATE SET note = EXCLUDED.note
            """,
            (pid, board_id, item.pin_type, item.target_id, item.note),
        )

    def resolve_appearance(self, conn: Connection, link: AppearanceIn) -> UUID | None:
        if link.person_id:
            return link.person_id
        if link.person:
            return self.upsert_person(conn, link.person)
        if link.person_slug:
            row = conn.execute(
                "SELECT id FROM people WHERE slug = %s", (link.person_slug,)
            ).fetchone()
            return row["id"] if row else None
        return None
