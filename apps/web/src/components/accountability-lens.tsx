import Link from "next/link";
import type { NeededHint } from "@/lib/accountability";
import { LENSES } from "@/lib/accountability";

export function AccountabilityNav({ current }: { current: string }) {
  return (
    <nav className="flex flex-wrap gap-x-4 gap-y-1 border-b border-rule pb-3 text-sm">
      {LENSES.map((item) => {
        const active =
          item.match === "exact" ? current === item.href : current === item.href;
        return (
          <Link
            key={item.href}
            href={item.href}
            className={active ? "text-ochre" : "text-navy hover:text-ochre"}
          >
            {item.label}
          </Link>
        );
      })}
    </nav>
  );
}

export function LensNeeded({ needed }: { needed: NeededHint }) {
  return (
    <aside className="border border-rule bg-card px-5 py-4">
      <p className="eyebrow">What this lens needs</p>
      <p className="mt-2 text-sm leading-relaxed text-muted">{needed.note}</p>
      <dl className="mt-3 space-y-1 text-xs text-muted">
        {needed.apply ? (
          <div>
            <dt className="inline font-mono text-navy">apply</dt>
            <dd className="ml-2 inline font-mono">{needed.apply}</dd>
          </div>
        ) : null}
        {needed.sources?.length ? (
          <div>
            <dt className="inline font-mono text-navy">ingest</dt>
            <dd className="ml-2 inline font-mono">{needed.sources.join(", ")}</dd>
          </div>
        ) : null}
        {needed.tables?.length ? (
          <div>
            <dt className="inline font-mono text-navy">tables</dt>
            <dd className="ml-2 inline font-mono">{needed.tables.join(", ")}</dd>
          </div>
        ) : null}
      </dl>
    </aside>
  );
}

export function EmptyRows({
  label,
  needed,
}: {
  label: string;
  needed: NeededHint;
}) {
  return (
    <div className="space-y-4">
      <p className="border border-dashed border-rule bg-paper-2/50 px-5 py-6 text-sm leading-relaxed text-muted">
        No {label} in the current store. That is expected until the listed
        sources write sourced rows. Nothing here is inferred from silence.
      </p>
      <LensNeeded needed={needed} />
    </div>
  );
}
