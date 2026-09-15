#!/usr/bin/env python3
"""Render 003_seed.sql from data/fixtures/seed.json. Run from repo root."""

from __future__ import annotations

import json
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SEED = json.loads((ROOT / "data/fixtures/seed.json").read_text())
OUT = Path(__file__).with_name("003_seed.sql")


def lit(value: object) -> str:
    if value is None:
        return "NULL"
    if isinstance(value, (int, float)):
        return str(value)
    text = str(value).replace("'", "''")
    return f"'{text}'"


def main() -> None:
    lines: list[str] = [
        "-- Generated from data/fixtures/seed.json by infra/postgres/render_seed.py",
        "-- Do not edit by hand; re-run the renderer after changing the fixture.",
        "",
        "INSERT INTO committees (id, slug, name, chamber, kind, aph_url) VALUES",
    ]
    comm_rows = [
        f"    ({lit(c['id'])}, {lit(c['slug'])}, {lit(c['name'])}, {lit(c['chamber'])}, {lit(c['kind'])}, {lit(c.get('aph_url'))})"
        for c in SEED["committees"]
    ]
    lines.append(",\n".join(comm_rows) + "\nON CONFLICT (id) DO NOTHING;")
    lines.append("")

    lines.append(
        "INSERT INTO people (id, slug, name, role_title, party, portfolio, organisation, aph_url, bio) VALUES"
    )
    people_rows = [
        "    ({id}, {slug}, {name}, {role}, {party}, {port}, {org}, {url}, {bio})".format(
            id=lit(p["id"]),
            slug=lit(p["slug"]),
            name=lit(p["name"]),
            role=lit(p.get("role_title")),
            party=lit(p.get("party")),
            port=lit(p.get("portfolio")),
            org=lit(p.get("organisation")),
            url=lit(p.get("aph_url")),
            bio=lit(p.get("bio")),
        )
        for p in SEED["people"]
    ]
    lines.append(",\n".join(people_rows) + "\nON CONFLICT (id) DO NOTHING;")
    lines.append("")

    lines.append(
        "INSERT INTO hearings (id, slug, committee_id, title, hearing_type, portfolio, held_on, location, source, source_url, source_key, status, summary) VALUES"
    )
    hearing_rows = [
        "    ({id}, {slug}, {cid}, {title}, {ht}, {port}, {held}, {loc}, {src}, {url}, {key}, {st}, {sum})".format(
            id=lit(h["id"]),
            slug=lit(h["slug"]),
            cid=lit(h["committee_id"]),
            title=lit(h["title"]),
            ht=lit(h["hearing_type"]),
            port=lit(h.get("portfolio")),
            held=lit(h.get("held_on")),
            loc=lit(h.get("location")),
            src=lit(h["source"]),
            url=lit(h.get("source_url")),
            key=lit(h["source_key"]),
            st=lit(h.get("status") or "published"),
            sum=lit(h.get("summary")),
        )
        for h in SEED["hearings"]
    ]
    lines.append(",\n".join(hearing_rows) + "\nON CONFLICT (id) DO NOTHING;")
    lines.append("")

    lines.append("INSERT INTO hearing_people (hearing_id, person_id, role) VALUES")
    hp_rows: list[str] = []
    for h in SEED["hearings"]:
        for link in h.get("people", []):
            hp_rows.append(
                f"    ({lit(h['id'])}, {lit(link['person_id'])}, {lit(link['role'])})"
            )
    lines.append(",\n".join(hp_rows) + "\nON CONFLICT DO NOTHING;")
    lines.append("")

    lines.append("INSERT INTO topics (id, slug, name) VALUES")
    topic_rows = [
        f"    ({lit(t['id'])}, {lit(t['slug'])}, {lit(t['name'])})" for t in SEED["topics"]
    ]
    lines.append(",\n".join(topic_rows) + "\nON CONFLICT (id) DO NOTHING;")
    lines.append("")

    slug_to_topic = {t["slug"]: t["id"] for t in SEED["topics"]}
    lines.append("INSERT INTO hearing_topics (hearing_id, topic_id) VALUES")
    ht_rows: list[str] = []
    for h in SEED["hearings"]:
        for slug in h.get("topic_slugs", []):
            ht_rows.append(f"    ({lit(h['id'])}, {lit(slug_to_topic[slug])})")
    lines.append(",\n".join(ht_rows) + "\nON CONFLICT DO NOTHING;")
    lines.append("")

    lines.append(
        "INSERT INTO documents (id, hearing_id, title, doc_type, source_url, source_key, content_text, published_at, license_note) VALUES"
    )
    doc_rows = [
        "    ({id}, {hid}, {title}, {dt}, {url}, {key}, {body}, {pub}, {lic})".format(
            id=lit(d["id"]),
            hid=lit(d["hearing_id"]),
            title=lit(d["title"]),
            dt=lit(d["doc_type"]),
            url=lit(d.get("source_url")),
            key=lit(d["source_key"]),
            body=lit(d.get("content_text")),
            pub=lit(d.get("published_at")),
            lic=lit(d.get("license_note")),
        )
        for d in SEED["documents"]
    ]
    lines.append(",\n".join(doc_rows) + "\nON CONFLICT (id) DO NOTHING;")
    lines.append("")

    lines.append("-- Paragraph chunks (embeddings filled by ingest).")
    lines.append(
        "INSERT INTO chunks (id, document_id, hearing_id, chunk_index, content, token_count, speaker_name, source_key, metadata) VALUES"
    )
    chunk_rows: list[str] = []
    for doc in SEED["documents"]:
        paragraphs = [p.strip() for p in doc["content_text"].split("\n\n") if p.strip()]
        for idx, para in enumerate(paragraphs):
            speaker = None
            if ":" in para.split("\n", 1)[0]:
                speaker = para.split(":", 1)[0].strip()[:80]
            chunk_id = str(uuid.uuid5(uuid.UUID(doc["id"]), f"chunk-{idx}"))
            source_key = f"chunk:{doc['source_key']}:{idx}"
            chunk_rows.append(
                "    ({id}, {did}, {hid}, {idx}, {content}, {tokens}, {speaker}, {key}, '{{}}'::jsonb)".format(
                    id=lit(chunk_id),
                    did=lit(doc["id"]),
                    hid=lit(doc["hearing_id"]),
                    idx=idx,
                    content=lit(para),
                    tokens=max(1, len(para.split())),
                    speaker=lit(speaker),
                    key=lit(source_key),
                )
            )
    lines.append(",\n".join(chunk_rows) + "\nON CONFLICT (id) DO NOTHING;")
    lines.append("")

    lines.append("INSERT INTO boards (id, slug, title, description) VALUES")
    board_rows = [
        f"    ({lit(b['id'])}, {lit(b['slug'])}, {lit(b['title'])}, {lit(b.get('description'))})"
        for b in SEED["boards"]
    ]
    lines.append(",\n".join(board_rows) + "\nON CONFLICT (id) DO NOTHING;")
    lines.append("")

    lines.append("INSERT INTO pins (id, board_id, pin_type, target_id, note) VALUES")
    pin_rows = [
        f"    ({lit(p['id'])}, {lit(p['board_id'])}, {lit(p['pin_type'])}, {lit(p['target_id'])}, {lit(p.get('note'))})"
        for p in SEED["pins"]
    ]
    lines.append(",\n".join(pin_rows) + "\nON CONFLICT (id) DO NOTHING;")
    lines.append("")
    lines.append("INSERT INTO ingest_runs (source, started_at, finished_at, status, records_fetched, records_upserted, meta)")
    lines.append(
        "VALUES ('fixture', now(), now(), 'success', 3, 3, '{\"note\": \"loaded from 003_seed.sql\"}'::jsonb);"
    )
    lines.append("")

    OUT.write_text("\n".join(lines) + "\n")
    print(f"Wrote {OUT}")


if __name__ == "__main__":
    main()
