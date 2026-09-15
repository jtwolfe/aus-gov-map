import { Pool, type PoolClient, type QueryResultRow } from "pg";

let pool: Pool | null = null;

export function databaseUrl(): string | undefined {
  const raw = process.env.DATABASE_URL?.trim();
  return raw || undefined;
}

export function getPool(): Pool | null {
  const url = databaseUrl();
  if (!url) return null;
  if (!pool) {
    pool = new Pool({
      connectionString: url,
      max: 5,
      connectionTimeoutMillis: 1500,
    });
    pool.on("error", () => {
      /* idle client errors should not crash the web process */
    });
  }
  return pool;
}

export async function query<T extends QueryResultRow>(
  text: string,
  params: unknown[] = [],
): Promise<T[]> {
  const client = getPool();
  if (!client) throw new Error("DATABASE_URL is not set");
  const result = await client.query<T>(text, params);
  return result.rows;
}

export async function queryOne<T extends QueryResultRow>(
  text: string,
  params: unknown[] = [],
): Promise<T | null> {
  const rows = await query<T>(text, params);
  return rows[0] ?? null;
}

export async function withClient<T>(fn: (client: PoolClient) => Promise<T>): Promise<T> {
  const clientPool = getPool();
  if (!clientPool) throw new Error("DATABASE_URL is not set");
  const client = await clientPool.connect();
  try {
    return await fn(client);
  } finally {
    client.release();
  }
}

export async function postgresAvailable(): Promise<boolean> {
  if (!databaseUrl()) return false;
  try {
    const rows = await query<{ ok: number }>("SELECT 1 AS ok");
    return rows[0]?.ok === 1;
  } catch {
    return false;
  }
}

/** Prefer live Postgres whenever DATABASE_URL reaches a healthy server. */
export async function usePostgres(): Promise<boolean> {
  return postgresAvailable();
}
