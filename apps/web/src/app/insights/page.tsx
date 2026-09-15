import Link from "next/link";
import { loadInsights } from "@/lib/insights";
import { formatDate } from "@/lib/format";

export const metadata = { title: "Insights" };
export const dynamic = "force-dynamic";

export default async function InsightsPage() {
  const insights = await loadInsights();

  return (
    <div className="space-y-12">
      <header className="max-w-3xl">
        <p className="eyebrow">Inefficiency starter queries</p>
        <h1 className="mt-2 font-serif text-4xl text-ink">Insights</h1>
        <p className="mt-3 text-muted">
          Stage 1.1 reads the analytics views in{" "}
          <span className="font-mono">infra/postgres/analytics/</span> (or the
          equivalent live SQL if views are not applied yet). Cypher twins live
          in <span className="font-mono">infra/neo4j/queries/</span>.
        </p>
        <p className="mt-2 text-xs text-muted">
          Source · <span className="font-mono">{insights.source}</span>
          {insights.source === "unavailable"
            ? " — start Postgres (`make db-up`) to run these."
            : ""}
        </p>
      </header>

      <section>
        <p className="eyebrow">People × Estimates</p>
        <h2 className="mt-2 font-serif text-2xl text-navy">Across many Estimates hearings</h2>
        <ul className="mt-4 divide-y divide-rule border-y border-rule">
          {insights.peopleAcrossEstimates.length ? (
            insights.peopleAcrossEstimates.map((row) => (
              <li key={row.slug} className="flex flex-wrap items-baseline justify-between gap-2 py-3">
                <div>
                  <Link href={`/people/${row.slug}`} className="font-serif text-lg text-navy hover:text-ochre">
                    {row.name}
                  </Link>
                  <p className="text-sm text-muted">
                    {[row.roleTitle, row.organisation].filter(Boolean).join(" · ")}
                  </p>
                </div>
                <p className="text-xs uppercase tracking-[0.12em] text-muted">
                  {row.estimatesHearings} hearing{row.estimatesHearings === 1 ? "" : "s"}
                  {row.lastSeen ? ` · last ${formatDate(row.lastSeen)}` : ""}
                </p>
              </li>
            ))
          ) : (
            <li className="py-4 text-sm text-muted">No Estimates appearances in the current store.</li>
          )}
        </ul>
      </section>

      <section>
        <p className="eyebrow">Committees</p>
        <h2 className="mt-2 font-serif text-2xl text-navy">Densest recent activity</h2>
        <ul className="mt-4 divide-y divide-rule border-y border-rule">
          {insights.committeeActivity.length ? (
            insights.committeeActivity.map((row) => (
              <li key={row.slug} className="flex flex-wrap items-baseline justify-between gap-2 py-3">
                <div>
                  <p className="font-serif text-lg text-navy">{row.name}</p>
                  <p className="text-sm text-muted">{row.chamber}</p>
                </div>
                <p className="text-xs uppercase tracking-[0.12em] text-muted">
                  {row.recentHearings} in 18 months · {row.hearingCount} total
                  {row.lastHearing ? ` · ${formatDate(row.lastHearing)}` : ""}
                </p>
              </li>
            ))
          ) : (
            <li className="py-4 text-sm text-muted">No committee rows yet.</li>
          )}
        </ul>
      </section>

      <section>
        <p className="eyebrow">Topics & text</p>
        <h2 className="mt-2 font-serif text-2xl text-navy">Repeated mentions</h2>
        <ul className="mt-4 divide-y divide-rule border-y border-rule">
          {insights.repeatedMentions.length ? (
            insights.repeatedMentions.map((row) => (
              <li key={`${row.kind}-${row.label}`} className="flex flex-wrap items-baseline justify-between gap-2 py-3">
                <div>
                  <p className="font-serif text-lg text-navy">{row.label}</p>
                  <p className="eyebrow">{row.kind}</p>
                </div>
                <p className="text-xs uppercase tracking-[0.12em] text-muted">
                  {row.hearingCount} hearing{row.hearingCount === 1 ? "" : "s"}
                  {row.lastSeen ? ` · ${formatDate(row.lastSeen)}` : ""}
                </p>
              </li>
            ))
          ) : (
            <li className="py-4 text-sm text-muted">
              No topic links or FOI/procurement-style chunk hits yet.
            </li>
          )}
        </ul>
      </section>
    </div>
  );
}
