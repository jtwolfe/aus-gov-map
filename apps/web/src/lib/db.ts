import { Pool, type PoolClient, type QueryResultRow } from "pg";

let pool: Pool | null = null;

export function databaseUrl(): string | undefined {
  return process.env.DATABASE_URL;
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
  try {
    const rows = await query<{ ok: number }>("SELECT 1 AS ok");
    return rows[0]?.ok === 1;
  } catch {
    return false;
  }
}
