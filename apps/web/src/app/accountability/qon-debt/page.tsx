import Link from "next/link";
import { AccountabilityNav, EmptyRows } from "@/components/accountability-lens";
import { loadQonDebt } from "@/lib/accountability";
import { formatDate, roleTypeLabel } from "@/lib/format";

export const metadata = { title: "QoN debt" };
export const dynamic = "force-dynamic";

export default async function QonDebtPage() {
  const payload = await loadQonDebt();

  return (
    <div className="space-y-8">
      <header className="max-w-3xl">
        <p className="eyebrow">Questions on notice</p>
        <h1 className="mt-2 font-serif text-4xl text-ink">QoN debt</h1>
        <p className="mt-3 text-muted leading-relaxed">
          Counts of questions still open, overdue, answered, or refused, by
          portfolio and answering agency. This is a process ledger. It does
          not rank ministers or agencies.
        </p>
        <p className="mt-2 text-xs text-muted">
          Source · <span className="font-mono">{payload.source}</span>
        </p>
      </header>

      <AccountabilityNav current="/accountability/qon-debt" />

      {payload.rows.length ? (
        <ul className="divide-y divide-rule border-y border-rule">
          {payload.rows.map((row) => (
            <li
              key={`${row.portfolio}-${row.agencySlug ?? "none"}`}
              className="flex flex-wrap items-baseline justify-between gap-2 py-3"
            >
              <div>
                <p className="font-serif text-lg text-navy">{row.portfolio}</p>
                <p className="text-sm text-muted">
                  {row.agencySlug ? (
                    <Link href={`/agencies/${row.agencySlug}`} className="hover:text-ochre">
                      {row.agencyName ?? row.agencySlug}
                    </Link>
                  ) : (
                    (row.agencyName ?? "Agency not linked")
                  )}
                  {row.responsibleOfficialName ? (
                    <>
                      {" · "}
                      {row.responsibleOfficialSlug ? (
                        <Link href={`/people/${row.responsibleOfficialSlug}`} className="hover:text-ochre">
                          {row.responsibleOfficialName}
                        </Link>
                      ) : (
                        row.responsibleOfficialName
                      )}
                      {row.responsibleOfficialRole
                        ? ` (${roleTypeLabel(row.responsibleOfficialRole)})`
                        : ""}
                    </>
                  ) : null}
                </p>
              </div>
              <p className="text-xs uppercase tracking-[0.12em] text-muted">
                {row.overdueCount} overdue · {row.openishCount} open/unknown ·{" "}
                {row.answeredCount} answered · {row.qonCount} total
                {row.latestDue ? ` · latest due ${formatDate(row.latestDue)}` : ""}
              </p>
            </li>
          ))}
        </ul>
      ) : (
        <EmptyRows label="QoN debt rows" needed={payload.needed} />
      )}
    </div>
  );
}
