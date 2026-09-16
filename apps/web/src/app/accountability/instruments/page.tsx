import Link from "next/link";
import { AccountabilityNav, EmptyRows } from "@/components/accountability-lens";
import { loadInstruments } from "@/lib/accountability";
import { formatDate, instrumentTypeLabel } from "@/lib/format";

export const metadata = { title: "Instruments" };
export const dynamic = "force-dynamic";

export default async function InstrumentsPage({
  searchParams,
}: {
  searchParams: Promise<Record<string, string | undefined>>;
}) {
  const params = await searchParams;
  const q = params.q?.trim() || null;
  const payload = await loadInstruments(q);

  return (
    <div className="space-y-8">
      <header className="max-w-3xl">
        <p className="eyebrow">Programs · measures · bills · contracts · grants</p>
        <h1 className="mt-2 font-serif text-4xl text-ink">Instruments</h1>
        <p className="mt-3 text-muted leading-relaxed">
          Public things that can be decided, funded, or delivered — including
          Bills and Acts. Amounts and dates stay nullable until a source
          provides them. Law dossiers live at{" "}
          <Link href="/laws" className="link">
            /laws
          </Link>
          . This list does not rank value or controversy.
        </p>
        <p className="mt-2 text-xs text-muted">
          Source · <span className="font-mono">{payload.source}</span>
        </p>
      </header>

      <AccountabilityNav current="/accountability/instruments" />

      <form className="flex flex-wrap items-end gap-3" method="get">
        <label className="text-sm text-muted">
          Search
          <input
            type="search"
            name="q"
            defaultValue={q ?? ""}
            placeholder="title or identifier"
            className="mt-1 block w-72 border border-rule bg-card px-3 py-1.5 text-ink"
          />
        </label>
        <button type="submit" className="border border-navy px-3 py-1.5 text-sm text-navy hover:bg-paper-2">
          Search
        </button>
      </form>

      {payload.rows.length ? (
        <ul className="divide-y divide-rule border-y border-rule">
          {payload.rows.map((row) => (
            <li key={row.slug} className="flex flex-wrap items-baseline justify-between gap-2 py-3">
              <div>
                <p className="eyebrow">{instrumentTypeLabel(row.instrumentType)}</p>
                <p className="font-serif text-lg text-navy">
                  <Link
                    href={
                      row.instrumentType === "bill" || row.instrumentType === "act"
                        ? `/laws/${row.slug}`
                        : `/accountability/instruments/${row.slug}`
                    }
                    className="hover:text-ochre"
                  >
                    {row.title}
                  </Link>
                </p>
                <p className="text-sm text-muted">
                  {row.status === "proposed" ? "proposed · " : ""}
                  {row.agencySlug ? (
                    <Link href={`/agencies/${row.agencySlug}`} className="hover:text-ochre">
                      {row.agencyName ?? row.agencySlug}
                    </Link>
                  ) : (
                    row.agencyName
                  )}
                  {row.source ? ` · ${row.source}` : ""}
                </p>
              </div>
              <p className="text-xs uppercase tracking-[0.12em] text-muted">
                {row.announcedOn ? formatDate(row.announcedOn) : "date unknown"}
                {row.amountAud ? ` · ${row.amountAud} AUD` : ""}
              </p>
            </li>
          ))}
        </ul>
      ) : (
        <EmptyRows label="instruments" needed={payload.needed} />
      )}
    </div>
  );
}
