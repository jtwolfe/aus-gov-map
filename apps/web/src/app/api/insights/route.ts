import { NextResponse } from "next/server";
import { loadInsights } from "@/lib/insights";

export const dynamic = "force-dynamic";

export async function GET() {
  const insights = await loadInsights();
  return NextResponse.json(insights);
}
