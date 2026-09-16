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
    AgencyIn,
    AppearanceIn,
    BoardIn,
    CommitteeIn,
    DivisionIn,
    DocumentIn,
    HandbookEntryIn,
    HandbookRoleIn,
    HandbookTenureIn,
    HearingIn,
    HearingSegmentIn,
    InstrumentIn,
    OutcomeIn,
    PersonIn,
    PersonRoleIn,
    PinIn,
    QuestionOnNoticeIn,
    ScrutinyItemIn,
    TopicIn,
)
from aus_gov_ingest.people import canonical_slug, names_are_same_person, pick_display_name, slug as slugify
from aus_gov_ingest.sources.util import stable_slug


def _uuid(*parts: str) -> UUID:
    return uuid5(NAMESPACE_URL, "aus-gov-map:" + "|".join(parts))


def _handbook_role_type(role_kind: str | None) -> str | None:
    kind = (role_kind or "").lower()
    if kind == "ministry":
        return "minister"
    if "shadow" in kind:
        return "shadow"
    if kind == "party":
        return None
    if "committee" in kind:
        return "committee"
    if kind in {"parliamentary", "other"}:
        return "other"
    return "other" if kind else None


def _chamber_role_type(chamber: str | None) -> str | None:
    text = (chamber or "").lower()
    if "senate" in text:
        return "senator"
    if "house" in text:
        return "mp"
    return None


