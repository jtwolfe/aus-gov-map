import { cache } from "react";
import { loadFixtures } from "./fixtures";
import { postgresAvailable, query, queryOne } from "./db";
import { isLiveSourceKey } from "./source";
import type {
  Appearance,
  Board,
  Chunk,
  CoAttendance,
  Committee,
  CoverageStats,
  DataSource,
  Document,
  Hearing,
  Person,
  Pin,
  Topic,
} from "./types";

export type Catalog = {
  source: DataSource;
  hearings: Hearing[];
  people: Person[];
  committees: Committee[];
  boards: Board[];
  pins: Pin[];
};

const HEARING_COLS = `
  h.id, h.slug, h.title, h.hearing_type, h.portfolio, h.held_on, h.location,
  h.source, h.source_url, h.source_key, h.status, h.summary,
  c.id AS committee_id, c.slug AS committee_slug, c.name AS committee_name,
  c.chamber AS committee_chamber, c.kind AS committee_kind,
  c.aph_url AS committee_aph_url
`;

const HEARING_SELECT = `
  SELECT ${HEARING_COLS}
  FROM hearings h
  LEFT JOIN committees c ON c.id = h.committee_id
`;

function mapPerson(row: Record<string, unknown>): Person {
  return {
    id: String(row.id),
    slug: String(row.slug),
    name: String(row.name),
    roleTitle: (row.role_title as string | null) ?? null,
    party: (row.party as string | null) ?? null,
    portfolio: (row.portfolio as string | null) ?? null,
    organisation: (row.organisation as string | null) ?? null,
    aphUrl: (row.aph_url as string | null) ?? null,
    bio: (row.bio as string | null) ?? null,
  };
}

function mapCommittee(row: Record<string, unknown>): Committee {
  return {
    id: String(row.id),
    slug: String(row.slug),
    name: String(row.name),
    chamber: String(row.chamber),
    kind: String(row.kind),
    aphUrl: (row.aph_url as string | null) ?? null,
  };
}

function mapDocument(row: Record<string, unknown>, includeText: boolean): Document {
  return {
    id: String(row.id),
    hearingId: String(row.hearing_id),
    title: String(row.title),
    docType: String(row.doc_type),
    sourceUrl: (row.source_url as string | null) ?? null,
    sourceKey: String(row.source_key),
    contentText: includeText ? ((row.content_text as string | null) ?? null) : null,
    publishedAt: row.published_at ? String(row.published_at).slice(0, 10) : null,
    licenseNote: (row.license_note as string | null) ?? null,
  };
}

function mapChunk(row: Record<string, unknown>): Chunk {
  return {
    id: String(row.id),
    documentId: String(row.document_id),
    hearingId: String(row.hearing_id),
    chunkIndex: Number(row.chunk_index),
    content: String(row.content),
    speakerName: (row.speaker_name as string | null) ?? null,
    sourceKey: String(row.source_key),
  };
}

function mapHearingRow(
  row: Record<string, unknown>,
  extras: {
    people?: Appearance[];
    topics?: Topic[];
    documents?: Document[];
    chunks?: Chunk[];
  } = {},
): Hearing {
  const committee: Committee | null = row.committee_id
    ? {
        id: String(row.committee_id),
        slug: String(row.committee_slug),
        name: String(row.committee_name),
        chamber: String(row.committee_chamber ?? "Senate"),
        kind: String(row.committee_kind ?? "legislation"),
        aphUrl: (row.committee_aph_url as string | null) ?? null,
      }
    : null;
  return {
    id: String(row.id),
    slug: String(row.slug),
    title: String(row.title),
    hearingType: row.hearing_type as Hearing["hearingType"],
    portfolio: (row.portfolio as string | null) ?? null,
    heldOn: row.held_on ? String(row.held_on).slice(0, 10) : null,
    location: (row.location as string | null) ?? null,
    source: String(row.source),
    sourceUrl: (row.source_url as string | null) ?? null,
    sourceKey: String(row.source_key),
    status: String(row.status),
    summary: (row.summary as string | null) ?? null,
    committee,
    people: extras.people ?? [],
    topics: extras.topics ?? [],
    documents: extras.documents ?? [],
    chunks: extras.chunks,
  };
}

