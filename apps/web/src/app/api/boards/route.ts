import { NextResponse } from "next/server";
import { createBoard, listBoards } from "@/lib/boards";

export const dynamic = "force-dynamic";

export async function GET() {
  const result = await listBoards();
  return NextResponse.json(result);
}

export async function POST(request: Request) {
  try {
    const body = (await request.json()) as { title?: string; description?: string };
    const board = await createBoard({
      title: body.title ?? "",
      description: body.description,
    });
    return NextResponse.json({ persist: true, board }, { status: 201 });
  } catch (err) {
    const message = err instanceof Error ? err.message : "Could not create board";
    const status = message.includes("Postgres") ? 503 : 400;
    return NextResponse.json({ error: message, persist: false }, { status });
  }
}
