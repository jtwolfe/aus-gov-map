import Link from "next/link";
import { SourceBadge } from "@/components/source-badge";
import { formatDate, typeLabel } from "@/lib/format";
import type { Hearing } from "@/lib/types";

export function HearingCard({ hearing }: { hearing: Hearing }) {
  return (
    <article className="group border-l-2 border-navy bg-card px-5 py-4 shadow-[0_1px_0_rgba(28,25,21,0.04)]">
      <div className="flex flex-wrap items-center gap-2 text-[11px] uppercase tracking-[0.14em] text-muted">
        <SourceBadge sourceKey={hearing.sourceKey} />
        <span className="text-ochre">{typeLabel(hearing.hearingType)}</span>
        <span>·</span>
        <span>{formatDate(hearing.heldOn)}</span>
        {hearing.committee ? (
          <>
            <span>·</span>
            <span>{hearing.committee.name}</span>
          </>
        ) : null}
      </div>
      <h3 className="mt-2 font-serif text-xl leading-snug text-navy group-hover:text-ochre">
        <Link href={`/hearings/${hearing.slug}`}>{hearing.title}</Link>
      </h3>
      {hearing.summary ? (
        <p className="mt-2 text-sm leading-relaxed text-muted">{hearing.summary}</p>
      ) : null}
      <ul className="mt-3 flex flex-wrap gap-x-3 gap-y-1 text-sm">
        {hearing.people.slice(0, 4).map((a) => (
          <li key={`${a.person.id}-${a.role}`}>
            <Link href={`/people/${a.person.slug}`} className="text-eucalyptus hover:underline">
              {a.person.name.replace(/^Senator (the Hon )?/, "")}
            </Link>
          </li>
        ))}
      </ul>
    </article>
  );
}