async function fromPostgres(): Promise<Catalog> {
  const [hearingRows, peopleRows, committeeRows, boardRows, pinRows, topicRows, appearRows] =
    await Promise.all([
      query<Record<string, unknown>>(`${HEARING_SELECT} ORDER BY h.held_on DESC NULLS LAST, h.title`),
      query<Record<string, unknown>>(`SELECT * FROM people ORDER BY name`),
      query<Record<string, unknown>>(`SELECT * FROM committees ORDER BY name`),
      query<Record<string, unknown>>(`SELECT * FROM boards ORDER BY created_at DESC, title`),
      query<Record<string, unknown>>(`SELECT * FROM pins ORDER BY created_at`),
      query<Record<string, unknown>>(`
        SELECT ht.hearing_id, t.id, t.slug, t.name
        FROM hearing_topics ht
        JOIN topics t ON t.id = ht.topic_id
      `),
      query<Record<string, unknown>>(`
        SELECT hp.hearing_id, hp.role, p.*
        FROM hearing_people hp
        JOIN people p ON p.id = hp.person_id
      `),
    ]);

  const people: Person[] = peopleRows.map(mapPerson);
  const peopleById = new Map(people.map((p) => [p.id, p]));
  const committees: Committee[] = committeeRows.map(mapCommittee);
  const topicsByHearing = new Map<string, Topic[]>();
  for (const row of topicRows) {
    const hid = String(row.hearing_id);
    const list = topicsByHearing.get(hid) ?? [];
    list.push({ id: String(row.id), slug: String(row.slug), name: String(row.name) });
    topicsByHearing.set(hid, list);
  }
  const appearByHearing = new Map<string, Appearance[]>();
  for (const row of appearRows) {
    const hid = String(row.hearing_id);
    const person = peopleById.get(String(row.id));
    if (!person) continue;
    const list = appearByHearing.get(hid) ?? [];
    list.push({ person, role: row.role as Appearance["role"] });
    appearByHearing.set(hid, list);
  }

  const hearings: Hearing[] = hearingRows.map((row) => {
    const id = String(row.id);
    return mapHearingRow(row, {
      people: appearByHearing.get(id) ?? [],
      topics: topicsByHearing.get(id) ?? [],
    });
  });

  return {
    source: "postgres",
    hearings,
    people,
    committees,
    boards: boardRows.map((b) => ({
      id: String(b.id),
      slug: String(b.slug),
      title: String(b.title),
      description: (b.description as string | null) ?? null,
    })),
    pins: pinRows.map((p) => ({
      id: String(p.id),
      boardId: String(p.board_id),
      pinType: String(p.pin_type),
      targetId: String(p.target_id),
      note: (p.note as string | null) ?? null,
    })),
  };
}

function fromFixtures(): Catalog {
  const seed = loadFixtures();
  return {
    source: "fixture",
    hearings: seed.hearings,
    people: seed.people,
    committees: seed.committees,
    boards: seed.boards,
    pins: seed.pins,
  };
}

export const loadCatalog = cache(async function loadCatalog(): Promise<Catalog> {
  if (await postgresAvailable()) {
    return fromPostgres();
  }
  return fromFixtures();
});

export const getCoverage = cache(async function getCoverage(): Promise<CoverageStats> {
  if (await postgresAvailable()) {
    const row = await queryOne<Record<string, unknown>>(`
      SELECT
        (SELECT COUNT(*)::int FROM hearings) AS hearings,
        (SELECT COUNT(*)::int FROM people) AS people,
        (SELECT COUNT(*)::int FROM chunks) AS chunks,
        (SELECT COUNT(*)::int FROM hearings WHERE source_key LIKE 'hansard:%') AS live_hearings,
        (SELECT COUNT(*)::int FROM hearings WHERE source_key NOT LIKE 'hansard:%') AS sample_hearings,
        (SELECT COUNT(*)::int FROM committees) AS committees
    `);
    return {
      source: "postgres",
      hearings: Number(row?.hearings ?? 0),
      people: Number(row?.people ?? 0),
      chunks: Number(row?.chunks ?? 0),
      liveHearings: Number(row?.live_hearings ?? 0),
      sampleHearings: Number(row?.sample_hearings ?? 0),
      committees: Number(row?.committees ?? 0),
    };
  }
  const seed = loadFixtures();
  const liveHearings = seed.hearings.filter((h) => isLiveSourceKey(h.sourceKey)).length;
  return {
    source: "fixture",
    hearings: seed.hearings.length,
    people: seed.people.length,
    chunks: seed.chunks.length,
    liveHearings,
    sampleHearings: seed.hearings.length - liveHearings,
    committees: seed.committees.length,
  };
});

