import { NextResponse } from "next/server";
import { getCoverage } from "@/lib/data";
import { postgresAvailable } from "@/lib/db";
import { loadFixtures } from "@/lib/fixtures";

export const dynamic = "force-dynamic";

export async function GET() {
  const fixture = loadFixtures();
  const postgres = await postgresAvailable();
  const coverage = await getCoverage();
  return NextResponse.json({
    ok: true,
    postgres,
    prefersDatabaseUrl: Boolean(process.env.DATABASE_URL),
    coverage,
    fixtureHearings: fixture.hearings.length,
    stage: "2",
  });
}
