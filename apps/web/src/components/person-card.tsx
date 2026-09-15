import Link from "next/link";
import type { Person } from "@/lib/types";

export function PersonCard({
  person,
  meta,
}: {
  person: Person;
  meta?: string;
}) {
  return (
    <article className="border border-rule bg-card p-4">
      <p className="eyebrow">{person.roleTitle ?? "Participant"}</p>
      <h3 className="mt-1 font-serif text-lg text-navy">
        <Link href={`/people/${person.slug}`} className="hover:text-ochre">
          {person.name}
        </Link>
      </h3>
      <p className="mt-1 text-sm text-muted">
        {[person.party, person.organisation, meta].filter(Boolean).join(" · ")}
      </p>
    </article>
  );
}