export async function getHearing(slug: string): Promise<{
  hearing: Hearing;
  source: DataSource;
} | null> {
  if (await postgresAvailable()) {
    const row = await queryOne<Record<string, unknown>>(`${HEARING_SELECT} WHERE h.slug = $1`, [slug]);
    if (!row) return null;
    const id = String(row.id);
    const [appearRows, topicRows, docRows, chunkRows] = await Promise.all([
      query<Record<string, unknown>>(
        `
        SELECT hp.role, p.*
        FROM hearing_people hp
        JOIN people p ON p.id = hp.person_id
        WHERE hp.hearing_id = $1
        ORDER BY p.name
        `,
        [id],
      ),
      query<Record<string, unknown>>(
        `
        SELECT t.id, t.slug, t.name
        FROM hearing_topics ht
        JOIN topics t ON t.id = ht.topic_id
        WHERE ht.hearing_id = $1
        `,
        [id],
      ),
      query<Record<string, unknown>>(
        `
        SELECT id, hearing_id, title, doc_type, source_url, source_key,
               CASE WHEN length(coalesce(content_text, '')) > 6000 THEN NULL ELSE content_text END AS content_text,
               published_at, license_note
        FROM documents
        WHERE hearing_id = $1
        ORDER BY published_at DESC NULLS LAST
        `,
        [id],
      ),
      query<Record<string, unknown>>(
        `
        SELECT id, document_id, hearing_id, chunk_index, content, speaker_name, source_key
        FROM chunks
        WHERE hearing_id = $1
        ORDER BY chunk_index
        LIMIT 48
        `,
        [id],
      ),
    ]);
    return {
      source: "postgres",
      hearing: mapHearingRow(row, {
        people: appearRows.map((r) => ({
          person: mapPerson(r),
          role: r.role as Appearance["role"],
        })),
        topics: topicRows.map((t) => ({
          id: String(t.id),
          slug: String(t.slug),
          name: String(t.name),
        })),
        documents: docRows.map((d) => mapDocument(d, true)),
        chunks: chunkRows.map(mapChunk),
      }),
    };
  }

  const catalog = await loadCatalog();
  const hearing = catalog.hearings.find((h) => h.slug === slug);
  if (!hearing) return null;
  if (!hearing.chunks) {
    const seed = loadFixtures();
    hearing.chunks = seed.chunks.filter((c) => c.hearingId === hearing.id);
  }
  return { hearing, source: catalog.source };
}

