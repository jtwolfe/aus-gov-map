import { PersonCard } from "@/components/person-card";
import { loadCatalog } from "@/lib/data";

export const metadata = { title: "People" };

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
          Appearances are the edges of the Stage 1 graph. Open a person to see
          every hearing they sit on in this seed.
        </p>
      </header>
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
