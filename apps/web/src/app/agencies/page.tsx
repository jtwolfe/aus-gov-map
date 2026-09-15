import Link from "next/link";
import { AccountabilityNav, EmptyRows } from "@/components/accountability-lens";
import { loadAgencies } from "@/lib/accountability";
import { roleTypeLabel } from "@/lib/format";

export const metadata = { title: "Agencies" };
export const dynamic = "force-dynamic";

export default async function AgenciesPage() {
  const payload = await loadAgencies();

  return (
    <div className="space-y-8">
      <header className="max-w-3xl">
        <p className="eyebrow">Public service organisations</p>
        <h1 className="mt-2 font-serif text-4xl text-ink">Agencies</h1>
        <p className="mt-3 text-muted leading-relaxed">
          Official department and agency names, with a current secretary or
          agency head when <span className="font-mono">aps_leaders</span> has
          written a sourced occupancy. An Estimates appearance is not a tenure.
        </p>
        <p className="mt-2 text-xs text-muted">
          Source · <span className="font-mono">{payload.source}</span>
        </p>
      </header>

      <AccountabilityNav current="/agencies" />

      {payload.rows.length ? (
        <ul className="divide-y divide-rule border-y border-rule">
          {payload.rows.map((row) => (
            <li key={row.slug} className="flex flex-wrap items-baseline justify-between gap-2 py-3">
              <div>
                <p className="font-serif text-lg text-navy">
                  <Link href={`/agencies/${row.slug}`} className="hover:text-ochre">
                    {row.name}
                  </Link>
                </p>
                <p className="text-sm text-muted">
                  {row.portfolio ?? "Portfolio unspecified"}
                  {row.officialName ? (
                    <>
                      {" · "}
                      {row.officialSlug ? (
                        <Link href={`/people/${row.officialSlug}`} className="hover:text-ochre">
                          {row.officialName}
                        </Link>
                      ) : (
                        row.officialName
                      )}
                      {row.officialRole ? ` (${roleTypeLabel(row.officialRole)})` : ""}
                    </>
                  ) : (
                    " · no sourced incumbent"
                  )}
                </p>
              </div>
              <p className="text-xs uppercase tracking-[0.12em] text-muted">
                {row.qonCount} QoN{row.qonCount === 1 ? "" : "s"}
              </p>
            </li>
          ))}
        </ul>
      ) : (
        <EmptyRows label="agencies" needed={payload.needed} />
      )}
    </div>
  );
}