export async function getPerson(slug: string): Promise<{
  person: Person;
  appearances: Array<{ hearing: Hearing; role: Appearance["role"] }>;
  satWith: CoAttendance[];
  source: DataSource;
} | null> {
  if (await postgresAvailable()) {
    const personRow = await queryOne<Record<string, unknown>>(
      `SELECT * FROM people WHERE slug = $1`,
      [slug],
    );
    if (!personRow) return null;
    const person = mapPerson(personRow);
    const appearRows = await query<Record<string, unknown>>(
      `
      SELECT ${HEARING_COLS}, hp.role
      FROM hearings h
      LEFT JOIN committees c ON c.id = h.committee_id
      JOIN hearing_people hp ON hp.hearing_id = h.id
      WHERE hp.person_id = $1
      ORDER BY h.held_on DESC NULLS LAST, h.title
      `,
      [person.id],
    );
    const appearances = appearRows.map((row) => ({
      hearing: mapHearingRow(row),
      role: row.role as Appearance["role"],
    }));
    const satRows = await query<Record<string, unknown>>(
      `
      SELECT p.slug, p.name, COUNT(*)::int AS count, MAX(h.held_on) AS last_held_on
      FROM hearing_people mine
      JOIN hearing_people other ON other.hearing_id = mine.hearing_id AND other.person_id <> mine.person_id
      JOIN people p ON p.id = other.person_id
      JOIN hearings h ON h.id = mine.hearing_id
      WHERE mine.person_id = $1
      GROUP BY p.id, p.slug, p.name
      ORDER BY count DESC, last_held_on DESC NULLS LAST, p.name
      LIMIT 40
      `,
      [person.id],
    );
    return {
      person,
      appearances,
      satWith: satRows.map((r) => ({
        slug: String(r.slug),
        name: String(r.name),
        count: Number(r.count),
        lastHeldOn: r.last_held_on ? String(r.last_held_on).slice(0, 10) : null,
      })),
      source: "postgres",
    };
  }

  const catalog = await loadCatalog();
  const person = catalog.people.find((p) => p.slug === slug);
  if (!person) return null;
  const appearances = catalog.hearings
    .flatMap((hearing) =>
      hearing.people
        .filter((a) => a.person.id === person.id)
        .map((a) => ({ hearing, role: a.role })),
    )
    .sort((a, b) => (b.hearing.heldOn ?? "").localeCompare(a.hearing.heldOn ?? ""));
  const sat = new Map<string, CoAttendance>();
  for (const { hearing } of appearances) {
    for (const other of hearing.people) {
      if (other.person.id === person.id) continue;
      const current = sat.get(other.person.id);
      if (current) {
        current.count += 1;
        if ((hearing.heldOn ?? "") > (current.lastHeldOn ?? "")) {
          current.lastHeldOn = hearing.heldOn;
        }
      } else {
        sat.set(other.person.id, {
          slug: other.person.slug,
          name: other.person.name,
          count: 1,
          lastHeldOn: hearing.heldOn,
        });
      }
    }
  }
  return {
    person,
    appearances,
    satWith: [...sat.values()].sort((a, b) => b.count - a.count),
    source: catalog.source,
  };
}

export async function getBoard(slug: string) {
  const catalog = await loadCatalog();
  const board = catalog.boards.find((b) => b.slug === slug);
  if (!board) return null;
  const pins = catalog.pins.filter((p) => p.boardId === board.id);
  return { board, pins, catalog };
}

export function relatedPeople(hearing: Hearing, catalog: Catalog): Person[] {
  const ids = new Set(hearing.people.map((a) => a.person.id));
  const counts = new Map<string, number>();
  for (const other of catalog.hearings) {
    if (other.id === hearing.id) continue;
    const overlap = other.people.filter((a) => ids.has(a.person.id));
    if (!overlap.length) continue;
    for (const a of other.people) {
      if (!ids.has(a.person.id)) {
        counts.set(a.person.id, (counts.get(a.person.id) ?? 0) + 1);
      }
    }
  }
  return catalog.people
    .filter((p) => counts.has(p.id))
    .sort((a, b) => (counts.get(b.id) ?? 0) - (counts.get(a.id) ?? 0));
}

export async function resolvePinTarget(
  pin: Pin,
  catalog: Catalog,
): Promise<{ href: string; label: string; excerpt?: string }> {
  if (pin.pinType === "hearing") {
    const hearing = catalog.hearings.find((h) => h.id === pin.targetId);
    if (hearing) return { href: `/hearings/${hearing.slug}`, label: hearing.title };
  }
  if (pin.pinType === "person") {
    const person = catalog.people.find((p) => p.id === pin.targetId);
    if (person) return { href: `/people/${person.slug}`, label: person.name };
  }
  if (pin.pinType === "chunk" && (await postgresAvailable())) {
    const row = await queryOne<Record<string, unknown>>(
      `
      SELECT ch.content, ch.speaker_name, h.slug, h.title
      FROM chunks ch
      JOIN hearings h ON h.id = ch.hearing_id
      WHERE ch.id = $1
      `,
      [pin.targetId],
    );
    if (row) {
      return {
        href: `/hearings/${row.slug}#chunk-${pin.targetId}`,
        label: String(row.title),
        excerpt: String(row.content).slice(0, 220),
      };
    }
  }
  if (pin.pinType === "chunk") {
    const seed = loadFixtures();
    const chunk = seed.chunks.find((c) => c.id === pin.targetId);
    const hearing = seed.hearings.find((h) => h.id === chunk?.hearingId);
    if (chunk && hearing) {
      return {
        href: `/hearings/${hearing.slug}#excerpt`,
        label: hearing.title,
        excerpt: chunk.content.slice(0, 220),
      };
    }
  }
  return { href: "/boards", label: pin.targetId };
}
