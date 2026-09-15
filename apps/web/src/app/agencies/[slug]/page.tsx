import Link from "next/link";
import { notFound } from "next/navigation";
import { AccountabilityNav, EmptyRows } from "@/components/accountability-lens";
import { loadAgency, loadRoleAtDate } from "@/lib/accountability";
import { formatDate, roleTypeLabel } from "@/lib/format";

export const dynamic = "force-dynamic";

export async function generateMetadata({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  const payload = await loadAgency(slug);
  return { title: payload.rows[0]?.name ?? "Agency" };
}

export default async function AgencyPage({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  const payload = await loadAgency(slug);
  const agency = payload.rows[0];
  if (payload.ready && !agency) notFound();
  const occupancies = agency
    ? await loadRoleAtDate(null, null, agency.slug)
    : { rows: [], source: payload.source, needed: payload.needed, ready: payload.ready };

  return (
    <div className="space-y-8">
      <header className="max-w-3xl">
        <p className="eyebrow">{agency?.portfolio ?? "Agency"}</p>
        <h1 className="mt-2 font-serif text-4xl text-ink">{agency?.name ?? slug}</h1>
        <p className="mt-3 text-muted leading-relaxed">
          Current occupants come from sourced <span className="font-mono">person_roles</span>.
          QoN counts are a process ledger, not a ranking.
        </p>
        <p className="mt-2 text-xs text-muted">
          Source · <span className="font-mono">{payload.source}</span>
          {agency?.sourceUrl ? (
            <>
              {" · "}
              <a href={agency.sourceUrl} className="link normal-case tracking-normal" rel="noreferrer">
                agency source
              </a>
            </>
          ) : null}
        </p>
      </header>

      <AccountabilityNav current="/agencies" />

      {!agency ? (
        <EmptyRows label="agency row" needed={payload.needed} />
      ) : (
        <>
          <section>
            <p className="eyebrow">Responsible official</p>
            <h2 className="mt-2 font-serif text-2xl text-navy">Current occupancy</h2>
            {agency.officialName ? (
              <p className="mt-3 text-muted">
                {agency.officialSlug ? (
                  <Link href={`/people/${agency.officialSlug}`} className="font-serif text-lg text-navy hover:text-ochre">
                    {agency.officialName}
                  </Link>
                ) : (
                  <span className="font-serif text-lg text-navy">{agency.officialName}</span>
                )}
                {agency.officialRole ? ` · ${roleTypeLabel(agency.officialRole)}` : ""}
              </p>
            ) : (
              <p className="mt-3 text-sm text-muted">
                No sourced secretary or agency head yet. Run{" "}
                <span className="font-mono">ingest run --source aps_leaders</span>.
              </p>
            )}
            <p className="mt-2 text-sm text-muted">
              <Link href="/accountability/qon-debt" className="hover:text-ochre">
                {agency.qonCount} QoN{agency.qonCount === 1 ? "" : "s"} linked to this agency
              </Link>
              {" · "}
              <Link
                href={`/accountability/role-at-date?portfolio=${encodeURIComponent(agency.slug)}`}
                className="hover:text-ochre"
              >
                Role at date
              </Link>
            </p>
          </section>

          <section>
            <p className="eyebrow">Occupancies</p>
            <h2 className="mt-2 font-serif text-2xl text-navy">Roles overlapping this agency</h2>
            {occupancies.rows.length ? (
              <ul className="mt-4 divide-y divide-rule border-y border-rule">
                {occupancies.rows.map((row, idx) => (
                  <li key={`${row.personSlug}-${row.roleType}-${idx}`} className="py-3">
                    <p className="font-serif text-lg text-navy">
                      {row.personSlug ? (
                        <Link href={`/people/${row.personSlug}`} className="hover:text-ochre">
                          {row.personName}
                        </Link>
                      ) : (
                        row.personName
                      )}
                    </p>
                    <p className="text-sm text-muted">
                      {roleTypeLabel(row.roleType)}
                      {row.roleTitle ? ` · ${row.roleTitle}` : ""}
                    </p>
                    <p className="mt-1 text-xs uppercase tracking-[0.12em] text-muted">
                      {formatDate(row.startDate)} – {row.endDate ? formatDate(row.endDate) : "open"}
                      {" · "}
                      {row.source}
                    </p>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="mt-3 text-sm text-muted">No overlapping occupancies in the current store.</p>
            )}
          </section>
        </>
      )}
    </div>
  );
}
