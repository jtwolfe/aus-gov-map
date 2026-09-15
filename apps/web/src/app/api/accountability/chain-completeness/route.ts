import { NextResponse } from "next/server";
import { loadChainCompleteness } from "@/lib/accountability";

export const dynamic = "force-dynamic";

export async function GET() {
  return NextResponse.json(await loadChainCompleteness());
}
