import Link from "next/link";
import { PersonCard } from "@/components/person-card";
import { loadCatalog } from "@/lib/data";

export const metadata = { title: "People" };
export const dynamic = "force-dynamic";

export default async function PeoplePage() {
  const catalog = await loadCatalog();
  const counts = new Map<string, number>();
  for (const hearing of catalog.hearings) {
    for (const a of hearing.people) {
      counts.set(a.person.id, (counts.get(a.person.id) ?? 0) + 1);
    }
  }

  return (
    <div className="space-y-8">
      <header>
        <p className="eyebrow">Senators, ministers, officials</p>
        <h1 className="mt-2 font-serif text-4xl text-ink">People</h1>
        <p className="mt-3 max-w-2xl text-muted">
          Appearances are the edges of the Stage 1 graph. Open a person for a
          timeline of hearings and who they sat with. An Estimates appearance
          is not a tenure — occupancy lives on Accountability and the Atlas.
        </p>
      </header>
      {!catalog.people.length ? (
        <p className="border border-dashed border-rule bg-paper-2/50 px-5 py-6 text-sm leading-relaxed text-muted">
          No people in the current store. That layer is filled by{" "}
          <span className="font-mono">estimates</span>,{" "}
          <span className="font-mono">handbook</span>, and{" "}
          <span className="font-mono">aps_leaders</span>. Empty is correct — it
          is not a finding.{" "}
          <Link href="/accountability" className="link">
            Accountability
          </Link>
        </p>
      ) : null}
      <div className="grid gap-3 sm:grid-cols-2">
        {catalog.people.map((person) => (
          <PersonCard
            key={person.id}
            person={person}
            meta={
              counts.get(person.id)
                ? `${counts.get(person.id)} hearing${counts.get(person.id) === 1 ? "" : "s"}`
                : undefined
            }
          />
        ))}
      </div>
    </div>
  );
}
