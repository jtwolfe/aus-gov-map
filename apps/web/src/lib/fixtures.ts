import { readFileSync } from "node:fs";
import { join } from "node:path";
import type {
  Appearance,
  Board,
  Chunk,
  Committee,
  Document,
  Hearing,
  Person,
  Pin,
  Topic,
} from "./types";

type RawSeed = {
  license_note?: string;
  committees: Array<{
    id: string;
    slug: string;
    name: string;
    chamber: string;
    kind: string;
    aph_url: string | null;
  }>;
  people: Array<{
    id: string;
    slug: string;
    name: string;
    role_title: string | null;
    party: string | null;
    portfolio: string | null;
    organisation: string | null;
    aph_url: string | null;
    bio: string | null;
  }>;
  hearings: Array<{
    id: string;
    slug: string;
    committee_id: string;
    title: string;
    hearing_type: Hearing["hearingType"];
    portfolio: string | null;
    held_on: string | null;
    location: string | null;
    source: string;
    source_url: string | null;
    source_key: string;
    status: string;
    summary: string | null;
    topic_slugs: string[];
    people: Array<{ person_id: string; role: Appearance["role"] }>;
  }>;
  topics: Array<{ id: string; slug: string; name: string }>;
  documents: Array<{
    id: string;
    hearing_id: string;
    title: string;
    doc_type: string;
    source_url: string | null;
    source_key: string;
    content_text: string | null;
    published_at: string | null;
    license_note: string | null;
  }>;
  boards: Array<{
    id: string;
    slug: string;
    title: string;
    description: string | null;
  }>;
  pins: Array<{
    id: string;
    board_id: string;
    pin_type: string;
    target_id: string;
    note: string | null;
  }>;
};

function fixturePath(): string {
  const cwd = process.cwd();
  const candidates = [
    process.env.AUS_GOV_FIXTURE_PATH,
    join(cwd, "data/fixtures/seed.json"),
    join(cwd, "../../data/fixtures/seed.json"),
    join(cwd, "../../../data/fixtures/seed.json"),
  ].filter((p): p is string => Boolean(p));
  for (const candidate of candidates) {
    try {
      readFileSync(candidate, "utf8");
      return candidate;
    } catch {
      /* try next */
    }
  }
  throw new Error(
    "Could not find data/fixtures/seed.json. Set AUS_GOV_FIXTURE_PATH or run from the repo.",
  );
}

let cached: ReturnType<typeof hydrate> | null = null;

function committeeOf(raw: RawSeed["committees"][number]): Committee {
  return {
    id: raw.id,
    slug: raw.slug,
    name: raw.name,
    chamber: raw.chamber,
    kind: raw.kind,
    aphUrl: raw.aph_url,
  };
}

function personOf(raw: RawSeed["people"][number]): Person {
  return {
    id: raw.id,
    slug: raw.slug,
    name: raw.name,
    roleTitle: raw.role_title,
    party: raw.party,
    portfolio: raw.portfolio,
    organisation: raw.organisation,
    aphUrl: raw.aph_url,
    bio: raw.bio,
  };
}

function hydrate(seed: RawSeed) {
  const committees = new Map(seed.committees.map((c) => [c.id, committeeOf(c)]));
  const people = new Map(seed.people.map((p) => [p.id, personOf(p)]));
  const topics = new Map(
    seed.topics.map((t) => [t.slug, { id: t.id, slug: t.slug, name: t.name } satisfies Topic]),
  );
  const documents: Document[] = seed.documents.map((d) => ({
    id: d.id,
    hearingId: d.hearing_id,
    title: d.title,
    docType: d.doc_type,
    sourceUrl: d.source_url,
    sourceKey: d.source_key,
    contentText: d.content_text,
    publishedAt: d.published_at,
    licenseNote: d.license_note,
  }));
  const chunks: Chunk[] = [];
  for (const doc of documents) {
    const paras = (doc.contentText ?? "").split(/\n\s*\n/).filter((p) => p.trim());
    paras.forEach((para, idx) => {
      const speaker = para.includes(":") ? para.split(":", 1)[0].trim().slice(0, 80) : null;
      chunks.push({
        id: `${doc.id}:${idx}`,
        documentId: doc.id,
        hearingId: doc.hearingId,
        chunkIndex: idx,
        content: para.trim(),
        speakerName: speaker,
        sourceKey: `chunk:${doc.sourceKey}:${idx}`,
      });
    });
  }
  const hearings: Hearing[] = seed.hearings.map((h) => ({
    id: h.id,
    slug: h.slug,
    title: h.title,
    hearingType: h.hearing_type,
    portfolio: h.portfolio,
    heldOn: h.held_on,
    location: h.location,
    source: h.source,
    sourceUrl: h.source_url,
    sourceKey: h.source_key,
    status: h.status,
    summary: h.summary,
    committee: committees.get(h.committee_id) ?? null,
    people: h.people
      .map((link) => {
        const person = people.get(link.person_id);
        if (!person) return null;
        return { person, role: link.role } satisfies Appearance;
      })
      .filter((x): x is Appearance => x !== null),
    topics: h.topic_slugs
      .map((slug) => topics.get(slug))
      .filter((t): t is Topic => Boolean(t)),
    documents: documents.filter((d) => d.hearingId === h.id),
  }));
  const boards: Board[] = seed.boards.map((b) => ({
    id: b.id,
    slug: b.slug,
    title: b.title,
    description: b.description,
  }));
  const pins: Pin[] = seed.pins.map((p) => ({
    id: p.id,
    boardId: p.board_id,
    pinType: p.pin_type,
    targetId: p.target_id,
    note: p.note,
  }));
  return {
    licenseNote: seed.license_note ?? null,
    committees: [...committees.values()],
    people: [...people.values()],
    hearings,
    topics: [...topics.values()],
    documents,
    chunks,
    boards,
    pins,
  };
}

export function loadFixtures() {
  if (cached) return cached;
  const seed = JSON.parse(readFileSync(fixturePath(), "utf8")) as RawSeed;
  cached = hydrate(seed);
  return cached;
}
