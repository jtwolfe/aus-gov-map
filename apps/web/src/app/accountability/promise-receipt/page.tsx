import Link from "next/link";
import { AccountabilityNav, EmptyRows } from "@/components/accountability-lens";
import { loadPromiseReceipt } from "@/lib/accountability";
import { formatDate } from "@/lib/format";

export const metadata = { title: "Promise → receipt" };
export const dynamic = "force-dynamic";

export default async function PromiseReceiptPage() {
  const payload = await loadPromiseReceipt();

  return (
    <div className="space-y-8">
      <header className="max-w-3xl">
        <p className="eyebrow">Claims · instruments · outcomes</p>
        <h1 className="mt-2 font-serif text-4xl text-ink">Promise → receipt</h1>
        <p className="mt-3 text-muted leading-relaxed">
          A claim is a cited span (promise, assurance, or taken on notice).
          A receipt is a later sourced outcome on the same instrument. Neither
          side is inferred from the other, and Hansard is not a finding.
        </p>
        <p className="mt-2 text-xs text-muted">
          Source · <span className="font-mono">{payload.source}</span>
        </p>
      </header>

      <AccountabilityNav current="/accountability/promise-receipt" />

      {payload.rows.length ? (
        <ul className="divide-y divide-rule border-y border-rule">
          {payload.rows.map((row, idx) => (
            <li key={`${row.claimType}-${idx}`} className="py-4">
              <p className="eyebrow">{row.claimType.replaceAll("_", " ")}</p>
              <p className="mt-1 font-serif text-lg text-navy">{row.textSpan}</p>
              <p className="mt-2 text-sm text-muted">
                {row.personSlug ? (
                  <Link href={`/people/${row.personSlug}`} className="link">
                    {row.personName ?? row.speakerName}
                  </Link>
                ) : (
                  row.speakerName ?? row.personName ?? "Unattributed span"
                )}
                {row.madeOn ? ` · ${formatDate(row.madeOn)}` : ""}
                {row.hearingSlug ? (
                  <>
                    {" · "}
                    <Link href={`/hearings/${row.hearingSlug}`} className="link">
                      {row.hearingTitle}
                    </Link>
                  </>
                ) : null}
              </p>
              <p className="mt-1 text-xs uppercase tracking-[0.12em] text-muted">
                {row.instrumentTitle ? (
                  <>
                    {row.instrumentType ?? "instrument"}
                    {" · "}
                    {row.instrumentSlug ? (
                      <Link href={`/accountability/instruments/${row.instrumentSlug}`} className="link normal-case tracking-normal">
                        {row.instrumentTitle}
                      </Link>
                    ) : (
                      row.instrumentTitle
                    )}
                  </>
                ) : (
                  "No instrument linked yet"
                )}
                {row.outcomeSignal
                  ? ` · outcome ${row.outcomeSignal}${row.outcomeOn ? ` ${formatDate(row.outcomeOn)}` : ""}`
                  : " · no sourced outcome"}
              </p>
            </li>
          ))}
        </ul>
      ) : (
        <EmptyRows label="promise / receipt pairs" needed={payload.needed} />
      )}
    </div>
  );
}
