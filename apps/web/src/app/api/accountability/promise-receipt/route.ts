import { NextResponse } from "next/server";
import { loadPromiseReceipt } from "@/lib/accountability";

export const dynamic = "force-dynamic";

export async function GET() {
  return NextResponse.json(await loadPromiseReceipt());
}
