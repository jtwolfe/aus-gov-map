from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

from aus_gov_ingest.chunking import chunk_text
from aus_gov_ingest.config import settings
from aus_gov_ingest.db.neo4j_graph import Neo4jStore
from aus_gov_ingest.db.postgres import PostgresStore
from aus_gov_ingest.embeddings import get_embedder
from aus_gov_ingest.funded_by import links_from_matches, match_funded_by
from aus_gov_ingest.instruments import propose_instruments
from aus_gov_ingest.models import HearingIn, InstrumentIn, SourceBatch
from aus_gov_ingest.qon_hearing import apply_hearing_match, match_qon_to_hearing
from aus_gov_ingest.segments import annotate_chunks
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


def _primary_count(source_name: str, batch: SourceBatch) -> int:
    if source_name == "handbook":
        return len(batch.handbook_entries) or len(batch.people)
    if source_name == "qon":
        return len(batch.questions)
    if source_name == "anao":
        return len(batch.scrutiny_items)
    if source_name in {"instrument_propose", "budget_measure", "austender", "legislation"}:
        return len(batch.instruments)
    if source_name == "theyvoteforyou":
        return len(batch.divisions)
    if source_name == "judgments":
        return len(batch.scrutiny_items)
    if source_name == "agencies":
        return len(batch.agencies)
    if source_name == "aps_leaders":
        return len(batch.person_roles) or len(batch.people)
    return len(batch.hearings)


def _dry_run_meta(batch: SourceBatch, *, embedder_name: str) -> dict[str, Any]:
    n_chunks = 0
    n_segments = 0
    speaker_chunks = 0
    for hearing in batch.hearings:
        n_segments += len(hearing.segments)
        for document in hearing.documents:
            pieces = annotate_chunks(chunk_text(document.content_text or ""), hearing.segments)
            n_chunks += len(pieces)
            speaker_chunks += sum(1 for c in pieces if c.speaker_name)
    return {
        "dry_run": True,
        "embedder": embedder_name,
        "titles": [h.title for h in batch.hearings],
        "held_on": [str(h.held_on) if h.held_on else None for h in batch.hearings],
        "with_transcript": sum(1 for h in batch.hearings if h.documents),
        "people_sample": [p.name for p in batch.people[:12]],
        "handbook_entries": len(batch.handbook_entries),
        "handbook_roles": sum(len(e.roles) for e in batch.handbook_entries),
        "handbook_tenure": sum(len(e.tenure) for e in batch.handbook_entries),
        "agencies": len(batch.agencies),
        "questions": len(batch.questions),
        "instruments": len(batch.instruments),
        "scrutiny_items": len(batch.scrutiny_items),
        "outcomes": len(batch.outcomes),
        "divisions": len(batch.divisions),
        "named_votes": sum(len(d.votes) for d in batch.divisions),
        "instrument_links": len(batch.instrument_links),
        "qons_with_hearing_key": sum(1 for q in batch.questions if q.hearing_source_key),
        "funded_by_links": sum(1 for lnk in batch.instrument_links if lnk.link_kind == "funded_by"),
        "person_roles": len(batch.person_roles),
        "occupancies": len(batch.person_roles),
        "role_types": sorted({pr.role_type for pr in batch.person_roles}),
        "leaders_sample": [
            f"{pr.person.name} · {pr.role_title}" for pr in batch.person_roles[:12]
        ],
        "segments": n_segments,
        "estimated_chunks": n_chunks,
        "chunks_with_speaker": speaker_chunks,
        **batch.meta,
    }


def run_ingest(
    source_name: str,
    *,
    limit: int = 0,
    incremental: bool = False,
    write_graph: bool = True,
    database_url: str | None = None,
    dry_run: bool = False,
    source_path: str | None = None,
    propose_instruments_flag: bool = False,
) -> RunResult:
    source = get_source(source_name, path=source_path)
    embedder = get_embedder()
    if dry_run:
        batch = source.fetch(limit=limit, incremental_keys=None)
        if propose_instruments_flag:
            _attach_proposed_instruments(batch)
        _attach_in_memory_links(batch)
        return RunResult(
            source=source_name,
            fetched=_primary_count(source_name, batch),
            upserted=0,
            chunks=sum(len(h.documents) for h in batch.hearings),
            status="dry_run",
            meta=_dry_run_meta(batch, embedder_name=embedder.name),
        )

    store = PostgresStore(dsn=database_url or settings.database_url)

    known: set[str] | None = None
    if incremental:
        if source_name in {"estimates", "estimates_schedule", "aph_transcript_file"}:
            known = store.existing_source_keys(source="estimates")
        elif source_name == "handbook":
            known = store.existing_handbook_keys()
        elif source_name == "qon":
            known = store.existing_qon_keys()
        elif source_name == "anao":
            known = store.existing_scrutiny_keys(item_type="anao")
        elif source_name in {"budget_measure", "austender", "legislation"}:
            known = store.existing_instrument_keys(source=source_name)
        elif source_name == "theyvoteforyou":
            known = store.existing_division_keys()
        elif source_name == "judgments":
            known = store.existing_scrutiny_keys(item_type="judgment")
        elif source_name == "aps_leaders":
            known = store.existing_person_role_keys()

    run_id = store.start_run(
        source_name,
        meta={
            "limit": limit,
            "incremental": incremental,
            "embedder": embedder.name,
            "propose_instruments": propose_instruments_flag,
        },
    )
    result = RunResult(source=source_name, meta={"run_id": str(run_id), "embedder": embedder.name})

    try:
        batch = source.fetch(limit=limit, incremental_keys=known)
        if propose_instruments_flag:
            _attach_proposed_instruments(batch)
        _attach_in_memory_links(batch)
        result.fetched = _primary_count(source_name, batch)
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


