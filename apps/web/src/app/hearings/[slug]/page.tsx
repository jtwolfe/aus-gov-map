import Link from "next/link";
import { notFound } from "next/navigation";
import { PinButton } from "@/components/pin-button";
import { getHearing, loadCatalog, relatedPeople } from "@/lib/data";
import { formatDate, roleLabel, typeLabel } from "@/lib/format";

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

  return (
    <article className="space-y-10">
      <header className="max-w-3xl">
        <p className="eyebrow">
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
                <a href={hearing.sourceUrl} className="link">
                  {hearing.source}
                </a>
              ) : (
                hearing.source
              )}
            </dd>
          </div>
        </dl>
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

      <section id="excerpt">
        <p className="eyebrow">The record</p>
        <h2 className="mt-2 font-serif text-2xl text-navy">Documents</h2>
        <div className="mt-4 space-y-6">
          {hearing.documents.map((doc) => (
            <div key={doc.id} className="border border-rule bg-card p-5">
              <div className="flex flex-wrap items-baseline justify-between gap-2">
                <h3 className="font-serif text-lg text-navy">{doc.title}</h3>
                <span className="eyebrow">{doc.docType}</span>
              </div>
              <p className="mt-2 text-xs text-muted">{doc.licenseNote}</p>
              <div className="mt-4 space-y-4 text-[15px] leading-relaxed text-ink">
                {(doc.contentText ?? "")
                  .split(/\n\s*\n/)
                  .filter(Boolean)
                  .map((para) => (
                    <p key={para.slice(0, 24)}>{para}</p>
                  ))}
              </div>
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
