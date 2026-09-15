import { createHash } from "node:crypto";

const TOKEN = /[a-z0-9']+/g;

/** Same hashed bag-of-tokens vector as `aus_gov_ingest.embeddings.hash.HashEmbedder`. */
export function hashEmbed(text: string, dim = 384): number[] {
  const vec = new Array<number>(dim).fill(0);
  const tokens = text.toLowerCase().match(TOKEN) ?? [];
  if (!tokens.length) {
    vec[0] = 1;
    return vec;
  }
  for (const token of tokens) {
    const digest = createHash("sha256").update(token, "utf8").digest();
    const idx = digest.readUInt32LE(0) % dim;
    const sign = digest[4] % 2 === 0 ? 1 : -1;
    vec[idx] += sign;
  }
  const norm = Math.sqrt(vec.reduce((sum, v) => sum + v * v, 0)) || 1;
  return vec.map((v) => v / norm);
}

export function vectorLiteral(values: number[]): string {
  return `[${values.map((v) => v.toFixed(8)).join(",")}]`;
}
