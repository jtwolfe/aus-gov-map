import { postgresAvailable, query, queryOne, withClient } from "./db";
import { loadFixtures } from "./fixtures";
import type { Board, Pin } from "./types";

const UUID_RE =
  /^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

export function isUuid(value: string): boolean {
  return UUID_RE.test(value);
}

export function slugify(text: string): string {
  const slug = text
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 72);
  return slug || "board";
}

function mapBoard(row: Record<string, unknown>): Board {
  return {
    id: String(row.id),
    slug: String(row.slug),
    title: String(row.title),
    description: (row.description as string | null) ?? null,
  };
}

function mapPin(row: Record<string, unknown>): Pin {
  return {
    id: String(row.id),
    boardId: String(row.board_id),
    pinType: String(row.pin_type),
    targetId: String(row.target_id),
    note: (row.note as string | null) ?? null,
  };
}

export async function listBoards(): Promise<{
  source: "postgres" | "fixture";
  persist: boolean;
  boards: Array<Board & { pinCount: number }>;
}> {
  if (await postgresAvailable()) {
    const rows = await query<Record<string, unknown>>(`
      SELECT b.*, COUNT(p.id)::int AS pin_count
      FROM boards b
      LEFT JOIN pins p ON p.board_id = b.id
      GROUP BY b.id
      ORDER BY b.created_at DESC, b.title
    `);
    return {
      source: "postgres",
      persist: true,
      boards: rows.map((row) => ({
        ...mapBoard(row),
        pinCount: Number(row.pin_count ?? 0),
      })),
    };
  }
  const seed = loadFixtures();
  return {
    source: "fixture",
    persist: false,
    boards: seed.boards.map((board) => ({
      ...board,
      pinCount: seed.pins.filter((p) => p.boardId === board.id).length,
    })),
  };
}

export async function getBoardBySlug(slug: string): Promise<{
  board: Board;
  pins: Pin[];
  persist: boolean;
} | null> {
  if (await postgresAvailable()) {
    const row = await queryOne<Record<string, unknown>>(`SELECT * FROM boards WHERE slug = $1`, [
      slug,
    ]);
    if (!row) return null;
    const pins = await query<Record<string, unknown>>(
      `SELECT * FROM pins WHERE board_id = $1 ORDER BY created_at DESC`,
      [row.id],
    );
    return { board: mapBoard(row), pins: pins.map(mapPin), persist: true };
  }
  const seed = loadFixtures();
  const board = seed.boards.find((b) => b.slug === slug);
  if (!board) return null;
  return {
    board,
    pins: seed.pins.filter((p) => p.boardId === board.id),
    persist: false,
  };
}

export async function createBoard(input: {
  title: string;
  description?: string | null;
}): Promise<Board> {
  if (!(await postgresAvailable())) {
    throw new Error("Postgres is required to create a board");
  }
  const title = input.title.trim();
  if (!title) throw new Error("Title is required");
  const base = slugify(title);
  return withClient(async (client) => {
    let slug = base;
    for (let n = 2; n < 50; n += 1) {
      const exists = await client.query(`SELECT 1 FROM boards WHERE slug = $1`, [slug]);
      if (exists.rowCount === 0) break;
      slug = `${base}-${n}`;
    }
    const inserted = await client.query<Record<string, unknown>>(
      `
      INSERT INTO boards (slug, title, description)
      VALUES ($1, $2, $3)
      RETURNING *
      `,
      [slug, title, input.description?.trim() || null],
    );
    return mapBoard(inserted.rows[0]);
  });
}

export async function ensureDefaultBoard(): Promise<Board> {
  if (!(await postgresAvailable())) {
    throw new Error("Postgres is required to pin");
  }
  const existing = await queryOne<Record<string, unknown>>(
    `SELECT * FROM boards ORDER BY created_at ASC LIMIT 1`,
  );
  if (existing) return mapBoard(existing);
  return createBoard({
    title: "Research",
    description: "Default pinboard for hearings, people, and excerpts.",
  });
}

export async function createPin(input: {
  pinType: string;
  targetId: string;
  note?: string | null;
  boardSlug?: string | null;
  boardId?: string | null;
}): Promise<{ pin: Pin; board: Board; created: boolean }> {
  if (!(await postgresAvailable())) {
    throw new Error("Postgres is required to persist pins");
  }
  const pinType = input.pinType.trim();
  if (!["hearing", "person", "chunk", "document"].includes(pinType)) {
    throw new Error("pinType must be hearing, person, chunk, or document");
  }
  if (!isUuid(input.targetId)) {
    throw new Error("targetId must be a UUID");
  }

  let board: Board | null = null;
  if (input.boardId && isUuid(input.boardId)) {
    const row = await queryOne<Record<string, unknown>>(`SELECT * FROM boards WHERE id = $1`, [
      input.boardId,
    ]);
    if (row) board = mapBoard(row);
  } else if (input.boardSlug) {
    const row = await queryOne<Record<string, unknown>>(`SELECT * FROM boards WHERE slug = $1`, [
      input.boardSlug,
    ]);
    if (row) board = mapBoard(row);
  }
  if (!board) board = await ensureDefaultBoard();

  const existing = await queryOne<Record<string, unknown>>(
    `SELECT * FROM pins WHERE board_id = $1 AND pin_type = $2 AND target_id = $3`,
    [board.id, pinType, input.targetId],
  );
  if (existing) {
    return { pin: mapPin(existing), board, created: false };
  }

  const inserted = await queryOne<Record<string, unknown>>(
    `
    INSERT INTO pins (board_id, pin_type, target_id, note)
    VALUES ($1, $2, $3, $4)
    RETURNING *
    `,
    [board.id, pinType, input.targetId, input.note?.trim() || null],
  );
  if (!inserted) throw new Error("Pin insert failed");
  return { pin: mapPin(inserted), board, created: true };
}

export async function deletePin(id: string): Promise<boolean> {
  if (!(await postgresAvailable())) {
    throw new Error("Postgres is required to delete pins");
  }
  if (!isUuid(id)) return false;
  const rows = await query<{ id: string }>(`DELETE FROM pins WHERE id = $1 RETURNING id`, [id]);
  return rows.length > 0;
}

export async function listPinsForBoard(boardId: string): Promise<Pin[]> {
  if (!(await postgresAvailable())) return [];
  const rows = await query<Record<string, unknown>>(
    `SELECT * FROM pins WHERE board_id = $1 ORDER BY created_at DESC`,
    [boardId],
  );
  return rows.map(mapPin);
}
