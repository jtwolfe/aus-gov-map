import { NextResponse } from "next/server";
import { loadRoleAtDate } from "@/lib/accountability";

export const dynamic = "force-dynamic";

export async function GET(request: Request) {
  const url = new URL(request.url);
  const on = url.searchParams.get("on");
  const person = url.searchParams.get("person");
  const portfolio = url.searchParams.get("portfolio");
  const payload = await loadRoleAtDate(on, person, portfolio);
  return NextResponse.json(payload);
}