def _attach_proposed_instruments(batch: SourceBatch) -> None:
    extra = []
    for hearing in batch.hearings:
        for document in hearing.documents:
            pieces = annotate_chunks(
                chunk_text(document.content_text or ""), hearing.segments
            )
            extra.extend(
                propose_instruments(
                    pieces,
                    hearing_source_key=hearing.source_key,
                    document_source_key=document.source_key,
                )
            )
    batch.instruments.extend(extra)


def _attach_in_memory_links(batch: SourceBatch) -> None:
    """Dry-run / same-batch links that do not need Postgres."""
    contracts = [i for i in batch.instruments if i.kind in {"contract", "grant"}]
    funders = [i for i in batch.instruments if i.kind in {"measure", "program"}]
    extra_funders: list[InstrumentIn] = []
    if contracts and not funders:
        extra_funders = _load_budget_fixture_instruments()
    extra_contracts: list[InstrumentIn] = []
    if funders and not contracts:
        extra_contracts = _load_austender_fixture_instruments()
    matches = match_funded_by(contracts or extra_contracts, funders or extra_funders)
    existing = {
        (lnk.instrument_source_key, lnk.other_instrument_source_key, lnk.link_kind)
        for lnk in batch.instrument_links
    }
    for link in links_from_matches(matches):
        key = (link.instrument_source_key, link.other_instrument_source_key, link.link_kind)
        if key not in existing:
            batch.instrument_links.append(link)
            existing.add(key)


def _load_budget_fixture_instruments() -> list[InstrumentIn]:
    try:
        from aus_gov_ingest.sources.budget_measure import (
            default_budget_dir,
            instrument_from_budget_row,
            load_budget_path,
        )

        records, _ = load_budget_path(default_budget_dir())
        return [item for item in (instrument_from_budget_row(r) for r in records) if item]
    except Exception:
        return []


