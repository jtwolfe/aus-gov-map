import { NextResponse } from "next/server";

export async function POST() {
  return NextResponse.json(
    {
      ok: false,
      stub: true,
      message:
        "Server-side pins are a Stage 1 stub. Use the Pin button (localStorage) or seed boards.",
    },
    { status: 501 },
  );
}
