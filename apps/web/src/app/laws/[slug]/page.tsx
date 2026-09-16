import Link from "next/link";
import { notFound } from "next/navigation";
import { AccountabilityNav, EmptyRows } from "@/components/accountability-lens";
import { CrossLinks } from "@/components/cross-links";
import { MiniAtlas } from "@/components/mini-atlas";
import { VoteList } from "@/components/vote-list";
import { formatDate, instrumentTypeLabel } from "@/lib/format";
import {
  loadDivisionsForInstrument,
  loadJudgmentsForInstrument,
  loadLaw,
  loadLinkedScrutiny,
  loadVotes,
  statusTimeline,
} from "@/lib/laws";

export const dynamic = "force-dynamic";

export async function generateMetadata({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  const payload = await loadLaw(slug);
  return { title: payload.rows[0]?.title ?? "Law" };
}

export default async function LawDossierPage({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  const payload = await loadLaw(slug);
  const row = payload.rows[0];
  if (payload.ready && !row) notFound();

  const [divisions, votes, judgments, linked] = row
    ? await Promise.all([
        loadDivisionsForInstrument(row.slug),
        loadVotes({ instrument: row.slug }),
        loadJudgmentsForInstrument(row.slug),
        loadLinkedScrutiny(row.slug),
      ])
    : [null, null, null, []];

  const timeline = row ? statusTimeline(row) : [];

  return (
    <div className="space-y-8">
      <header className="max-w-3xl">
        <p className="eyebrow">
          {row ? instrumentTypeLabel(row.instrumentType) : "Law"}
          {row?.status ? ` · ${row.status}` : ""}
        </p>
        <h1 className="mt-2 font-serif text-4xl text-ink">{row?.title ?? slug}</h1>
        <p className="mt-3 text-muted leading-relaxed">
          A sourced Bill or Act on the accountability spine. Votes are
          recorded divisions only. Judgments are court holdings attributed
          to the court — not a finding about any official.
        </p>
        <CrossLinks
          items={
            row
              ? [
                  { href: `/atlas?instrument=${encodeURIComponent(row.slug)}&includeProposed=1`, label: "Atlas focus" },
                  { href: `/accountability/instruments/${row.slug}`, label: "Instrument" },
                  { href: "/accountability", label: "Accountability" },
                  ...(row.agencySlug
                    ? [{ href: `/agencies/${row.agencySlug}`, label: "Agency" }]
                    : []),
                ]
              : [
                  { href: "/atlas", label: "Atlas" },
                  { href: "/accountability", label: "Accountability" },
                ]
          }
        />
        <p className="mt-2 text-xs text-muted">
          Source · <span className="font-mono">{payload.source}</span>
          {row?.source ? ` · ${row.source}` : ""}
          {row?.sourceUrl ? (
            <>
              {" · "}
              <a href={row.sourceUrl} className="link" rel="noreferrer">
                register / source
              </a>
            </>
          ) : null}
        </p>
      </header>

      <AccountabilityNav current="/laws" />

      {!row ? (
        <EmptyRows label="law instrument" needed={payload.needed} />
      ) : (
        <>
          <dl className="grid gap-3 border border-rule bg-card px-5 py-4 text-sm sm:grid-cols-2">
            <div>
              <dt className="text-xs uppercase tracking-[0.12em] text-muted">Identifiers</dt>
              <dd className="mt-1 text-navy">
                {row.identifiers.frlId ?? "No FRL id yet"}
                {row.identifiers.year != null ? ` · ${row.identifiers.year}` : ""}
                {row.identifiers.number != null ? ` No. ${row.identifiers.number}` : ""}
                {row.identifiers.collection ? ` · ${row.identifiers.collection}` : ""}
              </dd>
            </div>
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
            {row.summary ? (
              <div className="sm:col-span-2">
                <dt className="text-xs uppercase tracking-[0.12em] text-muted">Summary</dt>
                <dd className="mt-1 text-muted">{row.summary}</dd>
              </div>
            ) : null}
          </dl>

          <section>
            <p className="eyebrow">Register dates</p>
            <h2 className="mt-2 font-serif text-2xl text-navy">Status timeline</h2>
            <ol className="mt-4 border-l border-rule pl-5">
              {timeline.map((step) => (
                <li key={step.label} className="relative py-3">
                  <span className="absolute -left-[25px] top-5 h-2 w-2 rounded-full bg-navy" />
                  <p className="text-xs uppercase tracking-[0.14em] text-muted">
                    {step.on ? formatDate(step.on) : "Date not in this source"}
                  </p>
                  <p className="mt-1 text-navy">{step.label}</p>
                </li>
              ))}
            </ol>
          </section>

          <section>
            <p className="eyebrow">They Vote For You · Hansard</p>
            <h2 className="mt-2 font-serif text-2xl text-navy">Votes</h2>
            <p className="mt-2 text-sm text-muted">
              Sourced divisions only. Sitting in Estimates is not a vote.
              Named rows are a published excerpt unless the live adapter
              filled a fuller list.
            </p>
            {divisions?.rows.length ? (
              <ul className="mt-4 space-y-3 text-sm">
                {divisions.rows.map((div) => (
                  <li key={div.slug ?? div.title} className="border border-rule px-4 py-3">
                    <p className="font-serif text-lg text-navy">{div.title}</p>
                    <p className="text-muted">
                      {div.house}
                      {div.dividedOn ? ` · ${formatDate(div.dividedOn)}` : ""}
                      {div.number != null ? ` · no. ${div.number}` : ""}
                      {div.ayes != null || div.noes != null
                        ? ` · ayes ${div.ayes ?? "—"} / noes ${div.noes ?? "—"}`
                        : ""}
                      {` · ${div.namedVotes} named · ${div.resolvedVotes} resolved to people`}
                    </p>
                    {div.sourceUrl ? (
                      <a href={div.sourceUrl} className="link text-xs" rel="noreferrer">
                        division source
                      </a>
                    ) : null}
                  </li>
                ))}
              </ul>
            ) : null}
            <div className="mt-4">
              <VoteList
                votes={votes?.rows ?? []}
                empty="No sourced division votes for this instrument yet. Ingest theyvoteforyou after legislation. Unresolved names stay names — we do not invent MPs."
              />
            </div>
          </section>

          <section>
            <p className="eyebrow">High Court · Federal Court</p>
            <h2 className="mt-2 font-serif text-2xl text-navy">Judgments</h2>
            <p className="mt-2 text-sm text-muted">
              Precedent links use construes / upholds / invalidates only when
              the published holding supports that verb. Not a guilt score.
            </p>
            {judgments?.rows.length ? (
              <ul className="mt-4 divide-y divide-rule border-y border-rule">
                {judgments.rows.map((item) => (
                  <li key={`${item.citation}-${item.linkKind}`} className="py-3">
                    <p className="eyebrow">{item.linkKind}{item.court ? ` · ${item.court}` : ""}</p>
                    <p className="font-serif text-lg text-navy">
                      {item.sourceUrl ? (
                        <a href={item.sourceUrl} className="hover:text-ochre" rel="noreferrer">
                          {item.title}
                        </a>
                      ) : (
                        item.title
                      )}
                    </p>
                    <p className="text-sm text-muted">
                      {item.citation}
                      {item.publishedOn ? ` · ${formatDate(item.publishedOn)}` : ""}
                    </p>
                    {item.notes ? <p className="mt-1 text-sm text-muted">{item.notes}</p> : null}
                  </li>
                ))}
              </ul>
            ) : (
              <p className="mt-3 text-sm text-muted">
                No sourced judgment links yet. Ingest{" "}
                <span className="font-mono">judgments</span> after{" "}
                <span className="font-mono">legislation</span>.
              </p>
            )}
          </section>

          {linked.length ? (
            <section>
              <p className="eyebrow">Hearings · QoN · ANAO · contracts</p>
              <h2 className="mt-2 font-serif text-2xl text-navy">Later scrutiny</h2>
              <ul className="mt-3 space-y-2 text-sm">
                {linked.map((item, idx) => (
                  <li key={`${item.kind}-${idx}`}>
                    <span className="text-xs uppercase tracking-[0.12em] text-muted">{item.kind}</span>
                    {" · "}
                    {item.href ? (
                      item.href.startsWith("/") ? (
                        <Link href={item.href} className="link">
                          {item.title}
                        </Link>
                      ) : (
                        <a href={item.href} className="link" rel="noreferrer">
                          {item.title}
                        </a>
                      )
                    ) : (
                      item.title
                    )}
                  </li>
                ))}
              </ul>
            </section>
          ) : null}

          <MiniAtlas instrument={row.slug} agency={row.agencySlug ?? undefined} />

          <p className="text-xs text-muted">
            Also listed as an instrument at{" "}
            <Link href={`/accountability/instruments/${row.slug}`} className="link">
              /accountability/instruments/{row.slug}
            </Link>
            . Votes stay on this dossier; the Atlas shows the Act/Bill thread,
            not each aye/no.
          </p>
        </>
      )}
    </div>
  );
}
