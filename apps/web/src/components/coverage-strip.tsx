import type { CoverageStats } from "@/lib/types";

export function CoverageStrip({ coverage }: { coverage: CoverageStats }) {
  const items = [
    [coverage.hearings, "hearings"],
    [coverage.people, "people"],
    [coverage.chunks, "chunks"],
  ] as const;

  return (
    <div className="border border-rule bg-card px-4 py-3">
      <div className="flex flex-wrap items-baseline justify-between gap-3">
        <p className="text-sm text-ink">
          <span className="eyebrow mr-2">Current coverage</span>
          Serving from <span className="font-mono">{coverage.source}</span>
          {coverage.source === "postgres"
            ? " — live hearings and people from Postgres."
            : " — Docker Postgres is optional; this is the bundled seed."}
        </p>
        <p className="text-xs text-muted">
          {coverage.liveHearings} live Hansard · {coverage.sampleHearings} sample fixture
        </p>
      </div>
      <dl className="mt-3 grid grid-cols-3 gap-3 text-center sm:max-w-md">
        {items.map(([count, label]) => (
          <div key={label} className="border border-rule/70 bg-paper px-2 py-2">
            <dt className="eyebrow">{label}</dt>
            <dd className="mt-1 font-serif text-2xl text-navy">{count}</dd>
          </div>
        ))}
      </dl>
    </div>
  );
}
