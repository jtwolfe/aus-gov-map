import { loadFixtures } from "./fixtures";
import { postgresAvailable, query } from "./db";
import type {
  Appearance,
  Board,
  Committee,
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

async function fromPostgres(): Promise<Catalog> {
  const [hearingRows, peopleRows, committeeRows, boardRows, pinRows, topicRows, docRows, appearRows] =
    await Promise.all([
      query<Record<string, unknown>>(`
        SELECT h.*, c.slug AS committee_slug, c.name AS committee_name,
               c.chamber AS committee_chamber, c.kind AS committee_kind,
               c.aph_url AS committee_aph_url
        FROM hearings h
        LEFT JOIN committees c ON c.id = h.committee_id
        ORDER BY h.held_on DESC NULLS LAST, h.title
      `),
      query<Record<string, unknown>>(`SELECT * FROM people ORDER BY name`),
      query<Record<string, unknown>>(`SELECT * FROM committees ORDER BY name`),
      query<Record<string, unknown>>(`SELECT * FROM boards ORDER BY title`),
      query<Record<string, unknown>>(`SELECT * FROM pins ORDER BY created_at`),
      query<Record<string, unknown>>(`
        SELECT ht.hearing_id, t.id, t.slug, t.name
        FROM hearing_topics ht
        JOIN topics t ON t.id = ht.topic_id
      `),
      query<Record<string, unknown>>(`SELECT * FROM documents ORDER BY published_at DESC NULLS LAST`),
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
  const docsByHearing = new Map<string, Document[]>();
  for (const row of docRows) {
    const hid = String(row.hearing_id);
    const list = docsByHearing.get(hid) ?? [];
    list.push(mapDocument(row));
    docsByHearing.set(hid, list);
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
      id,
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
      people: appearByHearing.get(id) ?? [],
      topics: topicsByHearing.get(id) ?? [],
      documents: docsByHearing.get(id) ?? [],
    };
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

function mapDocument(row: Record<string, unknown>): Document {
  return {
    id: String(row.id),
    hearingId: String(row.hearing_id),
    title: String(row.title),
    docType: String(row.doc_type),
    sourceUrl: (row.source_url as string | null) ?? null,
    sourceKey: String(row.source_key),
    contentText: (row.content_text as string | null) ?? null,
    publishedAt: row.published_at ? String(row.published_at).slice(0, 10) : null,
    licenseNote: (row.license_note as string | null) ?? null,
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

export async function loadCatalog(): Promise<Catalog> {
  if (await postgresAvailable()) {
    try {
      const catalog = await fromPostgres();
      if (catalog.hearings.length > 0 || catalog.people.length > 0) {
        return catalog;
      }
    } catch {
      /* fall through */
    }
  }
  return fromFixtures();
}

export async function getHearing(slug: string): Promise<{ hearing: Hearing; source: DataSource } | null> {
  const catalog = await loadCatalog();
  const hearing = catalog.hearings.find((h) => h.slug === slug);
  return hearing ? { hearing, source: catalog.source } : null;
}

export async function getPerson(slug: string): Promise<{
  person: Person;
  appearances: Array<{ hearing: Hearing; role: Appearance["role"] }>;
  source: DataSource;
} | null> {
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
  return { person, appearances, source: catalog.source };
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
