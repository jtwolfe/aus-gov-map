import { AccountabilityNav, EmptyRows } from "@/components/accountability-lens";
import { loadChainCompleteness } from "@/lib/accountability";
import { instrumentTypeLabel } from "@/lib/format";

export const metadata = { title: "Chain completeness" };
export const dynamic = "force-dynamic";

export default async function ChainCompletenessPage() {
  const payload = await loadChainCompleteness();

  return (
    <div className="space-y-8">
      <header className="max-w-3xl">
        <p className="eyebrow">Duty edges</p>
        <h1 className="mt-2 font-serif text-4xl text-ink">Chain completeness</h1>
        <p className="mt-3 text-muted leading-relaxed">
          Each instrument should eventually carry a sourced accountable
          minister and a responsible official. A missing edge means the
          chain is incomplete in this store — not that a person failed a duty.
        </p>
        <p className="mt-2 text-xs text-muted">
          Source · <span className="font-mono">{payload.source}</span>
        </p>
      </header>

      <AccountabilityNav current="/accountability/chain-completeness" />

      {payload.rows.length ? (
        <ul className="divide-y divide-rule border-y border-rule">
          {payload.rows.map((row) => (
            <li key={row.slug} className="py-3">
              <p className="eyebrow">{instrumentTypeLabel(row.instrumentType)}</p>
              <p className="font-serif text-lg text-navy">{row.title}</p>
              <p className="text-sm text-muted">{row.agencyName ?? "Agency not linked"}</p>
              <p className="mt-1 text-xs uppercase tracking-[0.12em] text-muted">
                minister {row.hasAccountableMinister ? "linked" : "missing"}
                {" · "}
                official {row.hasResponsibleOfficial ? "linked" : "missing"}
              </p>
              {row.sourceUrl ? (
                <p className="mt-1 text-xs">
                  <a href={row.sourceUrl} className="link" rel="noreferrer">
                    source_url
                  </a>
                </p>
              ) : null}
            </li>
          ))}
        </ul>
      ) : (
        <EmptyRows label="instruments to score for chain gaps" needed={payload.needed} />
      )}
    </div>
  );
}
