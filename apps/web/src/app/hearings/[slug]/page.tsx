import Link from "next/link";
import { notFound } from "next/navigation";
import { Attribution } from "@/components/attribution";
import { PinButton } from "@/components/pin-button";
import { SourceBadge } from "@/components/source-badge";
import { getHearing, loadCatalog, relatedPeople } from "@/lib/data";
import { formatDate, roleLabel, typeLabel } from "@/lib/format";

export const dynamic = "force-dynamic";

export async function generateMetadata({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  const result = await getHearing(slug);
  return { title: result?.hearing.title ?? "Hearing" };
}

export default async function HearingPage({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  const result = await getHearing(slug);
  if (!result) notFound();
  const { hearing } = result;
  const catalog = await loadCatalog();
  const cousins = relatedPeople(hearing, catalog);
  const chunks = hearing.chunks ?? [];
  const longOfficial = hearing.documents.some((d) => !d.contentText);

  return (
    <article className="space-y-10">
      <header className="max-w-3xl">
        <p className="flex flex-wrap items-center gap-2 eyebrow">
          <SourceBadge sourceKey={hearing.sourceKey} />
          {typeLabel(hearing.hearingType)} · {formatDate(hearing.heldOn)}
        </p>
        <h1 className="mt-3 font-serif text-4xl leading-tight text-ink">{hearing.title}</h1>
        <p className="mt-4 text-muted">{hearing.summary}</p>
        <dl className="mt-6 grid gap-3 text-sm sm:grid-cols-2">
          <div>
            <dt className="eyebrow">Committee</dt>
            <dd className="mt-1">{hearing.committee?.name ?? "—"}</dd>
          </div>
          <div>
            <dt className="eyebrow">Portfolio</dt>
            <dd className="mt-1">{hearing.portfolio ?? "—"}</dd>
          </div>
          <div>
            <dt className="eyebrow">Location</dt>
            <dd className="mt-1">{hearing.location}</dd>
          </div>
          <div>
            <dt className="eyebrow">Source</dt>
            <dd className="mt-1">
              {hearing.sourceUrl ? (
                <a href={hearing.sourceUrl} className="link" rel="noreferrer">
                  {hearing.source}
                </a>
              ) : (
                hearing.source
              )}
            </dd>
          </div>
        </dl>
        <div className="mt-6">
          <Attribution
            sourceKey={hearing.sourceKey}
            sourceUrl={hearing.sourceUrl}
            licenseNote={hearing.documents[0]?.licenseNote}
          />
        </div>
        <div className="mt-6 flex flex-wrap gap-2">
          {hearing.topics.map((topic) => (
            <span
              key={topic.id}
              className="border border-rule px-2 py-1 text-xs uppercase tracking-[0.12em] text-muted"
            >
              {topic.name}
            </span>
          ))}
          <PinButton
            pinType="hearing"
            targetId={hearing.id}
            href={`/hearings/${hearing.slug}`}
            label={hearing.title}
          />
        </div>
      </header>

      <section>
        <p className="eyebrow">Graph · who was involved</p>
        <h2 className="mt-2 font-serif text-2xl text-navy">People</h2>
        <ul className="mt-4 divide-y divide-rule border-y border-rule">
          {hearing.people.map((appearance) => (
            <li
              key={`${appearance.person.id}-${appearance.role}`}
              className="flex flex-wrap items-baseline justify-between gap-2 py-3"
            >
              <Link
                href={`/people/${appearance.person.slug}`}
                className="font-serif text-lg text-navy hover:text-ochre"
              >
                {appearance.person.name}
              </Link>
              <span className="text-xs uppercase tracking-[0.14em] text-muted">
                {roleLabel(appearance.role)}
                {appearance.person.party ? ` · ${appearance.person.party}` : ""}
              </span>
            </li>
          ))}
        </ul>
      </section>

      {chunks.length ? (
        <section id="excerpt">
          <p className="eyebrow">The record</p>
          <h2 className="mt-2 font-serif text-2xl text-navy">Excerpts</h2>
          <p className="mt-2 text-sm text-muted">
            {longOfficial
              ? "Full Official text is on the APH source page — excerpts below are the ingested chunks."
              : "Ingested chunks from the Official / sample document."}
          </p>
          <div className="mt-4 space-y-4">
            {chunks.map((chunk) => (
              <div
                id={`chunk-${chunk.id}`}
                key={chunk.id}
                className="border border-rule bg-card p-5"
              >
                <div className="flex flex-wrap items-baseline justify-between gap-2">
                  <p className="eyebrow">{chunk.speakerName ?? "Official"}</p>
                  <PinButton
                    pinType="chunk"
                    targetId={chunk.id}
                    href={`/hearings/${hearing.slug}#chunk-${chunk.id}`}
                    label={`${hearing.title} · ${chunk.speakerName ?? "excerpt"}`}
                  />
                </div>
                <p className="mt-3 whitespace-pre-wrap text-[15px] leading-relaxed text-ink">
                  {chunk.content}
                </p>
              </div>
            ))}
          </div>
        </section>
      ) : null}

      <section>
        <p className="eyebrow">Documents</p>
        <h2 className="mt-2 font-serif text-2xl text-navy">Officials</h2>
        <div className="mt-4 space-y-6">
          {hearing.documents.map((doc) => (
            <div key={doc.id} className="border border-rule bg-card p-5">
              <div className="flex flex-wrap items-baseline justify-between gap-2">
                <h3 className="font-serif text-lg text-navy">{doc.title}</h3>
                <span className="eyebrow">{doc.docType}</span>
              </div>
              <p className="mt-2 font-mono text-xs text-muted">{doc.sourceKey}</p>
              {doc.sourceUrl ? (
                <p className="mt-2">
                  <a href={doc.sourceUrl} className="link" rel="noreferrer">
                    Open source_url
                  </a>
                </p>
              ) : null}
              {doc.contentText ? (
                <div className="mt-4 space-y-4 text-[15px] leading-relaxed text-ink">
                  {doc.contentText
                    .split(/\n\s*\n/)
                    .filter(Boolean)
                    .map((para) => (
                      <p key={para.slice(0, 24)}>{para}</p>
                    ))}
                </div>
              ) : (
                <p className="mt-3 text-sm text-muted">
                  Long Official stored in Postgres — use excerpts above or the APH link.
                </p>
              )}
            </div>
          ))}
        </div>
      </section>

      {cousins.length ? (
        <section>
          <p className="eyebrow">Cross-reference</p>
          <h2 className="mt-2 font-serif text-2xl text-navy">Also appeared nearby</h2>
          <ul className="mt-3 flex flex-wrap gap-3 text-sm">
            {cousins.map((person) => (
              <li key={person.id}>
                <Link href={`/people/${person.slug}`} className="link">
                  {person.name}
                </Link>
              </li>
            ))}
          </ul>
        </section>
      ) : null}
    </article>
  );
}
