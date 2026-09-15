import { NextResponse } from "next/server";
import { createPin, deletePin, listBoards } from "@/lib/boards";

export const dynamic = "force-dynamic";

export async function GET() {
  const boards = await listBoards();
  return NextResponse.json({
    persist: boards.persist,
    source: boards.source,
    boards: boards.boards,
  });
}

export async function POST(request: Request) {
  try {
    const body = (await request.json()) as {
      pinType?: string;
      targetId?: string;
      note?: string;
      boardSlug?: string;
      boardId?: string;
    };
    const result = await createPin({
      pinType: body.pinType ?? "",
      targetId: body.targetId ?? "",
      note: body.note,
      boardSlug: body.boardSlug,
      boardId: body.boardId,
    });
    return NextResponse.json(
      { persist: true, ...result },
      { status: result.created ? 201 : 200 },
    );
  } catch (err) {
    const message = err instanceof Error ? err.message : "Could not pin";
    const status = message.includes("Postgres") ? 503 : 400;
    return NextResponse.json({ ok: false, persist: false, error: message }, { status });
  }
}

export async function DELETE(request: Request) {
  const { searchParams } = new URL(request.url);
  const id = searchParams.get("id") ?? "";
  try {
    const ok = await deletePin(id);
    return NextResponse.json({ ok, persist: true }, { status: ok ? 200 : 404 });
  } catch (err) {
    const message = err instanceof Error ? err.message : "Could not delete pin";
    const status = message.includes("Postgres") ? 503 : 400;
    return NextResponse.json({ ok: false, persist: false, error: message }, { status });
  }
}
