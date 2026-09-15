import { HearingCard } from "@/components/hearing-card";
import { getCoverage, loadCatalog } from "@/lib/data";

export const metadata = { title: "Hearings" };
export const dynamic = "force-dynamic";

export default async function HearingsPage() {
  const [catalog, coverage] = await Promise.all([loadCatalog(), getCoverage()]);

  return (
    <div className="space-y-8">
      <header>
        <p className="eyebrow">Senate committees + Estimates</p>
        <h1 className="mt-2 font-serif text-4xl text-ink">Hearings</h1>
        <p className="mt-3 max-w-2xl text-muted">
          {coverage.hearings} hearing{coverage.hearings === 1 ? "" : "s"} in
          the current {coverage.source} set
          {coverage.source === "postgres"
            ? ` (${coverage.liveHearings} live Hansard · ${coverage.sampleHearings} sample).`
            : "."}{" "}
          Live ingest upserts on <span className="font-mono">source_key</span>.
        </p>
      </header>
      <div className="grid gap-4">
        {catalog.hearings.map((hearing) => (
          <HearingCard key={hearing.id} hearing={hearing} />
        ))}
      </div>
    </div>
  );
}
