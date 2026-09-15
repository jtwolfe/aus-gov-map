import Link from "next/link";
import { notFound } from "next/navigation";
import { PinButton } from "@/components/pin-button";
import { getPerson } from "@/lib/data";
import { formatDate, roleLabel, typeLabel } from "@/lib/format";

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
  const { person, appearances } = result;

  const coAppear = new Map<string, { slug: string; name: string; count: number }>();
  for (const { hearing } of appearances) {
    for (const other of hearing.people) {
      if (other.person.id === person.id) continue;
      const current = coAppear.get(other.person.id);
      if (current) current.count += 1;
      else {
        coAppear.set(other.person.id, {
          slug: other.person.slug,
          name: other.person.name,
          count: 1,
        });
      }
    }
  }

  return (
    <article className="space-y-10">
      <header className="max-w-3xl">
        <p className="eyebrow">{person.roleTitle ?? "Participant"}</p>
        <h1 className="mt-2 font-serif text-4xl text-ink">{person.name}</h1>
        <p className="mt-3 text-muted">
          {[person.party, person.organisation, person.portfolio].filter(Boolean).join(" · ")}
        </p>
        {person.bio ? <p className="mt-4 leading-relaxed">{person.bio}</p> : null}
        <div className="mt-5">
          <PinButton
            pinType="person"
            targetId={person.id}
            href={`/people/${person.slug}`}
            label={person.name}
          />
        </div>
      </header>

      <section>
        <p className="eyebrow">Appearances</p>
        <h2 className="mt-2 font-serif text-2xl text-navy">Hearings</h2>
        <ul className="mt-4 divide-y divide-rule border-y border-rule">
          {appearances.map(({ hearing, role }) => (
            <li key={hearing.id} className="py-4">
              <p className="text-xs uppercase tracking-[0.14em] text-muted">
                {typeLabel(hearing.hearingType)} · {formatDate(hearing.heldOn)} · {roleLabel(role)}
              </p>
              <Link
                href={`/hearings/${hearing.slug}`}
                className="mt-1 block font-serif text-xl text-navy hover:text-ochre"
              >
                {hearing.title}
              </Link>
              <p className="mt-1 text-sm text-muted">{hearing.committee?.name}</p>
            </li>
          ))}
        </ul>
      </section>

      {coAppear.size ? (
        <section>
          <p className="eyebrow">Cross-reference</p>
          <h2 className="mt-2 font-serif text-2xl text-navy">Sat with</h2>
          <ul className="mt-3 space-y-2 text-sm">
            {[...coAppear.values()]
              .sort((a, b) => b.count - a.count)
              .map((row) => (
                <li key={row.slug}>
                  <Link href={`/people/${row.slug}`} className="link">
                    {row.name}
                  </Link>
                  <span className="text-muted">
                    {" "}
                    · {row.count} shared hearing{row.count === 1 ? "" : "s"}
                  </span>
                </li>
              ))}
          </ul>
        </section>
      ) : null}
    </article>
  );
}
