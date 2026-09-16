import Link from "next/link";
import { MiniAtlasChart } from "@/components/mini-atlas-chart";
import { loadAtlas } from "@/lib/atlas";

export async function MiniAtlas({
  person,
  agency,
  instrument,
  lane,
}: {
  person?: string;
  agency?: string;
  instrument?: string;
  lane?: "agency" | "person";
}) {
  const params = new URLSearchParams({ compact: "1" });
  if (person) params.set("person", person);
  if (agency) params.set("agency", agency);
  if (instrument) {
    params.set("instrument", instrument);
    params.set("includeProposed", "1");
  }
  params.set("lane", lane ?? (person ? "person" : "agency"));
  const payload = await loadAtlas(params);
  const href = `/atlas?${new URLSearchParams({
    ...(person ? { person, lane: "person" } : {}),
    ...(agency ? { agency, lane: "agency" } : {}),
    ...(instrument ? { instrument, includeProposed: "1" } : {}),
  }).toString()}`;

  return (
    <section className="border border-rule">
      <div className="flex items-end justify-between gap-3 border-b border-rule px-4 py-3">
        <div>
          <p className="eyebrow">Responsibility Atlas</p>
          <h2 className="mt-1 font-serif text-2xl text-navy">Duty over time</h2>
        </div>
        <Link href={href} className="text-sm text-navy hover:text-ochre">
          Open atlas
        </Link>
      </div>
      {!payload.ready || payload.lanes.length === 0 ? (
        <p className="px-4 py-5 text-sm text-muted">
          No sourced tenures or moments for this filter yet. Sitting in
          Estimates is not a tenure.{" "}
          <Link href="/accountability" className="link">
            Accountability
          </Link>
        </p>
      ) : (
        <MiniAtlasChart payload={payload} />
      )}
    </section>
  );
}
