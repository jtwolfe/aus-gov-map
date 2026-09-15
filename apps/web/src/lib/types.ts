export type HearingType = "estimates" | "committee" | "other";

export type AppearanceRole =
  | "chair"
  | "senator"
  | "minister"
  | "official"
  | "witness"
  | "appeared";

export type Committee = {
  id: string;
  slug: string;
  name: string;
  chamber: string;
  kind: string;
  aphUrl: string | null;
};

export type Person = {
  id: string;
  slug: string;
  name: string;
  roleTitle: string | null;
  party: string | null;
  portfolio: string | null;
  organisation: string | null;
  aphUrl: string | null;
  bio: string | null;
};

export type Appearance = {
  person: Person;
  role: AppearanceRole;
};

export type Topic = {
  id: string;
  slug: string;
  name: string;
};

export type Document = {
  id: string;
  hearingId: string;
  title: string;
  docType: string;
  sourceUrl: string | null;
  sourceKey: string;
  contentText: string | null;
  publishedAt: string | null;
  licenseNote: string | null;
};

export type Chunk = {
  id: string;
  documentId: string;
  hearingId: string;
  chunkIndex: number;
  content: string;
  speakerName: string | null;
  sourceKey: string;
};

export type Hearing = {
  id: string;
  slug: string;
  title: string;
  hearingType: HearingType;
  portfolio: string | null;
  heldOn: string | null;
  location: string | null;
  source: string;
  sourceUrl: string | null;
  sourceKey: string;
  status: string;
  summary: string | null;
  committee: Committee | null;
  people: Appearance[];
  topics: Topic[];
  documents: Document[];
};

export type Board = {
  id: string;
  slug: string;
  title: string;
  description: string | null;
};

export type Pin = {
  id: string;
  boardId: string;
  pinType: "hearing" | "person" | "chunk" | "document" | string;
  targetId: string;
  note: string | null;
};

export type SearchHit = {
  kind: "hearing" | "person" | "chunk";
  id: string;
  slug?: string;
  title: string;
  subtitle?: string;
  excerpt: string;
  href: string;
  score: number;
  mode: "keyword" | "semantic";
};

export type SearchMode = "keyword" | "semantic" | "combined";

export type DataSource = "postgres" | "fixture";
