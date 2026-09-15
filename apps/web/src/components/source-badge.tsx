import { sourceKind, sourceKindLabel } from "@/lib/source";

export function SourceBadge({
  sourceKey,
  className = "",
}: {
  sourceKey?: string | null;
  className?: string;
}) {
  const live = sourceKind(sourceKey) === "live";
  return (
    <span
      className={`inline-flex items-center border px-2 py-0.5 text-[10px] uppercase tracking-[0.14em] ${
        live
          ? "border-eucalyptus/40 bg-eucalyptus/10 text-eucalyptus"
          : "border-rule bg-paper-2 text-muted"
      } ${className}`}
      title={sourceKey ?? undefined}
    >
      {sourceKindLabel(sourceKey)}
    </span>
  );
}
