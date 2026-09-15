import { NextResponse } from "next/server";
import { loadQonDebt } from "@/lib/accountability";

export const dynamic = "force-dynamic";

export async function GET() {
  return NextResponse.json(await loadQonDebt());
}
