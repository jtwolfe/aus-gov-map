import Link from "next/link";
import { notFound } from "next/navigation";
import { MiniAtlas } from "@/components/mini-atlas";
import { PinButton } from "@/components/pin-button";
import { SourceBadge } from "@/components/source-badge";
import { loadRoleAtDate } from "@/lib/accountability";
import { getPerson } from "@/lib/data";
import { formatDate, roleLabel, roleTypeLabel, typeLabel } from "@/lib/format";

export const dynamic = "force-dynamic";

export async function generateMetadata({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  const result = await getPerson(slug);
  return { title: result?.person.name ?? "Person" };
}

export default async function PersonPage({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  const result = await getPerson(slug);
  if (!result) notFound();
  const { person, appearances, satWith } = result;
  const occupancies = await loadRoleAtDate(null, person.slug, null);
  const roles = occupancies.rows.filter((row) => row.personSlug === person.slug);

  return (
    <article className="space-y-10">
      <header className="max-w-3xl">
        <p className="eyebrow">{person.roleTitle ?? "Participant"}</p>
        <h1 className="mt-2 font-serif text-4xl text-ink">{person.name}</h1>
        <p className="mt-3 text-muted">
          {[person.party, person.organisation, person.portfolio].filter(Boolean).join(" · ")}
        </p>
        {person.bio ? <p className="mt-4 leading-relaxed">{person.bio}</p> : null}
        {person.aphUrl ? (
          <p className="mt-3">
            <a href={person.aphUrl} className="link" rel="noreferrer">
              APH profile
            </a>
          </p>
        ) : null}
        <div className="mt-5">
          <PinButton
            pinType="person"
            targetId={person.id}
            href={`/people/${person.slug}`}
            label={person.name}
          />
        </div>
      </header>

      {roles.length ? (
        <section>
          <p className="eyebrow">Sourced occupancy</p>
          <h2 className="mt-2 font-serif text-2xl text-navy">Roles</h2>
          <ul className="mt-4 divide-y divide-rule border-y border-rule">
            {roles.map((row, idx) => (
              <li key={`${row.roleType}-${idx}`} className="py-3">
                <p className="font-serif text-lg text-navy">
                  {roleTypeLabel(row.roleType)}
                  {row.roleTitle ? ` · ${row.roleTitle}` : ""}
                </p>
                <p className="text-sm text-muted">
                  {row.agencySlug ? (
                    <Link href={`/agencies/${row.agencySlug}`} className="hover:text-ochre">
                      {row.agencyName ?? row.agencySlug}
                    </Link>
                  ) : (
                    (row.agencyName ?? row.organisation ?? row.portfolio)
                  )}
                </p>
                <p className="mt-1 text-xs uppercase tracking-[0.12em] text-muted">
                  {formatDate(row.startDate)} – {row.endDate ? formatDate(row.endDate) : "open"}
                  {" · "}
                  {row.source}
                </p>
              </li>
            ))}
          </ul>
        </section>
      ) : null}

      <MiniAtlas person={person.slug} lane="person" />

      <section>
        <p className="eyebrow">Appearances timeline</p>
        <h2 className="mt-2 font-serif text-2xl text-navy">Hearings</h2>
        <ol className="mt-4 border-l border-rule pl-5">
          {appearances.map(({ hearing, role }) => (
            <li key={`${hearing.id}-${role}`} className="relative py-4">
              <span className="absolute -left-[25px] top-6 h-2 w-2 rounded-full bg-navy" />
              <p className="flex flex-wrap items-center gap-2 text-xs uppercase tracking-[0.14em] text-muted">
                <SourceBadge sourceKey={hearing.sourceKey} />
                {typeLabel(hearing.hearingType)} · {formatDate(hearing.heldOn)} · {roleLabel(role)}
              </p>
              <Link
                href={`/hearings/${hearing.slug}`}
                className="mt-1 block font-serif text-xl text-navy hover:text-ochre"
              >
                {hearing.title}
              </Link>
              <p className="mt-1 text-sm text-muted">{hearing.committee?.name}</p>
              {hearing.sourceUrl ? (
                <p className="mt-1 text-xs">
                  <a href={hearing.sourceUrl} className="link" rel="noreferrer">
                    source_url
                  </a>
                </p>
              ) : null}
            </li>
          ))}
        </ol>
      </section>

      {satWith.length ? (
        <section>
          <p className="eyebrow">Co-attendance</p>
          <h2 className="mt-2 font-serif text-2xl text-navy">Sat with</h2>
          <ul className="mt-3 space-y-2 text-sm">
            {satWith.map((row) => (
              <li key={row.slug}>
                <Link href={`/people/${row.slug}`} className="link">
                  {row.name}
                </Link>
                <span className="text-muted">
                  {" "}
                  · {row.count} shared hearing{row.count === 1 ? "" : "s"}
                  {row.lastHeldOn ? ` · last ${formatDate(row.lastHeldOn)}` : ""}
                </span>
              </li>
            ))}
          </ul>
        </section>
      ) : null}
    </article>
  );
}
