import { NextResponse } from "next/server";
import { searchCatalog } from "@/lib/search";
import type { SearchMode } from "@/lib/types";

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const q = searchParams.get("q") ?? "";
  const rawMode = searchParams.get("mode") ?? "combined";
  const mode = (["keyword", "semantic", "combined"].includes(rawMode)
    ? rawMode
    : "combined") as SearchMode;
  const result = await searchCatalog(q, mode);
  return NextResponse.json(result);
}
