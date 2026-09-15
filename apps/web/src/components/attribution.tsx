import { COMMONWEALTH_ATTRIBUTION, FIXTURE_ATTRIBUTION, isLiveSourceKey } from "@/lib/source";

export function Attribution({
  sourceKey,
  sourceUrl,
  licenseNote,
}: {
  sourceKey?: string | null;
  sourceUrl?: string | null;
  licenseNote?: string | null;
}) {
  const live = isLiveSourceKey(sourceKey);
  return (
    <div className="border border-rule bg-card px-4 py-3 text-sm leading-relaxed text-muted">
      <p className="eyebrow">{live ? "Attribution" : "Sample record"}</p>
      <p className="mt-2">{licenseNote || (live ? COMMONWEALTH_ATTRIBUTION : FIXTURE_ATTRIBUTION)}</p>
      {sourceKey ? (
        <p className="mt-2 font-mono text-xs">
          source_key · {sourceKey}
        </p>
      ) : null}
      {sourceUrl ? (
        <p className="mt-2">
          <a href={sourceUrl} className="link" rel="noreferrer">
            Official source
          </a>
        </p>
      ) : null}
    </div>
  );
}
