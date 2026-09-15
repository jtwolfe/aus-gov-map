import { NextResponse } from "next/server";
import { loadInstruments } from "@/lib/accountability";

export const dynamic = "force-dynamic";

export async function GET(request: Request) {
  const url = new URL(request.url);
  const payload = await loadInstruments(url.searchParams.get("q"));
  return NextResponse.json(payload);
}
