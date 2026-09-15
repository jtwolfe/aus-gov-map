import type { DataSource } from "./types";

/** Live APH Officials use `hansard:` keys; fixture/sample rows use `estimates:` / `senate_committee:` / `doc:`. */
export function isLiveSourceKey(sourceKey: string | null | undefined): boolean {
  return Boolean(sourceKey && sourceKey.startsWith("hansard:"));
}

export function sourceKind(sourceKey: string | null | undefined): "live" | "sample" {
  return isLiveSourceKey(sourceKey) ? "live" : "sample";
}

export function sourceKindLabel(sourceKey: string | null | undefined): string {
  return isLiveSourceKey(sourceKey) ? "Live Hansard" : "Sample fixture";
}

export function catalogServingLabel(source: DataSource): string {
  return source === "postgres" ? "postgres" : "fixture";
}

export const COMMONWEALTH_ATTRIBUTION =
  "Official Hansard / committee / Estimates records are typically © Commonwealth of Australia and often CC BY-NC-ND. Attribute the Parliament of Australia. This project is framed as research / non-commercial.";

export const FIXTURE_ATTRIBUTION =
  "This text is invented sample Official in the repo fixture. It is not a parliamentary transcript.";
