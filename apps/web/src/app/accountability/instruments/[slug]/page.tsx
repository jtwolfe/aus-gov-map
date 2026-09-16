import Link from "next/link";
import { notFound } from "next/navigation";
import { AccountabilityNav, EmptyRows } from "@/components/accountability-lens";
import { CrossLinks } from "@/components/cross-links";
import { MiniAtlas } from "@/components/mini-atlas";
import { loadInstrument } from "@/lib/accountability";
import { formatDate, instrumentTypeLabel } from "@/lib/format";
import { isLawType } from "@/lib/laws";

export const dynamic = "force-dynamic";

export async function generateMetadata({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  const payload = await loadInstrument(slug);
  return { title: payload.rows[0]?.title ?? "Instrument" };
}

export default async function InstrumentPage({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  const payload = await loadInstrument(slug);
  const row = payload.rows[0];
  if (payload.ready && !row) notFound();

  return (
    <div className="space-y-8">
      <header className="max-w-3xl">
        <p className="eyebrow">{row ? instrumentTypeLabel(row.instrumentType) : "Instrument"}</p>
        <h1 className="mt-2 font-serif text-4xl text-ink">{row?.title ?? slug}</h1>
        <p className="mt-3 text-muted leading-relaxed">
          A public thing that can be decided, funded, or delivered. Dates and
          amounts stay nullable until a source provides them. Proposed status
          means a text candidate, not an asserted fact.
        </p>
        <CrossLinks
          items={
            row
              ? [
                  { href: `/atlas?instrument=${encodeURIComponent(row.slug)}&includeProposed=1`, label: "Atlas focus" },
                  { href: "/accountability/promise-receipt", label: "Promise → receipt" },
                  { href: "/accountability/chain-completeness", label: "Chain completeness" },
                  ...(isLawType(row.instrumentType)
                    ? [{ href: `/laws/${row.slug}`, label: "Law dossier" }]
                    : []),
                  ...(row.agencySlug
                    ? [{ href: `/agencies/${row.agencySlug}`, label: "Agency" }]
                    : []),
                ]
              : [{ href: "/accountability", label: "Accountability" }]
          }
        />
        <p className="mt-2 text-xs text-muted">
          Source · <span className="font-mono">{payload.source}</span>
          {row?.status ? ` · ${row.status}` : ""}
          {row?.sourceUrl ? (
            <>
              {" · "}
              <a href={row.sourceUrl} className="link" rel="noreferrer">
                source
              </a>
            </>
          ) : null}
        </p>
      </header>

      <AccountabilityNav current="/accountability/instruments" />

      {!row ? (
        <EmptyRows label="instrument" needed={payload.needed} />
      ) : (
        <>
          <dl className="grid gap-3 border border-rule bg-card px-5 py-4 text-sm sm:grid-cols-2">
            <div>
              <dt className="text-xs uppercase tracking-[0.12em] text-muted">Agency</dt>
              <dd className="mt-1 text-navy">
                {row.agencySlug ? (
                  <Link href={`/agencies/${row.agencySlug}`} className="hover:text-ochre">
                    {row.agencyName ?? row.agencySlug}
                  </Link>
                ) : (
                  (row.agencyName ?? "Not linked")
                )}
              </dd>
            </div>
            <div>
              <dt className="text-xs uppercase tracking-[0.12em] text-muted">Dates</dt>
              <dd className="mt-1 text-muted">
                {row.announcedOn || row.commencedOn
                  ? `${formatDate(row.commencedOn ?? row.announcedOn ?? null)} – ${row.endedOn ? formatDate(row.endedOn) : "open"}`
                  : "Date unknown"}
              </dd>
            </div>
            {row.amountAud ? (
              <div>
                <dt className="text-xs uppercase tracking-[0.12em] text-muted">Amount</dt>
                <dd className="mt-1 text-muted">{row.amountAud} AUD</dd>
              </div>
            ) : null}
            {row.summary ? (
              <div className="sm:col-span-2">
                <dt className="text-xs uppercase tracking-[0.12em] text-muted">Summary</dt>
                <dd className="mt-1 text-muted">{row.summary}</dd>
              </div>
            ) : null}
          </dl>
          {isLawType(row.instrumentType) ? (
            <p className="text-sm text-muted">
              This is a Bill or Act. The law dossier (status, votes, judgments)
              is at{" "}
              <Link href={`/laws/${row.slug}`} className="link">
                /laws/{row.slug}
              </Link>
              .
            </p>
          ) : null}
          <MiniAtlas instrument={row.slug} agency={row.agencySlug ?? undefined} />
        </>
      )}
    </div>
  );
}
