from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

from aus_gov_ingest.chunking import chunk_text
from aus_gov_ingest.config import settings
from aus_gov_ingest.db.neo4j_graph import Neo4jStore
from aus_gov_ingest.db.postgres import PostgresStore
from aus_gov_ingest.embeddings import get_embedder
from aus_gov_ingest.models import HearingIn, SourceBatch
from aus_gov_ingest.sources import get_source


@dataclass
class RunResult:
    source: str
    fetched: int = 0
    upserted: int = 0
    chunks: int = 0
    status: str = "success"
    error: str | None = None
    meta: dict[str, Any] = field(default_factory=dict)


def run_ingest(
    source_name: str,
    *,
    limit: int = 0,
    incremental: bool = False,
    write_graph: bool = True,
    database_url: str | None = None,
    dry_run: bool = False,
) -> RunResult:
    source = get_source(source_name)
    embedder = get_embedder()
    if dry_run:
        batch = source.fetch(limit=limit, incremental_keys=None)
        return RunResult(
            source=source_name,
            fetched=len(batch.hearings),
            upserted=0,
            chunks=sum(len(h.documents) for h in batch.hearings),
            status="dry_run",
            meta={
                "dry_run": True,
                "embedder": embedder.name,
                "titles": [h.title for h in batch.hearings],
                "held_on": [str(h.held_on) if h.held_on else None for h in batch.hearings],
                "with_transcript": sum(1 for h in batch.hearings if h.documents),
                **batch.meta,
            },
        )

    store = PostgresStore(dsn=database_url or settings.database_url)

    known: set[str] | None = None
    if incremental:
        known = store.existing_source_keys(
            source="estimates" if source_name in {"estimates", "estimates_schedule"} else None
        )

    run_id = store.start_run(
        source_name,
        meta={"limit": limit, "incremental": incremental, "embedder": embedder.name},
    )
    result = RunResult(source=source_name, meta={"run_id": str(run_id), "embedder": embedder.name})

    try:
        batch = source.fetch(limit=limit, incremental_keys=known)
        result.fetched = len(batch.hearings)
        result.meta.update(batch.meta)
        upserted, chunks = _persist(store, batch, embedder, write_graph=write_graph)
        result.upserted = upserted
        result.chunks = chunks
        result.status = "success"
        store.finish_run(
            run_id, status="success", fetched=result.fetched, upserted=result.upserted
        )
    except Exception as exc:
        result.status = "failed"
        result.error = str(exc)
        store.finish_run(
            run_id,
            status="failed",
            fetched=result.fetched,
            upserted=result.upserted,
            error=str(exc),
        )
        raise
    return result


def _persist(
    store: PostgresStore,
    batch: SourceBatch,
    embedder,
    *,
    write_graph: bool,
) -> tuple[int, int]:
    graph: Neo4jStore | None = None
    if write_graph:
        graph = Neo4jStore()
        if not graph.ping():
            graph = None

    upserted = 0
    chunks_written = 0
    with store.connect() as conn:
        topic_ids: dict[str, str] = {}
        for topic in batch.topics:
            topic_ids[topic.slug] = str(store.upsert_topic(conn, topic))
        person_ids: dict[str, str] = {}
        for person in batch.people:
            person_ids[person.slug] = str(store.upsert_person(conn, person))
        for committee in batch.committees:
            store.upsert_committee(conn, committee)
        board_ids: dict[str, UUID] = {}
        for board in batch.boards:
            board_ids[board.slug] = store.upsert_board(conn, board)
            if board.id:
                board_ids[str(board.id)] = board_ids[board.slug]
        for pin in batch.pins:
            board_id = pin.board_id
            if not board_id and pin.board_slug:
                board_id = board_ids.get(pin.board_slug)
            if board_id:
                store.upsert_pin(conn, pin, board_id)

        for hearing in batch.hearings:
            hid, n_chunks, ids = _persist_hearing(
                store, conn, hearing, embedder, topic_ids, person_ids
            )
            upserted += 1
            chunks_written += n_chunks
            if graph:
                try:
                    graph.upsert_hearing(hearing, ids)
                except Exception:
                    pass
        conn.commit()
    return upserted, chunks_written


def _persist_hearing(
    store: PostgresStore,
    conn,
    hearing: HearingIn,
    embedder,
    topic_ids: dict[str, str],
    person_ids: dict[str, str],
) -> tuple[UUID, int, dict]:
    committee_id = hearing.committee_id
    if hearing.committee:
        committee_id = store.upsert_committee(conn, hearing.committee)
    hid = store.upsert_hearing(conn, hearing, committee_id)

    local_people = dict(person_ids)
    for appearance in hearing.people:
        pid = store.resolve_appearance(conn, appearance)
        if pid:
            store.upsert_appearance(conn, hid, pid, appearance.role)
            slug = appearance.person_slug or (appearance.person.slug if appearance.person else None)
            if slug:
                local_people[slug] = str(pid)

    local_topics = dict(topic_ids)
    for topic in hearing.topics:
        tid = store.upsert_topic(conn, topic)
        local_topics[topic.slug] = str(tid)
        conn.execute(
            """
            INSERT INTO hearing_topics (hearing_id, topic_id)
            VALUES (%s, %s)
            ON CONFLICT DO NOTHING
            """,
            (hid, tid),
        )

    document_ids: list[str] = []
    n_chunks = 0
    for document in hearing.documents:
        did = store.upsert_document(conn, hid, document)
        document_ids.append(str(did))
        pieces = chunk_text(document.content_text or "")
        if not pieces:
            continue
        vectors = embedder.embed([c.content for c in pieces])
        for chunk, vector in zip(pieces, vectors, strict=True):
            source_key = f"chunk:{document.source_key}:{chunk.index}"
            store.upsert_chunk(
                conn,
                document_id=did,
                hearing_id=hid,
                chunk=chunk,
                source_key=source_key,
                embedding=vector,
                metadata={"embedder": embedder.name, "doc_type": document.doc_type},
            )
            n_chunks += 1

    ids = {
        "hearing_id": str(hid),
        "committee_id": str(committee_id) if committee_id else None,
        "person_ids": local_people,
        "topic_ids": local_topics,
        "document_ids": document_ids,
    }
    return hid, n_chunks, ids