def _load_austender_fixture_instruments() -> list[InstrumentIn]:
    try:
        from aus_gov_ingest.sources.austender import (
            default_austender_dir,
            instrument_from_cn,
            load_austender_path,
        )

        records, _ = load_austender_path(default_austender_dir())
        return [item for item in (instrument_from_cn(r) for r in records) if item]
    except Exception:
        return []


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
        for agency in batch.agencies:
            store.upsert_agency(conn, agency)
            upserted += 1

        for occupancy in batch.person_roles:
            store.upsert_person_role_occupancy(conn, occupancy)
            upserted += 1

        topic_ids: dict[str, str] = {}
        for topic in batch.topics:
            topic_ids[topic.slug] = str(store.upsert_topic(conn, topic))
        person_ids: dict[str, str] = {}
        for person in batch.people:
            person_ids[person.slug] = str(store.upsert_person(conn, person))
        for entry in batch.handbook_entries:
            pid = store.upsert_person(conn, entry.person)
            person_ids[entry.person.slug] = str(pid)
            store.upsert_handbook_entry(conn, entry, pid)
            upserted += 1
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

        hearing_ids: dict[str, UUID] = {}
        for hearing in batch.hearings:
            hid, n_chunks, ids = _persist_hearing(
                store, conn, hearing, embedder, topic_ids, person_ids
            )
            hearing_ids[hearing.source_key] = hid
            upserted += 1
            chunks_written += n_chunks
            if graph:
                try:
                    graph.upsert_hearing(hearing, ids)
                except Exception:
                    pass

        hearing_candidates = []
        if batch.questions:
            hearing_candidates = store.list_hearing_candidates(conn)
        matched_hearings = 0
        for question in batch.questions:
            hid = None
            match = match_qon_to_hearing(question, hearing_candidates)
            question = apply_hearing_match(question, match)
            if question.hearing_source_key:
                hid = hearing_ids.get(question.hearing_source_key)
                if hid is None:
                    hid = store.lookup_hearing_id(conn, question.hearing_source_key)
            if hid is None and match and match.hearing_id:
                hid = UUID(match.hearing_id)
            if hid:
                matched_hearings += 1
            store.upsert_question(conn, question, hearing_id=hid)
            upserted += 1
        batch.meta["qons_hearing_attached"] = matched_hearings

        instrument_ids: dict[str, UUID] = {}
        for instrument in batch.instruments:
            hid = None
            if instrument.hearing_source_key:
                hid = hearing_ids.get(instrument.hearing_source_key)
            iid = store.upsert_instrument(conn, instrument, hearing_id=hid)
            instrument_ids[instrument.source_key] = iid
            upserted += 1

        scrutiny_ids: dict[str, UUID] = {}
        for item in batch.scrutiny_items:
            sid = store.upsert_scrutiny_item(conn, item)
            scrutiny_ids[item.source_key] = sid
            upserted += 1

        for outcome in batch.outcomes:
            iid = (
                instrument_ids.get(outcome.instrument_source_key)
                if outcome.instrument_source_key
                else None
            )
            sid = (
                scrutiny_ids.get(outcome.scrutiny_source_key)
                if outcome.scrutiny_source_key
                else None
            )
            store.upsert_outcome(
                conn, outcome, instrument_id=iid, scrutiny_item_id=sid
            )
            upserted += 1
            if iid and sid and batch.source != "judgments":
                store.link_tested_in(
                    conn,
                    instrument_id=iid,
                    scrutiny_item_id=sid,
                    source=outcome.source or batch.source,
                )

        if batch.instruments:
            db_funders = store.list_funding_instruments(conn)
            db_contracts = store.list_contract_instruments(conn)
            batch_contracts = [i for i in batch.instruments if i.kind in {"contract", "grant"}]
            batch_funders = [i for i in batch.instruments if i.kind in {"measure", "program"}]
            for match in match_funded_by(
                batch_contracts or db_contracts,
                batch_funders or db_funders,
            ):
                already = any(
                    lnk.link_kind == "funded_by"
                    and lnk.instrument_source_key == match.contract_source_key
                    and lnk.other_instrument_source_key == match.funder_source_key
                    for lnk in batch.instrument_links
                )
                if not already:
                    batch.instrument_links.extend(links_from_matches([match]))

        for extra in batch.instrument_links:
            iid = instrument_ids.get(extra.instrument_source_key)
            if not iid and extra.instrument_source_key:
                iid = store.lookup_instrument_id(conn, extra.instrument_source_key)
            other_id = None
            if extra.other_instrument_source_key:
                other_id = instrument_ids.get(extra.other_instrument_source_key)
                if not other_id:
                    other_id = store.lookup_instrument_id(conn, extra.other_instrument_source_key)
            if iid and other_id and extra.link_kind == "funded_by":
                store.link_funded_by(
                    conn,
                    instrument_id=iid,
                    other_instrument_id=other_id,
                    source=extra.source or batch.source,
                    notes=extra.notes,
                    confidence=extra.confidence,
                )
                upserted += 1
                continue
            sid = (
                scrutiny_ids.get(extra.target_source_key)
                if extra.target_source_key
                else None
            )
            if not sid and extra.target_source_key:
                sid = store.lookup_scrutiny_id(conn, extra.target_source_key)
            if iid and sid:
                store.link_instrument(
                    conn,
                    instrument_id=iid,
                    scrutiny_item_id=sid,
                    link_kind=extra.link_kind,
                    source=extra.source or batch.source,
                    notes=extra.notes,
                )
                upserted += 1

        for division in batch.divisions:
            iid = None
            if division.instrument_source_key:
                iid = instrument_ids.get(division.instrument_source_key)
                if not iid:
                    iid = store.lookup_instrument_id(conn, division.instrument_source_key)
                    if not iid:
                        iid = store.lookup_instrument_id_by_title(conn, division.title)
            store.upsert_division(conn, division, instrument_id=iid)
            upserted += 1

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
    first_doc = None
    for document in hearing.documents:
        did = store.upsert_document(conn, hid, document)
        document_ids.append(str(did))
        if first_doc is None:
            first_doc = did
        pieces = annotate_chunks(
            chunk_text(document.content_text or ""), hearing.segments
        )
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
                metadata={
                    "embedder": embedder.name,
                    "doc_type": document.doc_type,
                    "portfolio": chunk.portfolio,
                    "agency": chunk.agency,
                    "taken_on_notice": chunk.taken_on_notice,
                },
            )
            n_chunks += 1

    for index, segment in enumerate(hearing.segments):
        store.upsert_hearing_segment(
            conn,
            hearing_id=hid,
            document_id=first_doc,
            hearing_source_key=hearing.source_key,
            index=index,
            segment=segment,
        )

    ids = {
        "hearing_id": str(hid),
        "committee_id": str(committee_id) if committee_id else None,
        "person_ids": local_people,
        "topic_ids": local_topics,
        "document_ids": document_ids,
    }
    return hid, n_chunks, ids
