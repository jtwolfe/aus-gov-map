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
  chunks?: Chunk[];
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
  kind: "hearing" | "person" | "chunk" | "document";
  id: string;
  slug?: string;
  title: string;
  subtitle?: string;
  excerpt: string;
  href: string;
  score: number;
  mode: "keyword" | "semantic";
  sourceKey?: string;
  hearingType?: string;
};

export type SearchMode = "keyword" | "semantic" | "combined";

export type SearchFilters = {
  committee?: string;
  person?: string;
  hearingType?: "estimates" | "other" | "all";
  from?: string;
  to?: string;
};

export type DataSource = "postgres" | "fixture";

export type CoverageStats = {
  source: DataSource;
  hearings: number;
  people: number;
  chunks: number;
  liveHearings: number;
  sampleHearings: number;
  committees: number;
};

export type CoAttendance = {
  slug: string;
  name: string;
  count: number;
  lastHeldOn: string | null;
};