def _portfolio_from_role(item: HandbookRoleIn) -> str | None:
    if item.role_kind == "ministry" and item.role_title:
        for prefix in ("Minister for ", "Minister of ", "Assistant Minister for "):
            if prefix in item.role_title:
                return item.role_title.split(prefix, 1)[1].strip() or None
        if item.notes:
            return None
    return None


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

    def existing_handbook_keys(self) -> set[str]:
        with self.connect() as conn:
            try:
                rows = conn.execute(
                    "SELECT handbook_key FROM handbook_entries WHERE handbook_key IS NOT NULL"
                ).fetchall()
            except Exception:
                return set()
        return {f"handbook:{row['handbook_key']}" for row in rows}

    def existing_qon_keys(self) -> set[str]:
        with self.connect() as conn:
            try:
                rows = conn.execute("SELECT source_key FROM qons").fetchall()
            except Exception:
                return set()
        return {row["source_key"] for row in rows}

    def existing_scrutiny_keys(self, item_type: str | None = None) -> set[str]:
        sql = "SELECT source_key FROM scrutiny_items WHERE source_key IS NOT NULL"
        params: tuple[Any, ...] = ()
        if item_type:
            sql += " AND item_type = %s"
            params = (item_type,)
        with self.connect() as conn:
            try:
                rows = conn.execute(sql, params).fetchall()
            except Exception:
                return set()
        return {row["source_key"] for row in rows}

    def existing_instrument_keys(self, source: str | None = None) -> set[str]:
        sql = "SELECT source_key FROM instruments WHERE source_key IS NOT NULL"
        params: tuple[Any, ...] = ()
        if source:
            sql += " AND source = %s"
            params = (source,)
        with self.connect() as conn:
            try:
                rows = conn.execute(sql, params).fetchall()
            except Exception:
                return set()
        return {row["source_key"] for row in rows}

    def existing_person_role_keys(self) -> set[str]:
        with self.connect() as conn:
            try:
                rows = conn.execute(
                    "SELECT source_key FROM person_roles WHERE source_key IS NOT NULL"
                ).fetchall()
            except Exception:
                return set()
        return {row["source_key"] for row in rows if row.get("source_key")}

    def existing_division_keys(self) -> set[str]:
        with self.connect() as conn:
            try:
                rows = conn.execute("SELECT source_key FROM divisions").fetchall()
            except Exception:
                return set()
        return {row["source_key"] for row in rows if row.get("source_key")}

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

    def upsert_agency(self, conn: Connection, item: AgencyIn) -> UUID:
        aid = _uuid("agency", item.slug)
        conn.execute(
            """
            INSERT INTO agencies (id, slug, name, short_name, portfolio, aao_ref, source, source_url)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (slug) DO UPDATE SET
                name = EXCLUDED.name,
                short_name = COALESCE(EXCLUDED.short_name, agencies.short_name),
                portfolio = COALESCE(EXCLUDED.portfolio, agencies.portfolio),
                aao_ref = COALESCE(EXCLUDED.aao_ref, agencies.aao_ref),
                source = COALESCE(EXCLUDED.source, agencies.source),
                source_url = COALESCE(EXCLUDED.source_url, agencies.source_url)
            """,
            (
                aid,
                item.slug,
                item.name,
                item.short_code,
                item.portfolio,
                item.kind,
                item.source or "seed",
                item.source_url,
            ),
        )
        row = conn.execute("SELECT id FROM agencies WHERE slug = %s", (item.slug,)).fetchone()
        return row["id"] if row else aid

    def upsert_handbook_entry(
        self, conn: Connection, item: HandbookEntryIn, person_id: UUID
    ) -> UUID:
        eid = _uuid("handbook", item.handbook_key)
        conn.execute(
            """
            INSERT INTO handbook_entries (
                id, person_id, handbook_key, display_name, chamber, electorate, party, aph_url
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (handbook_key) DO UPDATE SET
                person_id = COALESCE(EXCLUDED.person_id, handbook_entries.person_id),
                display_name = EXCLUDED.display_name,
                chamber = COALESCE(EXCLUDED.chamber, handbook_entries.chamber),
                electorate = COALESCE(EXCLUDED.electorate, handbook_entries.electorate),
                party = COALESCE(EXCLUDED.party, handbook_entries.party),
                aph_url = COALESCE(EXCLUDED.aph_url, handbook_entries.aph_url),
                updated_at = now()
            """,
            (
                eid,
                person_id,
                item.handbook_key,
                item.display_name,
                item.chamber,
                item.electorate,
                item.party,
                item.aph_url,
            ),
        )
        row = conn.execute(
            "SELECT id FROM handbook_entries WHERE handbook_key = %s", (item.handbook_key,)
        ).fetchone()
        entry_id = row["id"] if row else eid
        for role in item.roles:
            role_id = self.upsert_handbook_role(conn, entry_id, role)
            self._promote_handbook_role(conn, person_id, role_id, role, item)
        for tenure in item.tenure:
            tenure_id = self.upsert_handbook_tenure(conn, entry_id, tenure)
            self._promote_handbook_tenure(conn, person_id, tenure_id, tenure, item)
        return entry_id

    def upsert_handbook_role(
        self, conn: Connection, entry_id: UUID, item: HandbookRoleIn
    ) -> UUID:
        rid = _uuid(
            "handbook-role",
            str(entry_id),
            item.role_title,
            str(item.started_on or ""),
        )
        occupancy = _handbook_role_type(item.role_kind)
        existing = conn.execute(
            """
            SELECT id FROM handbook_roles
            WHERE handbook_entry_id = %s
              AND role_title = %s
              AND COALESCE(started_on, DATE '0001-01-01') = COALESCE(%s, DATE '0001-01-01')
            """,
            (entry_id, item.role_title, item.started_on),
        ).fetchone()
        if existing:
            conn.execute(
                """
                UPDATE handbook_roles SET
                    role_kind = COALESCE(%s, role_kind),
                    ended_on = COALESCE(%s, ended_on),
                    notes = COALESCE(%s, notes),
                    role_type = COALESCE(%s, role_type),
                    portfolio = COALESCE(%s, portfolio),
                    organisation = COALESCE(%s, organisation),
                    source = COALESCE(%s, source)
                WHERE id = %s
                """,
                (
                    item.role_kind,
                    item.ended_on,
                    item.notes,
                    occupancy,
                    _portfolio_from_role(item),
                    "Parliament of Australia",
                    "handbook",
                    existing["id"],
                ),
            )
            return existing["id"]
        conn.execute(
            """
            INSERT INTO handbook_roles (
                id, handbook_entry_id, role_title, role_kind, started_on, ended_on, notes,
                role_type, portfolio, organisation, source
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                rid,
                entry_id,
                item.role_title,
                item.role_kind,
                item.started_on,
                item.ended_on,
                item.notes,
                occupancy,
                _portfolio_from_role(item),
                "Parliament of Australia",
                "handbook",
            ),
        )
        return rid

    def upsert_handbook_tenure(
        self, conn: Connection, entry_id: UUID, item: HandbookTenureIn
    ) -> UUID:
        tid = _uuid(
            "handbook-tenure",
            str(entry_id),
            item.chamber or "",
            str(item.started_on or ""),
        )
        existing = conn.execute(
            """
            SELECT id FROM handbook_tenure
            WHERE handbook_entry_id = %s
              AND COALESCE(chamber, '') = COALESCE(%s, '')
              AND COALESCE(started_on, DATE '0001-01-01') = COALESCE(%s, DATE '0001-01-01')
            """,
            (entry_id, item.chamber, item.started_on),
        ).fetchone()
        if existing:
            conn.execute(
                """
                UPDATE handbook_tenure SET
                    electorate = COALESCE(%s, electorate),
                    parliament_number = COALESCE(%s, parliament_number),
                    ended_on = COALESCE(%s, ended_on),
                    source = COALESCE(%s, source)
                WHERE id = %s
                """,
                (item.electorate, item.parliament_number, item.ended_on, "handbook", existing["id"]),
            )
            return existing["id"]
        conn.execute(
            """
            INSERT INTO handbook_tenure (
                id, handbook_entry_id, chamber, electorate, parliament_number,
                started_on, ended_on, source
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                tid,
                entry_id,
                item.chamber,
                item.electorate,
                item.parliament_number,
                item.started_on,
                item.ended_on,
                "handbook",
            ),
        )
        return tid

    def _promote_handbook_role(
        self,
        conn: Connection,
        person_id: UUID,
        handbook_role_id: UUID,
        item: HandbookRoleIn,
        entry: HandbookEntryIn,
    ) -> None:
        role_type = _handbook_role_type(item.role_kind)
        if role_type is None:
            return
        role_id = self._upsert_role_catalog(
            conn,
            title=item.role_title,
            role_type=role_type,
            portfolio=_portfolio_from_role(item) or entry.person.portfolio,
            organisation="Parliament of Australia",
        )
        self._upsert_person_role(
            conn,
            person_id=person_id,
            role_id=role_id,
            role_type=role_type,
            portfolio=_portfolio_from_role(item) or entry.person.portfolio,
            organisation="Parliament of Australia",
            start_date=item.started_on,
            end_date=item.ended_on,
            source="handbook",
            source_url=entry.aph_url,
            handbook_role_id=handbook_role_id,
        )

    def _promote_handbook_tenure(
        self,
        conn: Connection,
        person_id: UUID,
        handbook_tenure_id: UUID,
        item: HandbookTenureIn,
        entry: HandbookEntryIn,
    ) -> None:
        role_type = _chamber_role_type(item.chamber)
        if role_type is None:
            return
        title = item.chamber or role_type
        if item.electorate:
            title = f"{title} — {item.electorate}"
        role_id = self._upsert_role_catalog(
            conn,
            title=title,
            role_type=role_type,
            portfolio=None,
            organisation=item.chamber or "Parliament of Australia",
        )
        self._upsert_person_role(
            conn,
            person_id=person_id,
            role_id=role_id,
            role_type=role_type,
            portfolio=None,
            organisation=item.chamber,
            start_date=item.started_on,
            end_date=item.ended_on,
            source="handbook",
            source_url=entry.aph_url,
            handbook_tenure_id=handbook_tenure_id,
        )

    def _upsert_role_catalog(
        self,
        conn: Connection,
        *,
        title: str,
        role_type: str,
        portfolio: str | None,
        organisation: str | None,
        agency_id: UUID | None = None,
        source: str = "handbook",
        source_url: str | None = None,
    ) -> UUID:
        slug = slugify(f"{role_type}-{title}-{portfolio or ''}")[:80] or slugify(title)
        rid = _uuid("role", slug)
        conn.execute(
            """
            INSERT INTO roles (id, slug, title, role_type, portfolio, organisation, agency_id, source, source_url)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (slug) DO UPDATE SET
                title = EXCLUDED.title,
                portfolio = COALESCE(EXCLUDED.portfolio, roles.portfolio),
                organisation = COALESCE(EXCLUDED.organisation, roles.organisation),
                agency_id = COALESCE(EXCLUDED.agency_id, roles.agency_id),
                source_url = COALESCE(EXCLUDED.source_url, roles.source_url)
            """,
            (rid, slug, title, role_type, portfolio, organisation, agency_id, source, source_url),
        )
        row = conn.execute("SELECT id FROM roles WHERE slug = %s", (slug,)).fetchone()
        return row["id"] if row else rid

    def _upsert_person_role(
        self,
        conn: Connection,
        *,
        person_id: UUID,
        role_id: UUID,
        role_type: str,
        portfolio: str | None,
        organisation: str | None,
        start_date,
        end_date,
        source: str,
        source_url: str | None,
        handbook_role_id: UUID | None = None,
        handbook_tenure_id: UUID | None = None,
        agency_id: UUID | None = None,
        source_key: str | None = None,
        notes: str | None = None,
    ) -> UUID:
        existing = None
        if source_key:
            try:
                existing = conn.execute(
                    "SELECT id FROM person_roles WHERE source_key = %s",
                    (source_key,),
                ).fetchone()
            except Exception:
                existing = None
        if existing is None:
            existing = conn.execute(
                """
                SELECT id FROM person_roles
                WHERE person_id = %s
                  AND role_id = %s
                  AND COALESCE(start_date, DATE '0001-01-01') = COALESCE(%s, DATE '0001-01-01')
                """,
                (person_id, role_id, start_date),
            ).fetchone()
        if existing:
            conn.execute(
                """
                UPDATE person_roles SET
                    end_date = COALESCE(%s, end_date),
                    portfolio = COALESCE(%s, portfolio),
                    organisation = COALESCE(%s, organisation),
                    agency_id = COALESCE(%s, agency_id),
                    handbook_role_id = COALESCE(%s, handbook_role_id),
                    handbook_tenure_id = COALESCE(%s, handbook_tenure_id),
                    source_url = COALESCE(%s, source_url),
                    notes = COALESCE(%s, notes)
                WHERE id = %s
                """,
                (
                    end_date,
                    portfolio,
                    organisation,
                    agency_id,
                    handbook_role_id,
                    handbook_tenure_id,
                    source_url,
                    notes,
                    existing["id"],
                ),
            )
            return existing["id"]
        prid = _uuid(
            "person-role",
            str(person_id),
            str(role_id),
            str(start_date or ""),
            source_key or "",
        )
        try:
            conn.execute(
                """
                INSERT INTO person_roles (
                    id, person_id, role_id, role_type, portfolio, organisation,
                    agency_id, start_date, end_date, source, source_url,
                    handbook_role_id, handbook_tenure_id, source_key, notes
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    prid,
                    person_id,
                    role_id,
                    role_type,
                    portfolio,
                    organisation,
                    agency_id,
                    start_date,
                    end_date,
                    source,
                    source_url,
                    handbook_role_id,
                    handbook_tenure_id,
                    source_key,
                    notes,
                ),
            )
        except Exception:
            # Pre-010 volumes: no source_key / notes columns yet.
            conn.execute(
                """
                INSERT INTO person_roles (
                    id, person_id, role_id, role_type, portfolio, organisation,
                    agency_id, start_date, end_date, source, source_url,
                    handbook_role_id, handbook_tenure_id
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    prid,
                    person_id,
                    role_id,
                    role_type,
                    portfolio,
                    organisation,
                    agency_id,
                    start_date,
                    end_date,
                    source,
                    source_url,
                    handbook_role_id,
                    handbook_tenure_id,
                ),
            )
        return prid

    def upsert_person_role_occupancy(self, conn: Connection, item: PersonRoleIn) -> UUID:
        person_id = self.upsert_person(conn, item.person)
        agency_id = None
        if item.agency:
            agency_id = self.upsert_agency(conn, item.agency)
        role_id = self._upsert_role_catalog(
            conn,
            title=item.role_title,
            role_type=item.role_type,
            portfolio=item.portfolio,
            organisation=item.organisation,
            agency_id=agency_id,
            source=item.source,
            source_url=item.source_url,
        )
        return self._upsert_person_role(
            conn,
            person_id=person_id,
            role_id=role_id,
            role_type=item.role_type,
            portfolio=item.portfolio,
            organisation=item.organisation,
            start_date=item.start_date,
            end_date=item.end_date,
            source=item.source,
            source_url=item.source_url,
            agency_id=agency_id,
            source_key=item.source_key,
            notes=item.notes,
        )

    def upsert_hearing_segment(
        self,
        conn: Connection,
        *,
        hearing_id: UUID,
        document_id: UUID | None,
        hearing_source_key: str,
        index: int,
        segment: HearingSegmentIn,
    ) -> UUID:
        source_key = f"segment:{hearing_source_key}:{index}:{segment.kind}"
        sid = _uuid("segment", source_key)
        conn.execute(
            """
            INSERT INTO hearing_segments (
                id, hearing_id, document_id, source_key, segment_index, kind,
                speaker_name, portfolio, agency, content, char_start, char_end, metadata
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (source_key) DO UPDATE SET
                speaker_name = EXCLUDED.speaker_name,
                portfolio = EXCLUDED.portfolio,
                agency = EXCLUDED.agency,
                content = EXCLUDED.content,
                metadata = EXCLUDED.metadata
            """,
            (
                sid,
                hearing_id,
                document_id,
                source_key,
                index,
                segment.kind,
                segment.speaker_name,
                segment.portfolio,
                segment.agency,
                segment.content,
                segment.char_start,
                segment.char_end,
                Json(segment.metadata or {}),
            ),
        )
        if segment.kind == "taken_on_notice":
            self._upsert_taken_on_notice(
                conn,
                hearing_id=hearing_id,
                source_key=source_key,
                segment=segment,
                index=index,
            )
        return sid

    def _upsert_taken_on_notice(
        self,
        conn: Connection,
        *,
        hearing_id: UUID,
        source_key: str,
        segment: HearingSegmentIn,
        index: int,
    ) -> None:
        held = conn.execute(
            "SELECT held_on FROM hearings WHERE id = %s", (hearing_id,)
        ).fetchone()
        made_on = held["held_on"] if held else None
        scrutiny_key = f"scrutiny:{source_key}"
        sid = _uuid("scrutiny", scrutiny_key)
        conn.execute(
            """
            INSERT INTO scrutiny_items (
                id, slug, item_type, title, identifiers, published_on,
                hearing_id, source, source_url, source_key, summary
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (source_key) DO UPDATE SET
                summary = EXCLUDED.summary,
                title = EXCLUDED.title
            """,
            (
                sid,
                slugify(source_key)[:80],
                "hearing_segment",
                "Taken on notice",
                Json({"segment_kind": segment.kind, "index": index}),
                made_on,
                hearing_id,
                "estimates_segment",
                None,
                scrutiny_key,
                (segment.content or "")[:500],
            ),
        )
        claim_key = f"claim:ton:{source_key}"
        cid = _uuid("claim", claim_key)
        conn.execute(
            """
            INSERT INTO claims (
                id, speaker_name, hearing_id, claim_type, text_span, made_on, source, source_key
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (source_key) DO UPDATE SET
                text_span = EXCLUDED.text_span,
                speaker_name = COALESCE(EXCLUDED.speaker_name, claims.speaker_name)
            """,
            (
                cid,
                segment.speaker_name,
                hearing_id,
                "taken_on_notice",
                (segment.content or "")[:1000],
                made_on,
                "estimates_segment",
                claim_key,
            ),
        )

    def upsert_question(
        self,
        conn: Connection,
        item: QuestionOnNoticeIn,
        *,
        hearing_id: UUID | None = None,
    ) -> UUID:
        qid = _uuid("qon", item.source_key)
        agency_id = self.resolve_agency(
            conn,
            slug=item.agency_slug,
            name=item.agency_name,
            portfolio=item.portfolio,
            source="eqon",
        )
        identifiers = {
            **(item.metadata or {}),
            "portfolio_question_number": item.portfolio_question_number,
            "committee_name": item.committee_name,
            "estimates_round": item.estimates_round,
            "agency_name": item.agency_name,
        }
        scrutiny_key = f"scrutiny:{item.source_key}"
        scrutiny_id = _uuid("scrutiny", scrutiny_key)
        conn.execute(
            """
            INSERT INTO scrutiny_items (
                id, slug, item_type, title, identifiers, published_on,
                hearing_id, source, source_url, source_key, summary
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (source_key) DO UPDATE SET
                summary = COALESCE(EXCLUDED.summary, scrutiny_items.summary),
                title = EXCLUDED.title
            """,
            (
                scrutiny_id,
                slugify(item.source_key)[:80],
                "qon",
                item.portfolio_question_number or item.qon_number or item.source_key,
                Json(identifiers),
                item.asked_on,
                hearing_id,
                "eqon",
                item.source_url,
                scrutiny_key,
                (item.question_text or "")[:500] or None,
            ),
        )
        number = item.portfolio_question_number or item.qon_number
        conn.execute(
            """
            INSERT INTO qons (
                id, number, house, portfolio, asking_member, answering_agency_id,
                asked_on, due_on, answered_on, status, question_ref, answer_ref,
                hearing_id, scrutiny_item_id, source, source_url, source_key, identifiers
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (source_key) DO UPDATE SET
                status = EXCLUDED.status,
                question_ref = COALESCE(EXCLUDED.question_ref, qons.question_ref),
                answer_ref = COALESCE(EXCLUDED.answer_ref, qons.answer_ref),
                answered_on = COALESCE(EXCLUDED.answered_on, qons.answered_on),
                due_on = COALESCE(EXCLUDED.due_on, qons.due_on),
                answering_agency_id = COALESCE(EXCLUDED.answering_agency_id, qons.answering_agency_id),
                identifiers = EXCLUDED.identifiers,
                scrutiny_item_id = COALESCE(EXCLUDED.scrutiny_item_id, qons.scrutiny_item_id)
            """,
            (
                qid,
                number,
                "Senate",
                item.portfolio,
                item.asked_by,
                agency_id,
                item.asked_on,
                item.due_on,
                item.answered_on,
                item.status if item.status in {"open", "answered", "overdue", "refused", "unknown"} else "unknown",
                item.question_text,
                item.answer_text,
                hearing_id,
                scrutiny_id,
                "eqon",
                item.source_url,
                item.source_key,
                Json(identifiers),
            ),
        )
        self._link_claims_to_qon(conn, item, qid)
        return qid

    def resolve_agency(
        self,
        conn: Connection,
        *,
        slug: str | None = None,
        name: str | None = None,
        portfolio: str | None = None,
        source: str | None = None,
        source_url: str | None = None,
        create: bool = True,
    ) -> UUID | None:
        if slug:
            row = conn.execute("SELECT id FROM agencies WHERE slug = %s", (slug,)).fetchone()
            if row:
                return row["id"]
        if name:
            row = conn.execute(
                "SELECT id FROM agencies WHERE name ILIKE %s LIMIT 1", (name,)
            ).fetchone()
            if row:
                return row["id"]
            row = conn.execute(
                "SELECT id FROM agencies WHERE short_name ILIKE %s LIMIT 1", (name,)
            ).fetchone()
            if row:
                return row["id"]
        if not create or not (slug or name):
            return None
        return self.upsert_agency(
            conn,
            AgencyIn(
                slug=slug or slugify(name or "agency"),
                name=name or slug or "Unknown agency",
                short_code=None,
                portfolio=portfolio,
                kind="agency",
                source=source,
                source_url=source_url,
            ),
        )

    def _link_claims_to_qon(
        self, conn: Connection, item: QuestionOnNoticeIn, qon_id: UUID
    ) -> None:
        """Attach taken-on-notice claims whose span cites this QoN number."""
        from aus_gov_ingest.sources.qon import qon_number_needles

        needles = qon_number_needles(item)
        if not needles:
            return
        try:
            for needle in needles:
                conn.execute(
                    """
                    UPDATE claims SET qon_id = %s
                    WHERE claim_type = 'taken_on_notice'
                      AND qon_id IS NULL
                      AND text_span ILIKE %s
                    """,
                    (qon_id, f"%{needle}%"),
                )
        except Exception:
            # Pre-010 volumes have no claims.qon_id.
            return

    def upsert_instrument(
        self,
        conn: Connection,
        item: InstrumentIn,
        *,
        hearing_id: UUID | None = None,
    ) -> UUID:
        iid = _uuid("instrument", item.source_key)
        slug = stable_slug(item.source_key, item.title)
        chunk_id = None
        if item.source_chunk_key:
            row = conn.execute(
                "SELECT id FROM chunks WHERE source_key = %s", (item.source_chunk_key,)
            ).fetchone()
            chunk_id = row["id"] if row else None
        instrument_type = item.kind if item.kind in {
            "program", "measure", "bill", "act", "contract", "grant", "policy", "other",
        } else "other"
        agency_id = self.resolve_agency(
            conn,
            slug=item.agency_slug,
            name=item.agency_name,
            portfolio=item.portfolio,
            source=item.source or "instrument",
            source_url=item.source_url,
            create=bool(item.agency_name or item.agency_slug),
        )
        identifiers = {
            **(item.metadata or {}),
            **(item.identifiers or {}),
            "source_chunk_key": item.source_chunk_key,
            "notes": item.notes,
            "supplier": item.supplier_name,
            "agency_name": item.agency_name,
            "portfolio": item.portfolio,
        }
        payload = (
            iid,
            slug,
            instrument_type,
            item.title,
            Json(identifiers),
            agency_id,
            item.announced_on,
            item.commenced_on,
            item.ended_on,
            item.amount_aud,
            item.source or "instrument_propose",
            item.source_url,
            item.source_key,
            item.evidence_text or item.notes,
            item.status or "proposed",
            item.confidence,
        )
        existing = conn.execute(
            "SELECT id FROM instruments WHERE source_key = %s", (item.source_key,)
        ).fetchone()
        if existing:
            conn.execute(
                """
                UPDATE instruments SET
                    slug = %s,
                    instrument_type = %s,
                    title = %s,
                    identifiers = %s,
                    agency_id = COALESCE(%s, instruments.agency_id),
                    announced_on = COALESCE(%s, instruments.announced_on),
                    commenced_on = COALESCE(%s, instruments.commenced_on),
                    ended_on = COALESCE(%s, instruments.ended_on),
                    amount_aud = COALESCE(%s, instruments.amount_aud),
                    source = COALESCE(%s, instruments.source),
                    source_url = COALESCE(%s, instruments.source_url),
                    summary = COALESCE(%s, instruments.summary),
                    status = %s,
                    confidence = %s,
                    updated_at = now()
                WHERE id = %s
                """,
                (
                    slug,
                    instrument_type,
                    item.title,
                    Json(identifiers),
                    agency_id,
                    item.announced_on,
                    item.commenced_on,
                    item.ended_on,
                    item.amount_aud,
                    item.source or "instrument_propose",
                    item.source_url,
                    item.evidence_text or item.notes,
                    item.status or "proposed",
                    item.confidence,
                    existing["id"],
                ),
            )
            instrument_id = existing["id"]
        else:
            conn.execute(
                """
                INSERT INTO instruments (
                    id, slug, instrument_type, title, identifiers, agency_id,
                    announced_on, commenced_on, ended_on, amount_aud,
                    source, source_url, source_key, summary, status, confidence
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (slug) DO UPDATE SET
                    title = EXCLUDED.title,
                    summary = COALESCE(EXCLUDED.summary, instruments.summary),
                    status = EXCLUDED.status,
                    confidence = EXCLUDED.confidence,
                    identifiers = EXCLUDED.identifiers,
                    agency_id = COALESCE(EXCLUDED.agency_id, instruments.agency_id),
                    announced_on = COALESCE(EXCLUDED.announced_on, instruments.announced_on),
                    commenced_on = COALESCE(EXCLUDED.commenced_on, instruments.commenced_on),
                    ended_on = COALESCE(EXCLUDED.ended_on, instruments.ended_on),
                    amount_aud = COALESCE(EXCLUDED.amount_aud, instruments.amount_aud),
                    source = COALESCE(EXCLUDED.source, instruments.source),
                    source_url = COALESCE(EXCLUDED.source_url, instruments.source_url),
                    source_key = EXCLUDED.source_key
                """,
                payload,
            )
            row = conn.execute(
                "SELECT id FROM instruments WHERE source_key = %s OR slug = %s",
                (item.source_key, slug),
            ).fetchone()
            instrument_id = row["id"] if row else iid
        if chunk_id:
            conn.execute(
                """
                INSERT INTO instrument_links (
                    instrument_id, target_kind, target_id, hearing_id, chunk_id,
                    link_kind, source, notes
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (instrument_id, target_kind, target_id, link_kind) DO NOTHING
                """,
                (
                    instrument_id,
                    "chunk",
                    chunk_id,
                    hearing_id,
                    chunk_id,
                    "mentioned",
                    item.source or "instrument_propose",
                    item.notes,
                ),
            )
        if agency_id:
            conn.execute(
                """
                INSERT INTO instrument_links (
                    instrument_id, target_kind, target_id, agency_id,
                    link_kind, source, notes
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (instrument_id, target_kind, target_id, link_kind) DO NOTHING
                """,
                (
                    instrument_id,
                    "agency",
                    agency_id,
                    agency_id,
                    "mentioned",
                    item.source or "instrument",
                    item.agency_name,
                ),
            )
        return instrument_id

    def upsert_scrutiny_item(self, conn: Connection, item: ScrutinyItemIn) -> UUID:
        sid = _uuid("scrutiny", item.source_key)
        slug = slugify(item.source_key)[:80] or slugify(item.title)
        agency_id = self.resolve_agency(
            conn,
            slug=item.agency_slug,
            name=item.agency_name,
            portfolio=item.portfolio,
            source=item.source,
            source_url=item.source_url,
            create=bool(item.agency_name or item.agency_slug),
        )
        identifiers = {
            **(item.identifiers or {}),
            "agency_name": item.agency_name,
            "portfolio": item.portfolio,
            "confidence": item.confidence,
            "agency_id": str(agency_id) if agency_id else None,
        }
        item_type = item.item_type if item.item_type in {
            "qon", "anao", "inquiry_report", "division", "hearing_segment",
            "judgment", "other",
        } else "other"
        conn.execute(
            """
            INSERT INTO scrutiny_items (
                id, slug, item_type, title, identifiers, published_on,
                source, source_url, source_key, summary
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (source_key) DO UPDATE SET
                title = EXCLUDED.title,
                summary = COALESCE(EXCLUDED.summary, scrutiny_items.summary),
                published_on = COALESCE(EXCLUDED.published_on, scrutiny_items.published_on),
                identifiers = EXCLUDED.identifiers,
                source_url = COALESCE(EXCLUDED.source_url, scrutiny_items.source_url)
            """,
            (
                sid,
                slug,
                item_type,
                item.title,
                Json(identifiers),
                item.published_on,
                item.source,
                item.source_url,
                item.source_key,
                item.summary,
            ),
        )
        row = conn.execute(
            "SELECT id FROM scrutiny_items WHERE source_key = %s", (item.source_key,)
        ).fetchone()
        return row["id"] if row else sid

    def upsert_outcome(
        self,
        conn: Connection,
        item: OutcomeIn,
        *,
        instrument_id: UUID | None = None,
        scrutiny_item_id: UUID | None = None,
    ) -> UUID:
        oid = _uuid("outcome", item.source_key)
        agency_id = self.resolve_agency(
            conn,
            slug=item.agency_slug,
            name=item.agency_name,
            source=item.source,
            source_url=item.source_url,
            create=False,
        )
        signal = item.signal if item.signal in {
            "met", "unmet", "partial", "adverse", "unknown",
        } else "unknown"
        try:
            conn.execute(
                """
                INSERT INTO outcomes (
                    id, outcome_type, instrument_id, signal, occurred_on,
                    source, source_url, notes, confidence, agency_id,
                    scrutiny_item_id, source_key, identifiers
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (source_key) DO UPDATE SET
                    signal = EXCLUDED.signal,
                    notes = COALESCE(EXCLUDED.notes, outcomes.notes),
                    confidence = EXCLUDED.confidence,
                    instrument_id = COALESCE(EXCLUDED.instrument_id, outcomes.instrument_id),
                    agency_id = COALESCE(EXCLUDED.agency_id, outcomes.agency_id),
                    scrutiny_item_id = COALESCE(EXCLUDED.scrutiny_item_id, outcomes.scrutiny_item_id)
                """,
                (
                    oid,
                    item.outcome_type,
                    instrument_id,
                    signal,
                    item.occurred_on,
                    item.source,
                    item.source_url,
                    item.notes,
                    item.confidence,
                    agency_id,
                    scrutiny_item_id,
                    item.source_key,
                    Json(item.identifiers or {}),
                ),
            )
        except Exception:
            # 009 columns missing — write the 007 core row only.
            conn.execute(
                """
                INSERT INTO outcomes (
                    id, outcome_type, instrument_id, signal, occurred_on,
                    source, source_url, notes
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    oid,
                    item.outcome_type,
                    instrument_id,
                    signal,
                    item.occurred_on,
                    item.source,
                    item.source_url,
                    item.notes,
                ),
            )
        return oid

    def link_tested_in(
        self,
        conn: Connection,
        *,
        instrument_id: UUID,
        scrutiny_item_id: UUID,
        source: str | None,
    ) -> None:
        conn.execute(
            """
            INSERT INTO instrument_links (
                instrument_id, target_kind, target_id, scrutiny_item_id,
                link_kind, source
            )
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (instrument_id, target_kind, target_id, link_kind) DO NOTHING
            """,
            (
                instrument_id,
                "scrutiny",
                scrutiny_item_id,
                scrutiny_item_id,
                "tested_in",
                source,
            ),
        )

    def lookup_instrument_id(self, conn: Connection, source_key: str) -> UUID | None:
        row = conn.execute(
            "SELECT id FROM instruments WHERE source_key = %s",
            (source_key,),
        ).fetchone()
        return row["id"] if row else None

    def lookup_scrutiny_id(self, conn: Connection, source_key: str) -> UUID | None:
        row = conn.execute(
            "SELECT id FROM scrutiny_items WHERE source_key = %s",
            (source_key,),
        ).fetchone()
        return row["id"] if row else None

    def lookup_instrument_id_by_title(self, conn: Connection, title: str) -> UUID | None:
        """Match an existing bill/act by title fragment. Never creates a row."""
        needle = (title or "").strip()
        if len(needle) < 8:
            return None
        row = conn.execute(
            """
            SELECT id FROM instruments
            WHERE instrument_type IN ('bill', 'act')
              AND (
                title ILIKE %s
                OR %s ILIKE '%' || title || '%'
              )
            ORDER BY CASE instrument_type WHEN 'bill' THEN 0 ELSE 1 END
            LIMIT 1
            """,
            (f"%{needle[:80]}%", needle),
        ).fetchone()
        return row["id"] if row else None

    def find_existing_person(self, conn: Connection, name: str) -> UUID | None:
        """Resolve a published name to an existing people row. Never INSERT."""
        if not (name or "").strip():
            return None
        item = PersonIn(slug=canonical_slug(name), name=name)
        merge = self.find_person_merge(conn, item)
        return merge["id"] if merge else None

    def link_instrument(
        self,
        conn: Connection,
        *,
        instrument_id: UUID,
        scrutiny_item_id: UUID,
        link_kind: str,
        source: str | None,
        notes: str | None = None,
    ) -> None:
        kind = link_kind if link_kind in {
            "accountable_for", "responsible_official", "promised_in", "tested_in",
            "voted_on", "funded_by", "mentioned", "other",
            "construes", "invalidates", "upholds",
        } else "other"
        try:
            conn.execute(
                """
                INSERT INTO instrument_links (
                    instrument_id, target_kind, target_id, scrutiny_item_id,
                    link_kind, source, notes
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (instrument_id, target_kind, target_id, link_kind) DO UPDATE SET
                    notes = COALESCE(EXCLUDED.notes, instrument_links.notes)
                """,
                (
                    instrument_id,
                    "scrutiny",
                    scrutiny_item_id,
                    scrutiny_item_id,
                    kind,
                    source,
                    notes,
                ),
            )
        except Exception:
            # Pre-013 volumes reject new link kinds — skip rather than invent.
            return

    def upsert_division(
        self,
        conn: Connection,
        item: DivisionIn,
        *,
        instrument_id: UUID | None = None,
    ) -> UUID:
        did = _uuid("division", item.source_key)
        slug = slugify(item.source_key)[:80] or slugify(item.title)
        house = item.house if item.house in {"representatives", "senate", "other"} else (
            "other" if item.house else None
        )
        scrutiny_id = None
        try:
            scrutiny_id = self.upsert_scrutiny_item(
                conn,
                ScrutinyItemIn(
                    source_key=item.source_key,
                    item_type="division",
                    title=item.title,
                    published_on=item.divided_on,
                    source=item.source,
                    source_url=item.source_url,
                    summary=item.summary,
                    identifiers=item.identifiers or {},
                ),
            )
        except Exception:
            scrutiny_id = None
        try:
            conn.execute(
                """
                INSERT INTO divisions (
                    id, slug, source_key, title, house, divided_on, number,
                    instrument_id, scrutiny_item_id, ayes, noes, abstentions,
                    possible_turnout, source, source_url, identifiers, summary
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (source_key) DO UPDATE SET
                    title = EXCLUDED.title,
                    house = COALESCE(EXCLUDED.house, divisions.house),
                    divided_on = COALESCE(EXCLUDED.divided_on, divisions.divided_on),
                    number = COALESCE(EXCLUDED.number, divisions.number),
                    instrument_id = COALESCE(EXCLUDED.instrument_id, divisions.instrument_id),
                    scrutiny_item_id = COALESCE(EXCLUDED.scrutiny_item_id, divisions.scrutiny_item_id),
                    ayes = COALESCE(EXCLUDED.ayes, divisions.ayes),
                    noes = COALESCE(EXCLUDED.noes, divisions.noes),
                    abstentions = COALESCE(EXCLUDED.abstentions, divisions.abstentions),
                    source_url = COALESCE(EXCLUDED.source_url, divisions.source_url),
                    identifiers = EXCLUDED.identifiers,
                    summary = COALESCE(EXCLUDED.summary, divisions.summary),
                    updated_at = now()
                """,
                (
                    did,
                    slug,
                    item.source_key,
                    item.title,
                    house,
                    item.divided_on,
                    item.number,
                    instrument_id,
                    scrutiny_id,
                    item.ayes,
                    item.noes,
                    item.abstentions,
                    item.possible_turnout,
                    item.source,
                    item.source_url,
                    Json(item.identifiers or {}),
                    item.summary,
                ),
            )
        except Exception:
            # 012 not applied — scrutiny_item (division) is still useful.
            return did
        row = conn.execute(
            "SELECT id FROM divisions WHERE source_key = %s", (item.source_key,)
        ).fetchone()
        division_id = row["id"] if row else did
        if instrument_id and scrutiny_id:
            self.link_instrument(
                conn,
                instrument_id=instrument_id,
                scrutiny_item_id=scrutiny_id,
                link_kind="tested_in",
                source=item.source,
                notes="Sourced parliamentary division",
            )
        for vote in item.votes:
            person_id = self.find_existing_person(conn, vote.person_name)
            vote_id = _uuid("division_vote", item.source_key, vote.person_name, vote.vote)
            conn.execute(
                """
                INSERT INTO division_votes (
                    id, division_id, person_id, person_name, vote, party,
                    electorate, source, identifiers
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (division_id, lower(person_name), vote) DO UPDATE SET
                    person_id = COALESCE(EXCLUDED.person_id, division_votes.person_id),
                    party = COALESCE(EXCLUDED.party, division_votes.party),
                    electorate = COALESCE(EXCLUDED.electorate, division_votes.electorate)
                """,
                (
                    vote_id,
                    division_id,
                    person_id,
                    vote.person_name,
                    vote.vote,
                    vote.party,
                    vote.electorate,
                    item.source,
                    Json(vote.identifiers or {}),
                ),
            )
            if person_id and instrument_id:
                try:
                    conn.execute(
                        """
                        INSERT INTO instrument_links (
                            instrument_id, target_kind, target_id, person_id,
                            scrutiny_item_id, link_kind, source, notes
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (instrument_id, target_kind, target_id, link_kind) DO NOTHING
                        """,
                        (
                            instrument_id,
                            "person",
                            person_id,
                            person_id,
                            scrutiny_id,
                            "voted_on",
                            item.source,
                            f"{vote.vote} on {item.title}",
                        ),
                    )
                except Exception:
                    pass
        return division_id

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
