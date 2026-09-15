import { NextResponse } from "next/server";
import { loadAccountabilitySummary } from "@/lib/accountability";

export const dynamic = "force-dynamic";

export async function GET() {
  const summary = await loadAccountabilitySummary();
  return NextResponse.json({
    ...summary,
    realVsProposed: {
      handbook: "real (Handbook API / fixture fallback)",
      estimatesSegments: "real Official text, derived structure",
      qon: "best-effort real EQON (live or fixture)",
      anao: "best-effort real work index / fixture fallback",
      budgetMeasure: "best-effort BP2 DOCX + PBS CSV (PDF follow-up)",
      austender: "best-effort OCDS / fixture fallback",
      instrumentsProposed: "regex from Officials — proposed only",
      agencies: "official names, stub rows (no secretaries)",
    },
  });
}
