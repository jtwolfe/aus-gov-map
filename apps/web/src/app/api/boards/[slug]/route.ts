import { NextResponse } from "next/server";
import { getBoardBySlug } from "@/lib/boards";
import { loadCatalog, resolvePinTarget } from "@/lib/data";

export const dynamic = "force-dynamic";

export async function GET(
  _request: Request,
  { params }: { params: Promise<{ slug: string }> },
) {
  const { slug } = await params;
  const result = await getBoardBySlug(slug);
  if (!result) {
    return NextResponse.json({ error: "Board not found" }, { status: 404 });
  }
  const catalog = await loadCatalog();
  const pins = await Promise.all(
    result.pins.map(async (pin) => ({
      ...pin,
      ...(await resolvePinTarget(pin, catalog)),
    })),
  );
  return NextResponse.json({ persist: result.persist, board: result.board, pins });
}
