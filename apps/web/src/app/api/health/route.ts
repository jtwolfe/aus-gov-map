import { NextResponse } from "next/server";
import { postgresAvailable } from "@/lib/db";
import { loadFixtures } from "@/lib/fixtures";

export async function GET() {
  const fixture = loadFixtures();
  const postgres = await postgresAvailable();
  return NextResponse.json({
    ok: true,
    postgres,
    fixtureHearings: fixture.hearings.length,
    stage: 1,
  });
}
