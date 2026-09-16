import { NextResponse } from "next/server";
import { loadAtlas } from "@/lib/atlas";

export const dynamic = "force-dynamic";

export async function GET(request: Request) {
  const url = new URL(request.url);
  const payload = await loadAtlas(url.searchParams);
  return NextResponse.json(payload);
}
