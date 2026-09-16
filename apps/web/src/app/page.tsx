import Link from "next/link";
import { CoverageStrip } from "@/components/coverage-strip";
import { HearingCard } from "@/components/hearing-card";
import { PersonCard } from "@/components/person-card";
import { SearchForm } from "@/components/search-form";
import { getCoverage, loadCatalog } from "@/lib/data";

export const dynamic = "force-dynamic";

export default async function HomePage() {
  const [catalog, coverage] = await Promise.all([loadCatalog(), getCoverage()]);
  const hearings = catalog.hearings.slice(0, 3);
  const people = catalog.people.slice(0, 6);

  return (
    <div className="space-y-16">
      <section className="max-w-3xl pt-4">
        <p className="eyebrow">Australian Commonwealth · public record</p>
        <h1 className="mt-3 font-serif text-4xl leading-[1.15] text-ink sm:text-5xl">
          A living map of federal public data
        </h1>
        <p className="mt-5 max-w-2xl text-lg leading-relaxed text-muted">
          Stage 1 follows Senate committees and Estimates hearings. Stage 2
          adds a sourced duty map — who held office when, and which
          instrument they were accountable or responsible for. When{" "}
          <span className="font-mono">DATABASE_URL</span> is up, search and
          pages read live Postgres — not the offline fixture.
        </p>
        <div className="mt-8">
          <SearchForm committees={catalog.committees} />
        </div>
      </section>

      <CoverageStrip coverage={coverage} />

      <section>
        <div className="mb-5 flex items-end justify-between">
          <div>
            <p className="eyebrow">The record</p>
            <h2 className="font-serif text-2xl text-navy">Recent hearings</h2>
          </div>
          <Link href="/hearings" className="text-sm text-navy hover:text-ochre">
            All hearings
          </Link>
        </div>
        <div className="grid gap-4">
          {hearings.map((hearing) => (
            <HearingCard key={hearing.id} hearing={hearing} />
          ))}
        </div>
      </section>

      <section>
        <div className="mb-5 flex items-end justify-between">
          <div>
            <p className="eyebrow">Who was involved</p>
            <h2 className="font-serif text-2xl text-navy">People</h2>
          </div>
          <Link href="/people" className="text-sm text-navy hover:text-ochre">
            All people
          </Link>
        </div>
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {people.map((person) => (
            <PersonCard key={person.id} person={person} />
          ))}
        </div>
      </section>

      <section className="border border-rule bg-card px-5 py-6">
        <p className="eyebrow">Duty map</p>
        <h2 className="mt-2 font-serif text-2xl text-navy">
          <Link href="/accountability" className="hover:text-ochre">
            Accountability
          </Link>
          <span className="text-muted"> · </span>
          <Link href="/atlas" className="hover:text-ochre">
            Atlas
          </Link>
          <span className="text-muted"> · </span>
          <Link href="/laws" className="hover:text-ochre">
            Laws
          </Link>
        </h2>
        <p className="mt-2 max-w-2xl text-sm leading-relaxed text-muted">
          Search a hearing or person, then step into Accountability lenses,
          the Atlas, or Laws. Lenses stay empty until Handbook, APS leaders,
          QoN, ANAO, Budget, AusTender, or legislation rows land — they do
          not invent conclusions or guilt labels. Sitting in Estimates is
          not a tenure.
        </p>
      </section>

      <section className="grid gap-6 border-t border-rule pt-10 md:grid-cols-3">
        {[
          {
            kicker: "01",
            title: "Ingest",
            body: "Python adapters fetch Estimates schedules and committee pages, chunk text, embed, and upsert idempotently.",
          },
          {
            kicker: "02",
            title: "Store",
            body: "Postgres + pgvector holds documents and vectors. Neo4j holds Person ↔ Hearing ↔ Committee ↔ Topic.",
          },
          {
            kicker: "03",
            title: "Read",
            body: "This map is the reading room: search, dossiers, Accountability lenses, insights, and pinboards that persist in Postgres.",
          },
        ].map((item) => (
          <div key={item.kicker}>
            <p className="eyebrow">{item.kicker}</p>
            <h3 className="mt-2 font-serif text-xl text-navy">{item.title}</h3>
            <p className="mt-2 text-sm leading-relaxed text-muted">{item.body}</p>
          </div>
        ))}
      </section>
    </div>
  );
}
