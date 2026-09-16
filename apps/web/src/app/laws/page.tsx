import Link from "next/link";
import { AccountabilityNav, EmptyRows } from "@/components/accountability-lens";
import { CrossLinks } from "@/components/cross-links";
import { formatDate, instrumentTypeLabel } from "@/lib/format";
import { loadLaws } from "@/lib/laws";

export const metadata = { title: "Laws" };
export const dynamic = "force-dynamic";

export default async function LawsPage({
  searchParams,
}: {
  searchParams: Promise<Record<string, string | undefined>>;
}) {
  const params = await searchParams;
  const q = params.q?.trim() || null;
  const type = params.type === "bill" || params.type === "act" ? params.type : null;
  const payload = await loadLaws(q, type);

  return (
    <div className="space-y-8">
      <header className="max-w-3xl">
        <p className="eyebrow">Bills · Acts · sourced divisions · precedent</p>
        <h1 className="mt-2 font-serif text-4xl text-ink">Laws</h1>
        <p className="mt-3 text-muted leading-relaxed">
          Commonwealth Bills and Acts as first-class instruments on the same
          duty map as programs and contracts. Follow bill → Act → votes →
          later scrutiny. Court links are sourced holdings, not guilt labels.
        </p>
        <CrossLinks
          items={[
            { href: "/atlas", label: "Atlas" },
            { href: "/accountability/instruments", label: "Instruments" },
            { href: "/accountability", label: "Accountability" },
          ]}
        />
        <p className="mt-2 text-xs text-muted">
          Source · <span className="font-mono">{payload.source}</span>
          {" · "}
          <span className="font-mono">docs/laws-and-precedent.md</span>
        </p>
      </header>

      <AccountabilityNav current="/laws" />

      <form className="flex flex-wrap items-end gap-3" method="get">
        <label className="text-sm text-muted">
          Search
          <input
            type="search"
            name="q"
            defaultValue={q ?? ""}
            placeholder="title or FRL id"
            className="mt-1 block w-72 border border-rule bg-card px-3 py-1.5 text-ink"
          />
        </label>
        <label className="text-sm text-muted">
          Type
          <select
            name="type"
            defaultValue={type ?? ""}
            className="mt-1 block border border-rule bg-card px-3 py-1.5 text-ink"
          >
            <option value="">Bills and Acts</option>
            <option value="bill">Bills</option>
            <option value="act">Acts</option>
          </select>
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
                <p className="eyebrow">
                  {instrumentTypeLabel(row.instrumentType)}
                  {row.status ? ` · ${row.status}` : ""}
                </p>
                <p className="font-serif text-lg text-navy">
                  <Link href={`/laws/${row.slug}`} className="hover:text-ochre">
                    {row.title}
                  </Link>
                </p>
                <p className="text-sm text-muted">
                  {row.identifiers.frlId ? `${row.identifiers.frlId} · ` : ""}
                  {row.agencySlug ? (
                    <Link href={`/agencies/${row.agencySlug}`} className="hover:text-ochre">
                      {row.agencyName ?? row.agencySlug}
                    </Link>
                  ) : (
                    (row.agencyName ?? row.source ?? "")
                  )}
                </p>
              </div>
              <p className="text-xs uppercase tracking-[0.12em] text-muted">
                {row.commencedOn
                  ? formatDate(row.commencedOn)
                  : row.announcedOn
                    ? formatDate(row.announcedOn)
                    : "date unknown"}
              </p>
            </li>
          ))}
        </ul>
      ) : (
        <EmptyRows label="Bills or Acts" needed={payload.needed} />
      )}
    </div>
  );
}
