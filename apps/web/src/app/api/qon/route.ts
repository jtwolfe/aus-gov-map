import { NextResponse } from "next/server";
import { loadQon } from "@/lib/accountability";

export const dynamic = "force-dynamic";

export async function GET(request: Request) {
  const url = new URL(request.url);
  const limit = Math.min(Number(url.searchParams.get("limit") || 40), 200);
  const payload = await loadQon(limit);
  const portfolio = url.searchParams.get("portfolio");
  const questions = portfolio
    ? payload.questions.filter(
        (row) => (row.portfolio || "").toLowerCase() === portfolio.toLowerCase(),
      )
    : payload.questions;
  return NextResponse.json({ ...payload, questions });
}
