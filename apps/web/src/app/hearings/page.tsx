import { HearingCard } from "@/components/hearing-card";
import { loadCatalog } from "@/lib/data";

export const metadata = { title: "Hearings" };

export default async function HearingsPage() {
  const catalog = await loadCatalog();

  return (
    <div className="space-y-8">
      <header>
        <p className="eyebrow">Senate committees + Estimates</p>
        <h1 className="mt-2 font-serif text-4xl text-ink">Hearings</h1>
        <p className="mt-3 max-w-2xl text-muted">
          {catalog.hearings.length} hearing{catalog.hearings.length === 1 ? "" : "s"} in
          the current {catalog.source} set. Live ingest adds rows without
          changing slugs already on disk.
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
