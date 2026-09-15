import { postgresAvailable, query } from "./db";

export type InsightPerson = {
  slug: string;
  name: string;
  roleTitle: string | null;
  organisation: string | null;
  estimatesHearings: number;
  firstSeen: string | null;
  lastSeen: string | null;
};

export type InsightCommittee = {
  slug: string;
  name: string;
  chamber: string;
  hearingCount: number;
  recentHearings: number;
  estimatesCount: number;
  lastHearing: string | null;
};

export type InsightMention = {
  label: string;
  kind: "topic" | "text";
  hearingCount: number;
  lastSeen: string | null;
};

export type InsightsPayload = {
  source: "postgres" | "unavailable";
  peopleAcrossEstimates: InsightPerson[];
  committeeActivity: InsightCommittee[];
  repeatedMentions: InsightMention[];
};

function dateOnly(value: unknown): string | null {
  return value ? String(value).slice(0, 10) : null;
}

async function viewsExist(): Promise<boolean> {
  const rows = await query<{ n: number }>(`
    SELECT COUNT(*)::int AS n
    FROM information_schema.views
    WHERE table_schema = 'public'
      AND table_name IN (
        'v_people_across_estimates',
        'v_committee_recent_activity',
        'v_repeated_topic_mentions'
      )
  `);
  return (rows[0]?.n ?? 0) >= 3;
}

export async function loadInsights(): Promise<InsightsPayload> {
  if (!(await postgresAvailable())) {
    return {
      source: "unavailable",
      peopleAcrossEstimates: [],
      committeeActivity: [],
      repeatedMentions: [],
    };
  }

  const useViews = await viewsExist();
  const peopleSql = useViews
    ? `
      SELECT slug, name, role_title, organisation, estimates_hearings, first_seen, last_seen
      FROM v_people_across_estimates
      ORDER BY estimates_hearings DESC, last_seen DESC NULLS LAST
      LIMIT 20
    `
    : `
      SELECT p.slug, p.name, p.role_title, p.organisation,
             COUNT(DISTINCT h.id)::int AS estimates_hearings,
             MIN(h.held_on) AS first_seen,
             MAX(h.held_on) AS last_seen
      FROM people p
      JOIN hearing_people hp ON hp.person_id = p.id
      JOIN hearings h ON h.id = hp.hearing_id
      WHERE h.hearing_type = 'estimates'
      GROUP BY p.id
      ORDER BY estimates_hearings DESC, last_seen DESC NULLS LAST
      LIMIT 20
    `;

  const committeeSql = useViews
    ? `
      SELECT slug, name, chamber, hearing_count, recent_hearings, estimates_count, last_hearing
      FROM v_committee_recent_activity
      ORDER BY recent_hearings DESC, last_hearing DESC NULLS LAST
      LIMIT 16
    `
    : `
      SELECT c.slug, c.name, c.chamber,
             COUNT(h.id)::int AS hearing_count,
             COUNT(h.id) FILTER (WHERE h.held_on >= CURRENT_DATE - INTERVAL '18 months')::int AS recent_hearings,
             COUNT(h.id) FILTER (WHERE h.hearing_type = 'estimates')::int AS estimates_count,
             MAX(h.held_on) AS last_hearing
      FROM committees c
      LEFT JOIN hearings h ON h.committee_id = c.id
      GROUP BY c.id
      ORDER BY recent_hearings DESC, last_hearing DESC NULLS LAST
      LIMIT 16
    `;

  const topicSql = useViews
    ? `
      SELECT name AS label, 'topic'::text AS kind, hearing_count, last_seen
      FROM v_repeated_topic_mentions
      ORDER BY hearing_count DESC, last_seen DESC NULLS LAST
      LIMIT 16
    `
    : `
      SELECT t.name AS label, 'topic'::text AS kind,
             COUNT(DISTINCT ht.hearing_id)::int AS hearing_count,
             MAX(h.held_on) AS last_seen
      FROM topics t
      JOIN hearing_topics ht ON ht.topic_id = t.id
      JOIN hearings h ON h.id = ht.hearing_id
      GROUP BY t.id
      ORDER BY hearing_count DESC, last_seen DESC NULLS LAST
      LIMIT 16
    `;

  const textSql = `
    WITH needles AS (
      SELECT unnest(ARRAY[
        'FOI', 'freedom of information', 'procurement', 'integrity',
        'question on notice', 'consultancy', 'grants'
      ]) AS needle
    )
    SELECT n.needle AS label, 'text'::text AS kind,
           COUNT(DISTINCT ch.hearing_id)::int AS hearing_count,
           MAX(h.held_on) AS last_seen
    FROM needles n
    JOIN chunks ch ON ch.content ILIKE '%' || n.needle || '%'
    JOIN hearings h ON h.id = ch.hearing_id
    GROUP BY n.needle
    HAVING COUNT(DISTINCT ch.hearing_id) >= 1
    ORDER BY hearing_count DESC
    LIMIT 16
  `;

  const [people, committees, topics, texts] = await Promise.all([
    query<Record<string, unknown>>(peopleSql),
    query<Record<string, unknown>>(committeeSql),
    query<Record<string, unknown>>(topicSql).catch(() => []),
    query<Record<string, unknown>>(textSql).catch(() => []),
  ]);

  const mentions: InsightMention[] = [
    ...topics.map((r) => ({
      label: String(r.label ?? r.name ?? ""),
      kind: "topic" as const,
      hearingCount: Number(r.hearing_count ?? 0),
      lastSeen: dateOnly(r.last_seen),
    })),
    ...texts.map((r) => ({
      label: String(r.label),
      kind: "text" as const,
      hearingCount: Number(r.hearing_count ?? 0),
      lastSeen: dateOnly(r.last_seen),
    })),
  ].sort((a, b) => b.hearingCount - a.hearingCount);

  return {
    source: "postgres",
    peopleAcrossEstimates: people.map((r) => ({
      slug: String(r.slug),
      name: String(r.name),
      roleTitle: (r.role_title as string | null) ?? null,
      organisation: (r.organisation as string | null) ?? null,
      estimatesHearings: Number(r.estimates_hearings ?? 0),
      firstSeen: dateOnly(r.first_seen),
      lastSeen: dateOnly(r.last_seen),
    })),
    committeeActivity: committees.map((r) => ({
      slug: String(r.slug),
      name: String(r.name),
      chamber: String(r.chamber ?? "Senate"),
      hearingCount: Number(r.hearing_count ?? 0),
      recentHearings: Number(r.recent_hearings ?? 0),
      estimatesCount: Number(r.estimates_count ?? 0),
      lastHearing: dateOnly(r.last_hearing),
    })),
    repeatedMentions: mentions,
  };
}
